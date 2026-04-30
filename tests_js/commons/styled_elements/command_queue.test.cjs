const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

test.beforeEach(() => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/CommandQueue.js');
});

test('StyledElements.CommandQueue validates constructor and ignores undefined commands', async () => {
    assert.throws(() => new StyledElements.CommandQueue({}, null), /callback parameter must be a function/);

    const queue = new StyledElements.CommandQueue({ id: 'ctx' }, (context, command) => command);
    assert.equal(queue.callback instanceof Function, true);
    assert.deepEqual(queue.context, { id: 'ctx' });
    await assert.doesNotReject(queue.addCommand(undefined));
});

test('StyledElements.CommandQueue processes commands sequentially', async () => {
    const handled = [];
    const queue = new StyledElements.CommandQueue({ prefix: 'ctx' }, async (context, command) => {
        handled.push(`${context.prefix}:${command}`);
        await Promise.resolve();
        return command.toUpperCase();
    });

    const events = [];
    queue.addEventListener('start', () => events.push('start'));
    queue.addEventListener('stop', () => events.push('stop'));

    const results = await Promise.all([
        queue.addCommand('one'),
        queue.addCommand('two'),
    ]);

    assert.deepEqual(results, ['ONE', 'TWO']);
    assert.deepEqual(handled, ['ctx:one', 'ctx:two']);
    assert.deepEqual(events, ['start', 'stop']);
    assert.equal(queue.running, false);
});

test('StyledElements.CommandQueue rejects failing commands and continues', async () => {
    const queue = new StyledElements.CommandQueue({}, (context, command) => {
        if (command === 'explode') {
            throw new Error('boom');
        }
        if (command === 'reject') {
            return Promise.reject(new Error('async-boom'));
        }
        return command;
    });

    await assert.rejects(queue.addCommand('explode'), /boom/);
    await assert.rejects(queue.addCommand('reject'), /async-boom/);
    await assert.doesNotReject(queue.addCommand('recover'));
    assert.equal(queue.running, false);
});
