const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupInputInterface = () => {
    class StyledElement {
        constructor() {}
    }

    class SelectInputInterface extends StyledElement {}

    global.StyledElements = {
        StyledElement,
        SelectInputInterface,
        InputValidationError: {
            NO_ERROR: 'NO_ERROR',
            REQUIRED_ERROR: 'REQUIRED_ERROR',
            OTHER_ERROR: 'OTHER_ERROR',
        },
        Utils: {},
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/InputInterface.js');
    return {
        InputInterface: StyledElements.InputInterface,
        SelectInputInterface,
    };
};

const makeInputElement = (value = '') => {
    const wrapperElement = document.createElement('div');
    return {
        value,
        wrapperElement,
        repaintCalls: 0,
        setValueCalls: [],
        setDisabledCalls: [],
        focusCalls: 0,
        insertIntoCalls: [],
        repaint() {
            this.repaintCalls += 1;
        },
        getValue() {
            return this.value;
        },
        setValue(newValue) {
            this.value = newValue;
            this.setValueCalls.push(newValue);
        },
        setDisabled(disabled) {
            this.setDisabledCalls.push(disabled);
        },
        focus() {
            this.focusCalls += 1;
        },
        insertInto(element) {
            this.insertIntoCalls.push(element);
        },
    };
};

test('StyledElements.InputInterface constructor requires fieldId', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();

    assert.throws(() => new InputInterface(null, {}), {
        name: 'TypeError',
        message: 'missing fieldId parameter',
    });
});

test('StyledElements.InputInterface constructor stores metadata and defaults description to label', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const options = {
        initialValue: 'init',
        defaultValue: 'def',
        label: 'My label',
        readOnly: true,
        hidden: true,
    };
    const field = new InputInterface('field-id', options);

    assert.equal(options.name, 'field-id');
    assert.equal(field.id, 'field-id');
    assert.equal(field.required, false);
    assert.equal(field.getLabel(), 'My label');
    assert.equal(field.getDescription(), 'My label');
    assert.equal(field.getDefaultValue(), 'def');
    assert.equal(field._readOnly, true);
    assert.equal(field._hidden, true);
});

test('StyledElements.InputInterface constructor supports explicit description and required flag', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        description: 'Desc',
        required: 1,
    });

    assert.equal(field.getDescription(), 'Desc');
    assert.equal(field.required, true);
});

test('StyledElements.InputInterface normalize and empty checks behave as expected', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });

    assert.equal(field._normalize(null), '');
    assert.equal(field._normalize('  hi  '), 'hi');
    assert.equal(field._isEmptyValue(''), true);
    assert.equal(field._isEmptyValue(null), true);
    assert.equal(field._isEmptyValue('x'), false);
});

test('StyledElements.InputInterface repaint and getValue delegate to inputElement', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.inputElement = makeInputElement('value');

    field.repaint();

    assert.equal(field.inputElement.repaintCalls, 1);
    assert.equal(field.getValue(), 'value');
});

test('StyledElements.InputInterface setValue only sets values passing validation', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.inputElement = makeInputElement('');
    field.checkValue = () => StyledElements.InputValidationError.NO_ERROR;

    field.setValue('  ok  ');
    field.checkValue = () => StyledElements.InputValidationError.OTHER_ERROR;
    field.setValue('bad');

    assert.deepEqual(field.inputElement.setValueCalls, ['ok']);
});

test('StyledElements.InputInterface isEmpty checks current value', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.inputElement = makeInputElement('');
    assert.equal(field.isEmpty(), true);
    field.inputElement.value = 'filled';
    assert.equal(field.isEmpty(), false);
});

test('StyledElements.InputInterface _checkValue base implementation returns NO_ERROR', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });

    assert.equal(field._checkValue('x'), StyledElements.InputValidationError.NO_ERROR);
});

test('StyledElements.InputInterface event listener registration and dispatch works', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    const payloads = [];
    field.addEventListener('change', (payload) => {
        payloads.push(payload);
    });

    field._callEvent('change', {value: 1});
    field._callEvent('unknown', {value: 2});

    assert.deepEqual(payloads, [{value: 1}]);
});

test('StyledElements.InputInterface checkValue validates undefined newValue using current value', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        required: true,
    });
    field.inputElement = makeInputElement('');

    assert.equal(field.checkValue(), StyledElements.InputValidationError.REQUIRED_ERROR);
});

test('StyledElements.InputInterface checkValue handles optional empty values', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        required: false,
    });
    field.inputElement = makeInputElement('');

    assert.equal(field.checkValue('   '), StyledElements.InputValidationError.NO_ERROR);
});

test('StyledElements.InputInterface checkValue delegates to _checkValue for non-empty values', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.inputElement = makeInputElement('');
    field._checkValue = (value) => value === 'ok' ? StyledElements.InputValidationError.NO_ERROR : StyledElements.InputValidationError.OTHER_ERROR;

    assert.equal(field.checkValue('ok'), StyledElements.InputValidationError.NO_ERROR);
    assert.equal(field.checkValue('nope'), StyledElements.InputValidationError.OTHER_ERROR);
});

test('StyledElements.InputInterface checkValue skips required/empty checks for SelectInputInterface subclasses', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    StyledElements.SelectInputInterface = InputInterface;

    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        required: true,
    });
    field.inputElement = makeInputElement('');
    field._checkValue = () => StyledElements.InputValidationError.OTHER_ERROR;

    assert.equal(field.checkValue(''), StyledElements.InputValidationError.OTHER_ERROR);
});

test('StyledElements.InputInterface validate clears timeout and sets/removes error class', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.inputElement = makeInputElement('');
    field.timeout = setTimeout(() => {}, 1000);
    field.checkValue = () => StyledElements.InputValidationError.OTHER_ERROR;

    field.validate();
    assert.equal(field.inputElement.wrapperElement.classList.contains('error'), true);

    field.checkValue = () => StyledElements.InputValidationError.NO_ERROR;
    field.validate();
    assert.equal(field.inputElement.wrapperElement.classList.contains('error'), false);
});

test('StyledElements.InputInterface isValidValue uses checkValue result', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });
    field.checkValue = () => StyledElements.InputValidationError.NO_ERROR;
    assert.equal(field.isValidValue('x'), true);
    field.checkValue = () => StyledElements.InputValidationError.OTHER_ERROR;
    assert.equal(field.isValidValue('x'), false);
});

test('StyledElements.InputInterface reset and resetToDefault clear errors and set normalized values', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '  init  ',
        defaultValue: '  def  ',
        label: 'Label',
    });
    field.inputElement = makeInputElement('');
    field.inputElement.wrapperElement.classList.add('error');

    field.resetToDefault();
    field.reset();

    assert.deepEqual(field.inputElement.setValueCalls, ['def', 'init']);
    assert.equal(field.inputElement.wrapperElement.classList.contains('error'), false);
});

test('StyledElements.InputInterface focus, disable/enable and insertInto delegate to inputElement', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        readOnly: true,
    });
    const target = document.createElement('div');
    field.inputElement = makeInputElement('');

    field.focus();
    field.setDisabled(false);
    field.setDisabled(true);
    field.enable();
    field.disable();
    field.insertInto(target);

    assert.equal(field.inputElement.focusCalls, 1);
    assert.deepEqual(field.inputElement.setDisabledCalls, [true, true, true, true]);
    assert.deepEqual(field.inputElement.insertIntoCalls, [target]);
});

test('StyledElements.InputInterface setDisabled forwards false when readOnly is false', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
        readOnly: false,
    });
    field.inputElement = makeInputElement('');

    field.setDisabled(false);

    assert.deepEqual(field.inputElement.setDisabledCalls, [false]);
});

test('StyledElements.InputInterface assignDefaultButton is a no-op', () => {
    resetLegacyRuntime();
    const {InputInterface} = setupInputInterface();
    const field = new InputInterface('field-id', {
        initialValue: '',
        defaultValue: '',
        label: 'Label',
    });

    assert.equal(field.assignDefaultButton({}), undefined);
});
