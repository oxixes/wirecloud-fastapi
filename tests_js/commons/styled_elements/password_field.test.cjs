const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPasswordField = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.value = initialValue;
            this.events = events;
            this.dispatched = [];
        }

        dispatchEvent(name, value) {
            this.dispatched.push({ name, value });
        }

        destroy() {
            this.destroyed = true;
        }
    }

    global.StyledElements = {
        InputElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {},
            stopInputKeydownPropagationListener: () => {},
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PasswordField.js');
    return StyledElements.PasswordField;
};

test('StyledElements.PasswordField initializes input with options', () => {
    resetLegacyRuntime();
    const PasswordField = setupPasswordField();
    const field = new PasswordField({
        class: 'custom',
        name: 'pwd',
        id: 'pwd-id',
        initialValue: 'secret',
    });

    assert.equal(field.inputElement.getAttribute('type'), 'password');
    assert.equal(field.wrapperElement.className, 'se-password-field custom');
    assert.equal(field.inputElement.getAttribute('name'), 'pwd');
    assert.equal(field.wrapperElement.getAttribute('id'), 'pwd-id');
    assert.equal(field.inputElement.getAttribute('value'), 'secret');
});

test('StyledElements.PasswordField dispatches change/focus/blur events', () => {
    resetLegacyRuntime();
    const PasswordField = setupPasswordField();
    const field = new PasswordField({});

    field.inputElement.dispatchEvent({ type: 'input' });
    field.inputElement.dispatchEvent({ type: 'focus' });
    field.inputElement.dispatchEvent({ type: 'blur' });

    assert.deepEqual(field.dispatched.map((entry) => entry.name), ['change', 'focus', 'blur']);
});

test('StyledElements.PasswordField accepts explicit null name/id via in-operator checks', () => {
    resetLegacyRuntime();
    const PasswordField = setupPasswordField();
    const field = new PasswordField({ name: null, id: null });

    assert.equal(field.inputElement.getAttribute('name'), 'null');
    assert.equal(field.wrapperElement.getAttribute('id'), 'null');
});

test('StyledElements.PasswordField destroy unbinds listeners and calls base destroy', () => {
    resetLegacyRuntime();
    const PasswordField = setupPasswordField();
    const field = new PasswordField({});

    field.destroy();

    assert.equal(field.destroyed, true);
});
