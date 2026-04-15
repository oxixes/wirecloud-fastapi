const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupRadioButton = () => {
    class StyledElement {}
    StyledElement.prototype.insertInto = function (element, refElement) {
        this.insertedInto = { element, refElement };
    };

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
    }

    class ButtonsGroup {
        constructor(name) {
            this.name = name;
            this.inserted = [];
        }

        insertButton(button) {
            this.inserted.push(button);
        }
    }

    global.StyledElements = {
        StyledElement,
        InputElement,
        ButtonsGroup,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {},
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/RadioButton.js');
    return StyledElements.RadioButton;
};

test('StyledElements.RadioButton initializes radio input attributes', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const radio = new RadioButton({
        value: 'x',
        name: 'group-1',
        id: 'radio-1',
        initiallyChecked: true,
    });

    assert.equal(radio.wrapperElement.getAttribute('type'), 'radio');
    assert.equal(radio.wrapperElement.getAttribute('value'), 'x');
    assert.equal(radio.wrapperElement.getAttribute('name'), 'group-1');
    assert.equal(radio.wrapperElement.getAttribute('id'), 'radio-1');
    assert.equal(radio.wrapperElement.getAttribute('checked'), 'true');
});

test('StyledElements.RadioButton registers into ButtonsGroup instances', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const group = new StyledElements.ButtonsGroup('g');
    const radio = new RadioButton({ group });

    assert.equal(radio.wrapperElement.getAttribute('name'), 'g');
    assert.equal(group.inserted[0], radio);
});

test('StyledElements.RadioButton supports string group names', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const radio = new RadioButton({ group: 'g2' });

    assert.equal(radio.wrapperElement.getAttribute('name'), 'g2');
});

test('StyledElements.RadioButton dispatches change only when enabled', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const radio = new RadioButton({});

    radio.enabled = false;
    radio.inputElement.dispatchEvent({ type: 'change' });
    const before = radio.dispatched.length;

    radio.enabled = true;
    radio.inputElement.dispatchEvent({ type: 'change' });
    const after = radio.dispatched.length;

    assert.equal(before, 0);
    assert.equal(after, 1);
});

test('StyledElements.RadioButton insertInto preserves checked property', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const radio = new RadioButton({});
    radio.inputElement.checked = true;

    radio.insertInto(document.createElement('div'));

    assert.equal(radio.inputElement.checked, true);
});

test('StyledElements.RadioButton reset and setValue update checked state', () => {
    resetLegacyRuntime();
    const RadioButton = setupRadioButton();
    const radio = new RadioButton({ initiallyChecked: true });

    radio.setValue(false);
    assert.equal(radio.inputElement.checked, false);
    radio.reset();
    assert.equal(radio.inputElement.checked, true);
});
