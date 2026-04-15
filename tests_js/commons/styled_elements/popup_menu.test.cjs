const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPopupMenu = () => {
    class PopupMenuBase {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.showCalls = [];
            this.hideCalls = 0;
            this.destroyCalls = 0;
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

    global.StyledElements = {
        PopupMenuBase,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PopupMenu.js');
    return StyledElements.PopupMenu;
};

test('StyledElements.PopupMenu constructor stores disable callback', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();

    assert.equal(typeof popup._disableCallback, 'function');
});

test('StyledElements.PopupMenu show registers click listener and delegates to base show', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();

    const result = popup.show({x: 1, y: 2});

    assert.equal(result, popup);
    assert.equal(document.listeners.click.length > 0, true);
    assert.deepEqual(popup.showCalls[0], {x: 1, y: 2});
});

test('StyledElements.PopupMenu disable callback ignores non-left click buttons', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();
    let timeoutCalls = 0;
    const originalSetTimeout = global.setTimeout;
    global.setTimeout = () => {
        timeoutCalls += 1;
    };

    popup._disableCallback({button: 1});

    global.setTimeout = originalSetTimeout;
    assert.equal(timeoutCalls, 0);
});

test('StyledElements.PopupMenu disable callback hides menu on outside clicks', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();
    popup.wrapperElement.getBoundingClientRect = () => ({
        left: 10,
        right: 20,
        top: 10,
        bottom: 20,
    });

    const originalSetTimeout = global.setTimeout;
    global.setTimeout = (callback) => {
        callback();
    };

    popup._disableCallback({
        button: 0,
        clientX: 30,
        clientY: 30,
    });

    global.setTimeout = originalSetTimeout;
    assert.equal(popup.hideCalls, 1);
});

test('StyledElements.PopupMenu disable callback keeps menu open on inside clicks', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();
    popup.wrapperElement.getBoundingClientRect = () => ({
        left: 10,
        right: 20,
        top: 10,
        bottom: 20,
    });
    let timeoutCalls = 0;
    const originalSetTimeout = global.setTimeout;
    global.setTimeout = () => {
        timeoutCalls += 1;
    };

    popup._disableCallback({
        button: 0,
        clientX: 15,
        clientY: 15,
    });

    global.setTimeout = originalSetTimeout;
    assert.equal(timeoutCalls, 0);
});

test('StyledElements.PopupMenu hide removes listeners and returns popup', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();
    popup.show({});

    const result = popup.hide();

    assert.equal(result, popup);
    assert.equal(popup.hideCalls, 1);
});

test('StyledElements.PopupMenu destroy nulls callback and delegates to base', () => {
    resetLegacyRuntime();
    const PopupMenu = setupPopupMenu();
    const popup = new PopupMenu();

    popup.destroy();

    assert.equal(popup._disableCallback, null);
    assert.equal(popup.destroyCalls, 1);
});
