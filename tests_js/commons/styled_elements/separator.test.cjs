const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test('StyledElements.Separator sets an hr wrapper with separator role', () => {
    resetLegacyRuntime();

    class StyledElement {
        constructor(events) {
            this.events = events;
        }
    }

    global.StyledElements = {
        StyledElement,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Separator.js');

    const separator = new StyledElements.Separator();
    assert.deepEqual(separator.events, []);
    assert.equal(separator.wrapperElement.tagName, 'HR');
    assert.equal(separator.wrapperElement.getAttribute('role'), 'separator');
});
