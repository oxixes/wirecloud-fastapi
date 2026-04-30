const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupInputInterfaceFactory = () => {
    class InputInterface {}

    class BaseField extends InputInterface {
        constructor(fieldId, fieldDesc, factory) {
            super();
            this.fieldId = fieldId;
            this.fieldDesc = fieldDesc;
            this.factory = factory;
            this.disableCalls = 0;
        }

        disable() {
            this.disableCalls += 1;
        }

        static parse(value) {
            return `parse:${value}`;
        }

        static stringify(value) {
            return `string:${value}`;
        }
    }

    global.StyledElements = {
        InputInterface,
        Utils: {
            clone(value) {
                return {...value};
            }
        },
        BooleanInputInterface: BaseField,
        TextInputInterface: BaseField,
        VersionInputInterface: BaseField,
        PasswordInputInterface: BaseField,
        HiddenInputInterface: BaseField,
        ListInputInterface: BaseField,
        NumberInputInterface: BaseField,
        LongTextInputInterface: BaseField,
        URLInputInterface: BaseField,
        EMailInputInterface: BaseField,
        SelectInputInterface: BaseField,
        ButtonGroupInputInterface: BaseField,
        FileInputInterface: BaseField,
        FieldSetInterface: BaseField,
        MultivaluedInputInterface: BaseField,
        CodeInputInterface: BaseField,
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/InputInterfaceFactory.js');
    return StyledElements.InputInterfaceFactory;
};

test('StyledElements.InputInterfaceFactory creates text interfaces by default', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    const instance = factory.createInterface('field-id', {});

    assert.equal(instance.fieldId, 'field-id');
    assert.equal(instance.fieldDesc.type, undefined);
    assert.equal(instance.factory, factory);
});

test('StyledElements.InputInterfaceFactory throws for unknown interface types', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    assert.throws(() => factory.createInterface('field-id', {type: 'missing'}), /missing/);
});

test('StyledElements.InputInterfaceFactory disables interfaces when initiallyDisabled is true', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    const instance = factory.createInterface('field-id', {type: 'text', initiallyDisabled: true});

    assert.equal(instance.disableCalls, 1);
});

test('StyledElements.InputInterfaceFactory addFieldType rejects classes not extending InputInterface', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();
    class InvalidClass {}

    assert.throws(() => factory.addFieldType('custom', InvalidClass), TypeError);
});

test('StyledElements.InputInterfaceFactory addFieldType rejects duplicated types', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();
    class CustomField extends StyledElements.InputInterface {}

    assert.throws(() => factory.addFieldType('text', CustomField), Error);
});

test('StyledElements.InputInterfaceFactory addFieldType registers custom types', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    class CustomField extends StyledElements.InputInterface {
        constructor(fieldId, fieldDesc) {
            super();
            this.fieldId = fieldId;
            this.fieldDesc = fieldDesc;
        }

        static parse(value) {
            return value.toUpperCase();
        }

        static stringify(value) {
            return String(value).toLowerCase();
        }
    }

    factory.addFieldType('custom', CustomField);
    const instance = factory.createInterface('f', {type: 'custom'});

    assert.equal(instance instanceof CustomField, true);
    assert.equal(factory.parse('custom', 'x'), 'X');
    assert.equal(factory.stringify('custom', 'X'), 'x');
});

test('StyledElements.InputInterfaceFactory parse throws for invalid type', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    assert.throws(() => factory.parse('missing', 'a'), /Invalid data type/);
});

test('StyledElements.InputInterfaceFactory parse delegates to mapped type', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    assert.equal(factory.parse('text', 'value'), 'parse:value');
});

test('StyledElements.InputInterfaceFactory stringify throws for invalid type', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    assert.throws(() => factory.stringify('missing', 'a'), /Invalid data type/);
});

test('StyledElements.InputInterfaceFactory stringify delegates to mapped type', () => {
    resetLegacyRuntime();
    const InputInterfaceFactory = setupInputInterfaceFactory();
    const factory = new InputInterfaceFactory();

    assert.equal(factory.stringify('text', 'value'), 'string:value');
});
