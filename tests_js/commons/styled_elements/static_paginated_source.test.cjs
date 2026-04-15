const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScripts,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const loadStaticPaginatedSource = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    loadLegacyScripts([
        'src/wirecloud/commons/static/js/StyledElements/PaginatedSource.js',
        'src/wirecloud/commons/static/js/StyledElements/StaticPaginatedSource.js',
    ]);
    return StyledElements.StaticPaginatedSource;
};

const createSource = (extra = {}) => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    return new StaticPaginatedSource({
        pageSize: 2,
        idAttr: 'id',
        sort_info: {
            created: { type: 'date' },
            score: { type: 'number' },
            name: { type: 'text' },
        },
        initialElements: [
            { id: 1, name: 'Charlie', score: '2', created: '2026-04-02' },
            { id: 2, name: 'Alice', score: '10', created: 'invalid-date' },
            { id: 3, name: 'Bob', score: null, created: '2026-04-01' },
        ],
        ...extra
    });
};

test('StyledElements.StaticPaginatedSource reports source length and elements', () => {
    const source = createSource();
    assert.equal(source.length, 3);
    assert.deepEqual(source.getElements().map((item) => item.id), [1, 2, 3]);
});

test('StyledElements.StaticPaginatedSource supports text ordering', () => {
    const source = createSource();
    source.changeOptions({ order: ['name'] });
    assert.deepEqual(source.currentElements.map((item) => item.id), [2, 3]);
});

test('StyledElements.StaticPaginatedSource supports inverse numeric ordering', () => {
    const source = createSource();
    source.changeOptions({ order: ['-score'] });
    assert.deepEqual(source.currentElements.map((item) => item.id), [2, 1]);
});

test('StyledElements.StaticPaginatedSource supports date ordering with invalid values', () => {
    const source = createSource();
    source.changeOptions({ order: ['created'] });
    assert.deepEqual(source.currentElements.map((item) => item.id), [2, 3]);
});

test('StyledElements.StaticPaginatedSource filters by keywords', () => {
    const source = createSource();
    source.changeOptions({ keywords: 'bo' });
    assert.deepEqual(source.currentElements.map((item) => item.id), [3]);
});

test('StyledElements.StaticPaginatedSource paginates and can move to next page', () => {
    const source = createSource();
    source.changeOptions({ keywords: '' });
    source.goToNext();
    assert.deepEqual(source.currentElements.map((item) => item.id), [3]);
});

test('StyledElements.StaticPaginatedSource requestFunc handles page underflow and overflow', () => {
    const source = createSource();
    source.changeOptions({ pageSize: 0, order: null });

    source.options.requestFunc(-1, source.options, (elements, paging) => {
        assert.equal(elements.length, 3);
        assert.equal(paging.current_page, 0);
    });
    source.options.requestFunc(99, source.options, (elements, paging) => {
        assert.equal(elements.length, 3);
        assert.equal(paging.current_page, source.totalPages);
    });
});

test('StyledElements.StaticPaginatedSource uses custom date parser when provided', () => {
    const source = createSource();
    source.options.sort_info.created.dateparser = (value) => new Date(value);
    source.changeOptions({ order: ['created'] });
    assert.equal(source.currentElements.length > 0, true);
});

test('StyledElements.StaticPaginatedSource supports number and text fallback sorting branches', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        sort_info: {
            score: { type: 'number' },
            label: { type: 'text' },
        },
        initialElements: [
            { score: null, label: null, unknown: 'z' },
            { score: '2', label: 'b', unknown: 'b' },
            { score: '10', label: 'a', unknown: 'a' },
        ]
    });

    source.changeOptions({ order: ['score'] });
    source.changeOptions({ order: ['label'] });
    source.changeOptions({ order: ['unknown'] });
    assert.equal(source.currentElements.length, 3);
});

test('StyledElements.StaticPaginatedSource handles null-first text sort branch', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        sort_info: {
            label: { type: 'text' },
        },
        initialElements: [{ label: 'x' }, { label: null }]
    });
    source.changeOptions({ order: ['label'] });
    assert.equal(source.currentElements.length, 2);
});

test('StyledElements.StaticPaginatedSource validates unique ids on constructor input', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    assert.throws(() => new StaticPaginatedSource({
        idAttr: 'id',
        initialElements: [{ id: 1 }, { id: 1 }]
    }), /unique ID/);
});

test('StyledElements.StaticPaginatedSource validates nested id paths on constructor input', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    assert.throws(() => new StaticPaginatedSource({
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 } }, { meta: {} }]
    }), /valid ID/);
});

test('StyledElements.StaticPaginatedSource rejects null nested ids', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    assert.throws(() => new StaticPaginatedSource({
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 } }, { meta: null }]
    }), /valid ID/);
});

test('StyledElements.StaticPaginatedSource updates existing elements by id', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [
            { meta: { id: 1 }, name: 'one' },
            { meta: { id: 2 }, name: 'two' },
        ]
    });

    source.addElement({ meta: { id: 2 }, name: 'two-new' });
    assert.deepEqual(source.getElements().map((item) => item.name), ['one', 'two-new']);
});

test('StyledElements.StaticPaginatedSource appends new elements', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 }, name: 'one' }]
    });

    source.addElement({ meta: { id: 3 }, name: 'three' });
    assert.equal(source.length, 2);
});

test('StyledElements.StaticPaginatedSource addElement respects active keyword filters', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [
            { meta: { id: 1 }, name: 'one' },
            { meta: { id: 2 }, name: 'three' },
        ]
    });

    source.changeOptions({ keywords: 'three' });
    source.addElement({ meta: { id: 4 }, name: 'other' });
    source.addElement({ meta: { id: 5 }, name: 'three-plus' });
    assert.deepEqual(source.currentElements.map((item) => item.meta.id), [2, 5]);
});

test('StyledElements.StaticPaginatedSource removeElement deletes matching entries', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [
            { meta: { id: 1 }, name: 'one' },
            { meta: { id: 2 }, name: 'two' },
        ]
    });

    source.removeElement({ meta: { id: 1 } });
    assert.equal(source.length, 1);
});

test('StyledElements.StaticPaginatedSource removeElement requires existing elements', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 }, name: 'one' }]
    });
    assert.throws(() => source.removeElement({ meta: { id: 99 } }), /Element does not exist/);
});

test('StyledElements.StaticPaginatedSource removeElement requires valid ids', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 }, name: 'one' }]
    });
    assert.throws(() => source.removeElement({ meta: {} }), /valid ID/);
});

test('StyledElements.StaticPaginatedSource addElement requires valid ids when idAttr is set', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        pageSize: 10,
        idAttr: ['meta', 'id'],
        initialElements: [{ meta: { id: 1 }, name: 'one' }]
    });
    assert.throws(() => source.addElement({ meta: {} }), /valid ID/);
});

test('StyledElements.StaticPaginatedSource removeElement requires idAttr to be set', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        initialElements: [{ a: 1 }]
    });
    assert.throws(() => source.removeElement({ a: 1 }), /idAttr is not set/);
});

test('StyledElements.StaticPaginatedSource addElement works without idAttr', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        initialElements: [{ a: 1 }]
    });

    source.addElement({ a: 2 });
    assert.equal(source.length, 2);
});

test('StyledElements.StaticPaginatedSource changeElements resets to empty on invalid inputs', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        initialElements: [{ a: 1 }]
    });
    source.changeElements('invalid');
    assert.equal(source.length, 0);
});

test('StyledElements.StaticPaginatedSource validates function-based id extractors', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource({
        idAttr: (entry) => entry.key,
        initialElements: [{ key: 'a' }]
    });
    assert.throws(() => source.changeElements([{ key: null }]), /valid ID/);
});

test('StyledElements.StaticPaginatedSource accepts non-object constructor options', () => {
    const StaticPaginatedSource = loadStaticPaginatedSource();
    const source = new StaticPaginatedSource('invalid-options');
    assert.equal(source.length, 0);
});
