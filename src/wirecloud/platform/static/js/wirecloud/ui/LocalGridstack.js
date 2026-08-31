// Lightweight local reimplementation of GridStack API used by GridstackLayout.js
// Provides init(options, container) -> grid instance with methods used by the codebase.

console.log('LocalGridstack loaded');

class LocalGridStack {
    constructor(opts = {}, container) {
        this.options = opts || {};
        this.container = container || document.body;
        this.baseColumns = this.options.column || 12;
        this.baseCellHeight = this.options.cellHeight || 20;
        this.cellHeight = this.baseCellHeight;
        this.maxRow = this.options.maxRow || 0;
        // responsive breakpoints: array of {maxWidth, columns, cellHeightMultiplier}
        this.breakpoints = this.options.responsive || [
            {maxWidth: 480, columns: 1, cellHeightMultiplier: 1},
            {maxWidth: 768, columns: 2, cellHeightMultiplier: 1},
            {maxWidth: 1024, columns: 3, cellHeightMultiplier: 1},
            {maxWidth: Infinity, columns: this.baseColumns, cellHeightMultiplier: 1}
        ];
        this._currentColumns = this.baseColumns;
        this.items = new Map(); // el -> node
        this.listeners = {};
        this._dragState = null;
        this._resizeState = null;
        this._rafPending = false;
        this._pendingMove = null;
        this._badgeThrottleMs = 80; // ms

        // ensure container is positioned
        const style = window.getComputedStyle(this.container);
        if (style.position === 'static' || !style.position) {
            this.container.style.position = 'relative';
        }

        // pointer capturing across document for drag/resize
        this._onPointerMove = this._onPointerMove.bind(this);
        this._onPointerUp = this._onPointerUp.bind(this);
    }

    _emit(event, ...args) {
        const handlers = this.listeners[event] || [];
        handlers.forEach((h) => h(...args));
    }

    on(event, handler) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(handler);
        return this;
    }

    _computeLayoutFromWidth(width) {
        // determine columns and cellHeight multiplier from breakpoints
        let cols = this.baseColumns;
        let multiplier = 1;
        for (let i = 0; i < this.breakpoints.length; i++) {
            const bp = this.breakpoints[i];
            if (width <= bp.maxWidth) {
                cols = bp.columns;
                multiplier = bp.cellHeightMultiplier || 1;
                break;
            }
        }
        return {cols, multiplier};
    }

    _getCellSizes() {
        const width = Math.max(1, this.container.clientWidth);
        const layout = this._computeLayoutFromWidth(width);
        // update current columns and cell height
        this._currentColumns = layout.cols;
        this.cellHeight = Math.round(this.baseCellHeight * layout.multiplier);

        const cellW = width / Math.max(1, this._currentColumns);
        const cellH = this.cellHeight;
        return {cellW, cellH, width};
    }

    _applyPositionToElement(el, node) {
        const {cellW, cellH} = this._getCellSizes();
        el.style.position = 'absolute';
        el.style.left = Math.round(node.x * cellW) + 'px';
        el.style.top = Math.round(node.y * cellH) + 'px';
        el.style.width = Math.round(node.w * cellW) + 'px';
        el.style.height = Math.round(node.h * cellH) + 'px';
        el.setAttribute('gs-x', String(node.x));
        el.setAttribute('gs-y', String(node.y));
        el.setAttribute('gs-w', String(node.w));
        el.setAttribute('gs-h', String(node.h));
    }

    makeWidget(el, node) {
        if (!el) return;
        console.log('LocalGridstack.makeWidget', el && el.getAttribute && el.getAttribute('data-id'));
        const parsed = Object.assign({}, {x:0,y:0,w:1,h:1}, node || {});
        // If already present, update node and reapply
        if (this.items.has(el)) {
            const current = this.items.get(el);
            Object.assign(current, parsed);
            this._applyPositionToElement(el, current);
            el.gridstackNode = current;
            return this;
        }
        this.items.set(el, parsed);
        el.classList.add('grid-stack-item');
        // mark element as having a gridstack node so external code knows
        el.gridstackNode = parsed;
        this._applyPositionToElement(el, parsed);
        // attach handlers
        this._attachDragHandle(el);
        this._attachResizeHandle(el);
        // create a small debug badge showing grid status
        this._ensureDebugBadge(el);
        this._updateDebugBadge(el);
        return this;
    }

    update(el, node) {
        if (!el || !this.items.has(el)) return this;
        const current = this.items.get(el);
        const updated = Object.assign({}, current, node);
        this.items.set(el, updated);
        this._applyPositionToElement(el, updated);
        return this;
    }

    removeWidget(el) {
        if (!el) return this;
        this._detachHandlers(el);
        this.items.delete(el);
        if (el.parentNode === this.container) {
            // leave DOM element as-is; GridstackLayout expects removeWidget to keep element
        }
        return this;
    }

    movable(el, enabled) {
        if (!el) return this;
        if (enabled) {
            el.setAttribute('data-local-gs-movable', 'true');
        } else {
            el.setAttribute('data-local-gs-movable', 'false');
        }
        if (el) this._updateDebugBadge(el);
        return this;
    }

    resizable(el, enabled) {
        if (!el) return this;
        if (enabled) {
            el.setAttribute('data-local-gs-resizable', 'true');
            this._ensureResizeHandle(el);
        } else {
            el.setAttribute('data-local-gs-resizable', 'false');
            this._removeResizeHandle(el);
        }
        if (el) this._updateDebugBadge(el);
        return this;
    }

    onResize(width) {
        // called when container width changes; recompute columns/cellHeight and reapply positions
        const currentWidth = typeof width === 'number' ? width : this.container.clientWidth;
        const layout = this._computeLayoutFromWidth(currentWidth);
        const newCols = layout.cols;
        const newCellHeight = Math.round(this.baseCellHeight * (layout.multiplier || 1));
        const colsChanged = newCols !== this._currentColumns;
        const cellHeightChanged = newCellHeight !== this.cellHeight;

        this._currentColumns = newCols;
        this.cellHeight = newCellHeight;

        // Reapply positions and sizes to all items
        this.items.forEach((node, el) => {
            // If reducing columns, ensure x does not overflow
            if (node.x + node.w > this._currentColumns) {
                node.x = Math.max(0, this._currentColumns - node.w);
            }
            this._applyPositionToElement(el, node);
        });

        // emit a resize event if layout changed
        if (colsChanged || cellHeightChanged) {
            this._emit('resize', {columns: this._currentColumns, cellHeight: this.cellHeight});
        }
    }

    _attachDragHandle(el) {
        // use the provided handle selector if available
        const handleSelector = (this.options.draggable && this.options.draggable.handle) || null;
        let handle = handleSelector ? el.querySelector(handleSelector) : el;
        if (!handle) handle = el;

        const startDrag = (e) => {
            // ignore right click
            if (e.button && e.button !== 0) return;
            // respect Gridstack 'no-move' attribute as well
            if (el.getAttribute('data-local-gs-movable') === 'false' || el.getAttribute('gs-no-move') === 'true') return;
            e.preventDefault();
            const rect = el.getBoundingClientRect();
            // hide debug badge for performance
            if (el && el._localGsDebugBadge) {
                el._localGsBadgeWasHidden = el._localGsDebugBadge.style.display === 'none';
                el._localGsDebugBadge.style.display = 'none';
            }
            this._dragState = {
                el: el,
                startX: e.clientX,
                startY: e.clientY,
                origLeft: rect.left - this.container.getBoundingClientRect().left,
                origTop: rect.top - this.container.getBoundingClientRect().top
            };
            console.log('LocalGridstack startDrag', el && el.getAttribute && el.getAttribute('data-id'), e.clientX, e.clientY);
            document.addEventListener('pointermove', this._onPointerMove);
            document.addEventListener('pointerup', this._onPointerUp);
        };

        handle.addEventListener('pointerdown', startDrag);
        // store reference for detach
        el._localGsHandle = {handle, startDrag};
            el.dataset.localGsDraggable = 'true';
    }

    _attachResizeHandle(el) {
        this._ensureResizeHandle(el);
    }

    _ensureResizeHandle(el) {
        if (el._localGsResize) return;
        const handle = document.createElement('div');
        handle.className = 'local-gs-resize-handle';
        // basic inline styling to make it visible and clickable
        handle.style.position = 'absolute';
        handle.style.width = '12px';
        handle.style.height = '12px';
        handle.style.right = '2px';
        handle.style.bottom = '2px';
        handle.style.cursor = 'nwse-resize';
        handle.style.zIndex = '9999';
        el.appendChild(handle);

        const startResize = (e) => {
            // respect Gridstack 'no-resize' attribute as well
            if (el.getAttribute('data-local-gs-resizable') === 'false' || el.getAttribute('gs-no-resize') === 'true') return;
            e.preventDefault();
            const rect = el.getBoundingClientRect();
            // store previous min styles and disable them so shrinking is possible
            try {
                el._prevMinWidth = el.style.minWidth || '';
                el._prevMinHeight = el.style.minHeight || '';
                el.style.minWidth = '0px';
                el.style.minHeight = '0px';
            } catch (err) {
                // ignore
            }
            // hide debug badge for performance
            if (el && el._localGsDebugBadge) {
                el._localGsBadgeWasHidden = el._localGsDebugBadge.style.display === 'none';
                el._localGsDebugBadge.style.display = 'none';
            }
            this._resizeState = {
                el: el,
                startX: e.clientX,
                startY: e.clientY,
                origW: rect.width,
                origH: rect.height
            };
            console.log('LocalGridstack startResize', el && el.getAttribute && el.getAttribute('data-id'), e.clientX, e.clientY);
            document.addEventListener('pointermove', this._onPointerMove);
            document.addEventListener('pointerup', this._onPointerUp);
        };

        handle.addEventListener('pointerdown', startResize);
        el._localGsResize = {handle, startResize};
        el.dataset.localGsResizable = 'true';
    }

    _removeResizeHandle(el) {
        if (!el._localGsResize) return;
        const {handle, startResize} = el._localGsResize;
        handle.removeEventListener('pointerdown', startResize);
        if (handle.parentNode === el) el.removeChild(handle);
        delete el._localGsResize;
    }

    _ensureDebugBadge(el) {
        if (el._localGsDebugBadge) return;
        const badge = document.createElement('div');
        badge.className = 'local-gs-debug-badge';
        badge.style.position = 'absolute';
        badge.style.left = '2px';
        badge.style.top = '2px';
        badge.style.background = 'rgba(0,0,0,0.6)';
        badge.style.color = 'white';
        badge.style.fontSize = '10px';
        badge.style.padding = '2px 4px';
        badge.style.zIndex = '10000';
        badge.style.pointerEvents = 'none';
        el.appendChild(badge);
        el._localGsDebugBadge = badge;
    }

    _updateDebugBadge(el) {
        if (!el._localGsDebugBadge) return;
        // throttle badge updates per element
        try {
            const now = Date.now();
            if (el._localGsBadgeLastTime && (now - el._localGsBadgeLastTime) < this._badgeThrottleMs) return;
            el._localGsBadgeLastTime = now;
        } catch (e) {
            // ignore
        }
        const attrs = {
            data_local_gs_movable: el.getAttribute('data-local-gs-movable'),
            data_local_gs_resizable: el.getAttribute('data-local-gs-resizable'),
            data_local_gs_draggable: el.dataset.localGsDraggable,
            data_local_gs_resizable_flag: el.dataset.localGsResizable,
            gs_no_move: el.getAttribute('gs-no-move'),
            gs_no_resize: el.getAttribute('gs-no-resize')
        };
        const node = el.gridstackNode || {};
        el._localGsDebugBadge.textContent = `mv:${attrs.data_local_gs_movable||''} rsz:${attrs.data_local_gs_resizable||''} d:${attrs.data_local_gs_draggable||''} nr:${attrs.data_local_gs_resizable_flag||''} no-m:${attrs.gs_no_move||''} no-r:${attrs.gs_no_resize||''} n:${node.x||0},${node.y||0},${node.w||0}x${node.h||0}`;
    }

    _removeDebugBadge(el) {
        if (!el._localGsDebugBadge) return;
        const b = el._localGsDebugBadge;
        if (b.parentNode === el) el.removeChild(b);
        delete el._localGsDebugBadge;
        delete el.dataset.localGsResizable;
    }

    _detachHandlers(el) {
        if (el._localGsHandle) {
            const {handle, startDrag} = el._localGsHandle;
            handle.removeEventListener('pointerdown', startDrag);
            delete el._localGsHandle;
            delete el.dataset.localGsDraggable;
        }
        this._removeResizeHandle(el);
    }

    _onPointerMove(e) {
        // Throttle DOM updates via requestAnimationFrame to avoid flooding the main thread
        if (this._dragState) {
            const ds = this._dragState;
            this._pendingMove = {type: 'drag', clientX: e.clientX, clientY: e.clientY, ds};
        } else if (this._resizeState) {
            const rs = this._resizeState;
            this._pendingMove = {type: 'resize', clientX: e.clientX, clientY: e.clientY, rs};
        } else {
            return;
        }

        if (this._rafPending) return;
        this._rafPending = true;
        requestAnimationFrame(() => {
            const pm = this._pendingMove;
            if (pm && pm.type === 'drag') {
                const ds = pm.ds;
                const dx = pm.clientX - ds.startX;
                const dy = pm.clientY - ds.startY;
                const newLeft = Math.max(0, ds.origLeft + dx);
                const newTop = Math.max(0, ds.origTop + dy);
                ds.el.style.left = newLeft + 'px';
                ds.el.style.top = newTop + 'px';
                if (ds.el && ds.el._localGsDebugBadge) this._updateDebugBadge(ds.el);
            } else if (pm && pm.type === 'resize') {
                const rs = pm.rs;
                const dx = pm.clientX - rs.startX;
                const dy = pm.clientY - rs.startY;
                const newW = Math.max(10, rs.origW + dx);
                const newH = Math.max(10, rs.origH + dy);
                rs.el.style.width = newW + 'px';
                rs.el.style.height = newH + 'px';
                if (rs.el && rs.el._localGsDebugBadge) this._updateDebugBadge(rs.el);
            }
            this._pendingMove = null;
            this._rafPending = false;
        });
    }

    _onPointerUp(e) {
        if (this._dragState) {
            const ds = this._dragState;
            const rect = ds.el.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();
            const relLeft = Math.max(0, rect.left - containerRect.left);
            const relTop = Math.max(0, rect.top - containerRect.top);
            const {cellW, cellH} = this._getCellSizes();
            const x = Math.max(0, Math.round(relLeft / cellW));
            const y = Math.max(0, Math.round(relTop / cellH));
            const node = this.items.get(ds.el) || {w:1,h:1};
            node.x = x; node.y = y;
            this.items.set(ds.el, node);
            // apply snapped position
            this._applyPositionToElement(ds.el, node);
            document.removeEventListener('pointermove', this._onPointerMove);
            document.removeEventListener('pointerup', this._onPointerUp);
            this._dragState = null;
            // update debug badge and log
            console.log('LocalGridstack drop', ds.el && ds.el.getAttribute && ds.el.getAttribute('data-id'), node.x, node.y, node.w, node.h);
            if (ds.el && ds.el._localGsDebugBadge) {
                // restore badge visibility
                try {
                    if (!ds.el._localGsBadgeWasHidden) ds.el._localGsDebugBadge.style.display = '';
                } catch (e) {}
                this._updateDebugBadge(ds.el);
            }
            // emit change event
            this._emit('change', [{x: node.x, y: node.y, w: node.w, h: node.h, el: ds.el}]);
            return;
        }
        if (this._resizeState) {
            const rs = this._resizeState;
            const rect = rs.el.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();
            const relLeft = Math.max(0, rect.left - containerRect.left);
            const relTop = Math.max(0, rect.top - containerRect.top);
            const {cellW, cellH} = this._getCellSizes();
            const w = Math.max(1, Math.round(rect.width / cellW));
            const h = Math.max(1, Math.round(rect.height / cellH));
            const node = this.items.get(rs.el) || {x:0,y:0};
            node.w = w; node.h = h;
            this.items.set(rs.el, node);
            this._applyPositionToElement(rs.el, node);
            document.removeEventListener('pointermove', this._onPointerMove);
            document.removeEventListener('pointerup', this._onPointerUp);
            this._resizeState = null;
            console.log('LocalGridstack resizeend', rs.el && rs.el.getAttribute && rs.el.getAttribute('data-id'), node.w, node.h);
            // restore min styles and badge visibility
            try {
                if (rs.el && rs.el._prevMinWidth !== undefined) rs.el.style.minWidth = rs.el._prevMinWidth || '';
                if (rs.el && rs.el._prevMinHeight !== undefined) rs.el.style.minHeight = rs.el._prevMinHeight || '';
            } catch (e) {}
            if (rs.el && rs.el._localGsDebugBadge) {
                try {
                    if (!rs.el._localGsBadgeWasHidden) rs.el._localGsDebugBadge.style.display = '';
                } catch (e) {}
                this._updateDebugBadge(rs.el);
            }
            this._emit('change', [{x: node.x, y: node.y, w: node.w, h: node.h, el: rs.el}]);
            return;
        }
    }
}

export const GridStack = {
    init: function(options, container) {
        return new LocalGridStack(options, container);
    }
};
