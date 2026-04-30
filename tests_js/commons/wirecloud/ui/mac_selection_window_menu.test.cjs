const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupMACSelectionWindowMenu = () => {
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
    }

    class WindowMenu {
        constructor(title, extraClass, events = []) {
            this.title = title;
            this.extraClass = extraClass;
            this.events = events;
            this.windowContent = document.createElement('div');
            this.windowBottom = document.createElement('div');
            this._closeListener = () => {
                this.closed = true;
            };
            this.dispatched = [];
            this.showCalls = [];
        }

        dispatchEvent(name, value) {
            this.dispatched.push({ name, value });
        }

        show(parentWindow) {
            this.showCalls.push(parentWindow);
        }
    }

    class MACSearch {
        constructor(options) {
            this.options = options;
        }

        insertInto(node) {
            this.parentNode = node;
        }

        focus() {
            this.focused = true;
        }

        refresh() {
            this.refreshed = true;
        }
    }

    global.StyledElements = { Button };
    global.Wirecloud = {
        Utils: {
            gettext: (text) => text
        },
        ui: {
            WindowMenu,
            MACSearch
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/MACSelectionWindowMenu.js');
    return Wirecloud.ui.MACSelectionWindowMenu;
};

test('Wirecloud.ui.MACSelectionWindowMenu creates MACSearch and close button', () => {
    resetLegacyRuntime();
    const MACSelectionWindowMenu = setupMACSelectionWindowMenu();
    const menu = new MACSelectionWindowMenu('Title', { scope: 'public' });

    assert.equal(menu.events.includes('select'), true);
    assert.equal(menu.macsearch.options.scope, 'public');
    assert.equal(menu.button.options.text, 'Close');
    assert.equal(menu.button.parentNode, menu.windowBottom);
});

test('Wirecloud.ui.MACSelectionWindowMenu resource selection closes and dispatches event', () => {
    resetLegacyRuntime();
    const MACSelectionWindowMenu = setupMACSelectionWindowMenu();
    const menu = new MACSelectionWindowMenu('Title', { scope: 'private' });
    const resource = { id: 'r1' };

    menu.macsearch.options.resourceButtonListener(resource);

    assert.equal(menu.closed, true);
    assert.deepEqual(menu.dispatched.at(-1), { name: 'select', value: resource });
});

test('Wirecloud.ui.MACSelectionWindowMenu setFocus delegates to macsearch', () => {
    resetLegacyRuntime();
    const MACSelectionWindowMenu = setupMACSelectionWindowMenu();
    const menu = new MACSelectionWindowMenu('Title', { scope: 'public' });

    menu.setFocus();

    assert.equal(menu.macsearch.focused, true);
});

test('Wirecloud.ui.MACSelectionWindowMenu show refreshes search and calls base show', () => {
    resetLegacyRuntime();
    const MACSelectionWindowMenu = setupMACSelectionWindowMenu();
    const menu = new MACSelectionWindowMenu('Title', { scope: 'public' });

    menu.show('parent-window');

    assert.equal(menu.macsearch.refreshed, true);
    assert.deepEqual(menu.showCalls, ['parent-window']);
});
