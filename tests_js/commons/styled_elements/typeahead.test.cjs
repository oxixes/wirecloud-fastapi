const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupTypeahead = () => {
    class ObjectWithEvents {
        constructor(events = []) {
            this.__listeners = {};
            events.forEach((eventName) => {
                this.__listeners[eventName] = [];
            });
        }

        addEventListener(eventName, listener) {
            if (!(eventName in this.__listeners)) {
                this.__listeners[eventName] = [];
            }
            this.__listeners[eventName].push(listener);
            return this;
        }

        dispatchEvent(eventName, ...args) {
            (this.__listeners[eventName] || []).forEach((listener) => listener(this, ...args));
            return this;
        }
    }

    class TextField {
        constructor(value = '') {
            this.value = value;
            this.inputElement = document.createElement('input');
            this.listeners = {};
            this.focusCalls = 0;
            this.setValueCalls = [];
        }

        addEventListener(eventName, listener) {
            this.listeners[eventName] = listener;
            return this;
        }

        setValue(value) {
            this.value = value;
            this.setValueCalls.push(value);
            return this;
        }

        focus() {
            this.focusCalls += 1;
            return this;
        }
    }

    class PopupMenu {
        constructor() {
            this.listeners = {};
            this.items = [];
            this.visible = false;
            this.clearCalls = 0;
            this.showCalls = [];
            this.hideCalls = 0;
            this.moveCursorUpCalls = 0;
            this.moveCursorDownCalls = 0;
            this.hasEnabledItemValue = false;
            this.activeItem = {
                clickCalls: 0,
                click() {
                    this.clickCalls += 1;
                },
            };
        }

        addEventListener(eventName, listener) {
            this.listeners[eventName] = listener;
            return this;
        }

        clear() {
            this.clearCalls += 1;
            this.items = [];
            return this;
        }

        append(item) {
            this.items.push(item);
            return this;
        }

        show(refElement) {
            this.visible = true;
            this.showCalls.push(refElement);
            return this;
        }

        hide() {
            this.visible = false;
            this.hideCalls += 1;
            return this;
        }

        hasEnabledItem() {
            return this.hasEnabledItemValue;
        }

        moveCursorDown() {
            this.moveCursorDownCalls += 1;
            return this;
        }

        moveCursorUp() {
            this.moveCursorUpCalls += 1;
            return this;
        }

        isVisible() {
            return this.visible;
        }
    }

    class MenuItem {
        constructor(title, handler = null, context = null) {
            this.title = title;
            this.handler = handler;
            this.context = context;
            this.iconClasses = [];
            this.description = null;
            this.disabled = false;
        }

        addIconClass(className) {
            this.iconClasses.push(className);
            return this;
        }

        setDescription(description) {
            this.description = description;
            return this;
        }

        disable() {
            this.disabled = true;
            return this;
        }
    }

    class Fragment {
        constructor(content) {
            this.content = content;
        }
    }

    class GUIBuilder {
        constructor() {
            this.DEFAULT_OPENING = '';
            this.DEFAULT_CLOSING = '';
        }

        parse(template, context) {
            return `parsed:${template}:${context.query ?? ''}`;
        }
    }

    global.StyledElements = {
        ObjectWithEvents,
        TextField,
        PopupMenu,
        MenuItem,
        Fragment,
        GUIBuilder,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            normalizeKey: (event) => event.key,
            highlight: (text, query) => `${text}|${query}`,
            gettext: (text) => text,
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Typeahead.js');
    return {
        Typeahead: StyledElements.Typeahead,
        TextField,
    };
};

test('StyledElements.Typeahead constructor validates required options', () => {
    resetLegacyRuntime();
    const {Typeahead} = setupTypeahead();

    assert.throws(() => new Typeahead({lookup: () => []}), {message: 'build option must be a function'});
    assert.throws(() => new Typeahead({build: () => ({})}), {message: 'lookup option must be a function'});
    assert.throws(() => new Typeahead({build: () => ({}), lookup: () => [], compare: 2}), {message: 'compare option must be a function'});
});

test('StyledElements.Typeahead constructor stores merged options and cleanedQuery defaults', () => {
    resetLegacyRuntime();
    const {Typeahead} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });

    assert.equal(typeahead.autocomplete, true);
    assert.equal(typeahead.minLength, 1);
    assert.equal(typeahead.cleanedQuery, '');
});

test('StyledElements.Typeahead bind validates TextField instances and sets ARIA attributes', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });

    assert.throws(() => typeahead.bind({}), TypeError);

    const textField = new TextField('test');
    const result = typeahead.bind(textField);

    assert.equal(result, typeahead);
    assert.equal(textField.inputElement.getAttribute('autocomplete'), 'off');
    assert.equal(textField.inputElement.getAttribute('autocorrect'), 'off');
    assert.equal(textField.inputElement.getAttribute('spellcheck'), 'false');
    assert.equal(textField.inputElement.getAttribute('aria-autocomplete'), 'list');
    assert.equal(textField.inputElement.getAttribute('aria-expanded'), 'false');
    assert.equal(textField.inputElement.getAttribute('aria-haspopup'), 'listbox');
});

test('StyledElements.Typeahead cleanedQuery normalizes spaces', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    typeahead.bind(new TextField('  one   two  '));

    assert.equal(typeahead.cleanedQuery, 'one two');
});

test('StyledElements.Typeahead change handler ignores updates when disableChangeEvents is true', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    let lookupCalls = 0;
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => {
            lookupCalls += 1;
            return [];
        },
    });
    const textField = new TextField('query');
    typeahead.bind(textField);
    typeahead.disableChangeEvents = true;

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 200));

    assert.equal(lookupCalls, 0);
});

test('StyledElements.Typeahead change handler clears previous timeout before scheduling a new search', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    const textField = new TextField('query');
    typeahead.bind(textField);
    typeahead.timeout = setTimeout(() => {}, 1000);
    let clearCalls = 0;
    const originalClearTimeout = global.clearTimeout;
    global.clearTimeout = (...args) => {
        clearCalls += 1;
        return originalClearTimeout(...args);
    };

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 200));

    global.clearTimeout = originalClearTimeout;
    assert.equal(clearCalls >= 1, true);
});

test('StyledElements.Typeahead search hides popup when query is shorter than minLength', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
        minLength: 5,
    });
    const textField = new TextField('abc');
    typeahead.bind(textField);

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 200));

    assert.equal(typeahead.popupMenu.hideCalls, 1);
});

test('StyledElements.Typeahead search aborts previous request and wraps non-promise responses', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    let aborted = 0;
    const typeahead = new Typeahead({
        build: (_ta, item) => ({title: item}),
        lookup: () => ['a', 'b'],
    });
    const textField = new TextField('abc');
    typeahead.bind(textField);
    typeahead.currentRequest = {
        abort() {
            aborted += 1;
        },
    };

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 250));

    assert.equal(aborted, 1);
    assert.equal(typeahead.popupMenu.items.length, 2);
    assert.equal(typeahead.popupMenu.showCalls.length, 1);
});

test('StyledElements.Typeahead search applies compare filtering and icon/description rendering', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: (_ta, item) => ({
            title: item.name,
            iconClass: item.icon,
            description: item.description,
            value: item.name,
            context: {id: item.name},
        }),
        lookup: () => Promise.resolve([
            {name: 'alpha', icon: 'a', description: 'desc-a'},
            {name: 'beta', icon: 'b', description: 'desc-b'},
        ]),
        compare: (query, entry) => query === entry.name ? 0 : 1,
    });
    const textField = new TextField('alpha');
    typeahead.bind(textField);

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 250));

    assert.equal(typeahead.popupMenu.items.length, 1);
    assert.deepEqual(typeahead.popupMenu.items[0].iconClasses, ['a']);
    assert.equal(typeahead.popupMenu.items[0].description instanceof StyledElements.Fragment, true);
});

test('StyledElements.Typeahead no-results path appends disabled message item and dispatches show', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => Promise.resolve([]),
        notFoundMessage: 'No matches for <t:query/>',
    });
    const textField = new TextField('x');
    typeahead.bind(textField);
    let showEventData;
    typeahead.addEventListener('show', (_source, data) => {
        showEventData = data;
    });

    textField.listeners.change(textField);
    await new Promise((resolve) => setTimeout(resolve, 250));

    assert.equal(typeahead.popupMenu.items.length, 1);
    assert.equal(typeahead.popupMenu.items[0].disabled, true);
    assert.deepEqual(showEventData, []);
});

test('StyledElements.Typeahead popup click selection updates value when autocomplete is true', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
        autocomplete: true,
    });
    const textField = new TextField('before');
    typeahead.bind(textField);
    let selectedMenuitem;
    typeahead.addEventListener('select', (_source, menuitem) => {
        selectedMenuitem = menuitem;
    });
    const menuitem = new StyledElements.MenuItem('title', null, {
        value: 'chosen',
        context: {id: 7},
    });

    typeahead.popupMenu.listeners.click(typeahead.popupMenu, menuitem);

    assert.deepEqual(textField.setValueCalls, ['chosen']);
    assert.equal(textField.focusCalls, 1);
    assert.deepEqual(selectedMenuitem.context, {id: 7});
});

test('StyledElements.Typeahead popup click selection uses empty value when autocomplete is false', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
        autocomplete: false,
    });
    const textField = new TextField('before');
    typeahead.bind(textField);
    const menuitem = new StyledElements.MenuItem('title', null, {
        value: 'chosen',
        context: {id: 9},
    });

    typeahead.popupMenu.listeners.click(typeahead.popupMenu, menuitem);

    assert.deepEqual(textField.setValueCalls, ['']);
});

test('StyledElements.Typeahead keydown handler controls popup navigation and activation', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    const textField = new TextField('q');
    typeahead.bind(textField);
    typeahead.popupMenu.hasEnabledItemValue = true;
    const event = {
        prevented: 0,
        preventDefault() {
            this.prevented += 1;
        },
    };

    textField.listeners.keydown(textField, event, 'Tab');
    textField.listeners.keydown(textField, event, 'Enter');
    textField.listeners.keydown(textField, event, 'ArrowDown');
    textField.listeners.keydown(textField, event, 'ArrowUp');
    textField.listeners.keydown(textField, event, 'A');

    assert.equal(typeahead.popupMenu.activeItem.clickCalls, 2);
    assert.equal(typeahead.popupMenu.moveCursorDownCalls, 1);
    assert.equal(typeahead.popupMenu.moveCursorUpCalls, 1);
    assert.equal(event.prevented, 4);
});

test('StyledElements.Typeahead submit and keydown do nothing when popup has no enabled items', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    const textField = new TextField('q');
    typeahead.bind(textField);
    typeahead.popupMenu.hasEnabledItemValue = false;

    textField.listeners.submit(textField);
    textField.listeners.keydown(textField, {preventDefault() {}}, 'Enter');

    assert.equal(typeahead.popupMenu.activeItem.clickCalls, 0);
});

test('StyledElements.Typeahead submit clicks active popup item when enabled items exist', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    const textField = new TextField('q');
    typeahead.bind(textField);
    typeahead.popupMenu.hasEnabledItemValue = true;

    textField.listeners.submit(textField);

    assert.equal(typeahead.popupMenu.activeItem.clickCalls, 1);
});

test('StyledElements.Typeahead blur clears timeout, aborts request and hides popup asynchronously', async () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    let aborted = 0;
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });
    const textField = new TextField('q');
    typeahead.bind(textField);
    typeahead.timeout = setTimeout(() => {}, 1000);
    typeahead.currentRequest = {
        abort() {
            aborted += 1;
        },
    };

    textField.listeners.blur(textField);
    await new Promise((resolve) => setTimeout(resolve, 150));

    assert.equal(typeahead.timeout, null);
    assert.equal(typeahead.currentRequest, null);
    assert.equal(aborted, 1);
    assert.equal(typeahead.popupMenu.hideCalls, 1);
});

test('StyledElements.Typeahead popup visibilityChange updates aria-expanded only when bound', () => {
    resetLegacyRuntime();
    const {Typeahead, TextField} = setupTypeahead();
    const typeahead = new Typeahead({
        build: () => ({}),
        lookup: () => [],
    });

    typeahead.popupMenu.visible = true;
    typeahead.popupMenu.listeners.visibilityChange();
    assert.equal(typeahead.textField, undefined);

    const textField = new TextField('q');
    typeahead.bind(textField);
    typeahead.popupMenu.visible = false;
    typeahead.popupMenu.listeners.visibilityChange();
    assert.equal(textField.inputElement.getAttribute('aria-expanded'), 'false');
});
