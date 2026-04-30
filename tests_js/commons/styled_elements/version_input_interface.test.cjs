const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupVersionInputInterface = () => {
    class TextInputInterface {
        constructor(fieldId, options) {
            this.fieldId = fieldId;
            this.options = options;
        }
    }

    global.StyledElements = {
        TextInputInterface,
        Utils: {},
        InputValidationError: {
            NO_ERROR: 0,
            VERSION_ERROR: 1,
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/VersionInputInterface.js');
    return StyledElements.VersionInputInterface;
};

test('StyledElements.VersionInputInterface sets default placeholder', () => {
    resetLegacyRuntime();
    const VersionInputInterface = setupVersionInputInterface();
    const input = new VersionInputInterface('version', {});

    assert.equal(input.options.placeholder, '1.0');
});

test('StyledElements.VersionInputInterface supports missing options argument', () => {
    resetLegacyRuntime();
    const VersionInputInterface = setupVersionInputInterface();
    const input = new VersionInputInterface('version');

    assert.equal(input.options.placeholder, '1.0');
});

test('StyledElements.VersionInputInterface respects custom placeholder', () => {
    resetLegacyRuntime();
    const VersionInputInterface = setupVersionInputInterface();
    const input = new VersionInputInterface('version', { placeholder: '2.0' });

    assert.equal(input.options.placeholder, '2.0');
});

test('StyledElements.VersionInputInterface accepts valid versions', () => {
    resetLegacyRuntime();
    const VersionInputInterface = setupVersionInputInterface();
    const input = new VersionInputInterface('version', {});

    assert.equal(input._checkValue('0'), 0);
    assert.equal(input._checkValue('1.2.3'), 0);
});

test('StyledElements.VersionInputInterface rejects invalid versions', () => {
    resetLegacyRuntime();
    const VersionInputInterface = setupVersionInputInterface();
    const input = new VersionInputInterface('version', {});

    assert.equal(input._checkValue('01.2'), 1);
    assert.equal(input._checkValue('1..2'), 1);
});
