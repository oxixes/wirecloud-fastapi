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

test('StyledElements.Event dispatches handlers with the bound context', () => {
    const context = { id: 'ctx-1' };
    const event = new StyledElements.Event(context);
    const calls = [];

    event.addEventListener((receivedContext, value) => {
        calls.push({ thisValue: this, receivedContext, value });
    });
    event.dispatch('payload');

    assert.equal(calls.length, 1);
    assert.equal(calls[0].receivedContext, context);
    assert.equal(calls[0].value, 'payload');
});

test('StyledElements.Event allows removing listeners during dispatch', () => {
    const event = new StyledElements.Event({});
    const calls = [];
    const removable = () => {
        calls.push('removed');
    };
    const keeper = function (context) {
        calls.push('keeper');
        event.removeEventListener(removable);
        assert.equal(context, event.context);
    };

    event.addEventListener(removable);
    event.addEventListener(keeper);

    event.dispatch();
    event.dispatch();

    assert.deepEqual(calls, ['removed', 'keeper', 'keeper']);
});

test('StyledElements.Event rejects non-function handlers', () => {
    const event = new StyledElements.Event({});

    assert.throws(() => event.addEventListener('nope'), /Handlers must be functions/);
    assert.throws(() => event.removeEventListener(null), /Handlers must be functions/);
});

test('StyledElements.Event clears listeners during dispatch', () => {
    const event = new StyledElements.Event({});
    const calls = [];
    event.addEventListener(() => {
        calls.push('first');
        event.clearEventListeners();
    });
    event.addEventListener(() => {
        calls.push('second');
    });

    event.dispatch('payload');
    event.dispatch('payload');

    assert.deepEqual(calls, ['first']);
});

test('StyledElements.Event logs handler errors and keeps dispatching', () => {
    const event = new StyledElements.Event({});
    const originalError = console.error;
    const logged = [];
    const calls = [];

    console.error = (error) => logged.push(error.message);
    event.addEventListener(() => {
        calls.push('broken');
        throw new Error('handler failed');
    });
    event.addEventListener(() => {
        calls.push('healthy');
    });

    event.dispatch('payload');
    console.error = originalError;

    assert.deepEqual(calls, ['broken', 'healthy']);
    assert.deepEqual(logged, ['handler failed']);
});
