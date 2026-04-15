const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupButtonsGroup = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.defaultValue = initialValue;
            this.events = events;
            this.dispatched = [];
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }
    }

    class CheckBox {}

    global.StyledElements = {
        InputElement,
        CheckBox,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/ButtonsGroup.js');
    return StyledElements.ButtonsGroup;
};

const createButton = (value, checked = false) => {
    return {
        inputElement: {
            value,
            checked,
        },
        listeners: {},
        setValueCalls: [],
        resetCalls: 0,
        addEventListener(name, listener) {
            this.listeners[name] = listener;
        },
        setValue(newValue) {
            this.setValueCalls.push(newValue);
            this.inputElement.checked = !!newValue;
        },
        getValue() {
            return value;
        },
        reset() {
            this.resetCalls += 1;
        }
    };
};

test('StyledElements.ButtonsGroup stores constructor name and starts empty', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group-name');

    assert.equal(group.name, 'group-name');
    assert.deepEqual(group.buttons, []);
});

test('StyledElements.ButtonsGroup insertButton registers change listener and dispatches events', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const button = createButton('a');

    const result = group.insertButton(button);
    button.listeners.change();

    assert.equal(result, group);
    assert.equal(group.buttons[0], button);
    assert.equal(group.dispatched[0].name, 'change');
});

test('StyledElements.ButtonsGroup getValue returns checked checkbox values', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const checked = createButton('one', true);
    const unchecked = createButton('two', false);
    Object.setPrototypeOf(checked, StyledElements.CheckBox.prototype);
    Object.setPrototypeOf(unchecked, StyledElements.CheckBox.prototype);
    group.insertButton(checked);
    group.insertButton(unchecked);

    assert.deepEqual(group.getValue(), ['one']);
});

test('StyledElements.ButtonsGroup getValue returns first checked radio-like button', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    group.insertButton(createButton('first', false));
    group.insertButton(createButton('second', true));
    group.insertButton(createButton('third', true));

    assert.equal(group.getValue(), 'second');
});

test('StyledElements.ButtonsGroup getValue returns undefined when no radio-like button is checked', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    group.insertButton(createButton('first', false));
    group.insertButton(createButton('second', false));

    assert.equal(group.getValue(), undefined);
});

test('StyledElements.ButtonsGroup setValue handles null by unchecking all buttons', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const first = createButton('a', true);
    const second = createButton('b', true);
    group.insertButton(first);
    group.insertButton(second);

    const result = group.setValue(null);

    assert.equal(result, group);
    assert.deepEqual(first.setValueCalls, [false]);
    assert.deepEqual(second.setValueCalls, [false]);
});

test('StyledElements.ButtonsGroup setValue converts strings into one-element selections', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const first = createButton('a');
    const second = createButton('b');
    group.insertButton(first);
    group.insertButton(second);

    group.setValue('b');

    assert.deepEqual(first.setValueCalls, [false]);
    assert.deepEqual(second.setValueCalls, [true]);
});

test('StyledElements.ButtonsGroup reset delegates to each button', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const first = createButton('a');
    const second = createButton('b');
    group.insertButton(first);
    group.insertButton(second);

    const result = group.reset();

    assert.equal(result, group);
    assert.equal(first.resetCalls, 1);
    assert.equal(second.resetCalls, 1);
});

test('StyledElements.ButtonsGroup getSelectedButtons returns empty list for empty groups', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');

    assert.deepEqual(group.getSelectedButtons(), []);
});

test('StyledElements.ButtonsGroup getSelectedButtons returns all checked checkboxes', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const first = createButton('a', true);
    const second = createButton('b', false);
    Object.setPrototypeOf(first, StyledElements.CheckBox.prototype);
    Object.setPrototypeOf(second, StyledElements.CheckBox.prototype);
    group.insertButton(first);
    group.insertButton(second);

    assert.deepEqual(group.getSelectedButtons(), [first]);
});

test('StyledElements.ButtonsGroup getSelectedButtons returns first selected radio-like button', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    const first = createButton('a', false);
    const second = createButton('b', true);
    group.insertButton(first);
    group.insertButton(second);

    assert.deepEqual(group.getSelectedButtons(), [second]);
});

test('StyledElements.ButtonsGroup getSelectedButtons returns empty list when no radio-like button is selected', () => {
    resetLegacyRuntime();
    const ButtonsGroup = setupButtonsGroup();
    const group = new ButtonsGroup('group');
    group.insertButton(createButton('a', false));
    group.insertButton(createButton('b', false));

    assert.deepEqual(group.getSelectedButtons(), []);
});
