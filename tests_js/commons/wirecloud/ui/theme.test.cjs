const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

test('Wirecloud.ui.Theme defines readonly fields from descriptor', () => {
    resetLegacyRuntime();
    global.Wirecloud = { ui: {} };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Theme.js');

    const theme = new Wirecloud.ui.Theme({
        name: 'default',
        label: 'Default Theme',
        templates: { dashboard: 'dashboard.html' },
    });

    assert.equal(theme.name, 'default');
    assert.equal(theme.label, 'Default Theme');
    assert.deepEqual(theme.templates, { dashboard: 'dashboard.html' });
    assert.equal(Object.getOwnPropertyDescriptor(theme, 'name').writable, false);
});
