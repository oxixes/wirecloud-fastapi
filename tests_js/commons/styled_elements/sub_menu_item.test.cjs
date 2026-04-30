const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupSubMenuItem = () => {
    class PopupMenuBase {
        constructor(options) {
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.showCalls = [];
            this.hideCalls = 0;
            this.destroyCalls = 0;
            this.baseListeners = {};
            if (options.seedId) {
                this.wrapperElement.setAttribute('id', options.seedId);
            }
        }

        addEventListener(eventName, handler) {
            this.baseListeners[eventName] = handler;
            return this;
        }

        show(refPosition) {
            this.showCalls.push(refPosition);
            return this;
        }

        hide() {
            this.hideCalls += 1;
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class MenuItem {
        constructor(title, callback) {
            this.title = title;
            this.callback = callback;
            this.wrapperElement = document.createElement('li');
            this.eventListeners = {};
            this.iconClasses = [];
            this.enabledCalls = 0;
            this.disabledCalls = 0;
            this.setDisabledCalls = [];
            this.runCalls = [];
            this.destroyCalls = 0;
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        addEventListener(eventName, handler) {
            this.eventListeners[eventName] = handler;
            return this;
        }

        addIconClass(className) {
            this.iconClasses.push(className);
            return this;
        }

        enable() {
            this.enabledCalls += 1;
            return this;
        }

        disable() {
            this.disabledCalls += 1;
            return this;
        }

        setDisabled(disabled) {
            this.setDisabledCalls.push(disabled);
            return this;
        }

        run(context) {
            this.runCalls.push(context);
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {
        PopupMenuBase,
        MenuItem,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/SubMenuItem.js');
    return StyledElements.SubMenuItem;
};

test('StyledElements.SubMenuItem constructor applies defaults and delegates icon option', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {enabled: false, iconClass: 'fas fa-star'});

    assert.deepEqual(submenu.options.placement, ['right-bottom', 'left-bottom']);
    assert.equal(submenu.wrapperElement.classList.contains('se-popup-submenu'), true);
    assert.equal(submenu.menuitem.wrapperElement.classList.contains('submenu'), true);
    assert.equal(submenu.menuitem.wrapperElement.getAttribute('aria-haspopup'), 'true');
    assert.equal(submenu.menuitem.wrapperElement.getAttribute('aria-expanded'), 'false');
    assert.equal(submenu.menuitem.wrapperElement.getAttribute('aria-controls') != null, true);
    assert.equal(submenu.menuitem.submenu, submenu);
    assert.equal(submenu.title, 'Actions');
    assert.equal(submenu.iconClasses == null, true);
    assert.deepEqual(submenu.menuitem.iconClasses, ['fas fa-star']);
    assert.equal(submenu.enabled, false);
});

test('StyledElements.SubMenuItem constructor keeps existing submenu id', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {seedId: 'known-submenu-id'});

    assert.equal(submenu.wrapperElement.getAttribute('id'), 'known-submenu-id');
    assert.equal(submenu.menuitem.wrapperElement.getAttribute('aria-controls'), 'known-submenu-id');
});

test('StyledElements.SubMenuItem menuitem callback shows submenu', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});

    submenu.menuitem.callback();

    assert.equal(submenu.showCalls.length, 1);
    assert.equal(submenu.showCalls[0], submenu.menuitem);
});

test('StyledElements.SubMenuItem _menuItemCallback hides root menu and runs item with context', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});
    const rootMenu = {
        parentMenu: null,
        hideCalls: 0,
        _context: {id: 'ctx'},
        hide() {
            this.hideCalls += 1;
        },
    };
    submenu.parentMenu = {parentMenu: rootMenu};
    const item = {
        calls: [],
        run(context) {
            this.calls.push(context);
        },
    };

    submenu._menuItemCallback(item);

    assert.equal(rootMenu.hideCalls, 1);
    assert.deepEqual(item.calls, [{id: 'ctx'}]);
});

test('StyledElements.SubMenuItem _setParentPopupMenu toggles visibility on itemOver', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});
    const parentPopup = {
        listener: null,
        addEventListener(eventName, handler) {
            assert.equal(eventName, 'itemOver');
            this.listener = handler;
        },
    };

    submenu._setParentPopupMenu(parentPopup);
    parentPopup.listener(parentPopup, submenu.menuitem);
    parentPopup.listener(parentPopup, {});

    assert.equal(submenu.showCalls.length, 1);
    assert.equal(submenu.showCalls[0], submenu.menuitem);
    assert.equal(submenu.hideCalls, 1);
});

test('StyledElements.SubMenuItem addEventListener delegates known DOM events to menuitem', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});
    const handler = () => {};

    const result = submenu.addEventListener('click', handler);

    assert.equal(result, submenu);
    assert.equal(submenu.menuitem.eventListeners.click, handler);
});

test('StyledElements.SubMenuItem addEventListener also delegates mouse enter and leave events', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});
    const enterHandler = () => {};
    const leaveHandler = () => {};

    submenu.addEventListener('mouseenter', enterHandler);
    submenu.addEventListener('mouseleave', leaveHandler);

    assert.equal(submenu.menuitem.eventListeners.mouseenter, enterHandler);
    assert.equal(submenu.menuitem.eventListeners.mouseleave, leaveHandler);
});

test('StyledElements.SubMenuItem addEventListener delegates unknown events to base popup', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});
    const handler = () => {};

    const result = submenu.addEventListener('visibilityChange', handler);

    assert.equal(result, submenu);
    assert.equal(submenu.baseListeners.visibilityChange, handler);
});

test('StyledElements.SubMenuItem wrapper methods delegate to menuitem and popup base', () => {
    resetLegacyRuntime();
    const SubMenuItem = setupSubMenuItem();
    const submenu = new SubMenuItem('Actions', {});

    submenu.addIconClass('fas fa-box');
    submenu.enable();
    submenu.disable();
    submenu.setDisabled(true);
    submenu.show({x: 1});
    submenu.hide();
    submenu.destroy();

    assert.deepEqual(submenu.menuitem.iconClasses, ['fas fa-box']);
    assert.equal(submenu.menuitem.enabledCalls, 1);
    assert.equal(submenu.menuitem.disabledCalls, 1);
    assert.deepEqual(submenu.menuitem.setDisabledCalls, [true]);
    assert.equal(submenu.menuitem.wrapperElement.getAttribute('aria-expanded'), 'false');
    assert.equal(submenu.showCalls.length, 1);
    assert.equal(submenu.hideCalls, 1);
    assert.equal(submenu.menuitem.destroyCalls, 1);
    assert.equal(submenu.destroyCalls, 1);
});
