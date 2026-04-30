const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPills = () => {
    class Container {
        constructor(options, events) {
            this.options = options;
            this.events = events;
            this.dispatched = [];
        }

        dispatchEvent(name, value) {
            this.dispatched.push({ name, value });
        }
    }

    global.StyledElements = {
        Container,
        Utils: {
            appendWord: (className, word) => className ? `${className} ${word}` : word,
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Pills.js');
    return StyledElements.Pills;
};

test('StyledElements.Pills initializes wrapper and internal state', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: 'custom' });

    assert.equal(pills.wrapperElement.className, 'custom se-pills');
    assert.equal(pills.wrapperElement.getAttribute('role'), 'tablist');
    assert.equal(pills.activePill, null);
});

test('StyledElements.Pills add creates tab entries', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });

    pills.add('one', 'First');

    assert.equal(pills.pills.one.textContent, 'First');
    assert.equal(pills.pills.one.getAttribute('role'), 'tab');
});

test('StyledElements.Pills switchPill activates selected tab and dispatches change', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });
    pills.add('one', 'First');
    pills.add('two', 'Second');

    pills.switchPill('one');

    assert.equal(pills.activePill, 'one');
    assert.equal(pills.pills.one.classList.contains('active'), true);
    assert.deepEqual(pills.dispatched.at(-1), { name: 'change', value: 'one' });
});

test('StyledElements.Pills switchPill deactivates previous tab', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });
    pills.add('one', 'First');
    pills.add('two', 'Second');

    pills.switchPill('one');
    pills.switchPill('two');

    assert.equal(pills.pills.one.classList.contains('active'), false);
    assert.equal(pills.pills.two.classList.contains('active'), true);
});

test('StyledElements.Pills switchPill ignores already active tab', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });
    pills.add('one', 'First');
    pills.switchPill('one');
    const eventsBefore = pills.dispatched.length;

    pills.switchPill('one');

    assert.equal(pills.dispatched.length, eventsBefore);
});

test('StyledElements.Pills switchPill rejects invalid ids', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });

    assert.throws(() => pills.switchPill('missing'), /Invalid pill id/);
});

test('StyledElements.Pills click callback prevents default and switches tab', () => {
    resetLegacyRuntime();
    const Pills = setupPills();
    const pills = new Pills({ class: '' });
    pills.add('one', 'First');

    let prevented = 0;
    let stopped = 0;
    pills.pills.one.dispatchEvent({
        type: 'click',
        preventDefault() {
            prevented += 1;
        },
        stopPropagation() {
            stopped += 1;
        }
    });

    assert.equal(prevented, 1);
    assert.equal(stopped, 1);
    assert.equal(pills.activePill, 'one');
});
