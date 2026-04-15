const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const flush = async () => {
    await Promise.resolve();
    await Promise.resolve();
};

const loadTask = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    global.Wirecloud = {
        Utils: StyledElements.Utils,
    };
    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/Task.js');
    return global.Wirecloud.Task;
};

test('Wirecloud.Task validates constructor inputs', () => {
    const Task = loadTask();

    assert.throws(() => new Task(), /missing title parameter/);
    assert.throws(() => new Task('bad', 'nope'), /executor must be a function or a task array/);
    assert.throws(() => new Task('bad', []), /at least one subtask is required/);
});

test('Wirecloud.Task resolves, rejects, updates progress, and aborts correctly', async () => {
    const Task = loadTask();
    const progressValues = [];
    const failureReasons = [];
    const abortReasons = [];
    let resolveTask;
    let rejectTask;
    let updateTask;

    const task = new Task('demo', (resolve, reject, update) => {
        resolveTask = resolve;
        rejectTask = reject;
        updateTask = update;
    });

    task.addEventListener('progress', (context, progress) => progressValues.push(progress));
    task.addEventListener('fail', (context, reason) => failureReasons.push(reason));
    task.addEventListener('abort', (context, reason) => abortReasons.push(reason));

    updateTask(-5);
    updateTask(150);
    updateTask(40);
    assert.deepEqual(progressValues.slice(0, 3), [0, 100, 40]);

    resolveTask('done');
    assert.equal(task.status, 'resolved');
    assert.equal(task.value, 'done');
    assert.equal(task.progress, 100);
    assert.equal(task.toString(), 'demo: 100%');
    assert.equal(task.renameTask('renamed').title, 'renamed');
    assert.throws(() => updateTask(10), /Only pending tasks can be resolved/);
    assert.throws(() => resolveTask('again'), /Only pending tasks can be resolved/);
    assert.throws(() => rejectTask('again'), /Only pending tasks can be resolved/);

    let rejectLater;
    const rejectable = new Task('rejectable', (resolve, reject) => {
        rejectLater = reject;
    });
    rejectLater('nope');
    assert.equal(rejectable.status, 'rejected');
    assert.equal(rejectable.value, 'nope');
    assert.deepEqual(failureReasons, []);

    let updateLater;
    let rejectAborted;
    const aborted = new Task('aborted', (resolve, reject, update) => {
        updateLater = update;
    });
    const abortedRejectable = new Task('abortedRejectable', (resolve, reject) => {
        rejectAborted = reject;
    });
    aborted.addEventListener('abort', (context, reason) => abortReasons.push(reason));
    aborted.addEventListener('fail', () => failureReasons.push('fail'));
    aborted.abort('stop');
    abortedRejectable.abort('stop-2');
    rejectAborted('ignored');
    updateLater(50);
    assert.equal(aborted.status, 'aborted');
    assert.equal(aborted.value, 'stop');
    assert.deepEqual(abortReasons, ['stop']);
    assert.deepEqual(failureReasons, []);
});

test('Wirecloud.Task aggregates subtasks and reflects resolved, rejected, and aborted states', async () => {
    const Task = loadTask();
    const makeSettledTask = (title, action) => new Task(title, (resolve, reject) => action(resolve, reject));

    const first = makeSettledTask('first', (resolve) => resolve('a'));
    const second = makeSettledTask('second', (resolve) => resolve('b'));
    const aggregated = new Task('group', [first, second]);
    assert.equal(aggregated.status, 'resolved');
    assert.deepEqual(aggregated.value, ['a', 'b']);

    const rejected = makeSettledTask('rejected', (resolve, reject) => reject('bad'));
    const rejectedGroup = new Task('rejectedGroup', [rejected]);
    assert.equal(rejectedGroup.status, 'rejected');
    assert.deepEqual(rejectedGroup.value, ['bad']);

    const pendingChild = new Task('pendingChild', () => {});
    const pendingGroup = new Task('pendingGroup', [pendingChild]);
    assert.equal(pendingGroup.status, 'pending');
    pendingChild.abort('halt');
    assert.equal(pendingGroup.status, 'aborted');
    assert.deepEqual(pendingGroup.value, ['halt']);

    const childA = new Task('childA', () => {});
    const childB = new Task('childB', () => {});
    const abortingGroup = new Task('abortingGroup', [childA, childB]);
    abortingGroup.abort('cascade');
    assert.equal(childA.status, 'aborted');
    assert.equal(childB.status, 'aborted');
});

test('Wirecloud.Task then, catch, finally, and toTask cover continuation branches', async () => {
    const Task = loadTask();

    const resolved = new Task('resolved', (resolve) => resolve(3));
    assert.equal(await resolved.then((value) => value + 1), 4);
    assert.equal(await resolved.then(), 3);
    await assert.rejects(resolved.then(() => { throw new Error('boom'); }), /boom/);

    const rejected = new Task('rejected', (resolve, reject) => reject('bad'));
    assert.equal(await rejected.catch((reason) => `handled:${reason}`), 'handled:bad');
    assert.equal(await rejected.finally(() => 'ignored'), 'ignored');

    const aborted = new Task('aborted', () => {});
    aborted.abort('stop');
    assert.equal((await aborted.then(null, null, (reason) => `aborted:${reason}`)).valueOf(), 'aborted:stop');

    const childTask = resolved.then((value) => new Task('child', (resolve) => resolve(value * 2)));
    assert.equal(await childTask, 6);

    const promiseChild = resolved.then((value) => Promise.resolve(value * 3));
    assert.equal(await promiseChild, 9);

    let rootResolve;
    let rootUpdate;
    const rootTask = new Task('root', (resolve, reject, update) => {
        rootResolve = resolve;
        rootUpdate = update;
    });
    const defaultWrapped = rootTask.toTask();
    const wrapped = rootTask.toTask('root-progress');
    assert.equal(defaultWrapped.title, 'root');
    rootUpdate(25);
    assert.equal(wrapped.progress, 25);
    rootResolve('root-value');
    assert.equal(wrapped.title, 'root-progress');
    assert.equal(await wrapped, 'root-value');
    assert.deepEqual(wrapped.subtasks, [rootTask]);
});

test('Wirecloud.TaskContinuation toTask tracks nested tasks and retroactive aborts parents', async () => {
    const Task = loadTask();

    let resolveParent;
    const parent = new Task('parent', (resolve) => {
        resolveParent = resolve;
    });
    const chain = parent.then((value) => new Task('nested', (resolve, reject, update) => {
        update(60);
        resolve(`${value}-nested`);
    }));
    const tracked = chain.toTask();
    resolveParent('value');
    await flush();

    assert.equal(await tracked, 'value-nested');
    assert.equal(tracked.title, 'parent');
    assert.equal(tracked.subtasks.length >= 2, true);

    let resolvePending;
    const pendingParent = new Task('pendingParent', (resolve) => {
        resolvePending = resolve;
    });
    const continuation = pendingParent.then((value) => value);
    continuation.abort('chain-stop', true);
    assert.equal(pendingParent.status, 'aborted');
    resolvePending('ignored');
    assert.equal(continuation.status, 'aborted');
});

test('Wirecloud.Task supports explicit continuation titles and abort-only handlers', async () => {
    const Task = loadTask();

    let resolveParent;
    const parent = new Task('parent', (resolve) => {
        resolveParent = resolve;
    });
    const continuation = parent.then((value) => value);
    const retitled = continuation.toTask('custom-title');
    assert.equal(retitled.title, 'custom-title');
    resolveParent('value');
    assert.equal(await retitled, 'value');

    const aborted = new Task('aborted', () => {});
    aborted.abort('stop');
    assert.equal(await aborted.catch(null, (reason) => `abort:${reason}`), 'abort:stop');
    assert.equal(await aborted.finally(() => 'after-abort'), 'after-abort');
});

test('Wirecloud.Task ignores resolution callbacks after a continuation has been aborted', async () => {
    const Task = loadTask();

    let resolveParent;
    const parent = new Task('parent', (resolve) => {
        resolveParent = resolve;
    });
    const continuation = parent.then((value) => value);
    continuation.abort('stop');
    resolveParent('ignored');
    await flush();

    assert.equal(continuation.status, 'aborted');
    assert.equal(parent.status, 'resolved');
});
