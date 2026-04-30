const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test.beforeEach(() => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
});

test('StyledElements.ObjectWithEvents dispatches named events and supports aliases', () => {
    const source = new StyledElements.ObjectWithEvents(['change']);
    const values = [];
    const handler = function (context, value) {
        values.push({ context, value });
    };

    source.on('change', handler);
    source.dispatchEvent('change', 42);
    source.off('change', handler);
    source.dispatchEvent('change', 64);

    assert.deepEqual(values, [{ context: source, value: 42 }]);
});

test('StyledElements.ObjectWithEvents rejects unknown events', () => {
    const source = new StyledElements.ObjectWithEvents(['known']);

    assert.throws(() => source.addEventListener('missing', () => {}), /Unhandled event 'missing'/);
    assert.throws(() => source.dispatchEvent('missing'), /Unhandled event 'missing'/);
});

test('StyledElements.ObjectWithEvents clears specific listeners and destroy nulls events', () => {
    const source = new StyledElements.ObjectWithEvents(['change', 'save']);
    const calls = [];
    const handler = () => calls.push('change');
    const other = () => calls.push('save');

    source.addEventListener('change', handler);
    source.addEventListener('save', other);
    source.clearEventListeners('change');
    source.dispatchEvent('change');
    source.dispatchEvent('save');
    assert.deepEqual(calls, ['save']);

    assert.throws(() => source.clearEventListeners('missing'), /Unhandled event 'missing'/);
    assert.throws(() => source.removeEventListener('missing', handler), /Unhandled event 'missing'/);
    assert.equal(source.destroy(), source);
    assert.equal(source.events, null);
});

test('StyledElements.ObjectWithEvents clears all listeners when called without a name', () => {
    const source = new StyledElements.ObjectWithEvents(['change', 'save']);
    const calls = [];

    source.addEventListener('change', () => calls.push('change'));
    source.addEventListener('save', () => calls.push('save'));
    assert.equal(source.clearEventListeners(), source);
    source.dispatchEvent('change');
    source.dispatchEvent('save');
    assert.deepEqual(calls, []);
});

test('StyledElements.ObjectWithEvents handles missing constructor event lists', () => {
    const source = new StyledElements.ObjectWithEvents(null);
    assert.deepEqual(source.events, {});
    assert.throws(() => source.dispatchEvent('anything'), /Unhandled event 'anything'/);
});
