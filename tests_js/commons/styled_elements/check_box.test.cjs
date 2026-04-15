const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupCheckBox = () => {
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
        InputElement,
        ButtonsGroup,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {},
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/CheckBox.js');
    return StyledElements.CheckBox;
};

test('StyledElements.CheckBox initializes attributes and checked value', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const box = new CheckBox({
        name: 'flag',
        id: 'flag-id',
        value: 'YES',
        initialValue: true
    });

    assert.equal(box.wrapperElement.getAttribute('type'), 'checkbox');
    assert.equal(box.wrapperElement.getAttribute('name'), 'flag');
    assert.equal(box.wrapperElement.getAttribute('id'), 'flag-id');
    assert.equal(box.wrapperElement.getAttribute('value'), 'YES');
    assert.equal(box.inputElement.checked, true);
});

test('StyledElements.CheckBox supports initiallyChecked backward compatibility option', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const box = new CheckBox({ initiallyChecked: true });

    assert.equal(box.inputElement.checked, true);
});

test('StyledElements.CheckBox registers into ButtonsGroup and supports string group name', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const group = new StyledElements.ButtonsGroup('g');
    const boxWithGroup = new CheckBox({ group });
    const boxWithStringGroup = new CheckBox({ group: 'g2' });

    assert.equal(group.inserted[0], boxWithGroup);
    assert.equal(boxWithGroup.wrapperElement.getAttribute('name'), 'g');
    assert.equal(boxWithStringGroup.wrapperElement.getAttribute('name'), 'g2');
});

test('StyledElements.CheckBox change event updates secondInput when enabled', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const secondInput = {
        setDisabledCalls: [],
        setDisabled(value) {
            this.setDisabledCalls.push(value);
        },
        setValue(value) {
            this.lastValue = value;
        },
        getValue() {
            return 'secondary';
        }
    };
    const box = new CheckBox({ secondInput, initialValue: false });

    box.inputElement.checked = true;
    box.inputElement.dispatchEvent({ type: 'change' });

    assert.deepEqual(secondInput.setDisabledCalls.at(-1), false);
    assert.equal(box.dispatched.at(-1).name, 'change');
});

test('StyledElements.CheckBox change event does nothing when disabled', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const secondInput = {
        setDisabled() {
            this.called = true;
        }
    };
    const box = new CheckBox({ secondInput });
    box.enabled = false;
    const calledBefore = secondInput.called === true ? 1 : 0;

    box.inputElement.dispatchEvent({ type: 'change' });

    const calledAfter = secondInput.called === true ? 1 : 0;
    assert.equal(calledAfter, calledBefore);
    assert.equal(box.dispatched.length, 0);
});

test('StyledElements.CheckBox getValue returns boolean when checkedValue is true without secondInput', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const box = new CheckBox({ value: true, initialValue: false });

    box.inputElement.checked = true;
    assert.equal(box.getValue(), true);
    box.inputElement.checked = false;
    assert.equal(box.getValue(), false);
});

test('StyledElements.CheckBox getValue returns checkedValue or null when no secondInput', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const box = new CheckBox({ value: 'X', initialValue: false });

    box.inputElement.checked = true;
    assert.equal(box.getValue(), 'X');
    box.inputElement.checked = false;
    assert.equal(box.getValue(), null);
});

test('StyledElements.CheckBox getValue delegates to secondInput when present', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const secondInput = {
        getValue() {
            return 'secondary-value';
        },
        setDisabled() {},
        setValue() {}
    };
    const box = new CheckBox({ secondInput, initialValue: true });

    assert.equal(box.getValue(), 'secondary-value');
});

test('StyledElements.CheckBox setValue updates secondInput state and value', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const secondInput = {
        disabledStates: [],
        setDisabled(value) {
            this.disabledStates.push(value);
        },
        setValue(value) {
            this.lastValue = value;
        },
        getValue() {
            return this.lastValue;
        }
    };
    const box = new CheckBox({ secondInput, initialValue: false });

    box.setValue('abc');
    assert.equal(box.inputElement.checked, true);
    assert.deepEqual(secondInput.disabledStates.at(-1), false);
    assert.equal(secondInput.lastValue, 'abc');

    box.setValue(false);
    assert.equal(box.inputElement.checked, false);
    assert.deepEqual(secondInput.disabledStates.at(-1), true);
});

test('StyledElements.CheckBox reset restores default value', () => {
    resetLegacyRuntime();
    const CheckBox = setupCheckBox();
    const box = new CheckBox({ initialValue: true });

    box.setValue(false);
    box.reset();

    assert.equal(box.inputElement.checked, true);
});
