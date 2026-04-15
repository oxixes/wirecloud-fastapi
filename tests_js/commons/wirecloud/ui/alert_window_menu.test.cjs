const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupAlertWindowMenu = () => {
    class StyledElement {}

    class Button {
        constructor(options) {
            this.options = options;
            this.listeners = {};
            this.classes = [];
            this.disabled = false;
            this.focusCalls = 0;
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }

        insertInto(node) {
            this.parentNode = node;
        }

        trigger(name, event = {}) {
            this.listeners[name](event);
        }

        addClassName(className) {
            if (!this.classes.includes(className)) {
                this.classes.push(className);
            }
            return this;
        }

        removeClassName(className) {
            this.classes = this.classes.filter((entry) => entry !== className);
            return this;
        }

        disable() {
            this.disabled = true;
            return this;
        }

        enable() {
            this.disabled = false;
            return this;
        }

        focus() {
            this.focusCalls += 1;
            return this;
        }
    }

    class WindowMenu {
        constructor(title, extraClass) {
            this.title = title;
            this.extraClass = extraClass;
            this.windowContent = document.createElement('div');
            this.windowBottom = document.createElement('div');
            this.hideCalls = 0;
            this.repaintCalls = 0;
            this.baseCloseCalls = 0;
        }

        hide() {
            this.hideCalls += 1;
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }
    }
    WindowMenu.prototype._closeListener = function _closeListener() {
        this.baseCloseCalls += 1;
    };

    global.StyledElements = {
        StyledElement,
        Button,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            gettext: (text) => text,
        },
    };
    global.Wirecloud = {
        ui: {WindowMenu},
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/AlertWindowMenu.js');
    return {AlertWindowMenu: Wirecloud.ui.AlertWindowMenu, StyledElement};
};

test('Wirecloud.ui.AlertWindowMenu validates constructor options', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();

    assert.throws(() => new AlertWindowMenu(), TypeError);
    assert.throws(() => new AlertWindowMenu({}), TypeError);
});

test('Wirecloud.ui.AlertWindowMenu constructor accepts string message and default labels', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('Proceed?');

    assert.equal(menu.title, 'Warning');
    assert.equal(menu.extraClass, 'wc-alert-modal');
    assert.equal(menu.msgElement.textContent, 'Proceed?');
    assert.equal(menu.acceptButton.options.text, 'Yes');
    assert.equal(menu.cancelButton.options.text, 'No');
});

test('Wirecloud.ui.AlertWindowMenu constructor accepts StyledElement message', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu, StyledElement} = setupAlertWindowMenu();
    class MessageElement extends StyledElement {
        insertInto(node) {
            this.insertedInto = node;
            node.appendChild(document.createTextNode('styled'));
        }
    }
    const message = new MessageElement();

    const menu = new AlertWindowMenu(message);

    assert.equal(message.insertedInto, menu.msgElement);
    assert.equal(menu.msgElement.textContent, 'styled');
});

test('Wirecloud.ui.AlertWindowMenu setMsg supports strings and StyledElement instances', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu, StyledElement} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('a');
    class MessageElement extends StyledElement {
        insertInto(node) {
            node.appendChild(document.createTextNode('msg2'));
        }
    }

    menu.setMsg('plain');
    assert.equal(menu.msgElement.textContent, 'plain');
    const beforeRepaints = menu.repaintCalls;
    menu.setMsg(new MessageElement());
    assert.equal(menu.msgElement.textContent, 'msg2');
    assert.equal(menu.repaintCalls > beforeRepaints, true);
});

test('Wirecloud.ui.AlertWindowMenu setHandler stores handlers and setFocus focuses cancel button', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('msg');
    const acceptHandler = () => {};
    const cancelHandler = () => {};

    const result = menu.setHandler(acceptHandler, cancelHandler).setFocus();

    assert.equal(result, menu);
    assert.equal(menu.acceptHandler, acceptHandler);
    assert.equal(menu.cancelHandler, cancelHandler);
    assert.equal(menu.cancelButton.focusCalls, 1);
});

test('Wirecloud.ui.AlertWindowMenu accept click hides when handler is non-promise', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('msg');
    menu.acceptHandler = () => null;

    menu.acceptButton.trigger('click');

    assert.equal(menu.hideCalls, 1);
});

test('Wirecloud.ui.AlertWindowMenu accept click with promise resolve hides and keeps busy class', async () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('msg');
    menu.acceptHandler = () => Promise.resolve();

    menu.acceptButton.trigger('click');
    await Promise.resolve();

    assert.equal(menu.acceptButton.classes.includes('busy'), true);
    assert.equal(menu.acceptButton.disabled, true);
    assert.equal(menu.cancelButton.disabled, true);
    assert.equal(menu.hideCalls, 1);
});

test('Wirecloud.ui.AlertWindowMenu accept click with promise reject restores buttons', async () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('msg');
    menu.acceptHandler = () => Promise.reject(new Error('nope'));

    menu.acceptButton.trigger('click');
    await Promise.resolve();

    assert.equal(menu.acceptButton.classes.includes('busy'), false);
    assert.equal(menu.acceptButton.disabled, false);
    assert.equal(menu.cancelButton.disabled, false);
    assert.equal(menu.hideCalls, 0);
});

test('Wirecloud.ui.AlertWindowMenu cancel click calls base close listener and optional cancel handler', () => {
    resetLegacyRuntime();
    const {AlertWindowMenu} = setupAlertWindowMenu();
    const menu = new AlertWindowMenu('msg');
    let cancelCalls = 0;
    menu.cancelHandler = () => {
        cancelCalls += 1;
    };

    menu.cancelButton.trigger('click', {});

    assert.equal(menu.baseCloseCalls, 1);
    assert.equal(cancelCalls, 1);

    menu.cancelHandler = null;
    menu.cancelButton.trigger('click', {});
    assert.equal(menu.baseCloseCalls, 2);
    assert.equal(cancelCalls, 1);
});
