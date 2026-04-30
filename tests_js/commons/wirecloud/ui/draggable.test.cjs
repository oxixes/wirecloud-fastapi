const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupDraggable = () => {
    const prevented = [];
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
        listeners.slice().forEach((listener) => {
            listener(event);
        });
        return true;
    };

    global.Wirecloud = {
        ui: {},
        Utils: {
            preventDefaultListener(event) {
                prevented.push(event.type);
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Draggable.js');
    return {Draggable: Wirecloud.ui.Draggable, prevented};
};

const createMouseEvent = (type, extra = {}) => ({
    type,
    button: 0,
    clientX: 0,
    clientY: 0,
    preventDefault() {},
    stopPropagation() {},
    ...extra,
});

const createTouchEvent = (type, x, y, touchesLength = 1) => ({
    type,
    touches: touchesLength > 0 ? [{clientX: x, clientY: y}] : [],
    preventDefault() {},
    stopPropagation() {},
});

test('Wirecloud.ui.Draggable ignores non-left mousedown and supports destroy cleanup', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const onDragCalls = [];
    const draggable = new Draggable(
        handler,
        {},
        () => null,
        (_e, _draggable, _data, xDelta, yDelta) => {
            onDragCalls.push({xDelta, yDelta});
        },
        () => {},
    );

    handler.dispatchEvent(createMouseEvent('mousedown', {button: 1}));
    document.dispatchEvent(createMouseEvent('mousemove', {clientX: 20, clientY: 10}));
    assert.equal(onDragCalls.length, 0);

    draggable.destroy();
    handler.dispatchEvent(createMouseEvent('mousedown'));
    document.dispatchEvent(createMouseEvent('mousemove', {clientX: 40, clientY: 30}));
    assert.equal(onDragCalls.length, 0);
});

test('Wirecloud.ui.Draggable canBeDragged=false prevents starting drag', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const onDragCalls = [];
    const canBeDragged = () => false;
    new Draggable(
        handler,
        {},
        () => null,
        () => {
            onDragCalls.push('drag');
        },
        () => {},
        canBeDragged,
    );

    handler.dispatchEvent(createMouseEvent('mousedown'));
    document.dispatchEvent(createMouseEvent('mousemove', {clientX: 10, clientY: 5}));

    assert.equal(onDragCalls.length, 0);
});

test('Wirecloud.ui.Draggable mouse drag computes deltas and finalizes on mouseup', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const calls = {start: 0, drag: [], finish: 0};
    new Draggable(
        handler,
        {id: 'ctx'},
        () => {
            calls.start += 1;
            return null;
        },
        (_e, _draggable, _data, xDelta, yDelta) => {
            calls.drag.push({xDelta, yDelta});
        },
        () => {
            calls.finish += 1;
        },
    );

    handler.dispatchEvent(createMouseEvent('mousedown', {clientX: 10, clientY: 20}));
    document.dispatchEvent(createMouseEvent('mousemove', {clientX: 35, clientY: 55}));
    document.dispatchEvent(createMouseEvent('mouseup', {button: 0}));

    assert.equal(calls.start, 1);
    assert.deepEqual(calls.drag[0], {xDelta: 25, yDelta: 35});
    assert.equal(calls.finish, 1);
});

test('Wirecloud.ui.Draggable touch drag path calls preventDefault and computes deltas', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const calls = {drag: []};
    let prevented = 0;
    new Draggable(
        handler,
        {},
        () => null,
        (_e, _draggable, _data, xDelta, yDelta) => {
            calls.drag.push({xDelta, yDelta});
        },
        () => {},
    );

    const startEvent = createTouchEvent('touchstart', 30, 40, 1);
    startEvent.preventDefault = () => {
        prevented += 1;
    };
    handler.dispatchEvent(startEvent);
    const moveEvent = createTouchEvent('touchmove', 70, 65, 1);
    moveEvent.preventDefault = () => {
        prevented += 1;
    };
    document.dispatchEvent(moveEvent);
    document.dispatchEvent(createTouchEvent('touchend', 0, 0, 0));

    assert.equal(prevented >= 2, true);
    assert.deepEqual(calls.drag[0], {xDelta: 40, yDelta: 25});
});

test('Wirecloud.ui.Draggable dragboard cover and scroll adjust deltas and cleanup', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const dragboard = document.createElement('div');
    dragboard.scrollHeight = 500;
    dragboard.scrollTop = 100;
    dragboard.scrollLeft = 50;
    const calls = {finish: 0, drag: []};

    new Draggable(
        handler,
        {},
        () => ({dragboard}),
        (_e, _draggable, _data, xDelta, yDelta) => {
            calls.drag.push({xDelta, yDelta});
        },
        () => {
            calls.finish += 1;
        },
    );

    handler.dispatchEvent(createMouseEvent('mousedown', {clientX: 20, clientY: 30}));
    const cover = dragboard.childNodes[0];
    assert.equal(cover.className, 'cover');
    assert.equal(cover.style.height, '500px');

    document.dispatchEvent(createMouseEvent('mousemove', {clientX: 60, clientY: 80}));
    dragboard.scrollTop = 70;
    dragboard.scrollLeft = 30;
    dragboard.dispatchEvent({type: 'scroll'});

    assert.deepEqual(calls.drag.at(-1), {xDelta: 20, yDelta: 20});

    document.dispatchEvent(createMouseEvent('mouseup', {button: 0}));
    assert.equal(dragboard.childNodes.length, 0);
    assert.equal(calls.finish, 1);
});

test('Wirecloud.ui.Draggable enddrag ignores non-final events', () => {
    resetLegacyRuntime();
    const {Draggable} = setupDraggable();
    const handler = document.createElement('div');
    const calls = {finish: 0};
    new Draggable(
        handler,
        {},
        () => null,
        () => {},
        () => {
            calls.finish += 1;
        },
    );

    handler.dispatchEvent(createMouseEvent('mousedown', {clientX: 10, clientY: 10}));
    document.dispatchEvent(createMouseEvent('mouseup', {button: 1}));
    assert.equal(calls.finish, 0);
    document.dispatchEvent(createTouchEvent('touchend', 0, 0, 1));
    assert.equal(calls.finish, 0);

    document.dispatchEvent(createTouchEvent('touchend', 0, 0, 0));
    assert.equal(calls.finish, 1);
});
