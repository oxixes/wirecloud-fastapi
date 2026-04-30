const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupFormWindowMenu = () => {
    class ButtonStub {
        constructor() {
            this.classes = [];
            this.disabled = false;
        }

        addClassName(className) {
            this.classes.push(className);
            return this;
        }

        removeClassName(className) {
            this.classes = this.classes.filter((entry) => entry !== className);
            return this;
        }

        enable() {
            this.disabled = false;
            return this;
        }

        disable() {
            this.disabled = true;
            return this;
        }
    }

    class Form {
        constructor(fields, options) {
            this.fields = fields;
            this.options = options;
            this.acceptButton = new ButtonStub();
            this.cancelButton = new ButtonStub();
            this.listeners = {};
            this.displayedMessages = [];
            this.insertedInto = null;
            this.dataValue = null;
            this.focusCalls = 0;
            this.resetCalls = 0;
            this.repaintCalls = 0;
        }

        insertInto(node) {
            this.insertedInto = node;
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }

        trigger(name, data = {}) {
            this.listeners[name](this, data);
        }

        displayMessage(error) {
            this.displayedMessages.push(error);
        }

        setData(value) {
            this.dataValue = value;
        }

        focus() {
            this.focusCalls += 1;
        }

        reset() {
            this.resetCalls += 1;
        }

        repaint() {
            this.repaintCalls += 1;
        }
    }

    class WindowMenu {
        constructor(title, extraClass) {
            this.title = title;
            this.extraClass = extraClass;
            this.windowBottom = document.createElement('div');
            this.windowContent = document.createElement('div');
            this._closeListener = () => {
                this.closeCalls = (this.closeCalls || 0) + 1;
            };
            this.showCalls = 0;
            this.hideCalls = 0;
        }

        show() {
            this.showCalls += 1;
        }

        hide() {
            this.hideCalls += 1;
            return this;
        }
    }

    global.StyledElements = {Form};
    global.Wirecloud = {
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        },
        ui: {
            WindowMenu,
            InputInterfaceFactory: {id: 'factory'},
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/FormWindowMenu.js');

    return Wirecloud.ui.FormWindowMenu;
};

test('Wirecloud.ui.FormWindowMenu constructor wires form, classes and cancel listener', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu(['field'], 'Title', 'extra');

    assert.equal(menu.form.fields.length, 1);
    assert.equal(menu.form.options.buttonArea, menu.windowBottom);
    assert.equal(menu.form.options.autoHide, true);
    assert.equal(menu.form.options.factory.id, 'factory');
    assert.equal(menu.form.insertedInto, menu.windowContent);
    assert.equal(menu.form.acceptButton.classes.includes('btn-accept'), true);
    assert.equal(menu.form.cancelButton.classes.includes('btn-cancel'), true);
    assert.equal(menu.form.listeners.cancel, menu._closeListener);
});

test('Wirecloud.ui.FormWindowMenu setValue delegates to form and is chainable', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');

    const result = menu.setValue({name: 'value'});

    assert.equal(result, menu);
    assert.deepEqual(menu.form.dataValue, {name: 'value'});
});

test('Wirecloud.ui.FormWindowMenu setFocus delegates to form and is chainable', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');

    const result = menu.setFocus();

    assert.equal(result, menu);
    assert.equal(menu.form.focusCalls, 1);
});

test('Wirecloud.ui.FormWindowMenu show resets form, enables buttons and repaints', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');
    menu.form.acceptButton.disabled = true;
    menu.form.cancelButton.disabled = true;

    const result = menu.show('parent');

    assert.equal(result, menu);
    assert.equal(menu.form.resetCalls, 1);
    assert.equal(menu.form.acceptButton.disabled, false);
    assert.equal(menu.form.cancelButton.disabled, false);
    assert.equal(menu.showCalls, 1);
    assert.equal(menu.form.repaintCalls, 1);
});

test('Wirecloud.ui.FormWindowMenu submit with promise resolve adds busy class and hides', async () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');
    menu.executeOperation = () => Promise.resolve();

    menu.form.trigger('submit', {k: 1});
    await Promise.resolve();

    assert.equal(menu.form.acceptButton.classes.includes('busy'), true);
    assert.equal(menu.hideCalls, 1);
});

test('Wirecloud.ui.FormWindowMenu submit with promise reject displays message and re-enables buttons', async () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');
    menu.executeOperation = () => Promise.reject('failure');

    menu.form.trigger('submit', {});
    await Promise.resolve();

    assert.deepEqual(menu.form.displayedMessages, ['failure']);
    assert.equal(menu.form.acceptButton.classes.includes('busy'), false);
    assert.equal(menu.form.acceptButton.disabled, false);
    assert.equal(menu.form.cancelButton.disabled, false);
});

test('Wirecloud.ui.FormWindowMenu submit without promise and autoHide true hides', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');
    menu.executeOperation = () => ({notThenable: true});

    menu.form.trigger('submit', {});

    assert.equal(menu.hideCalls, 1);
});

test('Wirecloud.ui.FormWindowMenu submit without promise and autoHide false does not hide', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra', {autoHide: false});
    menu.executeOperation = () => null;

    menu.form.trigger('submit', {});

    assert.equal(menu.hideCalls, 0);
});

test('Wirecloud.ui.FormWindowMenu submit handles executeOperation exceptions', () => {
    resetLegacyRuntime();
    const FormWindowMenu = setupFormWindowMenu();
    const menu = new FormWindowMenu([], 'Title', 'extra');
    menu.executeOperation = () => {
        throw new TypeError('boom');
    };

    menu.form.trigger('submit', {});

    assert.equal(menu.hideCalls, 1);
});
