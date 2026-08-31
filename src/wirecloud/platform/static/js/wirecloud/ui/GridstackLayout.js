// -*- coding: utf-8 -*-
// Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

// This file is part of Wirecloud.

// Wirecloud is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Wirecloud is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

/* globals Wirecloud */

import { GridStack } from './LocalGridstack';

(function (ns, utils) {

    "use strict";

    const _ensureGridstackLayout = () => {
        if (ns.GridstackLayout) {
            return;
        }
        if (typeof ns.DragboardLayout === 'undefined') {
            // Delay definition until DragboardLayout is available
            setTimeout(_ensureGridstackLayout, 0);
            return;
        }

    "use strict";

    const on_grid_change = function on_grid_change(_event, items) {
        if (this.syncing || !Array.isArray(items) || !items.length) {
            return;
        }

        const changedWidgets = [];

        items.forEach((item) => {
            const widget = item.el && item.el._wirecloudWidget;
            if (!widget) {
                return;
            }

            if (widget._gridstackSyncing) {
                return;
            }

            widget._gridstackSyncing = true;
            widget.setPosition({
                x: item.x,
                y: item.y,
                z: widget.position.z
            });
            widget.setShape({
                width: item.w,
                height: item.h
            }, false, false, false, true);
            widget._gridstackSyncing = false;
            changedWidgets.push(widget.id);
        });

        if (changedWidgets.length > 0) {
            this.dragboard.update(changedWidgets);
        }
    };

    ns.GridstackLayout = class GridstackLayout extends ns.DragboardLayout {

        constructor(dragboard, columns, cellHeight, verticalMargin, horizontalMargin, maxRow) {
            super(dragboard);

            this.initialized = false;
            this.grid = null;
            this.columns = columns;
            this.cellHeight = cellHeight;
            this.maxRow = maxRow;
            this.syncing = false;
            this.leftMargin = Math.floor(horizontalMargin / 2);
            this.rightMargin = horizontalMargin - this.leftMargin;
            this.topMargin = Math.floor(verticalMargin / 2);
            this.bottomMargin = verticalMargin - this.topMargin;
        }

        fromPixelsToVCells(pixels) {
            return pixels > 0 ? (pixels / this.cellHeight) : 0;
        }

        fromVCellsToPixels(cells) {
            return Math.round(cells * this.cellHeight);
        }

        getWidthInPixels(cells, width) {
            return Math.round(((width || this.getWidth()) * cells) / this.columns);
        }

        getHeightInPixels(cells) {
            return Math.round(cells * this.cellHeight);
        }

        fromPixelsToHCells(pixels, width) {
            if (pixels <= 0) {
                return 0;
            }

            return Math.round((pixels * this.columns) / (width || this.getWidth()));
        }

        fromHCellsToPixels(cells, width) {
            return Math.round(((width || this.getWidth()) * cells) / this.columns);
        }

        adaptColumnOffset(size, width) {
            let offsetInLU, pixels;

            const parsedSize = this.parseSize(size);
            if (parsedSize[1] === 'cells') {
                offsetInLU = Math.round(parsedSize[0]);
            } else {
                if (parsedSize[1] === '%') {
                    pixels = Math.round((parsedSize[0] * (width || this.getWidth())) / 100);
                } else {
                    pixels = parsedSize[0] < this.dragboard.leftMargin ? 0 : parsedSize[0] - this.dragboard.leftMargin;
                }
                offsetInLU = this.fromPixelsToHCells(pixels, width);
            }

            return new Wirecloud.ui.MultiValuedSize(this.getColumnOffset({x: offsetInLU}, width), offsetInLU);
        }

        adaptRowOffset(size) {
            let offsetInLU, pixels;

            const parsedSize = this.parseSize(size);
            if (parsedSize[1] === 'cells') {
                offsetInLU = Math.round(parsedSize[0]);
            } else {
                if (parsedSize[1] === '%') {
                    pixels = Math.round((parsedSize[0] * this.getHeight()) / 100);
                } else {
                    pixels = parsedSize[0] < this.dragboard.topMargin ? 0 : parsedSize[0] - this.dragboard.topMargin;
                }
                offsetInLU = Math.round(this.fromPixelsToVCells(pixels));
            }

            return new Wirecloud.ui.MultiValuedSize(this.getRowOffset({y: offsetInLU}), offsetInLU);
        }

        adaptHeight(size) {
            const parsedSize = this.parseSize(size);
            let pixels;

            if (parsedSize[1] === 'cells') {
                pixels = this.fromVCellsToPixels(Math.round(parsedSize[0]));
            } else if (parsedSize[1] === '%') {
                pixels = Math.round((parsedSize[0] * this.getHeight()) / 100);
            } else {
                pixels = parsedSize[0];
            }

            const heightLU = Math.max(1, Math.round(this.fromPixelsToVCells(pixels)));
            return new Wirecloud.ui.MultiValuedSize(this.getHeightInPixels(heightLU), heightLU);
        }

        adaptWidth(size, width) {
            const parsedSize = this.parseSize(size);
            let pixels;

            if (parsedSize[1] === 'cells') {
                pixels = this.fromHCellsToPixels(Math.round(parsedSize[0]), width);
            } else if (parsedSize[1] === '%') {
                pixels = Math.round((parsedSize[0] * (width || this.getWidth())) / 100);
            } else {
                pixels = parsedSize[0];
            }

            const widthLU = Math.max(1, Math.round(this.fromPixelsToHCells(pixels, width)));
            return new Wirecloud.ui.MultiValuedSize(this.getWidthInPixels(widthLU, width), widthLU);
        }

        padWidth(width) {
            return width;
        }

        padHeight(height) {
            return height;
        }

        getColumnOffset(position, width, css) {
            const offset = Math.round(((width || this.getWidth()) * position.x) / this.columns) + this.dragboard.leftMargin;
            return css ? offset + 'px' : offset;
        }

        getRowOffset(position, css) {
            const offset = this.dragboard.topMargin + Math.round(position.y * this.cellHeight);
            return css ? offset + 'px' : offset;
        }

        _buildNode(widget) {
            return {
                x: widget.position.x,
                y: widget.position.y,
                w: widget.shape.width,
                h: widget.shape.height
            };
        }

        _searchFreeSpace(width, height) {
            return this._searchFreeSpace2(width, height);
        }

        _searchFreeSpace2(width, height, matrix) {
            const occupied = matrix || this._buildMatrix();
            const maxColumns = Math.max(this.columns, 1);
            const maxRows = this.maxRow || 1000;

            for (let y = 0; y < maxRows; y++) {
                for (let x = 0; x <= maxColumns - width; x++) {
                    if (this._isSpaceFree(occupied, x, y, width, height)) {
                        return new Wirecloud.DragboardPosition(x, y);
                    }
                }
            }

            return new Wirecloud.DragboardPosition(0, 0);
        }

        _buildMatrix() {
            const matrix = [];

            Object.values(this.widgets).forEach((widget) => {
                if (widget == null) {
                    return;
                }

                for (let x = widget.position.x; x < widget.position.x + widget.shape.width; x++) {
                    if (!matrix[x]) {
                        matrix[x] = [];
                    }
                    for (let y = widget.position.y; y < widget.position.y + widget.shape.height; y++) {
                        matrix[x][y] = widget;
                    }
                }
            });

            return matrix;
        }

        _isSpaceFree(matrix, positionX, positionY, width, height) {
            for (let x = 0; x < width; x++) {
                for (let y = 0; y < height; y++) {
                    if (matrix[positionX + x] != null && matrix[positionX + x][positionY + y] != null) {
                        return false;
                    }
                }
            }

            return true;
        }

        _applyNode(widget, node) {
            if (this.grid == null) {
                return;
            }

            widget._gridstackSyncing = true;
            this.syncing = true;
            this.grid.update(widget.wrapperElement, node);
            Promise.resolve().then(() => {
                widget._gridstackSyncing = false;
                this.syncing = false;
            });
        }

        _makeWidget(widget) {
            if (this.grid == null) {
                return;
            }

            console.log('GridstackLayout._makeWidget for widget', widget && widget.id);
            widget.wrapperElement.classList.add('grid-stack-item');
            widget.wrapperElement._wirecloudWidget = widget;
            this.grid.makeWidget(widget.wrapperElement, this._buildNode(widget));
            const role = widget.tab.workspace.editing ? 'editor' : 'viewer';
            this.syncWidgetPermissions(widget, {
                moveable: widget.tab.workspace.editing && !widget.model.volatile && widget.model.isAllowed('move', role),
                resizable: widget.tab.workspace.editing && !widget.model.volatile && widget.model.isAllowed('resize', role)
            });
        }

        syncWidgetPermissions(widget, options) {
            if (this.grid == null || widget._gridstackSyncing || widget.wrapperElement.gridstackNode == null) {
                widget.wrapperElement.setAttribute('gs-no-move', String(!options.moveable));
                widget.wrapperElement.setAttribute('gs-no-resize', String(!options.resizable));
                return this;
            }

            this.grid.movable(widget.wrapperElement, options.moveable);
            this.grid.resizable(widget.wrapperElement, options.resizable);
            return this;
        }

        initialize() {
            if (this.initialized) {
                return false;
            }

            console.log('GridstackLayout.initialize for tab', this.dragboard.tab && this.dragboard.tab.model && this.dragboard.tab.model.id);
            this.dragboard.tab.wrapperElement.classList.add('grid-stack');
            this.dragboard.tab.wrapperElement.classList.add('wc-gridstack-layout');
            this.grid = GridStack.init({
                column: this.columns,
                maxRow: this.maxRow || 0,
                cellHeight: this.cellHeight,
                animate: true,
                float: false,
                disableOneColumnMode: true,
                margin: 0,
                draggable: {
                    handle: '.wc-widget-heading',
                    appendTo: 'body',
                    scroll: true
                },
                resizable: {
                    handles: 'e,se,s,sw,w,n,ne,nw'
                }
            }, this.dragboard.tab.wrapperElement);

            this.grid.on('change', on_grid_change.bind(this));
            this.initialized = true;

            Object.values(this.widgets).forEach((widget) => {
                this._makeWidget(widget);
            });

            this.grid.onResize(this.getWidth());

            return false;
        }

        addWidget(widget, affectsDragboard) {
            widget.wrapperElement.classList.add('grid-stack-item');
            widget.wrapperElement._wirecloudWidget = widget;
            if (this.initialized) {
                widget._gridstackSyncing = true;
            }
            const result = super.addWidget(widget, affectsDragboard);

            if (this.initialized) {
                widget._gridstackSyncing = false;
                this._makeWidget(widget);
            } else {
                const node = this._buildNode(widget);
                widget.wrapperElement.setAttribute('gs-x', String(node.x));
                widget.wrapperElement.setAttribute('gs-y', String(node.y));
                widget.wrapperElement.setAttribute('gs-w', String(node.w));
                widget.wrapperElement.setAttribute('gs-h', String(node.h));
            }

            return result;
        }

        removeWidget(widget, affectsDragboard) {
            if (this.grid != null) {
                this.grid.removeWidget(widget.wrapperElement, false, false);
            }

            return super.removeWidget(widget, affectsDragboard);
        }

        updatePosition(widget, element) {
            const node = this._buildNode(widget);

            if (this.initialized) {
                if (widget._gridstackSyncing) {
                    element.setAttribute('gs-x', String(node.x));
                    element.setAttribute('gs-y', String(node.y));
                } else {
                    this._applyNode(widget, node);
                }
            } else {
                element.setAttribute('gs-x', String(node.x));
                element.setAttribute('gs-y', String(node.y));
            }

            return this;
        }

        updateShape(widget, element) {
            const node = this._buildNode(widget);

            if (this.initialized) {
                if (widget._gridstackSyncing) {
                    element.setAttribute('gs-w', String(node.w));
                    element.setAttribute('gs-h', String(node.h));
                } else {
                    this._applyNode(widget, node);
                }
            } else {
                element.setAttribute('gs-w', String(node.w));
                element.setAttribute('gs-h', String(node.h));
            }

            return this;
        }

        _notifyResizeEvent(widget, oldWidth, oldHeight, newWidth, newHeight, resizeLeftSide, resizeTopSide, persist) {
            if (this.initialized && !widget._gridstackSyncing) {
                this._applyNode(widget, {
                    x: widget.position.x,
                    y: widget.position.y,
                    w: newWidth,
                    h: newHeight
                });
            }

            if (persist) {
                this.dragboard.update([widget.id]);
            }
        }

        _notifyWindowResizeEvent(widthChanged, heightChanged) {
            super._notifyWindowResizeEvent(widthChanged, heightChanged);

            if (this.grid != null && widthChanged) {
                this.grid.onResize(this.getWidth());
            }
        }

    };

    };

    // Kick off the deferred definition
    _ensureGridstackLayout();

})(Wirecloud.ui, Wirecloud.Utils);
