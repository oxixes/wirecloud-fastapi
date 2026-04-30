const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupList = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.enabled = true;
            this.dispatched = [];
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }
    }

    global.StyledElements = {
        StyledElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            prependWord(extra, base) {
                return `${base}${extra ? ` ${extra}` : ''}`;
            },
            clone(value) {
                return Array.isArray(value) ? value.slice() : {...value};
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/List.js');
    return StyledElements.List;
};

test('StyledElements.List constructor initializes entries and options defaults', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({});

    assert.equal(list.wrapperElement.className.includes('styled_list'), true);
    assert.equal(list.multivalued, false);
    assert.equal(list.allowEmpty, false);
    assert.deepEqual(list.entries, []);
    assert.deepEqual(list.currentSelection, []);
});

test('StyledElements.List constructor supports id, class, full and allowEmpty', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        id: 'list-id',
        class: 'extra',
        full: true,
        multivalued: true,
        allowEmpty: false,
    });

    assert.equal(list.wrapperElement.id, 'list-id');
    assert.equal(list.wrapperElement.className.includes('extra'), true);
    assert.equal(list.wrapperElement.classList.contains('full'), true);
    assert.equal(list.allowEmpty, false);
});

test('StyledElements.List addEntries validates input type', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({});

    assert.throws(() => list.addEntries({value: 1}), TypeError);
});

test('StyledElements.List addEntries ignores null and empty arrays', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({});

    list.addEntries(null);
    list.addEntries([]);

    assert.deepEqual(list.entries, []);
});

test('StyledElements.List addEntries accepts array and object entries', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({});

    list.addEntries([
        ['a', 'A label'],
        {value: 'b', label: 'B label'},
        {value: 'c'},
    ]);

    assert.equal(list.entries.length, 3);
    assert.equal(list.entriesByValue.a.element.textContent, 'A label');
    assert.equal(list.entriesByValue.b.element.textContent, 'B label');
    assert.equal(list.entriesByValue.c.element.textContent, 'c');
});

test('StyledElements.List item click toggles selection only when list is enabled', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({initialEntries: [{value: 'x', label: 'X'}]});
    const row = list.entriesByValue.x.element;

    row.dispatchEvent({type: 'click'});
    assert.deepEqual(list.currentSelection, ['x']);

    list.enabled = false;
    row.dispatchEvent({type: 'click'});
    assert.deepEqual(list.currentSelection, ['x']);
});

test('StyledElements.List getSelection returns a copy', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({initialEntries: [{value: 'x'}, {value: 'y'}], initialSelection: ['x']});

    const selection = list.getSelection();
    selection.push('y');

    assert.deepEqual(list.currentSelection, ['x']);
});

test('StyledElements.List cleanSelection emits change only when there is selection', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({initialEntries: [{value: 'x'}], initialSelection: ['x']});

    list.cleanSelection();
    assert.deepEqual(list.currentSelection, []);
    assert.equal(list.dispatched.at(-1).name, 'change');

    const eventsBefore = list.dispatched.length;
    list.cleanSelection();
    assert.equal(list.dispatched.length, eventsBefore);
});

test('StyledElements.List select replaces current selection', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({initialEntries: [{value: 'x'}, {value: 'y'}], initialSelection: ['x']});

    list.select(['y']);

    assert.deepEqual(list.currentSelection, ['y']);
});

test('StyledElements.List addSelection handles non-multivalued mode and no-op branches', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        multivalued: false,
        initialEntries: [{value: 'x'}, {value: 'y'}],
        initialSelection: ['x']
    });
    const eventsBefore = list.dispatched.length;
    list.addSelection([]);
    list.addSelection(['x']);
    assert.equal(list.dispatched.length, eventsBefore);

    list.addSelection(['y', 'x']);
    assert.deepEqual(list.currentSelection, ['y']);
});

test('StyledElements.List addSelection handles multivalued mode', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        multivalued: true,
        initialEntries: [{value: 'x'}, {value: 'y'}],
    });

    list.addSelection(['x', 'y', 'x']);

    assert.deepEqual(list.currentSelection, ['x', 'y']);
});

test('StyledElements.List removeSelection ignores empty input and only emits on real removals', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        multivalued: true,
        initialEntries: [{value: 'x'}, {value: 'y'}],
        initialSelection: ['x', 'y']
    });
    const eventsBefore = list.dispatched.length;
    list.removeSelection([]);
    assert.equal(list.dispatched.length, eventsBefore);
    assert.throws(() => list.removeSelection(['missing']), TypeError);

    list.removeSelection(['x']);
    assert.deepEqual(list.currentSelection, []);
    assert.equal(list.dispatched.at(-1).name, 'change');
});

test('StyledElements.List toggleElementSelection adds or removes entries based on allowEmpty', () => {
    resetLegacyRuntime();
    const List = setupList();
    const allowEmptyList = new List({
        allowEmpty: true,
        initialEntries: [{value: 'x'}]
    });
    allowEmptyList.toggleElementSelection('x');
    assert.deepEqual(allowEmptyList.currentSelection, ['x']);
    allowEmptyList.toggleElementSelection('x');
    assert.deepEqual(allowEmptyList.currentSelection, []);

    const noEmptyList = new List({
        allowEmpty: false,
        initialEntries: [{value: 'x'}]
    });
    noEmptyList.toggleElementSelection('x');
    noEmptyList.toggleElementSelection('x');
    assert.deepEqual(noEmptyList.currentSelection, ['x']);
});

test('StyledElements.List removeEntryByValue removes entry map but keeps value-based selection unchanged', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        initialEntries: [{value: 'x'}, {value: 'y'}],
        initialSelection: ['x']
    });

    list.removeEntryByValue('x');

    assert.equal(list.entriesByValue.x, undefined);
    assert.deepEqual(list.currentSelection, ['x']);
});

test('StyledElements.List removeEntryByValue removes object-based selected entry and emits change', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        initialEntries: [{value: 'x'}, {value: 'y'}],
    });
    const selectedEntry = list.entriesByValue.x;
    list.currentSelection = [selectedEntry];

    list.removeEntryByValue('x');

    assert.deepEqual(list.currentSelection, []);
    assert.equal(list.dispatched.at(-1).name, 'change');
    assert.deepEqual(list.dispatched.at(-1).args[2], ['x']);
});

test('StyledElements.List clear resets selection and entries', () => {
    resetLegacyRuntime();
    const List = setupList();
    const list = new List({
        initialEntries: [{value: 'x'}],
        initialSelection: ['x']
    });

    list.clear();

    assert.deepEqual(list.entries, []);
    assert.deepEqual(list.entriesByValue, {});
    assert.deepEqual(list.currentSelection, []);
    assert.equal(list.content.textContent, '');
});
