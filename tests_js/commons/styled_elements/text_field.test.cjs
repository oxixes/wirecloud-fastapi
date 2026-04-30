const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupTextField = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.defaultValue = initialValue;
            this.events = events;
            this.enabled = true;
            this.dispatched = [];
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({ name, args });
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
            normalizeKey: (event) => event.key,
            extractModifiers: (event) => ({
                altKey: !!event.altKey,
                metaKey: !!event.metaKey,
                ctrlKey: !!event.ctrlKey,
            }),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/TextField.js');
    return StyledElements.TextField;
};

test('StyledElements.TextField initializes attributes and classes from options', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({
        class: 'custom',
        name: 'title',
        id: 'field-id',
        ariaLabel: 'field',
        placeholder: 'type',
        initialValue: 'abc',
    });

    assert.equal(field.wrapperElement.className, 'se-text-field custom');
    assert.equal(field.inputElement.getAttribute('name'), 'title');
    assert.equal(field.wrapperElement.getAttribute('id'), 'field-id');
    assert.equal(field.wrapperElement.getAttribute('aria-label'), 'field');
    assert.equal(field.inputElement.getAttribute('placeholder'), 'type');
    assert.equal(field.inputElement.getAttribute('value'), 'abc');
});

test('StyledElements.TextField dispatches change/focus/blur events', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});

    field.inputElement.dispatchEvent({ type: 'input' });
    field.inputElement.dispatchEvent({ type: 'focus' });
    field.inputElement.dispatchEvent({ type: 'blur' });

    assert.deepEqual(field.dispatched.map((entry) => entry.name), ['change', 'focus', 'blur']);
});

test('StyledElements.TextField dispatches submit on Enter keypress', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});

    field.inputElement.dispatchEvent({ type: 'keypress', key: 'Enter' });

    assert.equal(field.dispatched.some((entry) => entry.name === 'submit'), true);
});

test('StyledElements.TextField keydown stops propagation for regular keys and backspace', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});
    let stopped = 0;

    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'a',
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {},
    });
    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'Backspace',
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {},
    });

    assert.equal(stopped, 2);
});

test('StyledElements.TextField keydown keeps propagation for Enter without backspace condition', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});
    let stopped = 0;

    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'Enter',
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {},
    });

    assert.equal(stopped, 0);
});

test('StyledElements.TextField keydown does not stop propagation when ctrl modifier is pressed', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});
    let stopped = 0;

    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'a',
        ctrlKey: true,
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {},
    });

    assert.equal(stopped, 0);
});

test('StyledElements.TextField keydown dispatches keydown event only when enabled', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});

    field.enabled = false;
    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'a',
        stopPropagation() {},
        preventDefault() {},
    });
    const before = field.dispatched.filter((entry) => entry.name === 'keydown').length;

    field.enabled = true;
    field.inputElement.dispatchEvent({
        type: 'keydown',
        key: 'a',
        stopPropagation() {},
        preventDefault() {},
    });
    const after = field.dispatched.filter((entry) => entry.name === 'keydown').length;

    assert.equal(before, 0);
    assert.equal(after, 1);
});

test('StyledElements.TextField setPlaceholder updates placeholder attribute', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});

    field.setPlaceholder('new');

    assert.equal(field.inputElement.getAttribute('placeholder'), 'new');
});

test('StyledElements.TextField destroy removes internal handlers and calls base destroy', () => {
    resetLegacyRuntime();
    const TextField = setupTextField();
    const field = new TextField({});

    field.destroy();

    assert.equal(field._oninput, undefined);
    assert.equal(field._onfocus, undefined);
    assert.equal(field._onblur, undefined);
    assert.equal(field._onkeypress, undefined);
    assert.equal(field._onkeydown_bound, undefined);
    assert.equal(field.destroyed, true);
});
