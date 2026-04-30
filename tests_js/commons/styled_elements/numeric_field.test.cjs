const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupNumericField = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.defaultValue = initialValue;
            this.events = events;
            this.dispatched = [];
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({ name, args });
        }
    }

    global.StyledElements = {
        InputElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopInputKeydownPropagationListener: () => {},
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/NumericField.js');
    return StyledElements.NumericField;
};

test('StyledElements.NumericField initializes wrapper and numeric input attributes', () => {
    resetLegacyRuntime();
    const NumericField = setupNumericField();
    const field = new NumericField({
        class: 'custom',
        name: 'amount',
        id: 'amount-id',
        min: '1',
        max: '10',
        inc: '2',
        initialValue: '4',
    });

    assert.equal(field.wrapperElement.className, 'se-numeric-field');
    assert.equal(field.inputElement.getAttribute('type'), 'number');
    assert.equal(field.inputElement.getAttribute('step'), '2');
    assert.equal(field.inputElement.getAttribute('min'), '1');
    assert.equal(field.inputElement.getAttribute('max'), '10');
    assert.equal(field.inputElement.getAttribute('name'), 'amount');
    assert.equal(field.wrapperElement.getAttribute('id'), 'amount-id');
    assert.equal(field.inputElement.getAttribute('value'), '4');
});

test('StyledElements.NumericField skips min/max attributes for infinite bounds', () => {
    resetLegacyRuntime();
    const NumericField = setupNumericField();
    const field = new NumericField({});

    assert.equal(field.inputElement.hasAttribute('min'), false);
    assert.equal(field.inputElement.hasAttribute('max'), false);
});

test('StyledElements.NumericField dispatches focus and blur and toggles focus class', () => {
    resetLegacyRuntime();
    const NumericField = setupNumericField();
    const field = new NumericField({});

    field.inputElement.dispatchEvent({ type: 'focus' });
    assert.equal(field.wrapperElement.classList.contains('focus'), true);
    field.inputElement.dispatchEvent({ type: 'blur' });
    assert.equal(field.wrapperElement.classList.contains('focus'), false);
    assert.deepEqual(field.dispatched.map((entry) => entry.name), ['focus', 'blur']);
});

test('StyledElements.NumericField dispatches change with input event payload', () => {
    resetLegacyRuntime();
    const NumericField = setupNumericField();
    const field = new NumericField({});
    const payload = { value: 5 };

    field.inputElement.dispatchEvent({ type: 'input', payload });

    assert.equal(field.dispatched.at(-1).name, 'change');
    assert.equal(field.dispatched.at(-1).args[0].payload, payload);
});

test('StyledElements.NumericField getValue returns numeric conversion', () => {
    resetLegacyRuntime();
    const NumericField = setupNumericField();
    const field = new NumericField({ initialValue: 0 });
    field.inputElement.value = '7';

    assert.equal(field.getValue(), 7);
});
