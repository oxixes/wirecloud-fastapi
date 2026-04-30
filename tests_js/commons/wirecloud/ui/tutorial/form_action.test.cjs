const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupFormAction = () => {
    class FakeSimpleDescription {
        constructor(tutorial, options) {
            this.tutorial = tutorial;
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.wrapperElement.offsetHeight = 20;
            this.wrapperElement.offsetWidth = 30;
            this.destroyCalls = 0;
            this.setLastCalls = 0;
        }

        setLast() {
            this.setLastCalls += 1;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class FakeUserAction {
        constructor(tutorial, options) {
            this.tutorial = tutorial;
            this.options = options;
            this.setNextCalls = 0;
            this.activateCalls = 0;
            this.destroyCalls = 0;
        }

        setNext() {
            this.setNextCalls += 1;
        }

        activate() {
            this.activateCalls += 1;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class FakePopUp {
        constructor(element, options) {
            this.element = element;
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.repaintCalls = 0;
            this.destroyCalls = 0;
        }

        repaint() {
            this.repaintCalls += 1;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.Wirecloud = {
        Utils: {
            gettext: (text) => `tx:${text}`,
        },
        ui: {
            Tutorial: {
                SimpleDescription: FakeSimpleDescription,
                UserAction: FakeUserAction,
                PopUp: FakePopUp,
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/FormAction.js');

    return {
        FormAction: Wirecloud.ui.Tutorial.FormAction,
        FakeSimpleDescription,
        FakeUserAction,
        FakePopUp,
    };
};

const createElement = (box) => {
    const element = document.createElement('div');
    element.getBoundingClientRect = () => box;
    return element;
};

const createInputElement = (box) => {
    const element = createElement(box);
    element.listeners = {};
    element.addEventListener = (name, listener) => {
        element.listeners[name] = listener;
    };
    return element;
};

const buildTutorial = () => {
    const msgLayer = document.createElement('div');
    return {
        msgLayer,
        resetControlLayerCalls: 0,
        deactivateLayerCalls: 0,
        resetControlLayer() {
            this.resetControlLayerCalls += 1;
        },
        deactivateLayer() {
            this.deactivateLayerCalls += 1;
        },
        nextStep() {},
    };
};

const buildForm = () => {
    const form = function () {
        return form;
    };
    form.acceptButton = {
        disabledCalls: 0,
        enabledCalls: 0,
        disable() {
            this.disabledCalls += 1;
        },
        enable() {
            this.enabledCalls += 1;
        }
    };
    form.cancelButton = {
        disabledCalls: 0,
        disable() {
            this.disabledCalls += 1;
        }
    };
    form.getBoundingClientRect = () => ({ top: 10, right: 60, left: 20, bottom: 50 });
    return form;
};

test('FormAction constructor normalizes options and creates main step', () => {
    resetLegacyRuntime();
    const { FormAction, FakeSimpleDescription } = setupFormAction();
    const tutorial = buildTutorial();
    const action = new FormAction(tutorial, {
        asynchronous: 'yes',
        mainTitle: 'Title',
        mainMsg: 'Body',
        disableElems: null,
        actionElements: [],
        actionElementsPos: [],
        actionElementsValidators: [],
        actionMsgs: [],
        form: buildForm(),
        endElementPos: 'down'
    });

    assert.equal(action.options.asynchronous, true);
    assert.ok(action.mainStep instanceof FakeSimpleDescription);
    assert.equal(action.mainStep.options.title, 'tx:Title');
    assert.equal(action.mainStep.setLastCalls, 1);
    assert.deepEqual(action.disableElems, []);
});

test('FormAction setLast and setNext update handlers', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const action = new FormAction(tutorial, {
        actionElements: [],
        actionElementsPos: [],
        actionElementsValidators: [],
        actionMsgs: [],
        form: buildForm()
    });
    let nextCalls = 0;
    tutorial.nextStep = () => {
        nextCalls += 1;
    };

    action.setLast();
    action.setNext();
    action.nextHandler();

    assert.equal(action.last, true);
    assert.equal(nextCalls, 1);
});

test('FormAction activate creates end action, substeps and disables elements', () => {
    resetLegacyRuntime();
    const { FormAction, FakePopUp, FakeUserAction } = setupFormAction();
    const tutorial = buildTutorial();
    const fieldA = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const fieldB = createInputElement({ top: 5, left: 6, width: 35, height: 12 });
    const disA = createElement({ top: 10, left: 11, width: 20, height: 21 });
    const disB = createElement({ top: 12, left: 13, width: 22, height: 23 });
    const validators = [
        (value) => value === 'ok',
        () => true,
    ];
    const form = buildForm();

    const action = new FormAction(tutorial, {
        mainMsg: 'Body',
        mainTitle: 'Title',
        mainPos: 'up',
        actionElements: [() => fieldA, () => fieldB],
        actionElementsPos: ['left', 'right'],
        actionElementsValidators: validators,
        actionMsgs: ['A', 'B'],
        disableElems: [() => disA, () => disB],
        form,
        endElementMsg: 'done',
        endElementPos: 'down',
    });

    action.activate();

    assert.ok(action.endAction instanceof FakeUserAction);
    assert.equal(action.endAction.setNextCalls, 1);
    assert.equal(action.endAction.activateCalls, 1);
    assert.equal(action.subSteps.length, 2);
    assert.ok(action.subSteps[0] instanceof FakePopUp);
    assert.equal(action.subSteps[0].wrapperElement.classList.contains('subFormAction'), true);
    assert.equal(form.cancelButton.disabledCalls, 1);
    assert.equal(tutorial.resetControlLayerCalls, 1);
    assert.equal(tutorial.deactivateLayerCalls, 1);
    assert.equal(action.disableLayer.length, 2);
});

test('FormAction validateInput toggles invalid class and accept button state', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    let valid = false;
    const form = buildForm();
    const action = new FormAction(tutorial, {
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => valid],
        actionMsgs: ['A'],
        form,
    });

    action.activate();
    field.listeners.keyup();
    assert.equal(action.subSteps[0].wrapperElement.classList.contains('invalid'), true);
    assert.equal(form.acceptButton.disabledCalls > 0, true);

    valid = true;
    field.listeners.keyup();
    assert.equal(action.subSteps[0].wrapperElement.classList.contains('invalid'), false);
    assert.equal(form.acceptButton.enabledCalls, 1);
});

test('FormAction focus and blur handlers toggle activate class', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const action = new FormAction(tutorial, {
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form: buildForm(),
    });

    action.activate();
    field.listeners.focus();
    assert.equal(action.subSteps[0].wrapperElement.classList.contains('activate'), true);

    field.listeners.blur();
    assert.equal(action.subSteps[0].wrapperElement.classList.contains('activate'), false);
});

test('FormAction mainStep right position sets left style', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const action = new FormAction(tutorial, {
        mainMsg: 'Body',
        mainTitle: 'Title',
        mainPos: 'right',
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form: buildForm(),
    });

    action.activate();

    assert.equal(action.mainStep.wrapperElement.style.left, '80px');
});

test('FormAction mainStep left position sets left style', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const action = new FormAction(tutorial, {
        mainMsg: 'Body',
        mainTitle: 'Title',
        mainPos: 'left',
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form: buildForm(),
    });

    action.activate();

    assert.equal(action.mainStep.wrapperElement.style.left, '-30px');
});

test('FormAction mainStep down position sets top style', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const action = new FormAction(tutorial, {
        mainMsg: 'Body',
        mainTitle: 'Title',
        mainPos: 'down',
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form: buildForm(),
    });

    action.activate();

    assert.equal(action.mainStep.wrapperElement.style.top, '70px');
});

test('FormAction mainStep default position leaves styles unchanged', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    const action = new FormAction(tutorial, {
        mainMsg: 'Body',
        mainTitle: 'Title',
        mainPos: 'unknown',
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form: buildForm(),
    });

    action.activate();

    assert.equal(action.mainStep.wrapperElement.style.top, undefined);
    assert.equal(action.mainStep.wrapperElement.style.left, undefined);
});

test('FormAction activate asynchronous form callback path', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const field = createInputElement({ top: 1, left: 2, width: 30, height: 10 });
    let callbackType = null;
    const action = new FormAction(tutorial, {
        asynchronous: true,
        actionElements: [() => field],
        actionElementsPos: ['up'],
        actionElementsValidators: [() => true],
        actionMsgs: ['A'],
        form(callback) {
            callbackType = typeof callback;
            callback(buildForm());
        },
    });

    action.activate();

    assert.equal(callbackType, 'function');
    assert.equal(action.element != null, true);
});

test('FormAction disable creates overlay using element box', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const action = new FormAction(tutorial, {
        actionElements: [],
        actionElementsPos: [],
        actionElementsValidators: [],
        actionMsgs: [],
        form: buildForm(),
    });
    const target = createElement({ top: 9, left: 8, width: 70, height: 60 });

    const layer = action.disable(target);

    assert.equal(layer.classList.contains('disableLayer'), true);
    assert.equal(layer.style.top, '9px');
    assert.equal(layer.style.left, '8px');
    assert.equal(layer.style.width, '70px');
    assert.equal(layer.style.height, '60px');
});

test('FormAction destroy removes overlays and destroys child steps', () => {
    resetLegacyRuntime();
    const { FormAction } = setupFormAction();
    const tutorial = buildTutorial();
    const action = new FormAction(tutorial, {
        actionElements: [],
        actionElementsPos: [],
        actionElementsValidators: [],
        actionMsgs: [],
        form: buildForm(),
    });
    const disableLayer = document.createElement('div');
    tutorial.msgLayer.appendChild(disableLayer);
    action.disableLayer = [disableLayer];
    action.subSteps = [{
        destroyed: 0,
        destroy() {
            this.destroyed += 1;
        }
    }];
    action.mainStep = {
        destroyed: 0,
        destroy() {
            this.destroyed += 1;
        }
    };
    action.endAction = {
        destroyed: 0,
        destroy() {
            this.destroyed += 1;
        }
    };

    action.destroy();

    assert.equal(tutorial.msgLayer.childNodes.length, 0);
    assert.equal(action.subSteps[0].destroyed, 1);
    assert.equal(action.mainStep, null);
    assert.equal(action.endAction, null);
});
