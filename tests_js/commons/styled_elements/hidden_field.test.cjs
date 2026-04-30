const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupHiddenField = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.initialValue = initialValue;
            this.events = events;
        }
    }

    global.StyledElements = {
        InputElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            prependWord: (className, prefix) => className ? `${prefix} ${className}` : prefix,
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/HiddenField.js');
    return StyledElements.HiddenField;
};

test('StyledElements.HiddenField applies defaults when options are missing', () => {
    resetLegacyRuntime();
    const HiddenField = setupHiddenField();
    const field = new HiddenField();

    assert.equal(field.wrapperElement.className, 'styled_hidden_field');
    assert.equal(field.inputElement.getAttribute('type'), 'hidden');
});

test('StyledElements.HiddenField sets name, id and initial value when provided', () => {
    resetLegacyRuntime();
    const HiddenField = setupHiddenField();
    const field = new HiddenField({
        class: 'custom',
        name: 'token',
        id: 'secret-id',
        initialValue: 'abc',
    });

    assert.equal(field.wrapperElement.className, 'styled_hidden_field custom');
    assert.equal(field.inputElement.getAttribute('name'), 'token');
    assert.equal(field.wrapperElement.getAttribute('id'), 'secret-id');
    assert.equal(field.inputElement.getAttribute('value'), 'abc');
});
