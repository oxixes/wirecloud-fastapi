const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupUserAction = () => {
    class FakePopUp {
        constructor(element, options) {
            this.element = element;
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.listeners = {};
            this.repaintCalls = 0;
            this.destroyCalls = 0;
        }

        repaint() {
            this.repaintCalls += 1;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.NodeList = class NodeList extends Array {};
    global.Wirecloud = {
        ui: {
            Tutorial: {
                PopUp: FakePopUp,
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/UserAction.js');

    return {
        UserAction: Wirecloud.ui.Tutorial.UserAction,
        FakePopUp,
    };
};

const createElement = (box = { top: 1, left: 2, width: 30, height: 10 }) => {
    const element = document.createElement('div');
    element.getBoundingClientRect = () => ({
        ...box,
        right: box.left + box.width,
        bottom: box.top + box.height,
    });
    return element;
};

const createTutorial = () => {
    const msgLayer = document.createElement('div');
    return {
        msgLayer,
        destroyCalls: 0,
        nextStepCalls: 0,
        deactivateLayerCalls: 0,
        setControlLayerCalls: [],
        destroy() {
            this.destroyCalls += 1;
        },
        nextStep() {
            this.nextStepCalls += 1;
        },
        deactivateLayer() {
            this.deactivateLayerCalls += 1;
        },
        setControlLayer(element) {
            this.setControlLayerCalls.push(element);
        },
    };
};

test('UserAction constructor defaults and setLast/setNext handlers', () => {
    resetLegacyRuntime();
    const { UserAction } = setupUserAction();
    const tutorial = createTutorial();
    const elem = createElement();
    const action = new UserAction(tutorial, { elem });

    action.setLast();
    action.nextHandler('event-data');
    assert.equal(action.last, true);
    assert.equal(tutorial.destroyCalls, 1);

    action.setNext();
    action.isWaitingForDeactivateLayerEvent = true;
    action.nextHandler();
    assert.equal(tutorial.nextStepCalls, 0);
    action.isWaitingForDeactivateLayerEvent = false;

    action.next_element = elem;
    action.nextHandler();
    assert.equal(tutorial.nextStepCalls, 1);
    assert.equal(action.next_element, null);
});

test('UserAction activate next-step phase supports msg, targetElement and filter', () => {
    resetLegacyRuntime();
    const { UserAction } = setupUserAction();
    const tutorial = createTutorial();
    const elem = createElement();
    const target = createElement();

    let filteredCalls = 0;
    const action = new UserAction(tutorial, {
        elem,
        msg: 'click here',
        pos: 'up',
        secondPos: 'right',
        targetElement: () => target,
        eventFilterFunction() {
            filteredCalls += 1;
            return false;
        },
    });

    action.activate();

    assert.equal(action.popup.element, target);
    assert.equal(action.popup.options.position, 'right');
    assert.equal(action.next_element, elem);
    assert.equal(tutorial.setControlLayerCalls[0], elem);
    action.popup.listeners.close();
    assert.equal(tutorial.destroyCalls, 1);

    action.nextHandler('x');
    assert.equal(filteredCalls, 1);
    assert.equal(tutorial.destroyCalls, 1);
});

test('UserAction start/deactivate layer path builds restart handlers and disabled overlays', () => {
    resetLegacyRuntime();
    const { UserAction } = setupUserAction();
    const tutorial = createTutorial();
    const start = createElement();
    const next = createElement();
    const restartA = createElement();
    const restartB = createElement();
    const disableA = createElement({ top: 10, left: 20, width: 11, height: 12 });
    const disableB = createElement({ top: 30, left: 40, width: 21, height: 22 });
    const disableC = createElement({ top: 50, left: 60, width: 31, height: 32 });
    const nodeList = new NodeList(disableA, disableB);

    const action = new UserAction(tutorial, {
        elem: () => next,
        eventToDeactivateLayer: 'blur',
        event: 'click',
        msg: 'start',
        nextStepMsg: 'next-msg',
        disableElems: [disableA, () => nodeList, () => [disableB], () => disableC],
        restartHandlers: [
            { element: () => restartA, event: 'keydown' },
            { element: restartB, event: 'click' },
        ],
        elemToApplyDeactivateLayerEvent: () => start,
    });

    action.activate();
    assert.equal(action.popup.options.msg, 'start');
    assert.equal(tutorial.setControlLayerCalls[0], start);

    action.deactivateLayer();
    assert.equal(tutorial.deactivateLayerCalls, 1);
    assert.equal(action.disableLayer.length, 5);
    assert.equal(action.disableLayer[0].className, 'disableLayer');
    assert.equal(action.popup.options.msg, 'next-msg');
    assert.equal(action.restart_handlers.length, 2);

    restartA.listeners.keydown[0]();
    assert.equal(action.next_element, null);
    assert.equal(action.isWaitingForDeactivateLayerEvent, true);
});

test('UserAction disable helper and activate asynchronous path', () => {
    resetLegacyRuntime();
    const { UserAction } = setupUserAction();
    const tutorial = createTutorial();
    const elem = createElement({ top: 2, left: 3, width: 40, height: 50 });

    let callbackType = null;
    const action = new UserAction(tutorial, {
        asynchronous: true,
        elem(callback) {
            if (typeof callback === 'function') {
                callbackType = typeof callback;
                callback(elem);
            }
            return elem;
        },
        msg: null,
        eventCapture: false,
    });

    const layer = action.disable(elem);
    assert.equal(layer.style.top, '2px');
    assert.equal(layer.style.left, '3px');
    assert.equal(layer.style.width, '40px');
    assert.equal(layer.style.height, '50px');

    action.activate();
    assert.equal(callbackType, 'function');
    assert.equal(action.options.eventCapture, false);
});

test('UserAction destroy removes handlers, overlays and popup', () => {
    resetLegacyRuntime();
    const { UserAction } = setupUserAction();
    const tutorial = createTutorial();
    const start = createElement();
    const next = createElement();
    const restart = createElement();

    const action = new UserAction(tutorial, {
        elem: next,
        eventToDeactivateLayer: 'focus',
        restartHandlers: [{ element: restart, event: 'click' }],
    });
    action.start_element = start;
    action.next_element = next;
    action.restart_handlers = [{ element: restart, event: 'click', func: action.restartStep }];
    const disableLayer = document.createElement('div');
    tutorial.msgLayer.appendChild(disableLayer);
    action.disableLayer = [disableLayer];
    action.popup = {
        destroyed: 0,
        destroy() {
            this.destroyed += 1;
        },
    };

    action.destroy();

    assert.equal(action.start_element, null);
    assert.equal(action.next_element, null);
    assert.equal(action.disableLayer, null);
    assert.equal(action.popup.destroyed, 1);
    assert.equal(action.textElement, null);
    assert.equal(action.arrow, null);
});


