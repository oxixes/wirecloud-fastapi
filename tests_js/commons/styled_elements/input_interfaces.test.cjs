const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupInputInterfaces = () => {
    class InputInterface {
        constructor(fieldId, options = {}) {
            this.fieldId = fieldId;
            this.options = options;
            this.required = !!options.required;
            this.events = {};
        }

        checkValue() {
            const current = this.getValue ? this.getValue() : undefined;
            return this._checkValue ? this._checkValue(current) : 0;
        }

        getLabel() {
            return this.options.label || this.fieldId;
        }

        _isEmptyValue(value) {
            return value == null || value === '';
        }

        _setError(error) {
            this.error = error;
        }
    }

    class TextInputInterface extends InputInterface {
        constructor(fieldId, options = {}) {
            super(fieldId, options);
            this.inputElement = {
                type: 'text',
                validationMessage: '',
            };
        }

        static parse(value) {
            return value;
        }

        static stringify(value) {
            return value;
        }

        parse(value) {
            return value;
        }

        stringify(value) {
            return value;
        }
    }

    class PasswordField {
        constructor(options) {
            this.options = options;
        }
    }

    class List {
        constructor() {
            this.selection = [];
        }

        cleanSelection() {
            this.selection = [];
        }

        addSelection(values) {
            if (Array.isArray(values)) {
                this.selection = this.selection.concat(values);
            } else {
                this.selection.push(values);
            }
        }

        getSelection() {
            return this.selection.slice(0);
        }
    }

    class NumericField {
        constructor(options = {}) {
            this.options = {
                min: options.min == null ? Number.NEGATIVE_INFINITY : options.min,
                max: options.max == null ? Number.POSITIVE_INFINITY : options.max,
            };
        }
    }

    class TextArea {
        constructor() {
            this.events = {
                blur: { id: 'blur-event' },
            };
        }
    }

    class CheckBox {
        constructor(options) {
            this.options = options;
        }

        insertInto(parent) {
            parent.appendChild(document.createElement('input'));
        }
    }

    class Select {
        constructor(desc) {
            this.idFunc = desc.idFunc || ((entry) => String(entry));
            this.optionValues = {};
            this.entries = [];
            if (Array.isArray(desc.initialEntries)) {
                this.addEntries(desc.initialEntries);
            }
        }

        clear() {
            this.optionValues = {};
            this.entries = [];
        }

        addEntries(entries) {
            this.entries = this.entries.concat(entries);
            entries.forEach((entry) => {
                this.optionValues[String(entry.value)] = entry;
            });
        }

        setValue(value) {
            this.value = value;
        }
    }

    class HiddenField {
        constructor(options) {
            this.options = options;
        }
    }

    class ButtonsGroup {
        constructor() {
            this.value = null;
        }

        setValue(value) {
            this.value = value;
        }

        getValue() {
            return this.value;
        }
    }

    class RadioButton {
        constructor(options) {
            this.options = options;
        }

        insertInto(parent) {
            parent.appendChild(document.createElement('input'));
        }
    }

    class FileField {
        constructor(desc) {
            this.desc = desc;
            this.disabled = false;
            this.value = 'file';
        }

        getValue() {
            return this.value;
        }
    }

    class Form {
        constructor(fields, options) {
            this.fields = fields;
            this.options = options;
            this.data = null;
            this.repaintCalls = 0;
            this.insertCalls = 0;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }

        insertInto(element) {
            this.insertCalls += 1;
            element.appendChild(document.createElement('div'));
        }

        getData() {
            return this.data;
        }

        setData(data) {
            this.data = data;
            return this;
        }
    }

    class CodeArea {
        constructor(desc) {
            this.desc = desc;
        }
    }

    global.StyledElements = {
        InputInterface,
        TextInputInterface,
        PasswordField,
        List,
        NumericField,
        TextArea,
        CheckBox,
        Select,
        HiddenField,
        ButtonsGroup,
        RadioButton,
        CheckBox,
        FileField,
        Form,
        CodeArea,
        Utils: {
            gettext(text) {
                return text;
            },
            interpolate(template, data) {
                return template.replace('%(fields)s', data.fields);
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/InputInterfaces.js');

    return StyledElements;
};

test('InputInterfaces validation manager, list, number, text and URL/email variants', () => {
    resetLegacyRuntime();
    const se = setupInputInterfaces();

    const manager = new se.ValidationErrorManager();
    const field = {
        checkValue: () => se.InputValidationError.REQUIRED_ERROR,
        _setError: (error) => {
            field.error = error;
        },
        getLabel: () => 'Name',
    };
    manager.validate(field);
    assert.equal(field.error, true);

    const okField = {
        checkValue: () => se.InputValidationError.NO_ERROR,
        _setError: (error) => {
            okField.error = error;
        },
        getLabel: () => 'Other',
    };
    manager.validate(okField);
    assert.equal(okField.error, false);

    manager.fieldsWithErrorById = {
        [se.InputValidationError.REQUIRED_ERROR]: ['A'],
        [se.InputValidationError.URL_ERROR]: ['B'],
        [se.InputValidationError.EMAIL_ERROR]: ['C'],
        [se.InputValidationError.VERSION_ERROR]: ['D'],
        [se.InputValidationError.ID_ERROR]: ['E'],
        [se.InputValidationError.COLOR_ERROR]: ['F'],
        [se.InputValidationError.OUT_OF_RANGE_ERROR]: ['G'],
        [se.InputValidationError.SCREEN_SIZES_ERROR]: ['H'],
    };
    const msgs = manager.toHTML();
    assert.equal(msgs.length, 8);

    const password = new se.PasswordInputInterface('pwd', { label: 'Password' });
    assert.equal(password.inputElement.options.label, 'Password');

    const list = new se.ListInputInterface('list', {});
    list._normalize('bad');
    list._setValue(['x', 'y']);
    assert.deepEqual(list.getValue(), ['x', 'y']);
    assert.equal(list.isEmpty(), false);
    list.inputElement.cleanSelection();
    assert.equal(list.isEmpty(), true);
    assert.deepEqual(se.ListInputInterface.parse('[1,2]'), [1, 2]);
    assert.equal(se.ListInputInterface.stringify(['a']), '["a"]');

    const number = new se.NumberInputInterface('num', { min: 0, max: 2 });
    assert.equal(se.NumberInputInterface.parse('3'), 3);
    assert.equal(number._normalize(null), 0);
    assert.equal(number._normalize('2'), 2);
    assert.equal(number._checkValue(1), se.InputValidationError.NO_ERROR);
    assert.equal(number._checkValue(4), se.InputValidationError.OUT_OF_RANGE_ERROR);

    const longText = new se.LongTextInputInterface('lt', {});
    assert.equal(longText.events.blur.id, 'blur-event');

    const url = new se.URLInputInterface('url', {});
    url.inputElement.validationMessage = 'has-error';
    assert.equal(url._checkValue('x'), se.InputValidationError.NO_ERROR);
    url.inputElement.validationMessage = '';
    assert.equal(url._checkValue('x'), se.InputValidationError.URL_ERROR);

    const email = new se.EMailInputInterface('email', {});
    email.inputElement.validationMessage = 'has-error';
    assert.equal(email._checkValue('x'), se.InputValidationError.NO_ERROR);
    email.inputElement.validationMessage = '';
    assert.equal(email._checkValue('x'), se.InputValidationError.EMAIL_ERROR);
});

test('InputInterfaces boolean, select, hidden and button-group variants', () => {
    resetLegacyRuntime();
    const se = setupInputInterfaces();

    const boolA = new se.BooleanInputInterface('b1', { initialValue: 'true' });
    const boolB = new se.BooleanInputInterface('b2', { initialValue: false });
    assert.equal(boolA.inputElement.options.initiallyChecked, true);
    assert.equal(boolB.inputElement.options.initiallyChecked, false);
    assert.equal(se.BooleanInputInterface.parse('true'), true);
    assert.equal(se.BooleanInputInterface.stringify(false), 'false');
    assert.equal(boolA.isEmpty(), false);
    assert.equal(boolA._normalize(0), false);
    assert.equal(boolA._checkValue(true), se.InputValidationError.NO_ERROR);
    assert.equal(boolA._checkValue('true'), se.InputValidationError.BOOLEAN_ERROR);

    const dynamicSelect = new se.SelectInputInterface('s1', {
        required: false,
        entries() {
            return [{ label: 'One', value: 1 }];
        },
    });
    dynamicSelect._setValue(1);
    assert.equal(dynamicSelect.inputElement.entries.length, 2);

    const staticSelect = new se.SelectInputInterface('s2', {
        required: false,
        initialEntries: [{ label: 'A', value: 'a' }],
    });
    assert.equal(staticSelect.inputElement.entries.length, 2);

    const requiredByDefault = new se.SelectInputInterface('s0', {
        initialEntries: [{ label: 'A', value: null }],
    });
    assert.equal(requiredByDefault.required, true);

    const existingEmpty = new se.SelectInputInterface('s3', {
        required: false,
        initialEntries: [{ label: 'Empty', value: null }],
    });
    assert.equal(existingEmpty.inputElement.entries.length, 1);
    assert.equal(se.SelectInputInterface.parse('x'), 'x');
    assert.equal(se.SelectInputInterface.stringify(4), '4');

    staticSelect.inputElement.idFunc = (value) => String(value.id);
    staticSelect.inputElement.optionValues = { '1': true };
    assert.equal(staticSelect._checkValue({ id: 1 }), se.InputValidationError.NO_ERROR);
    assert.equal(staticSelect._checkValue('unknown'), se.InputValidationError.OUT_OF_RANGE_ERROR);
    staticSelect.inputElement.idFunc = () => {
        throw new Error('bad');
    };
    assert.equal(staticSelect._checkValue({}), se.InputValidationError.OUT_OF_RANGE_ERROR);

    const hidden = new se.HiddenInputInterface('h', { id: 'hid' });
    assert.equal(hidden.inputElement.options.id, 'hid');

    const container = document.createElement('div');
    const secondInput = {
        inserted: 0,
        insertInto(parent) {
            this.inserted += 1;
            parent.appendChild(document.createElement('span'));
        },
    };
    const radioGroup = new se.ButtonGroupInputInterface('bg', {
        kind: 'radio',
        buttons: [{ label: 'A', value: 'a', secondInput }],
        initialValue: 'a',
    });
    radioGroup.insertInto(container);
    radioGroup._setValue('b');
    radioGroup._setError(true);
    assert.equal(secondInput.inserted, 1);
    assert.equal(radioGroup.inputElement.getValue(), 'b');

    const checkboxGroup = new se.ButtonGroupInputInterface('bg2', {
        kind: 'checkbox',
        buttons: [{ label: 'B', value: 'b' }],
    });
    assert.ok(checkboxGroup.wrapperElement.classList.contains('button_group'));

    assert.throws(() => {
        new se.ButtonGroupInputInterface('bad', { kind: 'other', buttons: [] });
    }, Error);
});

test('InputInterfaces file, fieldset and code variants', () => {
    resetLegacyRuntime();
    const se = setupInputInterfaces();

    const file = new se.FileInputInterface('file', { accept: '.txt' });
    assert.equal(file.getValue(), 'file');
    file._setValue('ignored');
    file._setError(true);
    file.setDisabled(true);
    assert.equal(file.inputElement.disabled, true);

    assert.throws(() => {
        new se.FieldSetInterface('fs', {
            fields: { a: { type: 'text' } },
        }, {
            createInterface() {},
        });
    }, ReferenceError);

    const fakeFieldSet = {
        form: new se.Form({}, {}),
    };
    const host = document.createElement('div');
    se.FieldSetInterface.prototype.insertInto.call(fakeFieldSet, host);
    se.FieldSetInterface.prototype.repaint.call(fakeFieldSet);
    se.FieldSetInterface.prototype._setValue.call(fakeFieldSet, { a: 1 });
    assert.deepEqual(se.FieldSetInterface.prototype.getValue.call(fakeFieldSet), { a: 1 });
    se.FieldSetInterface.prototype._setError.call(fakeFieldSet, true);

    const code = new se.CodeInputInterface('code', { language: 'js' });
    assert.equal(code.inputElement.desc.language, 'js');
    assert.equal(se.CodeInputInterface.parse('x'), 'x');
    assert.equal(se.CodeInputInterface.stringify('y'), 'y');
});



