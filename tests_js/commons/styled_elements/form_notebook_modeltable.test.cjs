const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const findNodeByPredicate = (node, predicate) => {
    if (node == null) {
        return null;
    }
    if (predicate(node)) {
        return node;
    }
    for (const child of node.childNodes || []) {
        const match = findNodeByPredicate(child, predicate);
        if (match != null) {
            return match;
        }
    }
    return null;
};

const collectNodesByPredicate = (node, predicate, acc = []) => {
    if (node == null) {
        return acc;
    }
    if (predicate(node)) {
        acc.push(node);
    }
    for (const child of node.childNodes || []) {
        collectNodesByPredicate(child, predicate, acc);
    }
    return acc;
};

const makeEvent = (type, extras = {}) => ({
    type,
    target: extras.target ?? document.createElement('div'),
    stopPropagation() {
        this.stopped = true;
    },
    ...extras,
});

const setupFormRuntime = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();

    const originalCreateElement = document.createElement.bind(document);
    document.createElement = (tagName) => {
        const element = originalCreateElement(tagName);

        if (tagName === 'table' || tagName === 'tbody') {
            element.insertRow = function insertRow() {
                const row = document.createElement('tr');
                row.insertCell = function insertCell() {
                    const cell = document.createElement('td');
                    cell.addClassName = function addClassName(className) {
                        this.classList.add(className);
                    };
                    row.appendChild(cell);
                    return cell;
                };
                element.appendChild(row);
                return row;
            };
        }

        if (tagName === 'tr') {
            element.insertCell = function insertCell() {
                const cell = document.createElement('td');
                cell.addClassName = function addClassName(className) {
                    this.classList.add(className);
                };
                this.appendChild(cell);
                return cell;
            };
        }

        return element;
    };

    class Button {
        constructor(options = {}) {
            this.options = options;
            this.enabled = true;
            this.listeners = {};
            this.destroyed = false;
            Button.instances.push(this);
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
            return this;
        }

        insertInto(parent) {
            this.parent = parent;
            if (parent && parent.appendChild) {
                parent.appendChild(document.createElement('button'));
            }
            return this;
        }

        destroy() {
            this.destroyed = true;
        }
    }
    Button.instances = [];

    class Tooltip {
        constructor(options) {
            this.options = options;
            this.bindCalls = [];
            Tooltip.instances.push(this);
        }

        bind(element) {
            this.bindCalls.push(element);
        }
    }
    Tooltip.instances = [];

    class Notebook {
        constructor(options) {
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.createdTabs = [];
            this.destroyed = false;
        }

        createTab(options) {
            const tab = {
                options,
                listeners: {},
                appended: [],
                addEventListener(name, handler) {
                    this.listeners[name] = handler;
                },
                appendChild(child) {
                    this.appended.push(child);
                },
            };
            this.createdTabs.push(tab);
            return tab;
        }

        repaint() {
            this.repaintCalls = (this.repaintCalls ?? 0) + 1;
            return this;
        }

        destroy() {
            this.destroyed = true;
        }
    }

    class ValidationErrorManager {
        constructor() {
            this.messages = [];
        }

        validate(field) {
            field._setError(Boolean(field.validationMessage));
            if (field.validationMessage) {
                this.messages.push(field.validationMessage);
            }
        }

        toHTML() {
            return this.messages.slice();
        }
    }

    class DefaultInputInterfaceFactory {}

    StyledElements.Button = Button;
    StyledElements.Tooltip = Tooltip;
    StyledElements.Notebook = Notebook;
    StyledElements.ValidationErrorManager = ValidationErrorManager;
    StyledElements.DefaultInputInterfaceFactory = DefaultInputInterfaceFactory;
    StyledElements.Fragment = class Fragment {
        constructor(elements) {
            this.elements = elements;
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Form.js');

    class FakeInputInterface {
        constructor(fieldId, field) {
            this.fieldId = fieldId;
            this.field = field;
            this.value = field.initialValue ?? field.defaultValue ?? `${fieldId}-initial`;
            this._defaultValue = field.defaultValue ?? `${fieldId}-default`;
            this._readOnly = Boolean(field.readOnlyInput);
            this.disabledCalls = [];
            this.setValueCalls = [];
            this.repaintCalls = 0;
            this.focusCalls = 0;
            this.wrapperElement = field.layoutWrapper === 'wrapper'
                ? { wrapperElement: document.createElement('div') }
                : null;
            this.inputElement = field.layoutWrapper === 'inputWrapper'
                ? { wrapperElement: document.createElement('div') }
                : null;
        }

        assignDefaultButton(button) {
            this.defaultButton = button;
        }

        insertInto(parent) {
            this.insertedInto = parent;
            parent.appendChild(document.createElement('span'));
        }

        setDisabled(value) {
            this.disabledCalls.push(value);
            this.disabled = value;
        }

        repaint() {
            this.repaintCalls += 1;
        }

        focus() {
            this.focusCalls += 1;
        }

        getValue() {
            return this.value;
        }

        _setValue(value) {
            this.setValueCalls.push(value);
            this.value = value;
        }

        _setError(error) {
            this.error = error;
        }

        reset() {
            this.resetCalls = (this.resetCalls ?? 0) + 1;
            this.value = this._defaultValue;
        }
    }

    class FakeFactory {
        constructor() {
            this.calls = [];
        }

        createInterface(fieldId, field) {
            const iface = new FakeInputInterface(fieldId, field);
            this.calls.push(iface);
            return iface;
        }
    }

    return {
        Button,
        Tooltip,
        Notebook,
        ValidationErrorManager,
        Form: StyledElements.Form,
        FakeFactory,
    };
};

const setupNotebookRuntime = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();

    class Button {
        constructor(options = {}) {
            this.options = options;
            this.listeners = {};
            this.enabled = true;
            this.disableCalls = 0;
            this.enableCalls = 0;
            this.setDisabledCalls = [];
            Button.instances.push(this);
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
            return this;
        }

        insertInto(parent) {
            this.parent = parent;
            if (parent && parent.appendChild) {
                parent.appendChild(this.wrapperElement);
            }
            return this;
        }

        disable() {
            this.disableCalls += 1;
            this.enabled = false;
        }

        enable() {
            this.enableCalls += 1;
            this.enabled = true;
        }

        setDisabled(value) {
            this.setDisabledCalls.push(value);
            this.enabled = !value;
        }
    }
    Button.instances = [];

    class Select extends Button {}

    class Container {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.children = [];
            this.addClassCalls = [];
            this.clearCalls = 0;
            this.repaintCalls = 0;
            this.wrapperElement.scrollLeft = 0;
            this.wrapperElement.clientWidth = 120;
            this.wrapperElement.scrollWidth = 400;
        }

        addClassName(className) {
            this.addClassCalls.push(className);
            this.wrapperElement.classList.add(className);
            return this;
        }

        appendChild(child) {
            this.children.push(child);
            this.wrapperElement.appendChild(child.wrapperElement ?? child);
            return child;
        }

        prependChild(child, ref) {
            this.children.unshift(child);
            if (ref?.wrapperElement && this.wrapperElement.childNodes.includes(ref.wrapperElement)) {
                this.wrapperElement.insertBefore(child.wrapperElement ?? child, ref.wrapperElement);
            } else {
                this.wrapperElement.insertBefore(child.wrapperElement ?? child, this.wrapperElement.firstChild);
            }
            return child;
        }

        removeChild(child) {
            this.children = this.children.filter((entry) => entry !== child);
            const node = child.wrapperElement ?? child;
            if (node.parentElement === this.wrapperElement) {
                this.wrapperElement.removeChild(node);
            }
            return child;
        }

        clear() {
            this.clearCalls += 1;
            this.children = [];
            this.wrapperElement.innerHTML = '';
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }
    }

    class HorizontalLayout {
        constructor(options = {}) {
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = options.class ?? '';
            this.west = new Container();
            this.center = new Container();
            this.east = new Container();
            this.wrapperElement.appendChild(this.west.wrapperElement);
            this.wrapperElement.appendChild(this.center.wrapperElement);
            this.wrapperElement.appendChild(this.east.wrapperElement);
            this.repaintCalls = 0;
        }

        insertInto(parent) {
            parent.appendChild(this.wrapperElement);
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            this.west.repaint();
            this.center.repaint();
            this.east.repaint();
            return this;
        }
    }

    class Tab extends StyledElements.StyledElement {
        constructor(tabId, notebook, options = {}) {
            super(['show', 'close']);
            this.tabId = tabId;
            this.notebook = notebook;
            this.label = options.label ?? options.name ?? `tab-${tabId}`;
            this.tabElement = document.createElement('button');
            this.tabElement.offsetLeft = options.offsetLeft ?? 0;
            this.tabElement.offsetWidth = options.offsetWidth ?? 60;
            this.tabElement.setAttribute('role', 'tab');
            this.wrapperElement = document.createElement('section');
            this.wrapperElement.classList.add('hidden');
            this.listeners = {};
            this.visibleCalls = [];
            this.repaintCalls = [];
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }

        dispatchEvent(name, ...args) {
            if (this.listeners[name]) {
                this.listeners[name](...args);
            }
        }

        getTabElement() {
            return this.tabElement;
        }

        insertInto(parent) {
            parent.appendChild(this.wrapperElement);
        }

        setVisible(value) {
            this.visibleCalls.push(value);
            if (value) {
                this.wrapperElement.classList.remove('hidden');
            } else {
                this.wrapperElement.classList.add('hidden');
            }
        }

        repaint(value) {
            this.repaintCalls.push(value);
        }
    }

    class CommandQueue {
        constructor(context, initFunc) {
            this.context = context;
            this.initFunc = initFunc;
            this.commands = [];
        }

        addCommand(command) {
            this.commands.push(command);
            const result = this.initFunc(this.context, command);
            return result && typeof result.then === 'function' ? result : Promise.resolve(result);
        }
    }

    StyledElements.Button = Button;
    StyledElements.Select = Select;
    StyledElements.Container = Container;
    StyledElements.HorizontalLayout = HorizontalLayout;
    StyledElements.Tab = Tab;
    StyledElements.CommandQueue = CommandQueue;

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Notebook.js');

    return {
        Button,
        Select,
        Container,
        HorizontalLayout,
        Tab: StyledElements.Tab,
        Notebook: StyledElements.Notebook,
        CommandQueue,
    };
};

const setupModelTableRuntime = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();

    const originalSetInterval = global.setInterval;
    const originalClearInterval = global.clearInterval;

    class Container {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.children = [];
            this.clearCalls = 0;
            this.repaintCalls = 0;
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        appendChild(child) {
            this.children.push(child);
            this.wrapperElement.appendChild(child.wrapperElement ?? child);
            return child;
        }

        prependChild(child, ref) {
            this.children.unshift(child);
            this.wrapperElement.insertBefore(child.wrapperElement ?? child, ref?.wrapperElement ?? ref ?? null);
            return child;
        }

        removeChild(child) {
            this.children = this.children.filter((entry) => entry !== child);
            const node = child.wrapperElement ?? child;
            if (node.parentElement === this.wrapperElement) {
                this.wrapperElement.removeChild(node);
            }
            return child;
        }

        clear() {
            this.clearCalls += 1;
            this.children = [];
            this.wrapperElement.innerHTML = '';
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }

        destroy() {
            this.destroyed = true;
        }
    }

    class VerticalLayout {
        constructor(options = {}) {
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = options.class ?? '';
            this.center = new Container();
            this.south = new Container();
            this.wrapperElement.appendChild(this.center.wrapperElement);
            this.wrapperElement.appendChild(this.south.wrapperElement);
        }

        destroy() {
            this.destroyed = true;
        }
    }

    class PaginationInterface {
        constructor(source) {
            this.source = source;
            this.wrapperElement = document.createElement('div');
        }

        destroy() {
            this.destroyed = true;
        }
    }

    class Tooltip {
        constructor(options) {
            this.options = options;
            this.bindCalls = [];
            Tooltip.instances.push(this);
        }

        bind(element) {
            this.bindCalls.push(element);
        }
    }
    Tooltip.instances = [];

    class StaticPaginatedSource {
        constructor(options = {}) {
            this.options = options;
            this.listeners = {};
            this.currentElements = options.initialElements ?? [];
            this.currentPage = options.currentPage ?? 1;
            this.totalPages = options.totalPages ?? 1;
            this.totalCount = this.currentElements.length;
            this.changeOptionsCalls = [];
            this.destroyed = false;
            StaticPaginatedSource.instances.push(this);
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }

        changeOptions(options) {
            this.changeOptionsCalls.push(options);
            this.lastChangeOptions = options;
        }

        getCurrentPage() {
            return this.currentElements;
        }

        destroy() {
            this.destroyed = true;
        }
    }
    StaticPaginatedSource.instances = [];

    global.setInterval = (callback) => {
        const id = { callback };
        setupModelTableRuntime.intervals.push(id);
        return id;
    };
    global.clearInterval = (id) => {
        setupModelTableRuntime.clearedIntervals.push(id);
    };
    setupModelTableRuntime.intervals = [];
    setupModelTableRuntime.clearedIntervals = [];
    document.body.contains = () => false;
    document.defaultView.getSelection = global.getSelection;

    const originalMoment = global.moment;
    global.moment = (date) => {
        const state = {
            date,
            zone: null,
        };
        return {
            tz(zone) {
                state.zone = zone;
                return this;
            },
            format(format) {
                if (format === ' z') {
                    return ' UTC';
                }
                if (format === 'LLLL z') {
                    return 'LONG UTC';
                }
                return `${format}:${state.zone ?? 'local'}`;
            },
            fromNow() {
                return 'relative-time';
            },
            calendar() {
                return 'calendar-time';
            },
        };
    };

    StyledElements.Fragment = class Fragment {
        constructor(elements) {
            this.elements = elements;
        }
    };

    StyledElements.VerticalLayout = VerticalLayout;
    StyledElements.PaginationInterface = PaginationInterface;
    StyledElements.Tooltip = Tooltip;
    StyledElements.StaticPaginatedSource = StaticPaginatedSource;

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/ModelTable.js');

    return {
        Container,
        VerticalLayout,
        PaginationInterface,
        Tooltip,
        StaticPaginatedSource,
        ModelTable: StyledElements.ModelTable,
        restoreGlobals() {
            global.setInterval = originalSetInterval;
            global.clearInterval = originalClearInterval;
            global.moment = originalMoment;
        },
        intervals: setupModelTableRuntime.intervals,
        clearedIntervals: setupModelTableRuntime.clearedIntervals,
    };
};

test('StyledElements.Form covers constructor branches, layouts, validation and button actions', () => {
    const { Form, Button, FakeFactory, Tooltip } = setupFormRuntime();
    const factory = new FakeFactory();
    const submitEvents = [];
    const cancelEvents = [];

    const form = new Form({
        title: { label: 'Title', description: 'A title', required: true, defaultValue: 'Initial title', layoutWrapper: 'wrapper' },
        category: { type: 'hidden', label: 'Category', defaultValue: 'general' },
        separator: { type: 'separator' },
        docs: { type: 'label', label: 'Docs', url: 'https://example.test' },
        columns: {
            type: 'columnLayout',
            columns: [
                [{ name: 'colA', label: 'Col A', defaultValue: 'A', layoutWrapper: 'wrapper' }],
                [{ name: 'colB', label: 'Col B', defaultValue: 'B', readOnlyInput: true, layoutWrapper: 'inputWrapper' }],
            ],
        },
        lines: {
            type: 'lineLayout',
            fields: [
                { name: 'lineA', label: 'Line A', defaultValue: 'LA', layoutWrapper: 'wrapper' },
                { name: 'lineB', label: 'Line B', defaultValue: 'LB', layoutWrapper: 'inputWrapper' },
            ],
        },
    }, {
        factory,
        setdefaultsButton: true,
        resetButton: true,
        acceptButton: true,
        cancelButton: true,
        useHtmlForm: true,
    });

    form.addEventListener('submit', (data) => submitEvents.push(data));
    form.addEventListener('cancel', () => cancelEvents.push('cancel'));

    assert.equal(form.wrapperElement.tagName, 'FORM');
    assert.equal(form.focusField, 'title');
    assert.equal(form.msgElement.style.display, 'none');
    assert.ok(form.setdefaultsButton instanceof Button);
    assert.ok(form.resetButton instanceof Button);
    assert.ok(form.acceptButton instanceof Button);
    assert.ok(form.cancelButton instanceof Button);
    assert.equal(form.fieldInterfaces.title.defaultButton, form.acceptButton);
    assert.equal(form.fieldInterfaces.colB.disabled, true);
    assert.equal(form.fieldInterfaces.lineA.insertedInto.childNodes.length > 0, true);
    assert.equal(form.fieldInterfaces.lineA.insertedInto.childNodes[0].tagName, 'SPAN');
    assert.equal(Tooltip.instances.length >= 1, true);
    assert.equal(Tooltip.instances[0].options.content, 'A title');
    assert.equal(form.fieldInterfaces.lineA.wrapperElement.wrapperElement.style.display, 'inline-block');
    assert.equal(form.fieldInterfaces.lineA.wrapperElement.wrapperElement.style.verticalAlign, 'middle');
    assert.equal(form.fieldInterfaces.lineB.inputElement.wrapperElement.style.display, 'inline-block');
    assert.equal(form.fieldInterfaces.lineB.inputElement.wrapperElement.style.verticalAlign, 'middle');

    form.fieldInterfaces.title.value = 'New title';
    form.fieldInterfaces.category.value = 'widgets';
    form.fieldInterfaces.colA.value = 'AA';
    form.fieldInterfaces.colB.value = 'BB';
    form.fieldInterfaces.lineA.value = 'LLA';
    form.fieldInterfaces.lineB.value = 'LLB';
    assert.deepEqual(form.getData(), {
        title: 'New title',
        category: 'widgets',
        colA: 'AA',
        colB: 'BB',
        lineA: 'LLA',
        lineB: 'LLB',
    });

    form.setData({
        title: 'Updated',
        category: 'core',
        colA: 'colA-updated',
        colB: 'colB-updated',
        lineA: 'lineA-updated',
        lineB: 'lineB-updated',
    });
    assert.equal(form.fieldInterfaces.title.value, 'Updated');
    assert.equal(form.fieldInterfaces.category.value, 'core');
    assert.equal(form.fieldInterfaces.colA.value, 'colA-updated');
    assert.equal(form.fieldInterfaces.colB.value, 'colB-updated');
    assert.equal(form.fieldInterfaces.lineA.value, 'lineA-updated');
    assert.equal(form.fieldInterfaces.lineB.value, 'lineB-updated');

    form.update({ title: 'Partial', lineB: 'Z' });
    assert.equal(form.fieldInterfaces.title.value, 'Partial');
    assert.equal(form.fieldInterfaces.lineB.value, 'Z');
    assert.throws(() => form.setData(1), TypeError);
    assert.throws(() => form.update(null), TypeError);

    form.displayMessage('Hello world');
    assert.equal(form.msgElement.textContent, 'Hello world');
    form.fieldInterfaces.title.validationMessage = 'Title is mandatory';
    assert.equal(form.is_valid(), false);
    assert.equal(form.msgElement.textContent, 'Title is mandatory');
    form.fieldInterfaces.title.validationMessage = '';
    form.extraValidation = () => null;
    assert.equal(form.is_valid(), true);
    assert.equal(form.msgElement.style.display, 'none');

    form.defaults();
    assert.equal(form.fieldInterfaces.title.value, 'Initial title');
    assert.equal(form.fieldInterfaces.category.value, 'general');
    form.reset();
    assert.equal(form.fieldInterfaces.title.value, 'Initial title');

    form['_onenabled'](false);
    assert.equal(form.fieldInterfaces.title.disabled, true);
    assert.equal(form.fieldInterfaces.colB.disabled, true);
    assert.equal(form.acceptButton.enabled, false);
    form['_onenabled'](true);
    assert.equal(form.acceptButton.enabled, true);

    form.focus();
    assert.equal(form.fieldInterfaces.title.focusCalls, 1);

    const host = document.createElement('div');
    form.insertInto(host);
    assert.equal(host.childNodes.length > 0, true);
    assert.equal(form.fieldInterfaces.title.repaintCalls > 0, true);

    form.acceptButton.listeners.click();
    form.cancelButton.listeners.click();
    assert.equal(submitEvents.length, 1);
    assert.equal(cancelEvents.length, 1);
});

test('StyledElements.Form supports grouped fields, explicit buttons and destroy lifecycle', () => {
    const { Form, Button } = setupFormRuntime();
    const factory = new (class {
        constructor() {
            this.calls = [];
        }

        createInterface(fieldId, field) {
            const iface = {
                fieldId,
                field,
                value: `${fieldId}-value`,
                _defaultValue: `${fieldId}-default`,
                _readOnly: false,
                setDisabledCalls: [],
                assignDefaultButton(button) {
                    this.defaultButton = button;
                },
                insertInto(parent) {
                    this.insertedInto = parent;
                },
                setDisabled(value) {
                    this.setDisabledCalls.push(value);
                    this.disabled = value;
                },
                repaint() {},
                focus() {},
                getValue() {
                    return this.value;
                },
                _setValue(value) {
                    this.value = value;
                },
                reset() {
                    this.value = this._defaultValue;
                },
            };
            this.calls.push(iface);
            return iface;
        }
    })();
    const explicitButtons = {
        setdefaultsButton: new Button({ text: 'defaults' }),
        resetButton: new Button({ text: 'reset' }),
        acceptButton: new Button({ text: 'accept' }),
        cancelButton: new Button({ text: 'cancel' }),
    };

    const form = new Form([
        { name: 'plain', label: 'Plain label', readOnlyInput: false },
    ], {
        factory,
        readOnly: true,
        useHtmlForm: false,
        buttonArea: document.createElement('div'),
        ...explicitButtons,
    });

    const syntheticChild = { destroy() { this.destroyed = true; } };
    form.childComponents.push(syntheticChild);

    assert.equal(form.wrapperElement.tagName, 'DIV');
    assert.equal(form.setdefaultsButton, explicitButtons.setdefaultsButton);
    assert.equal(form.resetButton, explicitButtons.resetButton);
    assert.equal(form.acceptButton, explicitButtons.acceptButton);
    assert.equal(form.cancelButton, explicitButtons.cancelButton);
    assert.equal(form.fieldInterfaces.plain.disabled, true);

    form['_onenabled'](false);
    assert.equal(form.resetButton.enabled, false);
    assert.equal(form.setdefaultsButton.enabled, false);
    assert.equal(form.acceptButton.enabled, false);
    assert.equal(form.cancelButton.enabled, false);

    form.destroy();
    assert.equal(form.childComponents, null);
    assert.equal(form.setdefaultsButton, null);
    assert.equal(form.resetButton, null);
    assert.equal(form.acceptButton, null);
    assert.equal(form.cancelButton, null);
    assert.equal(syntheticChild.destroyed, true);
});

test('StyledElements.Form rejects invalid fields and keeps cancel path working', () => {
    const { Form } = setupFormRuntime();

    assert.throws(() => new Form(null), TypeError);

    const factory = new (class {
        createInterface() {
            return {
                value: 'x',
                _defaultValue: 'default-x',
                _readOnly: false,
                assignDefaultButton() {},
                insertInto() {},
                setDisabled() {},
                repaint() {},
                focus() {},
                getValue() { return this.value; },
                _setValue(value) { this.value = value; },
                reset() { this.value = this._defaultValue; },
                _setError() {},
            };
        }
    })();
    const form = new Form([{ name: 'only', label: 'Only field' }], {
        factory,
        acceptButton: false,
        cancelButton: true,
        useHtmlForm: false,
    });
    let cancelled = 0;
    form.addEventListener('cancel', () => { cancelled += 1; });
    form.cancelButton.listeners.click();
    assert.equal(cancelled, 1);
});

test('StyledElements.Form covers grouped layouts, label fallback and submit preventDefault path', () => {
    const { Form } = setupFormRuntime();
    const factory = new (class {
        createInterface(fieldId, field) {
            return {
                fieldId,
                field,
                _defaultValue: `${fieldId}-default`,
                _readOnly: false,
                assignDefaultButton() {},
                insertInto(parent) { this.insertedInto = parent; },
                setDisabled() {},
                repaint() { this.repaintCalls = (this.repaintCalls ?? 0) + 1; },
                focus() {},
                getValue() { return this.value; },
                _setValue(value) { this.value = value; },
                reset() {},
                _setError() {},
            };
        }
    })();

    const form = new Form([
        { type: 'group', shortTitle: 'Main', fields: [{ name: 'inside', label: 'Inside' }] },
    ], {
        factory,
        acceptButton: false,
        cancelButton: false,
    });

    const labelForm = new Form([
        { name: 'plainLabel', type: 'label', label: 'Plain label' },
    ], {
        factory,
        acceptButton: false,
        cancelButton: false,
    });

    const submitEvent = makeEvent('submit', {
        prevented: false,
        preventDefault() {
            this.prevented = true;
        },
    });
    form.wrapperElement.dispatchEvent(submitEvent);
    assert.equal(submitEvent.prevented, true);

    const label = findNodeByPredicate(labelForm.wrapperElement, (node) => node.tagName === 'LABEL' && node.textContent === 'Plain label');
    assert.equal(label != null, true);

    const repaintingChild = { repaintCalls: [], repaint(value) { this.repaintCalls.push(value); } };
    form.childComponents.push(repaintingChild);
    form.repaint(true);
    assert.deepEqual(repaintingChild.repaintCalls, [true]);

    form.focusField = 'unknown';
    form.focus();

    assert.throws(() => {
        new Form([{ type: 'group', shortTitle: 'Nested', nested: true, name: 'nestedFieldset', fields: [{ name: 'child', label: 'Child' }] }], {
            factory,
            acceptButton: false,
            cancelButton: false,
        });
    }, ReferenceError);

    const emptyForm = new Form([], { factory, acceptButton: false, cancelButton: false });
    assert.equal(emptyForm.focusField, null);
});

test('StyledElements.Notebook covers tab creation, scrolling buttons and lifecycle branches', async () => {
    const { Notebook, Tab, Button, Select } = setupNotebookRuntime();
    const originalDate = global.Date;
    let tick = 1_000_000;
    global.Date = class FakeDate {
        constructor() {
            this.time = tick;
            tick += 1_000;
        }

        getTime() {
            return this.time;
        }
    };

    try {
        const notebook = new Notebook({
            class: 'custom-class',
            full: false,
            focusOnSetVisible: true,
            id: 'note-1',
        });

        assert.equal(notebook.wrapperElement.getAttribute('id'), 'note-1');
        assert.equal(notebook.wrapperElement.classList.contains('full'), false);
        assert.equal(notebook.tabArea.wrapperElement.getAttribute('role'), 'tablist');

        let newTabEvents = 0;
        notebook.events.newTab.addEventListener(() => {
            newTabEvents += 1;
        });
        notebook.new_tab_button_tabs.listeners.click();
        assert.equal(newTabEvents, 1);
        assert.equal(notebook.new_tab_button_left != null, true);

        const tab1 = notebook.createTab({ label: 'One', initiallyVisible: true, offsetLeft: 0, offsetWidth: 40 });
        const tab2 = notebook.createTab({ label: 'Two', offsetLeft: 200, offsetWidth: 40 });
        const tab3 = notebook.createTab({ label: 'Three', offsetLeft: 320, offsetWidth: 40 });

        assert.equal(notebook.getTab(tab1.tabId), tab1);
        assert.equal(notebook.getTabByLabel('Two'), tab2);
        assert.equal(notebook.getTabByIndex(2), tab3);
        assert.equal(notebook.getTabIndex(tab2), 1);
        assert.equal(notebook.getTabIndex('missing'), null);
        assert.throws(() => notebook.createTab({ tab_constructor: class BadTab {} }), TypeError);

        notebook.tabArea.wrapperElement.clientWidth = 120;
        notebook.tabArea.wrapperElement.scrollWidth = 400;
        notebook.tabArea.wrapperElement.scrollLeft = 0;
        notebook.repaint();
        assert.equal(notebook.moveLeftButton.enabled, false);
        assert.equal(notebook.moveRightButton.enabled, true);

        notebook.tabArea.wrapperElement.scrollLeft = 180;
        notebook.repaint();
        assert.equal(notebook.new_tab_button_tabs.enabled, false);
        assert.equal(notebook.new_tab_button_left.enabled, true);

        notebook.goToTab(tab2.tabId, { context: 'switch' });
        assert.equal(notebook.visibleTab, tab2);
        assert.equal(tab1.visibleCalls.includes(false), true);
        assert.equal(tab2.visibleCalls.includes(true), true);

            notebook.goToTab(tab2);
            assert.equal(notebook.transitionsQueue.commands.length >= 1, true);

        await notebook.shiftRightTabs();
        await notebook.shiftLeftTabs();
        await notebook.focus(tab3);
        assert.equal(notebook.transitionsQueue.commands.some((command) => command.type === 'shiftRight'), true);
        assert.equal(notebook.transitionsQueue.commands.some((command) => command.type === 'shiftLeft'), true);
        assert.equal(notebook.transitionsQueue.commands.some((command) => command.type === 'focus'), true);

        notebook.wrapperElement.requestFullscreen = () => {
            notebook.requestFullscreenCalled = true;
        };
        notebook.requestFullscreen();
        assert.equal(notebook.requestFullscreenCalled, true);

        document.exitFullscreen = () => {
            notebook.exitFullscreenCalled = true;
            document.fullscreenElement = null;
        };
        document.fullscreenElement = notebook.wrapperElement;
        notebook.exitFullscreen();
        assert.equal(notebook.exitFullscreenCalled, true);

        notebook.addToEastSection(document.createElement('span'), 'right');
        notebook.addToEastSection(document.createElement('span'), 'left');
        notebook.addButton(new Button(), 'right');
        notebook.addButton(new Select(), 'left');
        assert.throws(() => notebook.addButton({}, 'right'), TypeError);

        const removed = notebook.removeTab(tab2);
        assert.equal(removed, notebook);
        assert.equal(tab2.visibleCalls.includes(false), true);
        assert.equal(notebook.tabs.length, 2);
        assert.equal(notebook.removeTab(999), notebook);
        assert.throws(() => notebook.removeTab(new Tab('alien', { tabsById: [] }, {})), TypeError);

        notebook._onenabled(false);
        assert.equal(notebook.disabledLayer != null, true);
        notebook._onenabled(true);
        assert.equal(notebook.disabledLayer, null);

        notebook.clear();
        assert.equal(notebook.tabs.length, 0);
        assert.equal(notebook.tabsById.length, 0);

        notebook.destroy();
        assert.equal(notebook.tabs, null);
        assert.equal(notebook.visibleTab, null);
    } finally {
        global.Date = originalDate;
    }
});

test('StyledElements.Notebook supports tab creation errors and no-tab button state', () => {
    const { Notebook } = setupNotebookRuntime();
    const notebook = new Notebook({ focusOnSetVisible: false });

    notebook.repaint();

    assert.equal(notebook.moveLeftButton.enabled, false);
    assert.equal(notebook.moveRightButton.enabled, false);
    assert.equal(notebook.new_tab_button_tabs, undefined);
    assert.equal(notebook.new_tab_button_left, undefined);

    const tab = notebook.createTab({ label: 'Solo' });
    assert.equal(tab.tabElement.getAttribute('role'), 'tab');
    assert.equal(notebook.tabs.length, 1);
    assert.equal(notebook.getTabIndex(tab.tabId), 0);
    assert.throws(() => notebook.focus('missing'), TypeError);
    assert.throws(() => notebook.goToTab('missing'), TypeError);
    assert.throws(() => notebook.createTab({ tab_constructor: function Bad() {} }), TypeError);

    notebook.removeTab(tab.tabId);
    assert.equal(notebook.visibleTab, null);
    notebook.clear();
    assert.equal(notebook.tabs.length, 0);
});

test('StyledElements.Notebook covers early returns, foreign-tab errors and fullscreen vendor fallbacks', async () => {
    const { Notebook, Tab } = setupNotebookRuntime();
    const originalSetTimeout = global.setTimeout;
    const timeoutQueue = [];
    global.setTimeout = (callback) => {
        timeoutQueue.push(callback);
        return timeoutQueue.length;
    };

    try {
        const notebook = new Notebook({ focusOnSetVisible: true });
        await notebook.shiftLeftTabs();
        await notebook.shiftRightTabs();

        assert.equal(notebook.getTabByLabel('missing'), null);

        const tab = notebook.createTab({ label: 'Only', offsetLeft: 300, offsetWidth: 40 });
        const outsider = new Tab(999, { tabsById: [] }, { label: 'Out' });
        assert.equal(notebook.getTabIndex(outsider), null);
        assert.throws(() => notebook.goToTab(outsider), /owned/);
        assert.throws(() => notebook.focus(outsider), /owned/);

        notebook.goToTab(tab.tabId);
        notebook.repaint(true);
        assert.equal(tab.repaintCalls.includes(true), true);

        const removedByInit = notebook.transitionsQueue.addCommand({ type: 'focus', tab: { tabId: 12345 } });
        assert.equal(await removedByInit, false);

        notebook.tabArea.wrapperElement.clientWidth = 80;
        notebook.tabArea.wrapperElement.scrollWidth = 400;
        notebook.tabArea.wrapperElement.scrollLeft = 0;
        const removeBeforeStep = notebook.transitionsQueue.addCommand({ type: 'focus', tab });
        delete notebook.tabsById[tab.tabId];
        while (timeoutQueue.length > 0) {
            timeoutQueue.shift()();
        }
        await removeBeforeStep;

        notebook.wrapperElement.msRequestFullscreen = () => { notebook.msReq = true; };
        notebook.requestFullscreen();
        assert.equal(notebook.msReq, true);

        delete notebook.wrapperElement.msRequestFullscreen;
        notebook.wrapperElement.mozRequestFullScreen = () => { notebook.mozReq = true; };
        notebook.requestFullscreen();
        assert.equal(notebook.mozReq, true);

        delete notebook.wrapperElement.mozRequestFullScreen;
        notebook.wrapperElement.webkitRequestFullscreen = () => { notebook.webkitReq = true; };
        notebook.requestFullscreen();
        assert.equal(notebook.webkitReq, true);

        document.fullscreenElement = null;
        const earlyExit = notebook.exitFullscreen();
        assert.equal(earlyExit, notebook);

        document.fullscreenElement = notebook.wrapperElement;
        document.msExitFullscreen = () => { notebook.msExit = true; document.fullscreenElement = null; };
        notebook.exitFullscreen();
        assert.equal(notebook.msExit, true);

        document.fullscreenElement = notebook.wrapperElement;
        delete document.msExitFullscreen;
        document.mozCancelFullScreen = () => { notebook.mozExit = true; document.fullscreenElement = null; };
        notebook.exitFullscreen();
        assert.equal(notebook.mozExit, true);

        document.fullscreenElement = notebook.wrapperElement;
        delete document.mozCancelFullScreen;
        document.webkitExitFullscreen = () => { notebook.webkitExit = true; document.fullscreenElement = null; };
        notebook.exitFullscreen();
        assert.equal(notebook.webkitExit, true);

        const notebook2 = new Notebook({ focusOnSetVisible: false });
        const tabA = notebook2.createTab({ label: 'A' });
        const tabB = notebook2.createTab({ label: 'B' });
        notebook2.goToTab(tabB.tabId);
        notebook2.removeTab(tabB.tabId);
        assert.equal(notebook2.visibleTab, tabA);
    } finally {
        global.setTimeout = originalSetTimeout;
        delete document.msExitFullscreen;
        delete document.mozCancelFullScreen;
        delete document.webkitExitFullscreen;
    }
});

const createModelTableItems = () => ([
    {
        id: 1,
        name: 'Alpha',
        score: 7,
        created: '2026-04-01T10:00:00Z',
        profile: { title: 'Dr.' },
        state: 'warning',
        meta: { id: 101 },
    },
    {
        id: 2,
        name: 'Beta',
        score: 10,
        created: '2026-04-02T10:00:00Z',
        profile: { title: 'Ms.' },
        state: 'ok',
        meta: { id: 102 },
    },
    {
        id: 3,
        name: 'Gamma',
        score: null,
        created: 'invalid-date',
        profile: { title: 'Mx.' },
        state: null,
        meta: { id: 103 },
    },
]);

test('StyledElements.ModelTable renders rows, formats values and supports selection interactions', () => {
    const { ModelTable, Tooltip, StaticPaginatedSource, restoreGlobals, intervals, clearedIntervals } = setupModelTableRuntime();
    const source = new StaticPaginatedSource({
        pageSize: 5,
        idAttr: 'id',
        initialElements: createModelTableItems(),
    });
    source.currentElements = createModelTableItems();
    source.currentPage = 1;
    source.totalPages = 2;
    source.totalCount = source.currentElements.length;
    source.getCurrentPage = function () {
        return this.currentElements;
    };
    source.changeOptions = function (options) {
        this.changeOptionsCalls.push(options);
        this.lastChangeOptions = options;
    };
    source.changeOptionsCalls = [];

    const table = new ModelTable([
        { field: 'name', label: 'Name', sortable: true, class: 'name-col', width: '120px' },
        { field: 'score', type: 'number', unit: 'pts', sortable: true, sort_id: 'score_id' },
        { field: 'created', type: 'date', format: 'relative', tooltip: 'none', dateparser: (value) => new Date(value), sortable: true, timezone: 'UTC' },
        { field: ['profile', 'title'], label: 'Profile title', type: 'date', format: 'calendar', tooltip: 'LLL z', sortable: true },
        { field: 'custom', label: 'Custom', sortable: false, contentBuilder: (item) => {
            if (item.id === 1) {
                const element = document.createElement('strong');
                element.textContent = 'bold';
                return element;
            }
            if (item.id === 2) {
                return new (class extends StyledElements.StyledElement {
                    constructor() {
                        super();
                        this.wrapperElement = document.createElement('em');
                        this.wrapperElement.textContent = 'styled';
                    }
                })();
            }
            return null;
        } },
    ], {
        source,
        id: 'id',
        selectionType: 'multiple',
        stateFunc: (item) => item.state,
    });

    const root = table.wrapperElement;
    const tableBody = findNodeByPredicate(root, (node) => node.classList?.contains('se-model-table-body'));
    const headerCells = collectNodesByPredicate(root, (node) => node.getAttribute?.('role') === 'columnheader');
    assert.equal(headerCells.length, 5);
    assert.equal(tableBody.style.gridTemplateColumns.includes('120px'), true);
    assert.equal(source.changeOptionsCalls.length >= 1, true);
    assert.deepEqual(source.changeOptionsCalls[0], { order: ['name'] });

    table.reload();
    const rows = collectNodesByPredicate(root, (node) => node.getAttribute?.('role') === 'row' && node.classList?.contains('se-model-table-row'));
    assert.equal(rows.length, 3);
    assert.equal(rows[0].classList.contains('se-model-table-row-warning'), true);
    assert.equal(rows[1].classList.contains('odd'), true);
    assert.equal(rows[0].childNodes[0].textContent, 'Alpha');
    assert.equal(rows[0].childNodes[1].textContent, '7 pts');
    assert.equal(rows[0].childNodes[2].textContent, 'relative-time');
    assert.equal(rows[0].childNodes[3].textContent.length > 0, true);
    assert.equal(rows[0].childNodes[4].childNodes[0].tagName, 'STRONG');
    assert.equal(rows[1].childNodes[4].childNodes[0].tagName, 'EM');
    assert.equal(rows[2].childNodes[4].textContent, '');
    assert.equal(Tooltip.instances.length >= 3, true);

    assert.equal(intervals.length >= 2, true);
    intervals[0].callback();
    intervals[1].callback();
    assert.equal(clearedIntervals.length >= 2, true);

    const firstCell = rows[0].childNodes[0];
    const secondCell = rows[1].childNodes[0];
    const thirdCell = rows[2].childNodes[0];
    firstCell.dispatchEvent(makeEvent('click', { target: firstCell }));
    assert.deepEqual(table.selection, [1]);
    assert.equal(rows[0].classList.contains('highlight'), true);

    secondCell.dispatchEvent(makeEvent('click', { target: secondCell, ctrlKey: true }));
    assert.deepEqual(table.selection.sort(), [1, 2]);

    thirdCell.dispatchEvent(makeEvent('click', { target: thirdCell, shiftKey: true }));
    assert.equal(table.selection.includes(3), true);

    root.dispatchEvent(makeEvent('click', { target: root }));
    assert.deepEqual(table.selection, []);

    headerCells[0].dispatchEvent(makeEvent('click', { target: headerCells[0] }));
    assert.equal(source.lastChangeOptions.order[0], '-name');

    headerCells[1].dispatchEvent(makeEvent('click', { target: headerCells[1] }));
    assert.equal(source.lastChangeOptions.order[0], 'score_id');

    headerCells[2].dispatchEvent(makeEvent('click', { target: headerCells[2] }));
    assert.equal(source.lastChangeOptions.order[0], 'created');

    headerCells[3].dispatchEvent(makeEvent('click', { target: headerCells[3] }));
    assert.deepEqual(source.lastChangeOptions.order, [['profile', 'title']]);

    table.select([2]);
    assert.deepEqual(table.selection, [2]);
    assert.equal(rows[1].classList.contains('highlight'), true);

    table.selection = [];
    assert.deepEqual(table.selection, []);
    table.selection = [1, 2];
    assert.deepEqual(table.selection, [1, 2]);

    table.destroy();
    assert.equal(source.destroyed, true);
    restoreGlobals();
});

test('StyledElements.ModelTable handles source-free construction, alternate ids and error states', () => {
    const { ModelTable, StaticPaginatedSource, restoreGlobals } = setupModelTableRuntime();
    const table = new ModelTable([
        { field: 'name', sortable: false },
        { field: 'score', sortable: false },
    ], {
        pageSize: 10,
        id: ['meta', 'id'],
        selectionType: 'single',
        emptyMessage: 'Nothing here',
        initialSortColumn: -1,
    });

    assert.equal(StaticPaginatedSource.instances.length, 1);
    assert.deepEqual(StaticPaginatedSource.instances[0].options.sort_info, {
        name: table.columns[0],
        score: table.columns[1],
    });
    assert.equal(table.source.options.pageSize, 10);
    assert.equal(table.selection.length, 0);
    assert.throws(() => {
        table.selection = ['a', 'b'];
    }, /single/);

    table.source.currentPage = 1;
    table.source.currentElements = [{ meta: { id: 7 }, name: 'ArrayId', score: 1 }];
    table.reload();
    const rowsWithArrayId = collectNodesByPredicate(table.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
    assert.equal(rowsWithArrayId.length, 1);

    table.source.currentElements = [];
    table.reload();
    assert.equal(table.wrapperElement.textContent.includes('Nothing here'), true);

    table.source.listeners.requestEnd(table.source, 'boom');
    const errorMessage = findNodeByPredicate(table.wrapperElement, (node) => node.classList?.contains('se-model-table-msg') && node.classList?.contains('alert-danger'));
    assert.equal(errorMessage.textContent, 'boom');

    table.source.listeners.requestEnd(table.source);
    assert.equal(table.source.changeOptionsCalls.length >= 1, true);

    table.destroy();
    restoreGlobals();
});

test('StyledElements.ModelTable supports function ids and disabled selection mode', () => {
    const { ModelTable, restoreGlobals } = setupModelTableRuntime();
    const source = {
        options: { pageSize: 5 },
        listeners: {},
        currentElements: createModelTableItems(),
        currentPage: 1,
        totalPages: 1,
        changeOptionsCalls: [],
        addEventListener(name, handler) {
            this.listeners[name] = handler;
        },
        changeOptions(options) {
            this.changeOptionsCalls.push(options);
        },
        getCurrentPage() {
            return this.currentElements;
        },
        destroy() {
            this.destroyed = true;
        },
    };
    const table = new ModelTable([
        { field: 'id', sortable: true },
    ], {
        source,
        id: (item) => item.meta.id,
        selectionType: 'none',
        initialSortColumn: 'id',
    });

    assert.equal(typeof table.source.listeners.requestEnd, 'function');
    assert.deepEqual(table.selection, []);
    assert.throws(() => {
        table.selection = [1];
    }, /Selection is disabled/);
    table.destroy();
    restoreGlobals();
});

test('StyledElements.ModelTable covers remaining selection and formatting branches', () => {
    const { ModelTable, StaticPaginatedSource, Tooltip, restoreGlobals, intervals } = setupModelTableRuntime();

    const source = new StaticPaginatedSource({
        pageSize: 5,
        idAttr: 'id',
        initialElements: [
            { id: 1, when: '', numeric: 3, flag: true },
            { id: 2, when: '2026-04-01T10:00:00Z', numeric: 4, flag: false },
        ],
    });
    source.currentElements = source.options.initialElements.slice();
    source.getCurrentPage = function () { return this.currentElements; };
    source.changeOptionsCalls = [];
    source.changeOptions = function (options) {
        this.lastChangeOptions = options;
        this.changeOptionsCalls.push(options);
    };

    const originalMoment = global.moment;
    let tick = 0;
    global.moment = () => ({
        tz() { return this; },
        format(fmt) { return fmt === ' z' ? ' UTC' : 'FMT'; },
        fromNow() { tick += 1; return tick === 1 ? 'now' : 'later'; },
        calendar() { return 'calendar'; },
    });

    try {
        const table = new ModelTable([
            { field: 'when', type: 'date', format: 'relative', tooltip: 'none', sortable: true },
            { field: 'numeric', sortable: false },
            { field: 'flag', sortable: false },
        ], {
            class: 'extra-class',
            source,
            id: 'id',
            selectionType: 'multiple',
        });

        assert.equal(table.wrapperElement.className.includes('extra-class'), true);
        assert.equal(table.statusBar != null, true);

        table.reload();
        const rows = collectNodesByPredicate(table.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
        assert.equal(rows[0].childNodes[0].textContent, '');
        assert.equal(rows[0].childNodes[1].textContent, '3');
        assert.equal(rows[0].childNodes[2].textContent, 'true');

        const firstCell = rows[0].childNodes[0];
        firstCell.dispatchEvent(makeEvent('click', { target: firstCell, shiftKey: true }));
        assert.deepEqual(table.selection, [1]);

        const secondCell = rows[1].childNodes[0];
        secondCell.dispatchEvent(makeEvent('click', { target: secondCell, ctrlKey: true }));
        assert.deepEqual(table.selection.sort(), [1, 2]);
        secondCell.dispatchEvent(makeEvent('click', { target: secondCell, ctrlKey: true }));
        assert.deepEqual(table.selection, [1]);

        firstCell.dispatchEvent(makeEvent('click', { target: firstCell }));
        secondCell.dispatchEvent(makeEvent('click', { target: secondCell, ctrlKey: true, shiftKey: true }));
        assert.equal(table.selection.includes(1), true);
        assert.equal(table.selection.includes(2), true);

        table.wrapperElement.dispatchEvent(makeEvent('click', { target: table.wrapperElement, shiftKey: true }));
        assert.equal(table.selection.length > 0, true);

        assert.throws(() => {
            table.selection = 1;
        }, TypeError);
        table.select(null);
        assert.deepEqual(table.selection, []);

        intervals.forEach((entry) => entry.callback());
        assert.equal(rows[1].childNodes[0].textContent, 'later');

        source.currentElements = [{ id: 10, when: '2026-04-02T10:00:00Z', numeric: 1, flag: true }];
        table.reload();
        const refreshedRows = collectNodesByPredicate(table.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
        const refreshedCell = refreshedRows[0].childNodes[0];
        refreshedCell.dispatchEvent(makeEvent('click', { target: refreshedCell, ctrlKey: true, shiftKey: true }));
        assert.deepEqual(table.selection, [10]);

        table.destroy();

        const disabledTable = new ModelTable([{ field: 'id', sortable: false }], {
            source,
            id: 'id',
            selectionType: 'none',
            initialSortColumn: 'missing-field',
        });
        disabledTable.reload();
        const disabledRows = collectNodesByPredicate(disabledTable.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
        const disabledCell = disabledRows[0].childNodes[0];
        disabledCell.dispatchEvent(makeEvent('click', { target: disabledCell }));
        assert.deepEqual(disabledTable.selection, []);
        assert.equal(source.lastChangeOptions.order, null);
        disabledTable.destroy();

        const formattedSource = new StaticPaginatedSource({
            pageSize: 5,
            idAttr: 'id',
            initialElements: [{ id: 20, when: '2026-04-03T10:00:00Z' }],
        });
        formattedSource.currentElements = formattedSource.options.initialElements.slice();
        formattedSource.getCurrentPage = function () { return this.currentElements; };
        formattedSource.changeOptions = function () {};
        const formattedTable = new ModelTable([
            { field: 'when', type: 'date', format: 'YYYY', tooltip: 'none', sortable: false },
        ], {
            source: formattedSource,
            id: 'id',
            selectionType: 'single',
        });
        formattedTable.reload();
        const formattedRows = collectNodesByPredicate(formattedTable.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
        assert.equal(formattedRows[0].childNodes[0].textContent, 'FMT');
        formattedTable.select(20);
        assert.deepEqual(formattedTable.selection, [20]);
        formattedTable.destroy();

        const defaultDateSource = new StaticPaginatedSource({
            pageSize: 5,
            idAttr: 'id',
            initialElements: [{ id: 30, when: '2026-04-03T10:00:00Z' }],
        });
        defaultDateSource.currentElements = defaultDateSource.options.initialElements.slice();
        defaultDateSource.getCurrentPage = function () { return this.currentElements; };
        defaultDateSource.changeOptions = function () {};
        const defaultDateTable = new ModelTable([
            { field: 'when', type: 'date', sortable: false },
        ], {
            source: defaultDateSource,
            id: 'id',
            selectionType: 'none',
        });
        defaultDateTable.reload();
        const defaultRows = collectNodesByPredicate(defaultDateTable.wrapperElement, (node) => node.classList?.contains('se-model-table-row'));
        assert.equal(defaultRows[0].childNodes[0].textContent.length > 0, true);
        assert.equal(Tooltip.instances.length > 0, true);
        defaultDateTable.destroy();

        const autoSourceSortTable = new ModelTable([
            { field: 'name', sortable: false, sort_id: 'name_sort' },
        ], {
            pageSize: 5,
            id: 'id',
            selectionType: 'none',
        });
        assert.equal(autoSourceSortTable.source.options.sort_info.name_sort, autoSourceSortTable.columns[0]);
        autoSourceSortTable.destroy();
    } finally {
        global.moment = originalMoment;
        restoreGlobals();
    }
});











