const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test('StyledElements.DefaultInputInterfaceFactory instantiates InputInterfaceFactory', () => {
    resetLegacyRuntime();
    class FakeFactory {}
    global.StyledElements = {
        InputInterfaceFactory: FakeFactory
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/DefaultInputInterfaceFactory.js');

    assert.equal(StyledElements.DefaultInputInterfaceFactory instanceof FakeFactory, true);
});
