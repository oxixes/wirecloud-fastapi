const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupTutorial = () => {
    const scheduled = [];
    global.setTimeout = (fn) => {
        scheduled.push(fn);
        return scheduled.length;
    };

    global.utils = {
        gettext: (text) => text,
    };

    global.Wirecloud = {
        ui: {},
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial.js');

    class BaseStep {
        constructor(tutorial, instruction) {
            this.tutorial = tutorial;
            this.instruction = instruction;
            this.flags = {last: 0, next: 0, activated: 0, destroyed: 0};
            BaseStep.instances.push(this);
        }

        setLast() {
            this.flags.last += 1;
        }

        setNext() {
            this.flags.next += 1;
        }

        activate() {
            this.flags.activated += 1;
        }

        destroy() {
            this.flags.destroyed += 1;
        }
    }
    BaseStep.instances = [];

    Wirecloud.ui.Tutorial.SimpleDescription = BaseStep;
    Wirecloud.ui.Tutorial.UserAction = BaseStep;
    Wirecloud.ui.Tutorial.FormAction = BaseStep;
    Wirecloud.ui.Tutorial.AutoAction = BaseStep;

    return {
        Tutorial: Wirecloud.ui.Tutorial,
        BaseStep,
        scheduled,
    };
};

test('Wirecloud.ui.Tutorial constructor initializes layers and metadata', () => {
    resetLegacyRuntime();
    const {Tutorial} = setupTutorial();
    const tutorial = new Tutorial('Label', []);

    assert.equal(tutorial.label, 'Label');
    assert.equal(tutorial.controlLayer.className, 'controlLayer');
    assert.equal(tutorial.controlLayer.childNodes.length, 5);
    assert.deepEqual(tutorial.steps, []);
});

test('Wirecloud.ui.Tutorial start builds steps, marks last/next and activates first', () => {
    resetLegacyRuntime();
    const {Tutorial, BaseStep} = setupTutorial();
    const instructions = [
        {type: 'simpleDescription'},
        {type: 'userAction'},
        {type: 'formAction'},
        {type: 'autoAction'},
    ];
    const tutorial = new Tutorial('Label', instructions);

    tutorial.start();

    assert.equal(document.body.childNodes.includes(tutorial.controlLayer), true);
    assert.equal(document.body.childNodes.includes(tutorial.msgLayer), true);
    assert.equal(tutorial.msgLayer.classList.contains('msgLayer'), true);
    assert.equal(BaseStep.instances.length, 4);
    assert.equal(BaseStep.instances[0].flags.next, 1);
    assert.equal(BaseStep.instances[3].flags.last, 1);
    assert.equal(BaseStep.instances[0].flags.activated, 1);
});

test('Wirecloud.ui.Tutorial nextStep advances with timeout and destroys current step', () => {
    resetLegacyRuntime();
    const {Tutorial, BaseStep, scheduled} = setupTutorial();
    const tutorial = new Tutorial('Label', [{type: 'simpleDescription'}, {type: 'userAction'}]);
    tutorial.start();

    tutorial.nextStep();
    assert.equal(BaseStep.instances[0].flags.destroyed, 1);
    assert.equal(scheduled.length, 1);
    scheduled[0]();
    assert.equal(BaseStep.instances[1].flags.activated, 1);

    tutorial.nextStep();
    assert.equal(tutorial.steps.length, 0);
    assert.equal(tutorial.msgLayer, null);
});

test('Wirecloud.ui.Tutorial resetControlLayer supports transparent true/false', () => {
    resetLegacyRuntime();
    const {Tutorial} = setupTutorial();
    const tutorial = new Tutorial('Label', []);

    tutorial.resetControlLayer(true);
    assert.equal(tutorial.controlLayer.classList.contains('transparent'), true);
    tutorial.resetControlLayer(false);
    assert.equal(tutorial.controlLayer.classList.contains('transparent'), false);
    assert.equal(tutorial.controlLayerUp.style.height, '50%');
    assert.equal(tutorial.controlLayerCenter.style.width, '0');
});

test('Wirecloud.ui.Tutorial setControlLayer ignores non-object and handles center toggling', () => {
    resetLegacyRuntime();
    const {Tutorial} = setupTutorial();
    const tutorial = new Tutorial('Label', []);
    const element = document.createElement('div');
    element.getBoundingClientRect = () => ({
        top: 10,
        left: 20,
        width: 30,
        height: 40,
    });

    tutorial.setControlLayer('bad', true);
    assert.equal(tutorial.controlLayer.classList.contains('hidden'), false);

    tutorial.setControlLayer(element, true);
    assert.equal(tutorial.controlLayerCenter.style.display, 'block');
    assert.equal(tutorial.controlLayerCenter.style.left, '20px');

    tutorial.setControlLayer(element, false);
    assert.equal(tutorial.controlLayerCenter.style.display, 'none');
    assert.equal(tutorial.controlLayerLeft.style.width, '20px');
});

test('Wirecloud.ui.Tutorial deactivateLayer and findElementByTextContent', () => {
    resetLegacyRuntime();
    const {Tutorial} = setupTutorial();
    const tutorial = new Tutorial('Label', []);
    const nodes = [document.createElement('span'), document.createElement('span')];
    nodes[0].textContent = 'First';
    nodes[1].textContent = 'Second';

    tutorial.deactivateLayer();
    assert.equal(tutorial.controlLayer.classList.contains('hidden'), true);
    assert.equal(tutorial.findElementByTextContent(nodes, 'second'), nodes[1]);
    assert.equal(tutorial.findElementByTextContent(nodes, 'missing'), null);
});
