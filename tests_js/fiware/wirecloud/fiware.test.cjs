const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test('Wirecloud.FiWare namespace is initialized', () => {
    resetLegacyRuntime();

    global.Wirecloud = {
        FiWare: {
            stale: true,
        },
    };

    loadLegacyScript('src/wirecloud/fiware/static/js/wirecloud/FiWare.js');

    assert.deepEqual(Wirecloud.FiWare, {});
});

