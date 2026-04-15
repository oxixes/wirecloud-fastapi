const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupMessageWindowMenu = () => {
    class StyledElement {
        insertInto(node) {
            this.insertedInto = node;
        }
    }

    class Button {
        constructor(options) {
            this.options = options;
        }

        insertInto(node) {
            this.parentNode = node;
        }

        addEventListener(name, handler) {
            this.listener = { name, handler };
        }

        focus() {
            this.focused = true;
        }
    }

    class WindowMenu {
        constructor(title, extraClass) {
            this.title = title;
            this.extraClass = extraClass;
            this.windowContent = document.createElement('div');
            this.windowBottom = document.createElement('div');
            this._closeListener = () => {
                this.closed = true;
            };
        }

        repaint() {
            this.repaintCalls = (this.repaintCalls || 0) + 1;
        }

        setTitle(value) {
            this.title = value;
        }
    }

    global.StyledElements = {
        StyledElement,
        Button
    };
    global.Wirecloud = {
        Utils: {
            gettext: (text) => text
        },
        ui: {
            WindowMenu
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/MessageWindowMenu.js');
    return Wirecloud.ui.MessageWindowMenu;
};

test('Wirecloud.ui.MessageWindowMenu builds message container and accept button', () => {
    resetLegacyRuntime();
    const MessageWindowMenu = setupMessageWindowMenu();
    const menu = new MessageWindowMenu('hello', 1);

    assert.equal(menu.msgElement.getAttribute('role'), 'status');
    assert.equal(menu.button.options.text, 'Accept');
    assert.equal(menu.button.parentNode, menu.windowBottom);
    assert.equal(menu.button.listener.name, 'click');
});

test('Wirecloud.ui.MessageWindowMenu setMsg accepts plain text', () => {
    resetLegacyRuntime();
    const MessageWindowMenu = setupMessageWindowMenu();
    const menu = new MessageWindowMenu('hello', 3);

    menu.setMsg('new text');

    assert.equal(menu.msgElement.textContent, 'new text');
    assert.equal(menu.repaintCalls > 0, true);
});

test('Wirecloud.ui.MessageWindowMenu setMsg accepts StyledElement instances', () => {
    resetLegacyRuntime();
    const MessageWindowMenu = setupMessageWindowMenu();
    const menu = new MessageWindowMenu('hello', 2);

    const styledElement = new StyledElements.StyledElement();
    menu.setMsg(styledElement);

    assert.equal(styledElement.insertedInto, menu.msgElement);
});

test('Wirecloud.ui.MessageWindowMenu setFocus forwards focus to accept button', () => {
    resetLegacyRuntime();
    const MessageWindowMenu = setupMessageWindowMenu();
    const menu = new MessageWindowMenu('hello', 2);

    menu.setFocus();

    assert.equal(menu.button.focused, true);
});

test('Wirecloud.ui.MessageWindowMenu setType supports numeric and custom titles', () => {
    resetLegacyRuntime();
    const MessageWindowMenu = setupMessageWindowMenu();
    const menu = new MessageWindowMenu('hello', 1);

    menu.setType(2);
    assert.equal(menu.title, 'Warning');
    menu.setType('Custom');
    assert.equal(menu.title, 'Custom');
});
