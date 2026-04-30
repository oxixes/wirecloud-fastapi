const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupTab = () => {
    class Container {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.eventListeners = {};
            this.showCalls = 0;
            this.hideCalls = 0;
            this.repaintCalls = [];
            this.wrapperElement.classList.add('hidden');
        }

        addEventListener(eventName, handler) {
            if (!this.eventListeners[eventName]) {
                this.eventListeners[eventName] = [];
            }
            this.eventListeners[eventName].push(handler);
            return this;
        }

        dispatchEvent(eventName) {
            (this.eventListeners[eventName] || []).forEach((listener) => listener());
            return this;
        }

        show() {
            this.showCalls += 1;
            this.wrapperElement.classList.remove('hidden');
            return this;
        }

        hide() {
            this.hideCalls += 1;
            this.wrapperElement.classList.add('hidden');
            return this;
        }

        repaint(force) {
            this.repaintCalls.push(force);
            return this;
        }
    }

    class Notebook {
        constructor() {
            this.goToTabCalls = [];
            this.removeTabCalls = [];
        }

        goToTab(tabId) {
            this.goToTabCalls.push(tabId);
        }

        removeTab(tabId) {
            this.removeTabCalls.push(tabId);
        }
    }

    class Tooltip {
        constructor(options) {
            this.options = options;
            this.bindCalls = [];
            this.destroyCalls = 0;
            Tooltip.instances.push(this);
        }

        bind(element) {
            this.bindCalls.push(element);
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }
    Tooltip.instances = [];

    class Button {
        constructor() {
            this.wrapperElement = document.createElement('button');
            this.listeners = {};
            Button.instances.push(this);
        }

        insertInto(element) {
            element.appendChild(this.wrapperElement);
            return this;
        }

        addEventListener(eventName, handler) {
            this.listeners[eventName] = handler;
            return this;
        }
    }
    Button.instances = [];

    global.StyledElements = {
        Container,
        Notebook,
        Tooltip,
        Button,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Tab.js');
    return {
        Tab: StyledElements.Tab,
        Notebook,
        Tooltip,
        Button,
    };
};

test('StyledElements.Tab constructor validates notebook argument', () => {
    resetLegacyRuntime();
    const {Tab} = setupTab();

    assert.throws(() => new Tab('t1', {}, {}), {
        name: 'TypeError',
        message: 'Invalid notebook argument',
    });
});

test('StyledElements.Tab constructor initializes tab and wrapper attributes', () => {
    resetLegacyRuntime();
    const {Tab, Notebook, Button} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-1', notebook, {label: 'Tab Label'});

    assert.equal(tab.tabId, 'tab-1');
    assert.equal(tab.notebook, notebook);
    assert.equal(tab.label, 'Tab Label');
    assert.equal(tab.tabElement.getAttribute('role'), 'tab');
    assert.equal(tab.tabElement.getAttribute('aria-selected'), 'false');
    assert.equal(tab.tabElement.getAttribute('aria-controls'), 'se-notebook-tabpanel-tab-1');
    assert.equal(tab.wrapperElement.getAttribute('role'), 'tabpanel');
    assert.equal(tab.wrapperElement.getAttribute('id'), 'se-notebook-tabpanel-tab-1');
    assert.equal(tab.wrapperElement.getAttribute('aria-labelledby'), 'se-notebook-tab-tab-1');
    assert.equal(Button.instances.length, 1);
});

test('StyledElements.Tab constructor supports deprecated name option and non-closable tabs', () => {
    resetLegacyRuntime();
    const {Tab, Notebook, Button} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-2', notebook, {name: 'Legacy Name', closable: false});

    assert.equal(tab.label, 'Legacy Name');
    assert.equal(Button.instances.length, 0);
});

test('StyledElements.Tab tab click delegates selection to notebook', () => {
    resetLegacyRuntime();
    const {Tab, Notebook} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-3', notebook, {label: 'Clickable'});

    tab.tabElement.dispatchEvent({type: 'click'});

    assert.deepEqual(notebook.goToTabCalls, ['tab-3']);
});

test('StyledElements.Tab close button callback removes tab and emits close event', () => {
    resetLegacyRuntime();
    const {Tab, Notebook, Button} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-4', notebook, {label: 'Closable'});
    let closeEvents = 0;
    tab.addEventListener('close', () => {
        closeEvents += 1;
    });

    Button.instances[0].listeners.click();

    assert.deepEqual(notebook.removeTabCalls, ['tab-4']);
    assert.equal(closeEvents, 1);
});

test('StyledElements.Tab setTitle creates tooltip and updates existing tooltip content', () => {
    resetLegacyRuntime();
    const {Tab, Notebook, Tooltip} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-5', notebook, {label: 'With Tooltip'});

    tab.setTitle('First title');
    tab.setTitle('Second title');

    assert.equal(Tooltip.instances.length, 1);
    assert.equal(Tooltip.instances[0].bindCalls.length, 1);
    assert.equal(Tooltip.instances[0].bindCalls[0], tab.tabElement);
    assert.equal(tab.tooltip.options.content, 'Second title');
});

test('StyledElements.Tab setTitle destroys tooltip on empty title', () => {
    resetLegacyRuntime();
    const {Tab, Notebook, Tooltip} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-6', notebook, {label: 'With Tooltip', title: 'Initial'});

    tab.setTitle('');
    tab.setTitle(null);

    assert.equal(Tooltip.instances.length, 1);
    assert.equal(Tooltip.instances[0].destroyCalls, 1);
    assert.equal(tab.tooltip, null);
});

test('StyledElements.Tab setVisible delegates to show and hide', () => {
    resetLegacyRuntime();
    const {Tab, Notebook} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-7', notebook, {label: 'Visibility'});

    tab.setVisible(true);
    tab.setVisible(false);

    assert.equal(tab.showCalls, 1);
    assert.equal(tab.hideCalls, 1);
});

test('StyledElements.Tab show and hide update selected state and repaint', () => {
    resetLegacyRuntime();
    const {Tab, Notebook} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-8', notebook, {label: 'State'});

    tab.show();
    tab.hide();

    assert.equal(tab.tabElement.classList.contains('selected'), false);
    assert.equal(tab.tabElement.getAttribute('aria-selected'), 'false');
    assert.deepEqual(tab.repaintCalls, [false]);
});

test('StyledElements.Tab getTabElement and rename alias map to the current tab state', () => {
    resetLegacyRuntime();
    const {Tab, Notebook} = setupTab();
    const notebook = new Notebook();
    const tab = new Tab('tab-9', notebook, {label: 'Old'});

    tab.rename('New');

    assert.equal(tab.getTabElement(), tab.tabElement);
    assert.equal(tab.label, 'New');
});
