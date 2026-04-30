const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const loadPaginatedSource = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PaginatedSource.js');
    return StyledElements.PaginatedSource;
};

const makeSource = (extraOptions = {}) => {
    const PaginatedSource = loadPaginatedSource();
    const calls = [];
    const source = new PaginatedSource({
        pageSize: 2,
        requestFunc(page, options, onSuccess, onError) {
            calls.push({ page, options: { ...options } });
            if (options.fail) {
                onError(options.fail === true ? null : options.fail);
                return;
            }
            onSuccess([{ page }], { current_page: String(page), total_count: 5 });
        },
        ...extraOptions
    });
    return { source, calls, PaginatedSource };
};

test('StyledElements.PaginatedSource requires requestFunc', () => {
    const PaginatedSource = loadPaginatedSource();
    assert.throws(() => new PaginatedSource({}), /requestFunc must be a function/);
});

test('StyledElements.PaginatedSource refresh populates current page data', () => {
    const { source } = makeSource();

    source.refresh();

    assert.equal(source.currentPage, 1);
    assert.deepEqual(source.currentElements, [{ page: 1 }]);
});

test('StyledElements.PaginatedSource invokes processFunc on successful requests', () => {
    const processed = [];
    const { source } = makeSource({
        processFunc(elements, options) {
            processed.push({ elements, options });
        }
    });

    source.refresh();

    assert.equal(processed.length, 1);
});

test('StyledElements.PaginatedSource exposes totalCount after refresh', () => {
    const { source } = makeSource();

    source.refresh();

    assert.equal(source.totalCount, 5);
});

test('StyledElements.PaginatedSource keeps getCurrentPage aligned with currentElements', () => {
    const { source } = makeSource();

    source.refresh();

    assert.equal(source.getCurrentPage(), source.currentElements);
});

test('StyledElements.PaginatedSource navigation methods request the expected pages', () => {
    const { source, calls } = makeSource();

    source.refresh();
    source.goToNext();
    source.goToLast();
    source.goToPrevious();
    source.goToFirst();

    assert.deepEqual(calls.map((entry) => entry.page), [1, 2, 3, 2, 1]);
});

test('StyledElements.PaginatedSource emits requestStart and requestEnd for each request', () => {
    const { source } = makeSource();
    const starts = [];
    const ends = [];

    source.addEventListener('requestStart', () => starts.push(true));
    source.addEventListener('requestEnd', (context, detail) => ends.push(detail ?? null));

    source.refresh();
    source.goToNext();
    source.goToFirst();

    assert.equal(starts.length, 3);
    assert.equal(ends.length, 3);
});

test('StyledElements.PaginatedSource emits paginationChanged when total count changes', () => {
    const { source } = makeSource();
    const changes = [];

    source.addEventListener('paginationChanged', () => changes.push(source.totalPages));
    source.refresh();
    source.goToNext();

    assert.deepEqual(changes, [3]);
});

test('StyledElements.PaginatedSource recalculates totalPages when pageSize changes', () => {
    const { source } = makeSource({ pageSize: 4 });

    source.refresh();
    source.changeOptions({ pageSize: 2 });

    assert.equal(source.options.pageSize, 2);
    assert.equal(source.totalPages, 3);
});

test('StyledElements.PaginatedSource changeOptions emits optionsChanged and resets page on non-pageSize fields', () => {
    const { source } = makeSource();
    const optionChanges = [];

    source.refresh();
    source.goToNext();
    source.addEventListener('optionsChanged', (context, options) => optionChanges.push({ ...options }));
    source.changeOptions({ filterName: 'name-filter' });

    assert.equal(source.currentPage, 1);
    assert.equal(optionChanges.length, 1);
});

test('StyledElements.PaginatedSource ignores non-object changeOptions inputs', () => {
    const { source, calls } = makeSource();

    source.refresh();
    source.changeOptions('ignored');

    assert.equal(calls.length, 1);
});

test('StyledElements.PaginatedSource defaults null errors to unknown cause', () => {
    const { source } = makeSource();
    const errors = [];

    source.addEventListener('requestEnd', (context, error) => errors.push(error));
    source.changeOptions({ fail: true });

    assert.deepEqual(source.currentElements, []);
    assert.deepEqual(errors.at(-1), { message: 'unknown cause' });
});

test('StyledElements.PaginatedSource forwards explicit errors in requestEnd', () => {
    const { source } = makeSource();
    const errors = [];

    source.addEventListener('requestEnd', (context, error) => errors.push(error));
    source.changeOptions({ fail: { message: 'provided cause' } });

    assert.deepEqual(errors.at(-1), { message: 'provided cause' });
});

test('StyledElements.PaginatedSource clamps changePage to valid bounds', () => {
    const { source, calls } = makeSource();

    source.refresh();
    source.changePage(99);
    source.changePage(-10);

    assert.equal(calls.at(-2).page, 3);
    assert.equal(calls.at(-1).page, 1);
});

test('StyledElements.PaginatedSource keeps totalPages to one when pageSize is zero', () => {
    const { source } = makeSource();

    source.refresh();
    source.changeOptions({ pageSize: 0 });

    assert.equal(source.options.pageSize, 0);
    assert.equal(source.totalPages, 1);
});
