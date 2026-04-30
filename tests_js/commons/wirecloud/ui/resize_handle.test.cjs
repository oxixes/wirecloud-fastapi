const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupResizeHandle = () => {
    const documentListeners = {};

    document.addEventListener = (type, listener) => {
        if (!(type in documentListeners)) {
            documentListeners[type] = [];
        }
        documentListeners[type].push(listener);
    };
    document.removeEventListener = (type, listener) => {
        if (!(type in documentListeners)) {
            return;
        }
        documentListeners[type] = documentListeners[type].filter((entry) => entry !== listener);
    };
    document.dispatchEvent = (event) => {
        const listeners = documentListeners[event.type] || [];
        listeners.slice().forEach((listener) => listener(event));
        return true;
    };

    global.Wirecloud = {
        ui: {},
        Utils: {
            preventDefaultListener() {},
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/ResizeHandle.js');
    return Wirecloud.ui.ResizeHandle;
};

const mouseEvent = (type, extra = {}) => ({
    type,
    button: 0,
    clientX: 0,
    clientY: 0,
    ...extra,
});

const touchEvent = (type, x, y, touchesLength = 1) => ({
    type,
    touches: touchesLength > 0 ? [{clientX: x, clientY: y}] : [],
    preventDefault() {},
});

test('Wirecloud.ui.ResizeHandle ignores non-left start and supports destroy', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const resizable = document.createElement('div');
    const handle = document.createElement('div');
    const calls = [];
    const rh = new ResizeHandle(
        resizable,
        handle,
        {},
        () => {},
        (_resizable, _handle, _data, xDelta, yDelta) => calls.push({xDelta, yDelta}),
        () => {},
    );

    handle.dispatchEvent(mouseEvent('mousedown', {button: 1}));
    document.dispatchEvent(mouseEvent('mousemove', {clientX: 40, clientY: 30}));
    assert.equal(calls.length, 0);

    rh.destroy();
    handle.dispatchEvent(mouseEvent('mousedown', {button: 0}));
    document.dispatchEvent(mouseEvent('mousemove', {clientX: 80, clientY: 60}));
    assert.equal(calls.length, 0);
});

test('Wirecloud.ui.ResizeHandle canBeResized=false prevents resize', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const handle = document.createElement('div');
    let resized = 0;
    new ResizeHandle(
        document.createElement('div'),
        handle,
        {},
        () => {},
        () => {
            resized += 1;
        },
        () => {},
        () => false,
    );

    handle.dispatchEvent(mouseEvent('mousedown', {button: 0}));
    document.dispatchEvent(mouseEvent('mousemove', {clientX: 20, clientY: 15}));
    assert.equal(resized, 0);
});

test('Wirecloud.ui.ResizeHandle mouse resize computes deltas and finishes', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const handle = document.createElement('div');
    const calls = {start: 0, resize: [], finish: 0};
    new ResizeHandle(
        document.createElement('div'),
        handle,
        {},
        () => {
            calls.start += 1;
        },
        (_resizable, _handle, _data, xDelta, yDelta) => {
            calls.resize.push({xDelta, yDelta});
        },
        () => {
            calls.finish += 1;
        },
    );

    handle.dispatchEvent(mouseEvent('mousedown', {clientX: 10, clientY: 10}));
    document.dispatchEvent(mouseEvent('mousemove', {clientX: 45, clientY: 40}));
    document.dispatchEvent(mouseEvent('mouseup', {button: 0}));

    assert.equal(calls.start, 1);
    assert.deepEqual(calls.resize[0], {xDelta: 35, yDelta: 30});
    assert.equal(calls.finish, 1);
});

test('Wirecloud.ui.ResizeHandle touch path and end guards work', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const handle = document.createElement('div');
    let touchPrevented = 0;
    let finish = 0;
    new ResizeHandle(
        document.createElement('div'),
        handle,
        {},
        () => {},
        () => {},
        () => {
            finish += 1;
        },
    );

    handle.dispatchEvent(touchEvent('touchstart', 20, 30, 1));
    const move = touchEvent('touchmove', 25, 40, 1);
    move.preventDefault = () => {
        touchPrevented += 1;
    };
    document.dispatchEvent(move);
    document.dispatchEvent(touchEvent('touchend', 0, 0, 1));
    assert.equal(finish, 0);
    document.dispatchEvent(touchEvent('touchend', 0, 0, 0));
    assert.equal(finish, 1);
    assert.equal(touchPrevented, 1);
});

test('Wirecloud.ui.ResizeHandle mouse end guard ignores non-left mouseup', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const handle = document.createElement('div');
    let finish = 0;
    new ResizeHandle(
        document.createElement('div'),
        handle,
        {},
        () => {},
        () => {},
        () => {
            finish += 1;
        },
    );

    handle.dispatchEvent(mouseEvent('mousedown', {clientX: 10, clientY: 10}));
    document.dispatchEvent(mouseEvent('mouseup', {button: 1}));
    assert.equal(finish, 0);
    document.dispatchEvent(mouseEvent('mouseup', {button: 0}));
    assert.equal(finish, 1);
});

test('Wirecloud.ui.ResizeHandle scroll updates resize deltas and setResizableElement works', () => {
    resetLegacyRuntime();
    const ResizeHandle = setupResizeHandle();
    const handle = document.createElement('div');
    const first = document.createElement('div');
    const second = document.createElement('div');
    document.body.scrollTop = 100;
    document.body.scrollHeight = 400;
    const deltas = [];
    const rh = new ResizeHandle(
        first,
        handle,
        {},
        () => {},
        (resizable, _handle, _data, xDelta, yDelta) => {
            deltas.push({resizable, xDelta, yDelta});
        },
        () => {},
    );

    rh.setResizableElement(second);
    handle.dispatchEvent(mouseEvent('mousedown', {clientX: 10, clientY: 10}));
    document.dispatchEvent(mouseEvent('mousemove', {clientX: 30, clientY: 50}));
    document.body.scrollTop = 70;
    document.body.dispatchEvent({type: 'scroll'});
    document.dispatchEvent(mouseEvent('mouseup', {button: 0}));

    assert.equal(deltas.at(-1).resizable, second);
    assert.deepEqual(deltas.at(-1), {resizable: second, xDelta: 20, yDelta: 10});
});
