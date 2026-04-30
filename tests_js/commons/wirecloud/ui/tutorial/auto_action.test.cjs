const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupAutoAction = () => {
    class FakePopup {
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

        addEventListener(event, handler) {
            this.listeners[event] = handler;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {};
    global.Wirecloud = {
        Utils: {},
        ui: {
            Tutorial: {
                PopUp: FakePopup,
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/AutoAction.js');

    return {
        AutoAction: Wirecloud.ui.Tutorial.AutoAction,
        FakePopup,
    };
};

const buildTutorial = () => {
    const msgLayer = document.createElement('div');
    const tutorial = {
        msgLayer,
        nextStepCalls: 0,
        setControlLayerCalls: [],
        resetControlLayerCalls: 0,
        destroyCalls: 0,
        nextStep() {
            this.nextStepCalls += 1;
        },
        setControlLayer(element, center) {
            this.setControlLayerCalls.push({ element, center });
        },
        resetControlLayer() {
            this.resetControlLayerCalls += 1;
        },
        destroy() {
            this.destroyCalls += 1;
        }
    };
    return tutorial;
};

test('AutoAction constructor normalizes asynchronous and stores options', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const action = new AutoAction(tutorial, {
        asynchronous: 1,
        elem: null,
        pos: 'down',
        event: 'click',
        action() {}
    });

    assert.equal(action.options.asynchronous, true);
    assert.equal(action.layer, tutorial.msgLayer);
    assert.equal(action.position, 'down');
});

test('AutoAction setLast toggles last flag', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const action = new AutoAction(tutorial, { elem: null, action() {} });

    action.setLast();

    assert.equal(action.last, true);
});

test('AutoAction setNext and nextHandler remove highlight and advance tutorial', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const element = document.createElement('div');
    element.classList.add('tuto_highlight');
    const action = new AutoAction(tutorial, { elem: element, action() {} });
    action.currentElement = element;

    action.setNext();
    action.nextHandler();

    assert.equal(element.classList.contains('tuto_highlight'), false);
    assert.equal(tutorial.nextStepCalls, 1);
});

test('AutoAction activate sync with popup configures popup and control layer', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const element = document.createElement('div');
    let actionCall = null;
    const action = new AutoAction(tutorial, {
        elem: element,
        msg: 'hello',
        pos: 'topLeft',
        action(instance, currentElement) {
            actionCall = { instance, currentElement };
        }
    });

    action.activate();

    assert.equal(action.popup.options.msg, 'hello');
    assert.equal(action.popup.options.position, 'topLeft');
    assert.equal(tutorial.msgLayer.childNodes.includes(action.popup.wrapperElement), true);
    assert.equal(tutorial.setControlLayerCalls.length, 1);
    assert.equal(actionCall.currentElement, element);
    action.popup.listeners.close();
    assert.equal(tutorial.destroyCalls, 1);
});

test('AutoAction activate sync with null element resets control layer', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    let called = 0;
    const action = new AutoAction(tutorial, {
        elem: null,
        action() {
            called += 1;
        }
    });

    action.activate();

    assert.equal(tutorial.resetControlLayerCalls, 1);
    assert.equal(called, 1);
});

test('AutoAction activate asynchronous invokes callback path', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const element = document.createElement('div');
    let callbackType = null;
    const action = new AutoAction(tutorial, {
        asynchronous: true,
        elem(callback) {
            callbackType = typeof callback;
            callback(element);
        },
        action() {}
    });

    action.activate();

    assert.equal(callbackType, 'function');
    assert.equal(action.currentElement, element);
});

test('AutoAction activate sync resolves function elements', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const element = document.createElement('div');
    const action = new AutoAction(tutorial, {
        elem() {
            return element;
        },
        action() {}
    });

    action.activate();

    assert.equal(action.currentElement, element);
    assert.equal(tutorial.setControlLayerCalls.length, 1);
});

test('AutoAction destroy handles function element and popup cleanup', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    const action = new AutoAction(tutorial, {
        elem() {},
        action() {}
    });
    action.popup = {
        destroyCalls: 0,
        destroy() {
            this.destroyCalls += 1;
        }
    };
    action.textElement = {};
    action.arrow = {};

    action.destroy();

    assert.equal(action.element, null);
    assert.equal(action.popup.destroyCalls, 1);
    assert.equal(action.textElement, null);
    assert.equal(action.arrow, null);
});

test('AutoAction destroy unregisters click listener for plain element', () => {
    resetLegacyRuntime();
    const { AutoAction } = setupAutoAction();
    const tutorial = buildTutorial();
    let removeListenerArgs = null;
    const element = {
        removeEventListener(event, handler, capture) {
            removeListenerArgs = { event, handler, capture };
        }
    };
    const action = new AutoAction(tutorial, {
        elem: element,
        action() {}
    });
    action.setNext();

    action.destroy();

    assert.equal(removeListenerArgs.event, 'click');
    assert.equal(removeListenerArgs.handler, action.nextHandler);
    assert.equal(removeListenerArgs.capture, true);
});
