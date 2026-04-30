const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupMACSearch = (options = {}) => {
    const timeoutState = {
        seq: 0,
        callbacks: new Map(),
        cleared: [],
    };
    global.setTimeout = (callback) => {
        timeoutState.seq += 1;
        timeoutState.callbacks.set(timeoutState.seq, callback);
        return timeoutState.seq;
    };
    global.clearTimeout = (id) => {
        timeoutState.cleared.push(id);
        timeoutState.callbacks.delete(id);
    };

    const searchCalls = [];
    const abortCalls = [];
    const searchQueue = [];

    class StyledElement {
        constructor(events = []) {
            this.events = {};
            this.dispatched = [];
            events.forEach((name) => {
                this.events[name] = true;
            });
        }

        dispatchEvent(name, value) {
            this.dispatched.push({name, value});
            return this;
        }
    }

    class Container extends StyledElement {
        constructor(options = {}) {
            super();
            this.options = options;
            this.children = [];
            this.enabled = true;
        }

        appendChild(node) {
            this.children.push(node);
            return this;
        }

        clear() {
            this.children = [];
            return this;
        }

        repaint() {
            this.repaintCalls = (this.repaintCalls || 0) + 1;
            return this;
        }

        disable() {
            this.enabled = false;
            return this;
        }

        enable() {
            this.enabled = true;
            return this;
        }
    }

    class TextField extends StyledElement {
        constructor(options = {}) {
            super();
            this.options = options;
            this.listeners = {};
            this.value = '';
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
            return this;
        }

        fire(name, ...args) {
            return this.listeners[name](this, ...args);
        }

        focus() {
            this.focusCalls = (this.focusCalls || 0) + 1;
            return this;
        }
    }

    class Button {
        constructor(options = {}) {
            this.options = options;
            this.listeners = {};
            Button.instances.push(this);
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
            return this;
        }

        fire(name, event = {}) {
            this.listeners[name](event);
        }
    }
    Button.instances = [];

    class Fragment {
        constructor(value) {
            this.value = value;
        }
    }

    class GUIBuilder {
        constructor() {
            this.DEFAULT_OPENING = '<o>';
            this.DEFAULT_CLOSING = '</o>';
        }

        parse(template, context = {}) {
            if ('searchinput' in context && 'list' in context) {
                const input = context.searchinput();
                const wrapper = document.createElement('div');
                wrapper.appendChild(document.createElement('section'));

                if (options.wrapperAsStyled === true) {
                    class Wrapper extends StyledElement {
                        constructor(element) {
                            super();
                            this.element = element;
                        }

                        get() {
                            return this.element;
                        }
                    }
                    return {elements: [null, new Wrapper(wrapper)], input};
                }

                return {elements: [null, wrapper], input};
            }

            if ('message' in context) {
                return {type: 'message', template, message: context.message};
            }

            return {type: 'parsed', template, context};
        }
    }

    class ResourcePainter {
        constructor(_arg1, _arg2, _arg3, context) {
            this.context = context;
        }

        paint(resource) {
            if (this.context && typeof this.context.mainbutton === 'function') {
                this.lastButton = this.context.mainbutton({}, {}, resource);
            }
            return {painted: resource};
        }
    }

    class Version {
        constructor(value) {
            if (value === 'bad') {
                throw new TypeError('invalid');
            }
            this.value = value;
        }
    }

    const makeAbortable = (promise) => {
        promise.abort = (reason, userInput) => {
            abortCalls.push({reason, userInput});
        };
        return promise;
    };

    global.StyledElements = {
        StyledElement,
        Container,
        TextField,
        Button,
        Fragment,
        GUIBuilder,
    };
    global.Wirecloud = {
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            gettext: (text) => text,
            interpolate: (template, context) => template.replace('%(keywords)s', context.keywords).replace('%(scope)s', context.scope),
            escapeHTML: (text) => text.replace('<', '&lt;').replace('>', '&gt;'),
        },
        ui: {
            ResourcePainter,
        },
        LocalCatalogue: {
            search(query) {
                searchCalls.push(query);
                const next = searchQueue.shift();
                if (next == null) {
                    return makeAbortable(Promise.resolve({total_count: 0, resources: []}));
                }
                return makeAbortable(next(query));
            },
        },
        contextManager: {
            get(name) {
                return name === 'language' ? 'en' : null;
            },
        },
        currentTheme: {
            templates: {
                'wirecloud/macsearch/base': '<base/>',
                'wirecloud/macsearch/component': '<component/>',
            },
        },
        Version,
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/MACSearch.js');

    return {
        MACSearch: Wirecloud.ui.MACSearch,
        timeoutState,
        searchCalls,
        abortCalls,
        searchQueue,
        Button,
    };
};

const flushAsync = async (times = 4) => {
    for (let i = 0; i < times; i += 1) {
        await Promise.resolve();
    }
};

test('Wirecloud.ui.MACSearch validates constructor options', () => {
    resetLegacyRuntime();
    const {MACSearch} = setupMACSearch();

    assert.throws(() => new MACSearch(), TypeError);
    assert.throws(() => new MACSearch({}), TypeError);
    assert.throws(() => new MACSearch({resourceButtonListener: 5}), TypeError);
});

test('Wirecloud.ui.MACSearch constructor initializes fields and unwraps StyledElement wrapper', () => {
    resetLegacyRuntime();
    const {MACSearch} = setupMACSearch({wrapperAsStyled: true});
    const search = new MACSearch({
        scope: 'private',
        resourceButtonListener: () => {},
        resourceButtonIconClass: 'icon',
        resourceButtonTooltip: 'tooltip',
    });

    assert.equal(search.search_scope, 'private');
    assert.equal(search.input.options.placeholder, 'Keywords...');
    assert.equal(search.wrapperElement instanceof Element, true);
    assert.equal(search.list.options.class.includes('wc-macsearch-list'), true);
});

test('Wirecloud.ui.MACSearch paintInfo/paintError/clear/repaint/focus work', () => {
    resetLegacyRuntime();
    const {MACSearch} = setupMACSearch();
    const search = new MACSearch({
        resourceButtonListener: () => {},
    });

    search.paintInfo('message');
    search.paintInfo('<t:corrected_query/>', {corrected_query: 'abc'});
    search.paintError('err');
    assert.equal(search.list.children.length, 3);
    search.clear();
    assert.equal(search.list.children.length, 0);
    search.repaint();
    search.focus();
    assert.equal(search.list.repaintCalls, 1);
    assert.equal(search.input.focusCalls, 1);
});

test('Wirecloud.ui.MACSearch input change debounce and Enter key trigger searches', async () => {
    resetLegacyRuntime();
    const {MACSearch, timeoutState, searchCalls, searchQueue} = setupMACSearch();
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    const search = new MACSearch({
        resourceButtonListener: () => {},
    });

    search.input.value = ' first ';
    search.input.fire('change');
    search.input.value = 'second';
    search.input.fire('change');
    assert.equal(timeoutState.cleared.length, 1);

    const timeoutId = timeoutState.seq;
    timeoutState.callbacks.get(timeoutId)();
    await flushAsync();
    assert.equal(searchCalls.at(-1).search_criteria, 'second');

    search.input.value = 'enter';
    search.input.fire('change');
    search.input.fire('keydown', {}, 'Enter');
    await flushAsync();
    assert.equal(searchCalls.at(-1).search_criteria, 'enter');
    assert.equal(timeoutState.cleared.length >= 2, true);
});

test('Wirecloud.ui.MACSearch current abort path throws when request promise lacks abort', async () => {
    resetLegacyRuntime();
    const {MACSearch, searchQueue} = setupMACSearch();
    let resolveFirst;
    searchQueue.push(() => new Promise((resolve) => {
        resolveFirst = resolve;
    }));
    const search = new MACSearch({
        resourceButtonListener: () => {},
    });
    search.input.value = 'first';
    search.refresh();
    assert.throws(() => search.refresh(), TypeError);
    resolveFirst({total_count: 0, resources: []});
    await flushAsync();
});

test('Wirecloud.ui.MACSearch refresh handles success with corrected query and painter buttons', async () => {
    resetLegacyRuntime();
    const {MACSearch, searchQueue, Button} = setupMACSearch();
    let selected = null;
    searchQueue.push(() => Promise.resolve({
        total_count: 2,
        corrected_query: 'good',
        resources: [
            {version: '1.0.0', others: ['0.1.0'], id: 'a'},
            {version: 'bad', others: []},
        ],
    }));
    const search = new MACSearch({
        scope: 'public',
        resourceButtonIconClass: 'fas fa-check',
        resourceButtonTooltip: (resource) => `select ${resource.id}`,
        resourceButtonListener: (resource) => {
            selected = resource.id;
        },
    });
    search.input.value = 'abc';
    search.refresh();
    await flushAsync();

    assert.equal(search.list.enabled, true);
    assert.equal(search.list.children.length, 2);
    assert.equal(search.list.children[1].painted.id, 'a');
    assert.equal(Button.instances.at(-1).options.title, 'select a');
    Button.instances.at(-1).fire('click');
    assert.equal(selected, 'a');
});

test('Wirecloud.ui.MACSearch no-result messages cover keywords and scope branches', async () => {
    resetLegacyRuntime();
    const {MACSearch, searchQueue} = setupMACSearch();
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    const search = new MACSearch({
        scope: 'widget',
        resourceButtonListener: () => {},
    });

    search.input.value = ' <bad> ';
    search.refresh();
    await flushAsync();
    assert.equal(String(search.list.children.at(-1).message.value).includes('&lt;bad&gt;'), true);

    search.input.value = '';
    search.refresh();
    await flushAsync();
    assert.equal(String(search.list.children.at(-1).message.value).includes('widget'), true);

    search.search_scope = '';
    search.input.value = '';
    search.refresh();
    await flushAsync();
    assert.equal(String(search.list.children.at(-1).message.value).includes('any component'), true);
});

test('Wirecloud.ui.MACSearch handles catalogue errors and supports preloaded painter', async () => {
    resetLegacyRuntime();
    const {MACSearch, searchQueue} = setupMACSearch();
    searchQueue.push(() => Promise.reject(new Error('offline')));
    const customPainter = {paint() { return {custom: true}; }};
    const search = new MACSearch({
        resourceButtonListener: () => {},
        resource_painter: customPainter,
    });

    search.input.value = 'x';
    search.refresh();
    await flushAsync();

    assert.equal(search.list.enabled, true);
    assert.equal(search.list.children.length, 1);
    assert.equal(search.list.children[0].message, 'Connection error: No resource retrieved');
});

test('Wirecloud.ui.MACSearch refresh clears pending timeout before searching', async () => {
    resetLegacyRuntime();
    const {MACSearch, timeoutState, searchQueue, searchCalls} = setupMACSearch();
    searchQueue.push(() => Promise.resolve({total_count: 0, resources: []}));
    const search = new MACSearch({
        resourceButtonListener: () => {},
    });

    search.input.value = 'queued';
    search.input.fire('change');
    const pendingTimeoutId = timeoutState.seq;
    search.input.value = 'refresh-now';
    search.refresh();
    await flushAsync();

    assert.equal(timeoutState.cleared.includes(pendingTimeoutId), true);
    assert.equal(searchCalls.at(-1).search_criteria, 'refresh-now');
});
