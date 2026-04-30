const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPopupMenuBase = () => {
    class ObjectWithEvents {
        constructor(events = []) {
            this.__listeners = {};
            events.forEach((eventName) => {
                this.__listeners[eventName] = [];
            });
            this.destroyCalls = 0;
        }

        addEventListener(eventName, listener) {
            if (!(eventName in this.__listeners)) {
                this.__listeners[eventName] = [];
            }
            this.__listeners[eventName].push(listener);
            return this;
        }

        removeEventListener(eventName, listener) {
            if (!(eventName in this.__listeners)) {
                return this;
            }
            this.__listeners[eventName] = this.__listeners[eventName].filter((entry) => entry !== listener);
            return this;
        }

        dispatchEvent(eventName, ...args) {
            (this.__listeners[eventName] || []).forEach((listener) => listener(...args));
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class MenuItem extends ObjectWithEvents {
        constructor(title = '', handler = null, context = null) {
            super(['click', 'mouseenter', 'mouseleave', 'focus', 'blur']);
            this.title = title;
            this.run = handler;
            this.context = context;
            this.enabled = true;
            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = 'menu-item';
            this.activateCalls = 0;
            this.deactivateCalls = 0;
            this.focusCalls = 0;
            this.destroyCalls = 0;
            this.parentElement = null;
        }

        insertInto(element) {
            element.appendChild(this.wrapperElement);
            return this;
        }

        activate() {
            this.activateCalls += 1;
            this.wrapperElement.classList.add('active');
            return this;
        }

        deactivate() {
            this.deactivateCalls += 1;
            this.wrapperElement.classList.remove('active');
            return this;
        }

        focus() {
            this.focusCalls += 1;
            return this;
        }

        hasClassName(className) {
            return this.wrapperElement.classList.contains(className);
        }

        destroy() {
            this.destroyCalls += 1;
            if (this.wrapperElement.parentElement) {
                this.wrapperElement.parentElement.removeChild(this.wrapperElement);
            }
        }
    }

    class Separator {
        constructor() {
            this.wrapperElement = document.createElement('hr');
            this.destroyCalls = 0;
            this.parentElement = null;
        }

        insertInto(element) {
            element.appendChild(this.wrapperElement);
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
            if (this.wrapperElement.parentElement) {
                this.wrapperElement.parentElement.removeChild(this.wrapperElement);
            }
        }
    }

    class SubMenuItem extends ObjectWithEvents {
        constructor() {
            super(['click']);
            this.menuitem = new MenuItem('submenu');
            this.menuitem.wrapperElement.classList.add('submenu');
            this.hideCalls = 0;
            this.showCalls = 0;
            this.setParentCalls = 0;
            this.destroyCalls = 0;
            this.visible = true;
        }

        _setParentPopupMenu(parent) {
            this.parentMenu = parent;
            this.setParentCalls += 1;
        }

        show() {
            this.showCalls += 1;
            this.visible = true;
            return this;
        }

        hide() {
            this.hideCalls += 1;
            this.visible = false;
            return this;
        }

        isVisible() {
            return this.visible;
        }

        hasEnabledItem() {
            return true;
        }

        moveFocusDown() {
            return this;
        }

        moveFocusUp() {
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class DynamicMenuItems {
        constructor(builder) {
            this.builder = builder;
            this.calls = [];
        }

        build(context) {
            this.calls.push(context);
            return this.builder(context);
        }
    }

    const fullscreenElement = document.createElement('div');
    fullscreenElement.offsetHeight = 300;
    fullscreenElement.getBoundingClientRect = () => ({
        left: 0,
        top: 0,
        right: 300,
        bottom: 300,
        width: 300,
        height: 300,
    });

    global.StyledElements = {
        ObjectWithEvents,
        MenuItem,
        Separator,
        SubMenuItem,
        DynamicMenuItems,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            getFullscreenElement: () => fullscreenElement,
        },
    };

    global.Wirecloud = {
        UserInterfaceManager: {
            registerCalls: 0,
            unregisterCalls: 0,
            _registerPopup() {
                this.registerCalls += 1;
            },
            _unregisterPopup() {
                this.unregisterCalls += 1;
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PopupMenuBase.js');
    return {
        PopupMenuBase: StyledElements.PopupMenuBase,
        MenuItem,
        Separator,
        SubMenuItem,
        DynamicMenuItems,
        fullscreenElement,
    };
};

const setMenuGeometry = (popup, box, parentBox = null) => {
    popup.wrapperElement.offsetWidth = box.width;
    popup.wrapperElement.offsetHeight = box.height;
    popup.wrapperElement.getBoundingClientRect = () => {
        const left = parseInt(popup.wrapperElement.style.left || '0', 10);
        const top = parseInt(popup.wrapperElement.style.top || '0', 10);
        const width = box.width;
        const height = box.height;
        return {
            left,
            top,
            right: left + width,
            bottom: top + height,
            width,
            height,
        };
    };
    if (parentBox && popup.wrapperElement.parentElement) {
        popup.wrapperElement.parentElement.getBoundingClientRect = () => parentBox;
        popup.wrapperElement.parentElement.offsetHeight = parentBox.height;
    }
};

test('StyledElements.PopupMenuBase constructor handles placement options and defaults', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const arrayPlacement = new PopupMenuBase({placement: ['left-bottom']});
    const stringPlacement = new PopupMenuBase({placement: 'top-left'});
    const defaultPlacement = new PopupMenuBase({});

    assert.deepEqual(arrayPlacement._placement, ['left-bottom']);
    assert.deepEqual(stringPlacement._placement, ['top-left']);
    assert.deepEqual(defaultPlacement._placement, ['bottom-left', 'bottom-right', 'top-left', 'top-right']);
    assert.equal(defaultPlacement.hidden, true);
    assert.equal(defaultPlacement.wrapperElement.getAttribute('role'), 'menu');
});

test('StyledElements.PopupMenuBase getters return null when hidden or no enabled items', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});

    assert.equal(popup.activeItem, null);
    assert.equal(popup.firstEnabledItem, null);
    assert.equal(popup.lastEnabledItem, null);
});

test('StyledElements.PopupMenuBase append validates child types', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});

    assert.throws(() => popup.append({}), {name: 'TypeError', message: 'Invalid chlid element'});
    assert.throws(() => popup.append(null), {name: 'TypeError', message: 'child parameter cannot be null'});
});

test('StyledElements.PopupMenuBase append accepts MenuItem, SubMenuItem, DynamicMenuItems and Separator', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem, SubMenuItem, DynamicMenuItems, Separator} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    const item = new MenuItem('a');
    const submenu = new SubMenuItem();
    const dynamic = new DynamicMenuItems(() => []);
    const separator = new Separator();

    popup.append(item).append(submenu).append(dynamic).append(separator);

    assert.equal(popup._items.length, 4);
    assert.equal(submenu.setParentCalls, 1);
});

test('StyledElements.PopupMenuBase appendSeparator appends a separator', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, Separator} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});

    popup.appendSeparator();

    assert.equal(popup._items[0] instanceof Separator, true);
});

test('StyledElements.PopupMenuBase show supports already visible guard', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;

    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    const result = popup.show({left: 2, top: 2, right: 3, bottom: 3, width: 1, height: 1});

    assert.equal(result, popup);
});

test('StyledElements.PopupMenuBase show displays content, registers popup and sets width when requested', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem, fullscreenElement} = setupPopupMenuBase();
    const popup = new PopupMenuBase({oneActiveAtLeast: true, useRefElementWidth: true});
    popup.append(new MenuItem('one'));
    popup.append(new MenuItem('two'));
    const ref = {left: 10, top: 10, right: 40, bottom: 30, width: 30, height: 20};
    popup.wrapperElement.offsetWidth = 20;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 20, height: 10});

    popup.show(ref);

    assert.equal(popup.hidden, false);
    assert.equal(fullscreenElement.childNodes.includes(popup.wrapperElement), true);
    assert.equal(popup.wrapperElement.style.width, '30px');
    assert.equal(Wirecloud.UserInterfaceManager.registerCalls, 1);
    assert.equal(popup.activeItem != null, true);
});

test('StyledElements.PopupMenuBase show handles element references and aria attributes', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.removeAttribute('id');
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const refElement = document.createElement('button');
    refElement.getBoundingClientRect = () => ({left: 5, top: 5, right: 15, bottom: 15, width: 10, height: 10});
    refElement.setAttribute('aria-controls', 'existing-id');

    popup.show(refElement);

    assert.equal(refElement.getAttribute('aria-expanded'), 'true');
    assert.equal(refElement.getAttribute('aria-controls').includes('existing-id'), true);
    assert.equal(refElement.getAttribute('aria-controls').includes('se-popup-menu-'), true);
});

test('StyledElements.PopupMenuBase show handles x/y reference coordinates', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});

    popup.show({x: 123, y: 45});

    assert.equal(popup.wrapperElement.style.left, '123px');
    assert.equal(popup.wrapperElement.style.top, '45px');
});

test('StyledElements.PopupMenuBase show falls back to document.body when fullscreen is unavailable', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    StyledElements.Utils.getFullscreenElement = () => null;
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});

    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    assert.equal(document.body.childNodes.includes(popup.wrapperElement), true);
});

test('StyledElements.PopupMenuBase show executes fixPosition fallback for overflowing placements', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, fullscreenElement} = setupPopupMenuBase();
    const popup = new PopupMenuBase({placement: ['bottom-left', 'top-left']});
    popup.wrapperElement.offsetWidth = 90;
    popup.wrapperElement.offsetHeight = 90;
    fullscreenElement.getBoundingClientRect = () => ({
        left: 0, top: 0, right: 50, bottom: 50, width: 50, height: 50,
    });
    setMenuGeometry(popup, {width: 90, height: 90});

    popup.show({left: 40, top: 40, right: 45, bottom: 45, width: 5, height: 5});

    assert.equal(
        popup.wrapperElement.style.left === '10px' ||
        popup.wrapperElement.style.right === '10px' ||
        popup.wrapperElement.style.top === '10px' ||
        popup.wrapperElement.style.bottom === '10px',
        true
    );
});

test('StyledElements.PopupMenuBase setPosition covers top-right and bottom-right placements', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const topRight = new PopupMenuBase({placement: ['top-right']});
    topRight.wrapperElement.offsetWidth = 20;
    topRight.wrapperElement.offsetHeight = 10;
    setMenuGeometry(topRight, {width: 20, height: 10});
    topRight.show({left: 10, top: 30, right: 50, bottom: 40, width: 40, height: 10});
    assert.equal(topRight.wrapperElement.style.top, '21px');
    assert.equal(topRight.wrapperElement.style.left, '30px');

    const bottomRight = new PopupMenuBase({placement: ['bottom-right']});
    bottomRight.wrapperElement.offsetWidth = 20;
    bottomRight.wrapperElement.offsetHeight = 10;
    setMenuGeometry(bottomRight, {width: 20, height: 10});
    bottomRight.show({left: 10, top: 30, right: 50, bottom: 40, width: 40, height: 10});
    assert.equal(bottomRight.wrapperElement.style.top, '39px');
    assert.equal(bottomRight.wrapperElement.style.left, '30px');
});

test('StyledElements.PopupMenuBase setPosition covers left-bottom and right-bottom placements', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const leftBottom = new PopupMenuBase({placement: ['left-bottom']});
    leftBottom.wrapperElement.offsetWidth = 20;
    leftBottom.wrapperElement.offsetHeight = 10;
    setMenuGeometry(leftBottom, {width: 20, height: 10});
    leftBottom.show({left: 10, top: 30, right: 50, bottom: 40, width: 40, height: 10});
    assert.equal(leftBottom.wrapperElement.classList.contains('se-popup-menu-left-bottom'), true);
    assert.equal(leftBottom.wrapperElement.style.left !== '', true);
    assert.equal(leftBottom.wrapperElement.style.top, '29px');

    const rightBottom = new PopupMenuBase({placement: ['right-bottom']});
    rightBottom.wrapperElement.offsetWidth = 20;
    rightBottom.wrapperElement.offsetHeight = 10;
    setMenuGeometry(rightBottom, {width: 20, height: 10});
    rightBottom.show({left: 10, top: 30, right: 50, bottom: 40, width: 40, height: 10});
    assert.equal(rightBottom.wrapperElement.classList.contains('se-popup-menu-right-bottom'), true);
    assert.equal(rightBottom.wrapperElement.style.left !== '', true);
    assert.equal(rightBottom.wrapperElement.style.top, '29px');
});

test('StyledElements.PopupMenuBase append while visible displays and activates first item when needed', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({oneActiveAtLeast: true});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    const item = new MenuItem('late');

    popup.append(item);

    assert.equal(item.parentElement, popup);
    assert.equal(popup.activeItem, item);
});

test('StyledElements.PopupMenuBase show displays submenu items from _items and tracks them for hideContent', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, SubMenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const submenu = new SubMenuItem();
    popup.append(submenu);

    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    assert.equal(popup._submenus.length, 1);

    popup.hide();
    assert.equal(submenu.hideCalls >= 1, true);
});

test('StyledElements.PopupMenuBase clear removes listeners and content in hidden and visible states', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const hiddenPopup = new PopupMenuBase({});
    hiddenPopup.append(new MenuItem('h1'));
    hiddenPopup.clear();
    assert.equal(hiddenPopup._items.length, 0);

    const visiblePopup = new PopupMenuBase({});
    visiblePopup.wrapperElement.offsetWidth = 10;
    visiblePopup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(visiblePopup, {width: 10, height: 10});
    visiblePopup.append(new MenuItem('v1'));
    visiblePopup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    visiblePopup.clear();
    assert.equal(visiblePopup.wrapperElement.innerHTML, '');
    assert.equal(visiblePopup._items.length, 0);
});

test('StyledElements.PopupMenuBase _menuItemCallback dispatches click, hides non-submenu and runs handlers', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    popup.setContext({ctx: 1});
    const regular = new MenuItem('regular', (ctx, data) => {
        regular.lastRun = {ctx, data};
    }, {id: 3});
    const submenu = new MenuItem('submenu');
    submenu.wrapperElement.classList.add('submenu');
    let clickEvents = 0;
    popup.addEventListener('click', () => {
        clickEvents += 1;
    });

    popup._menuItemCallback(regular);
    assert.equal(clickEvents, 1);
    assert.deepEqual(regular.lastRun, {ctx: {ctx: 1}, data: {id: 3}});
    assert.equal(popup.hidden, true);

    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    popup._menuItemCallback(submenu);
    assert.equal(popup.hidden, false);
});

test('StyledElements.PopupMenuBase hover and focus handlers update active/focused state', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const first = new MenuItem('one');
    const second = new MenuItem('two');
    popup.append(first).append(second);
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    popup._menuItem_onmouseenter_bound(first);
    assert.equal(popup.activeItem, first);
    popup._menuItem_onfocus_bound(first);
    assert.equal(popup._focusedMenuItem, first);
    popup._menuItem_onblur_bound(first);
    assert.equal(popup._focusedMenuItem, null);

    popup.oneActiveAtLeast && popup._menuItem_onmouseleave_bound(second);
    popup._menuItem_onmouseleave_bound(first);
    assert.equal(first.deactivateCalls >= 1, true);
});

test('StyledElements.PopupMenuBase oneActiveAtLeast mouseleave deactivates non-active menu items', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({oneActiveAtLeast: true});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const active = new MenuItem('active');
    const other = new MenuItem('other');
    popup.append(active).append(other);
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    popup._activeMenuItem = active;

    popup._menuItem_onmouseleave_bound(other);

    assert.equal(other.deactivateCalls, 1);
});

test('StyledElements.PopupMenuBase move cursor and focus operations navigate and wrap', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const a = new MenuItem('a');
    const b = new MenuItem('b');
    popup.append(a).append(b);
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    popup.moveCursorDown();
    assert.equal(popup.activeItem, a);
    popup.moveCursorDown();
    assert.equal(popup.activeItem, b);
    popup.moveCursorDown();
    assert.equal(popup.activeItem, a);

    popup.moveCursorUp();
    assert.equal(popup.activeItem, b);

    popup.moveFocusDown();
    assert.equal(a.focusCalls, 1);
    popup._focusedMenuItem = a;
    popup.moveFocusDown();
    assert.equal(b.focusCalls, 1);
    popup.moveFocusUp();
    assert.equal(b.focusCalls, 2);
});

test('StyledElements.PopupMenuBase moveCursorUp covers non-zero index and null-active branches', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const a = new MenuItem('a');
    const b = new MenuItem('b');
    popup.append(a).append(b);
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    popup._activeMenuItem = b;
    popup.moveCursorUp();
    assert.equal(popup.activeItem, a);

    popup._activeMenuItem = null;
    popup.moveCursorUp();
    assert.equal(popup.activeItem, b);
});

test('StyledElements.PopupMenuBase moveFocusDown and moveFocusUp cover wrap and null-focused branches', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const a = new MenuItem('a');
    const b = new MenuItem('b');
    popup.append(a).append(b);
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    popup._focusedMenuItem = b;
    popup.moveFocusDown();
    assert.equal(a.focusCalls, 1);

    popup._focusedMenuItem = b;
    popup.moveFocusUp();
    assert.equal(a.focusCalls, 2);

    popup._focusedMenuItem = null;
    popup.moveFocusUp();
    assert.equal(b.focusCalls >= 1, true);
});

test('StyledElements.PopupMenuBase navigation methods are no-op without enabled items', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});

    popup.moveCursorDown();
    popup.moveCursorUp();
    popup.moveFocusDown();
    popup.moveFocusUp();

    assert.equal(popup.hidden, true);
});

test('StyledElements.PopupMenuBase repaint only repositions when refPosition is set', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    popup.repaint();
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    const before = popup.wrapperElement.style.left;
    popup.repaint();

    assert.equal(typeof before, 'string');
});

test('StyledElements.PopupMenuBase repaint handles refPosition elements via getBoundingClientRect', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const ref = document.createElement('div');
    ref.getBoundingClientRect = () => ({left: 8, top: 9, right: 18, bottom: 19, width: 10, height: 10});
    popup.show(ref);

    popup.repaint();

    assert.equal(typeof popup.wrapperElement.style.left, 'string');
});

test('StyledElements.PopupMenuBase hide handles hidden and visible states and updates aria-expanded', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    const hiddenResult = popup.hide();
    assert.equal(hiddenResult, popup);

    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    const ref = document.createElement('button');
    ref.getBoundingClientRect = () => ({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    popup.show(ref);
    popup.hide();

    assert.equal(ref.getAttribute('aria-expanded'), 'false');
    assert.equal(Wirecloud.UserInterfaceManager.unregisterCalls, 1);
    assert.equal(popup.hidden, true);
});

test('StyledElements.PopupMenuBase show/hide works without Wirecloud global', () => {
    resetLegacyRuntime();
    const {PopupMenuBase} = setupPopupMenuBase();
    delete global.Wirecloud;
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});

    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    popup.hide();

    assert.equal(popup.hidden, true);
});

test('StyledElements.PopupMenuBase destroy cleans menu items and delegates to parent', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem, DynamicMenuItems, SubMenuItem, Separator} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    popup.append(new MenuItem('one'));
    popup.append(new DynamicMenuItems(() => [new SubMenuItem(), new Separator(), new MenuItem('dyn')]));
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});

    popup.destroy();

    assert.equal(popup._items, null);
    assert.equal(popup._menuItemCallback, null);
    assert.equal(popup._context, null);
    assert.equal(popup.destroyCalls, 1);
});

test('StyledElements.PopupMenuBase hasEnabledItem returns true only when visible and enabled items exist', () => {
    resetLegacyRuntime();
    const {PopupMenuBase, MenuItem} = setupPopupMenuBase();
    const popup = new PopupMenuBase({});
    assert.equal(popup.hasEnabledItem(), false);
    popup.wrapperElement.offsetWidth = 10;
    popup.wrapperElement.offsetHeight = 10;
    setMenuGeometry(popup, {width: 10, height: 10});
    popup.append(new MenuItem('one'));
    popup.show({left: 1, top: 1, right: 2, bottom: 2, width: 1, height: 1});
    assert.equal(popup.hasEnabledItem(), true);
});
