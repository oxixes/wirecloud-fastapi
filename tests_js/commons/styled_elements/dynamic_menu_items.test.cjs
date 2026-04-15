const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test('StyledElements.DynamicMenuItems supports default and injected builders', () => {
    resetLegacyRuntime();
    global.StyledElements = {};

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/DynamicMenuItems.js');

    const DynamicMenuItems = StyledElements.DynamicMenuItems;
    const customBuild = () => ['x'];
    const custom = new DynamicMenuItems(customBuild);
    const defaults = new DynamicMenuItems();

    assert.equal(custom.build, customBuild);
    assert.deepEqual(defaults.build(), []);
});
