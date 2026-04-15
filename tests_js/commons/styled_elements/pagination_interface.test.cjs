const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPaginationInterface = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
        }
    }

    class Container extends StyledElement {
        constructor() {
            super();
            this.clearCalls = 0;
            this.appended = [];
        }

        clear() {
            this.clearCalls += 1;
            this.appended = [];
            return this;
        }

        appendChild(value) {
            this.appended.push(value);
            return this;
        }
    }

    class Button extends StyledElement {
        constructor() {
            super();
            this.listeners = {};
            this.disableCalls = 0;
            this.enableCalls = 0;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        disable() {
            this.disableCalls += 1;
        }

        enable() {
            this.enableCalls += 1;
        }
    }

    class GUIBuilder {
        constructor() {
            this.DEFAULT_OPENING = '<layout>';
            this.DEFAULT_CLOSING = '</layout>';
        }

        parse(template, elements) {
            GUIBuilder.lastParse = {template, elements};
            return {template, elements};
        }
    }
    GUIBuilder.lastParse = null;

    global.StyledElements = {
        StyledElement,
        Container,
        Button,
        GUIBuilder,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            gettext: (text) => text,
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PaginationInterface.js');
    return StyledElements.PaginationInterface;
};

const createSource = (overrides = {}) => {
    const source = {
        currentPage: 1,
        totalPages: 3,
        totalCount: 9,
        listeners: {},
        firstCalls: 0,
        prevCalls: 0,
        nextCalls: 0,
        lastCalls: 0,
        goToFirst() {
            this.firstCalls += 1;
        },
        goToPrevious() {
            this.prevCalls += 1;
        },
        goToNext() {
            this.nextCalls += 1;
        },
        goToLast() {
            this.lastCalls += 1;
        },
        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }
    };
    return Object.assign(source, overrides);
};

test('StyledElements.PaginationInterface creates controls and wires source navigation actions', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource();
    const pagination = new PaginationInterface(source, {});

    pagination.firstBtn.listeners.click();
    pagination.prevBtn.listeners.click();
    pagination.nextBtn.listeners.click();
    pagination.lastBtn.listeners.click();

    assert.equal(source.firstCalls, 1);
    assert.equal(source.prevCalls, 1);
    assert.equal(source.nextCalls, 1);
    assert.equal(source.lastCalls, 1);
    assert.equal(typeof source.listeners.requestEnd, 'function');
});

test('StyledElements.PaginationInterface setter layout parses template and replaces contents', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource();
    const pagination = new PaginationInterface(source, {});

    pagination.layout = '<custom-layout/>';

    assert.equal(StyledElements.GUIBuilder.lastParse.template, '<custom-layout/>');
    assert.equal(pagination.wrapperContainer.clearCalls >= 2, true);
    assert.equal(pagination.wrapperContainer.appended.length, 1);
});

test('StyledElements.PaginationInterface changeLayout delegates to layout setter', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource();
    const pagination = new PaginationInterface(source, {});

    pagination.changeLayout('<changed/>');

    assert.equal(StyledElements.GUIBuilder.lastParse.template, '<changed/>');
});

test('StyledElements.PaginationInterface constructor disables previous buttons on first page', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource({currentPage: 1, totalPages: 3});
    const pagination = new PaginationInterface(source, {});

    assert.equal(pagination.firstBtn.disableCalls > 0, true);
    assert.equal(pagination.prevBtn.disableCalls > 0, true);
    assert.equal(pagination.nextBtn.enableCalls > 0, true);
    assert.equal(pagination.lastBtn.enableCalls > 0, true);
});

test('StyledElements.PaginationInterface constructor disables next buttons on last page', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource({currentPage: 4, totalPages: 4});
    const pagination = new PaginationInterface(source, {});

    assert.equal(pagination.nextBtn.disableCalls > 0, true);
    assert.equal(pagination.lastBtn.disableCalls > 0, true);
});

test('StyledElements.PaginationInterface requestEnd updates labels and auto-hides when one page', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource({currentPage: 2, totalPages: 3, totalCount: 9});
    const pagination = new PaginationInterface(source, {autoHide: true});

    source.currentPage = 1;
    source.totalPages = 1;
    source.totalCount = 2;
    source.listeners.requestEnd(source);

    assert.equal(pagination.wrapperElement.style.display, 'none');
    assert.equal(pagination.currentPageLabel.textContent, '1');
    assert.equal(pagination.totalPagesLabel.textContent, '1');
    assert.equal(pagination.totalCountLabel.textContent, '2');
});

test('StyledElements.PaginationInterface requestEnd shows controls when pages are available', () => {
    resetLegacyRuntime();
    const PaginationInterface = setupPaginationInterface();
    const source = createSource({currentPage: 1, totalPages: 1, totalCount: 1});
    const pagination = new PaginationInterface(source, {autoHide: true});

    source.currentPage = 2;
    source.totalPages = 4;
    source.totalCount = 20;
    source.listeners.requestEnd(source);

    assert.equal(pagination.wrapperElement.style.display, '');
});
