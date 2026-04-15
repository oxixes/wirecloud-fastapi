const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupFragment = () => {
    class StyledElement {}

    const appendedCalls = [];
    global.StyledElements = {
        StyledElement,
        Utils: {
            appendChild(parent, child, ref) {
                appendedCalls.push({parent, child, ref});
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Fragment.js');
    return {Fragment: StyledElements.Fragment, appendedCalls};
};

test('StyledElements.Fragment constructor stores children and exposes elements alias', () => {
    resetLegacyRuntime();
    const {Fragment} = setupFragment();
    const child = document.createElement('span');
    const fragment = new Fragment(child);

    assert.deepEqual(fragment.children, [child]);
    assert.equal(fragment.elements, fragment.children);
});

test('StyledElements.Fragment appendChild ignores null values', () => {
    resetLegacyRuntime();
    const {Fragment} = setupFragment();
    const fragment = new Fragment(null);
    const result = fragment.appendChild(null);

    assert.equal(result, fragment);
    assert.equal(fragment.children.length, 0);
});

test('StyledElements.Fragment appendChild expands html strings into nodes', () => {
    resetLegacyRuntime();
    const {Fragment} = setupFragment();
    const fragment = new Fragment(null);

    const result = fragment.appendChild('<span>a</span>');

    assert.equal(result, fragment);
    assert.equal(Array.isArray(fragment.children), true);
});

test('StyledElements.Fragment appendChild merges children from nested fragments', () => {
    resetLegacyRuntime();
    const {Fragment} = setupFragment();
    const nestedChild = document.createElement('i');
    const nested = new Fragment(nestedChild);
    const fragment = new Fragment(null);

    fragment.appendChild(nested);

    assert.deepEqual(fragment.children, [nestedChild]);
});

test('StyledElements.Fragment appendTo delegates to utils.appendChild for each child', () => {
    resetLegacyRuntime();
    const {Fragment, appendedCalls} = setupFragment();
    const first = document.createElement('a');
    const second = document.createElement('b');
    const parent = document.createElement('div');
    const ref = document.createElement('mark');
    const fragment = new Fragment([first, second]);

    const result = fragment.appendTo(parent, ref);

    assert.equal(result, fragment);
    assert.equal(appendedCalls.length, 2);
    assert.equal(appendedCalls[0].child, first);
    assert.equal(appendedCalls[1].child, second);
});

test('StyledElements.Fragment repaint only calls repaint-capable children', () => {
    resetLegacyRuntime();
    const {Fragment} = setupFragment();
    const childWithRepaint = {
        repaintCalls: 0,
        repaint() {
            this.repaintCalls += 1;
        }
    };
    const childWithoutRepaint = {};
    const fragment = new Fragment([childWithRepaint, childWithoutRepaint]);

    const result = fragment.repaint();

    assert.equal(result, fragment);
    assert.equal(childWithRepaint.repaintCalls, 1);
});
