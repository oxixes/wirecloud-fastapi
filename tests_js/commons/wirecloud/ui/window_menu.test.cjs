const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupWindowMenu = () => {
    const fullscreenCallbacks = [];
    const uiCalls = {
        registerPopup: 0,
        unregisterPopup: 0,
        registerRoot: 0,
        unregisterRoot: 0,
    };

    class ObjectWithEvents {
        constructor(events = []) {
            this.events = {};
            this.dispatched = [];
            events.forEach((name) => {
                this.events[name] = true;
            });
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
            return this;
        }
    }

    class Button {
        constructor(options) {
            this.options = options;
            this.listeners = {};
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
            return this;
        }
    }

    class GUIBuilder {
        parse(_template, callbacks) {
            const root = document.createElement('div');
            const top = document.createElement('div');
            top.className = 'window_top';
            const body = callbacks.body({class: 'body-class'});
            const footer = callbacks.footer({class: 'footer-class'});
            const closebutton = callbacks.closebutton({});
            callbacks.title({});

            root.appendChild(top);
            root.appendChild(body);
            root.appendChild(footer);
            root._closebutton = closebutton;

            return {
                elements: [document.createTextNode('ignore'), root],
            };
        }
    }

    class Draggable {
        constructor(handler, context, onStart, onDrag, onFinish, isEnabled) {
            this.handler = handler;
            this.context = context;
            this.onStart = onStart;
            this.onDrag = onDrag;
            this.onFinish = onFinish;
            this.isEnabled = isEnabled;
        }

        runDrag(xDelta, yDelta) {
            this.onStart(this, this.context);
            this.onDrag({}, this, this.context, xDelta, yDelta);
            this.onFinish(this, this.context);
        }
    }

    global.StyledElements = {
        ObjectWithEvents,
        Button,
        GUIBuilder,
    };
    global.Wirecloud = {
        currentTheme: {
            templates: {
                'wirecloud/modals/base': '<div></div>',
            },
        },
        ui: {
            Draggable,
        },
        UserInterfaceManager: {
            _registerPopup() {
                uiCalls.registerPopup += 1;
            },
            _unregisterPopup() {
                uiCalls.unregisterPopup += 1;
            },
            _registerRootWindowMenu() {
                uiCalls.registerRoot += 1;
            },
            _unregisterRootWindowMenu() {
                uiCalls.unregisterRoot += 1;
            },
        },
        Utils: {
            gettext: (text) => text,
            getFullscreenElement: () => null,
            onFullscreenChange(_target, callback) {
                fullscreenCallbacks.push(callback);
            },
            removeFullscreenChangeCallback(_target, callback) {
                const index = fullscreenCallbacks.indexOf(callback);
                if (index !== -1) {
                    fullscreenCallbacks.splice(index, 1);
                }
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/WindowMenu.js');
    return {
        WindowMenu: Wirecloud.ui.WindowMenu,
        uiCalls,
        fullscreenCallbacks,
    };
};

test('Wirecloud.ui.WindowMenu constructor handles non-iterable events and builds elements', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('Title', 'extra', null);

    assert.equal(menu.events.show, true);
    assert.equal(menu.events.hide, true);
    assert.equal(menu.htmlElement.classList.contains('window_menu'), true);
    assert.equal(menu.htmlElement.classList.contains('extra'), true);
    assert.equal(menu.windowContent.className, 'body-class');
    assert.equal(menu.windowBottom.className, 'footer-class');
    assert.equal(menu.titleElement.textContent, 'Title');
});

test('Wirecloud.ui.WindowMenu constructor preserves existing show/hide events', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, ['show', 'hide', 'custom']);

    assert.equal(menu.events.custom, true);
    assert.equal(Object.keys(menu.events).length, 3);
});

test('Wirecloud.ui.WindowMenu setPosition/getStylePosition/setTitle work', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('old', null, []);

    menu.setPosition({posX: 12, posY: 34});
    menu.setTitle('new');

    assert.deepEqual(menu.getStylePosition(), {posX: 12, posY: 34});
    assert.equal(menu.titleElement.textContent, 'new');
});

test('Wirecloud.ui.WindowMenu draggable callbacks update and clamp position', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);
    menu.htmlElement.style.left = '';
    menu.htmlElement.style.top = '';

    assert.equal(menu.draggable.isEnabled(), true);
    menu.draggable.runDrag(-20, -30);

    assert.deepEqual(menu.getStylePosition(), {posX: 8, posY: 8});
});

test('Wirecloud.ui.WindowMenu draggable onStart reads existing numeric style positions', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);
    menu.htmlElement.style.left = '15px';
    menu.htmlElement.style.top = '25px';

    menu.draggable.runDrag(3, 4);

    assert.deepEqual(menu.getStylePosition(), {posX: 18, posY: 29});
});

test('Wirecloud.ui.WindowMenu repaint returns early when detached', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);

    const result = menu.repaint();

    assert.equal(result, menu);
});

test('Wirecloud.ui.WindowMenu repaint centers menu and updates size constraints', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);
    document.body.appendChild(menu.htmlElement);

    window.innerWidth = 100;
    window.innerHeight = 80;
    menu.htmlElement.offsetWidth = 140;
    menu.htmlElement.offsetHeight = 120;
    menu.windowHeader = menu.windowHeader || document.createElement('div');
    menu.windowHeader.offsetHeight = 10;
    menu.windowBottom.offsetHeight = 20;

    menu.repaint();

    assert.equal(menu.htmlElement.style.maxWidth, '100px');
    assert.equal(menu.htmlElement.style.maxHeight, '80px');
    assert.equal(menu.htmlElement.style.top, '0px');
    assert.equal(menu.windowContent.style.maxHeight, '50px');
    assert.equal(menu.htmlElement.style.left, '0px');
});

test('Wirecloud.ui.WindowMenu repaint also repaints child window', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const parent = new WindowMenu('parent', null, []);
    const child = new WindowMenu('child', null, []);
    document.body.appendChild(parent.htmlElement);

    child.repaintCalls = 0;
    child.repaint = function repaint() {
        this.repaintCalls += 1;
        return this;
    };

    parent.show();
    child.show(parent);
    child.repaintCalls = 0;
    parent.repaint();

    assert.equal(child.repaintCalls, 1);
});

test('Wirecloud.ui.WindowMenu show/hide root window menu lifecycle', () => {
    resetLegacyRuntime();
    const {WindowMenu, uiCalls, fullscreenCallbacks} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);

    menu.show();
    assert.equal(uiCalls.registerRoot, 1);
    assert.equal(menu.htmlElement.parentElement, document.body);
    assert.equal(fullscreenCallbacks.length, 1);
    assert.equal(menu.dispatched.at(-1).name, 'show');

    menu.hide();
    assert.equal(uiCalls.unregisterRoot, 1);
    assert.equal(menu.htmlElement.parentElement, null);
    assert.equal(fullscreenCallbacks.length, 0);
    assert.equal(menu.dispatched.at(-1).name, 'hide');
});

test('Wirecloud.ui.WindowMenu show enforces parent-child constraints', () => {
    resetLegacyRuntime();
    const {WindowMenu, uiCalls} = setupWindowMenu();
    const parent = new WindowMenu('p', null, []);
    const child = new WindowMenu('c', null, []);
    const otherParent = new WindowMenu('o', null, []);
    parent.show();

    child.show(parent);
    assert.equal(uiCalls.registerPopup, 1);
    assert.equal(child.show(parent), child);
    assert.throws(() => child.show(otherParent), TypeError);
    assert.throws(() => new WindowMenu('c2', null, []).show(parent), TypeError);

    child.hide();
    assert.equal(uiCalls.unregisterPopup, 1);
});

test('Wirecloud.ui.WindowMenu hide handles hidden menus and msgElement cleanup', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);
    menu.msgElement = document.createElement('div');
    menu.msgElement.textContent = 'msg';

    assert.equal(menu.hide(), menu);
    menu.show();
    menu.hide();

    assert.equal(menu.msgElement.textContent, '');
});

test('Wirecloud.ui.WindowMenu hide cascades to child windows', () => {
    resetLegacyRuntime();
    const {WindowMenu, uiCalls} = setupWindowMenu();
    const parent = new WindowMenu('p', null, []);
    const child = new WindowMenu('c', null, []);

    parent.show();
    child.show(parent);
    parent.hide();

    assert.equal(parent.htmlElement.parentElement, null);
    assert.equal(child.htmlElement.parentElement, null);
    assert.equal(uiCalls.unregisterPopup, 1);
    assert.equal(uiCalls.unregisterRoot, 1);
});

test('Wirecloud.ui.WindowMenu _closeListener and destroy delegate to hide', () => {
    resetLegacyRuntime();
    const {WindowMenu} = setupWindowMenu();
    const menu = new WindowMenu('x', null, []);
    menu.show();

    menu._closeListener({});
    assert.equal(menu.htmlElement.parentElement, null);

    menu.show();
    menu.destroy();
    assert.equal(menu._closeListener, null);
});
