const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupSimpleDescription = () => {
    class FakeWindowMenu {
        constructor(title, className) {
            this.title = title;
            this.className = className;
            this.htmlElement = document.createElement('div');
            this.htmlElement.style = {};
            this.htmlElement.offsetHeight = 50;
            this.htmlElement.offsetWidth = 80;
            this.windowContent = document.createElement('div');
            this.windowBottom = document.createElement('div');
            this.htmlElement.appendChild(this.windowContent);
            this.htmlElement.appendChild(this.windowBottom);
            this.closedEvents = [];
        }

        _closeListener(event) {
            this.closedEvents.push(event);
        }
    }

    class FakeButton {
        constructor(options) {
            this.options = options;
            this.listeners = {};
            this.label = options.text;
            this.focusCalls = 0;
            this.removed = 0;
        }

        insertInto(parent) {
            this.parent = parent;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        removeEventListener(name) {
            delete this.listeners[name];
        }

        setLabel(label) {
            this.label = label;
        }

        remove() {
            this.removed += 1;
        }

        focus() {
            this.focusCalls += 1;
        }
    }

    global.StyledElements = {
        Button: FakeButton,
    };
    global.Wirecloud = {
        Utils: {
            gettext: (text) => `tx:${text}`,
        },
        ui: {
            WindowMenu: FakeWindowMenu,
            Tutorial: {},
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/SimpleDescription.js');

    return {
        SimpleDescription: Wirecloud.ui.Tutorial.SimpleDescription,
        FakeButton,
    };
};

const createTutorial = () => {
    const msgLayer = document.createElement('div');
    return {
        msgLayer,
        destroyCalls: 0,
        nextStepCalls: 0,
        setControlLayerCalls: [],
        resetControlLayerCalls: [],
        destroy() {
            this.destroyCalls += 1;
        },
        nextStep() {
            this.nextStepCalls += 1;
        },
        setControlLayer(element, center) {
            this.setControlLayerCalls.push({ element, center });
        },
        resetControlLayer(transparent) {
            this.resetControlLayerCalls.push(transparent);
        },
    };
};

const buildRect = ({ top = 20, left = 40, width = 100, height = 30 }) => ({
    top,
    left,
    width,
    height,
    right: left + width,
    bottom: top + height,
});

test('SimpleDescription constructor and close listener wire title, buttons and layer', () => {
    resetLegacyRuntime();
    const { SimpleDescription } = setupSimpleDescription();
    const tutorial = createTutorial();
    const step = new SimpleDescription(tutorial, {
        title: 'Main',
        msg: 'Body',
        pos: 'down',
        elem: null,
    });

    step._closeListener('evt');

    assert.equal(step.nextButton.options.class, 'nextButton btn-primary');
    assert.equal(step.cancelButton.options.class, 'cancelButton');
    assert.equal(step.windowContent.innerHTML, 'Body');
    assert.equal(tutorial.msgLayer.childNodes.includes(step.htmlElement), true);
    assert.equal(step.cancelButton.listeners.click, step._closeListener);
    assert.equal(tutorial.destroyCalls, 1);
});

test('SimpleDescription get/set position and setLast branches', () => {
    resetLegacyRuntime();
    const { SimpleDescription } = setupSimpleDescription();
    const tutorial = createTutorial();
    const step = new SimpleDescription(tutorial, {
        title: 'Main',
        msg: 'Body',
        elem: null,
        pos: 'down',
    });

    step.setPosition({ posX: 7, posY: 9 });
    assert.deepEqual(step.getStylePosition(), { posX: 7, posY: 9 });

    step.setLast();
    assert.equal(step.last, true);
    assert.equal(step.nextButton.removed, 1);
    assert.equal(step.cancelButton.label, 'tx:tx:Close');

    let optionalCalls = 0;
    step.setLast('Done', function () {
        optionalCalls += 1;
    });
    step.cancelButton.listeners.click();
    assert.equal(step.cancelButton.label, 'tx:Done');
    assert.equal(optionalCalls, 1);
});

test('SimpleDescription setNext removes highlight and advances tutorial', () => {
    resetLegacyRuntime();
    const { SimpleDescription } = setupSimpleDescription();
    const tutorial = createTutorial();
    const currentElement = document.createElement('div');
    currentElement.classList.add('tuto_highlight');
    const step = new SimpleDescription(tutorial, {
        title: 'Main',
        msg: 'Body',
        elem: currentElement,
        pos: 'down',
    });
    step.currentElement = currentElement;

    step.setNext();
    step.nextButton.listeners.click();

    assert.equal(currentElement.classList.contains('tuto_highlight'), false);
    assert.equal(tutorial.nextStepCalls, 1);
});

test('SimpleDescription activate positions around element, fixes overflow and supports async', () => {
    resetLegacyRuntime();
    const { SimpleDescription } = setupSimpleDescription();
    const tutorial = createTutorial();
    document.body.getBoundingClientRect = () => ({ top: 0, left: 0, right: 100, bottom: 100 });

    const currentElement = document.createElement('div');
    currentElement.getBoundingClientRect = () => buildRect({ top: 40, left: 40, width: 10, height: 10 });
    const step = new SimpleDescription(tutorial, {
        title: 'Main',
        msg: 'Body',
        elem: () => currentElement,
        pos: 'up',
    });

    step.htmlElement.getBoundingClientRect = () => ({
        width: 200,
        height: 200,
        top: 0,
        left: 0,
        right: 200,
        bottom: 200,
    });

    step.activate();

    assert.equal(step.htmlElement.classList.contains('activeStep'), true);
    assert.equal(currentElement.classList.contains('tuto_highlight'), true);
    assert.equal(tutorial.setControlLayerCalls.length, 1);
    assert.equal(step.nextButton.focusCalls, 1);
    assert.equal(step.htmlElement.style.top, '70px');

    const asyncStep = new SimpleDescription(tutorial, {
        title: 'Async',
        msg: 'Body',
        asynchronous: true,
        elem(callback) {
            if (typeof callback === 'function') {
                callback(currentElement);
            }
            return currentElement;
        },
    });
    asyncStep.htmlElement.getBoundingClientRect = step.htmlElement.getBoundingClientRect;
    asyncStep.activate();
    assert.equal(asyncStep.nextButton.focusCalls, 1);
});

test('SimpleDescription activate without element recenters and calls resetControlLayer', () => {
    resetLegacyRuntime();
    const { SimpleDescription } = setupSimpleDescription();
    const tutorial = createTutorial();
    window.innerHeight = 300;
    window.innerWidth = 500;

    const step = new SimpleDescription(tutorial, {
        title: 'Main',
        msg: 'Body',
        elem: null,
        pos: 'left',
        nextButtonText: 'Continue',
    });

    step.activate();

    assert.equal(step.nextButton.options.text, 'tx:Continue');
    assert.equal(tutorial.resetControlLayerCalls[0], false);
    assert.equal(step.htmlElement.style.top, '125px');
    assert.equal(step.htmlElement.style.left, '210px');
});
