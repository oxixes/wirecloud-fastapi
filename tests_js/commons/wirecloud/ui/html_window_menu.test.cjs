const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupHTMLWindowMenu = () => {
    let mode = 'success';

    class WindowMenu {
        constructor(title, extraClass) {
            this.title = title;
            this.extraClass = extraClass;
            this.windowBottom = document.createElement('div');
            this.windowContent = document.createElement('div');
            this._closeListener = () => {
                this.closed = true;
            };
            this.baseShowCalls = 0;
        }

        show() {
            this.baseShowCalls += 1;
        }

        repaint() {
            this.repaintCalls = (this.repaintCalls || 0) + 1;
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
            this.eventName = name;
            this.handler = handler;
        }
    }

    global.StyledElements = { Button };
    global.Wirecloud = {
        Utils: {
            gettext: (text) => text,
        },
        io: {
            makeRequest(url, options) {
                assert.equal(url, '/docs');
                if (mode === 'success') {
                    options.onSuccess({ responseText: '<strong>ok</strong>' });
                } else {
                    options.onFailure({});
                }
                options.onComplete();
            }
        },
        ui: { WindowMenu }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/HTMLWindowMenu.js');

    return {
        HTMLWindowMenu: Wirecloud.ui.HTMLWindowMenu,
        setMode: (value) => {
            mode = value;
        }
    };
};

test('Wirecloud.ui.HTMLWindowMenu constructor prefixes extra class names', () => {
    resetLegacyRuntime();
    const { HTMLWindowMenu } = setupHTMLWindowMenu();
    const menu = new HTMLWindowMenu('/docs', 'Documentation', 'extra');
    assert.equal(menu.extraClass, 'wc-html-window-menu extra');
});

test('Wirecloud.ui.HTMLWindowMenu constructor uses default class when extra class is null', () => {
    resetLegacyRuntime();
    const { HTMLWindowMenu } = setupHTMLWindowMenu();
    const menu = new HTMLWindowMenu('/docs', 'Documentation', null);
    assert.equal(menu.extraClass, 'wc-html-window-menu');
});

test('Wirecloud.ui.HTMLWindowMenu constructor wires the close button', () => {
    resetLegacyRuntime();
    const { HTMLWindowMenu } = setupHTMLWindowMenu();
    const menu = new HTMLWindowMenu('/docs', 'Documentation', 'extra');

    assert.equal(menu.button.options.text, 'Close');
    assert.equal(menu.button.parentNode, menu.windowBottom);
    assert.equal(menu.button.eventName, 'click');
    assert.equal(menu.button.handler, menu._closeListener);
});

test('Wirecloud.ui.HTMLWindowMenu show success path injects content and repaints', () => {
    resetLegacyRuntime();
    const { HTMLWindowMenu } = setupHTMLWindowMenu();
    const menu = new HTMLWindowMenu('/docs', 'Documentation', 'extra');

    menu.show();

    assert.equal(menu.baseShowCalls, 1);
    assert.equal(menu.windowContent.innerHTML, '<strong>ok</strong>');
    assert.equal(menu.repaintCalls, 1);
    assert.equal(menu.windowContent.classList.contains('disabled'), false);
});

test('Wirecloud.ui.HTMLWindowMenu show failure path currently throws TypeError', () => {
    resetLegacyRuntime();
    const { HTMLWindowMenu, setMode } = setupHTMLWindowMenu();
    const menu = new HTMLWindowMenu('/docs', 'Documentation', 'extra');

    setMode('failure');
    assert.throws(() => menu.show(), TypeError);
});
