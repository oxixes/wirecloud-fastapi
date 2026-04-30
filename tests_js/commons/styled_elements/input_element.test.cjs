const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupInputElement = () => {
    class StyledElement {
        constructor(events = []) {
            this.events = {};
            events.forEach((name) => {
                this.events[name] = true;
            });
            this.enabled = true;
            this.dispatched = [];
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }

        enable() {
            this.enabled = true;
            return this;
        }

        disable() {
            this.enabled = false;
            return this;
        }
    }

    global.StyledElements = {
        StyledElement,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/InputElement.js');
    return StyledElements.InputElement;
};

const createInputElement = (events = ['change']) => {
    const InputElement = setupInputElement();
    const input = new InputElement('default', events);
    input.inputElement = {
        value: 'initial',
        disabled: false,
        blurCalls: 0,
        focusCalls: 0,
        blur() {
            this.blurCalls += 1;
        },
        focus() {
            this.focusCalls += 1;
        }
    };
    return input;
};

test('StyledElements.InputElement exposes value getter and setter', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    assert.equal(input.value, 'initial');
    input.value = 'next';
    assert.equal(input.inputElement.value, 'next');
});

test('StyledElements.InputElement setValue dispatches change when value differs', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    const result = input.setValue('updated');

    assert.equal(result, input);
    assert.equal(input.dispatched.length, 1);
    assert.equal(input.dispatched[0].name, 'change');
});

test('StyledElements.InputElement setValue does not dispatch change when value is equal', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    input.setValue('initial');

    assert.equal(input.dispatched.length, 0);
});

test('StyledElements.InputElement setValue skips dispatch when change event is not configured', () => {
    resetLegacyRuntime();
    const input = createInputElement([]);

    input.setValue('updated');

    assert.equal(input.dispatched.length, 0);
});

test('StyledElements.InputElement reset restores default value', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    input.setValue('different');
    input.reset();

    assert.equal(input.getValue(), 'default');
});

test('StyledElements.InputElement enable and disable sync input disabled flag', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    input.disable();
    assert.equal(input.enabled, false);
    assert.equal(input.inputElement.disabled, true);
    input.enable();
    assert.equal(input.enabled, true);
    assert.equal(input.inputElement.disabled, false);
});

test('StyledElements.InputElement blur and focus delegate to native input', () => {
    resetLegacyRuntime();
    const input = createInputElement();

    input.blur();
    input.focus();

    assert.equal(input.inputElement.blurCalls, 1);
    assert.equal(input.inputElement.focusCalls, 1);
});
