const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupTextInputInterface = () => {
    class InputInterface {
        constructor(fieldId, options) {
            this.fieldId = fieldId;
            this.options = options;
        }

        validate() {
            this.validateCalls = (this.validateCalls || 0) + 1;
        }
    }

    class TextField {
        constructor(options) {
            this.options = options;
            this.listeners = {};
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }
    }

    global.StyledElements = {
        InputInterface,
        TextField,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/TextInputInterface.js');
    return StyledElements.TextInputInterface;
};

test('StyledElements.TextInputInterface wires change and blur listeners', () => {
    resetLegacyRuntime();
    const TextInputInterface = setupTextInputInterface();
    const input = new TextInputInterface('field', { placeholder: 'x' });

    assert.equal(typeof input.inputElement.listeners.change, 'function');
    assert.equal(typeof input.inputElement.listeners.blur, 'function');
});

test('StyledElements.TextInputInterface parse/stringify return same value', () => {
    resetLegacyRuntime();
    const TextInputInterface = setupTextInputInterface();

    assert.equal(TextInputInterface.parse('demo'), 'demo');
    assert.equal(TextInputInterface.stringify('demo'), 'demo');
});

test('StyledElements.TextInputInterface assignDefaultButton invokes button click on submit', () => {
    resetLegacyRuntime();
    const TextInputInterface = setupTextInputInterface();
    const input = new TextInputInterface('field', {});
    let clicks = 0;

    input.assignDefaultButton({
        click() {
            clicks += 1;
        }
    });
    input.inputElement.listeners.submit();

    assert.equal(clicks, 1);
});

test('StyledElements.TextInputInterface blur listener triggers validate immediately', () => {
    resetLegacyRuntime();
    const TextInputInterface = setupTextInputInterface();
    const input = new TextInputInterface('field', {});

    input.inputElement.listeners.blur();

    assert.equal(input.validateCalls, 1);
});

test('StyledElements.TextInputInterface change listener schedules validate and clears existing timeout', async () => {
    resetLegacyRuntime();
    const TextInputInterface = setupTextInputInterface();
    const input = new TextInputInterface('field', {});

    input.timeout = setTimeout(() => {}, 1000);
    input.inputElement.listeners.change();
    await new Promise((resolve) => setTimeout(resolve, 750));

    assert.equal(input.validateCalls, 1);
});
