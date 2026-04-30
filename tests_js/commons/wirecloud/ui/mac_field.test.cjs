const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupMACField = () => {
    class InputInterface {
        constructor(fieldId, options) {
            this.fieldId = fieldId;
            this.options = options;
        }
    }

    class InputElement {
        constructor(initialValue, events) {
            this.inputElement = null;
            this.events = events;
            this.dispatched = [];
            this.insertCalls = [];
            this.repaintCalls = 0;
        }

        dispatchEvent(name, value) {
            this.dispatched.push({name, value});
            return this;
        }

        insertInto(element, refElement) {
            this.insertCalls.push({element, refElement});
            element.appendChild(this.wrapperElement);
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }
    }

    class Button {
        constructor(options) {
            this.options = options;
            this.listeners = {};
            this.disabled = false;
            Button.instances.push(this);
        }

        appendTo(node) {
            this.parentNode = node;
            node.appendChild(document.createElement('button'));
            return this;
        }

        disable() {
            this.disabled = true;
            return this;
        }

        setDisabled(value) {
            this.disabled = value;
            return this;
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

    class MACSelectionWindowMenu {
        constructor(title, options) {
            this.title = title;
            this.options = options;
            this.listeners = {};
            MACSelectionWindowMenu.instances.push(this);
        }

        show(parentWindow) {
            this.parentWindow = parentWindow;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }
    }
    MACSelectionWindowMenu.instances = [];

    global.StyledElements = {
        Button,
        InputElement,
        InputInterface,
    };
    global.Wirecloud = {
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            gettext: (text) => text,
        },
        UserInterfaceManager: {
            currentWindowMenu: {id: 'current'},
        },
        ui: {
            MACSelectionWindowMenu,
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/MACField.js');
    return {
        MACField: Wirecloud.ui.MACField,
        MACInputInterface: Wirecloud.ui.MACInputInterface,
        Button,
        MACSelectionWindowMenu,
    };
};

test('Wirecloud.ui.MACField constructor configures wrapper/input/buttons', () => {
    resetLegacyRuntime();
    const {MACField, Button} = setupMACField();
    const field = new MACField({
        class: 'extra',
        scope: 'private',
        dialog_title: 'Pick one',
        name: 'mac',
        id: 'mac-id',
    });

    assert.equal(field.wrapperElement.className.includes('se-mac-field'), true);
    assert.equal(field.wrapperElement.className.includes('extra'), true);
    assert.equal(field.inputElement.getAttribute('name'), 'mac');
    assert.equal(field.wrapperElement.getAttribute('id'), 'mac-id');
    assert.equal(field.scope, 'private');
    assert.equal(field.dialog_title, 'Pick one');
    assert.equal(Button.instances.length, 2);
});

test('Wirecloud.ui.MACField setValue/getValue support object and string inputs', () => {
    resetLegacyRuntime();
    const {MACField} = setupMACField();
    const field = new MACField({});

    field.setValue({uri: 'urn:resource', title: 'Resource'});
    assert.equal(field.getValue(), 'urn:resource');
    assert.equal(field.name_preview.textContent, 'Resource');
    assert.equal(field.close_button.disabled, false);

    field.setValue('x');
    assert.equal(field.getValue(), 'x');
    assert.equal(field.name_preview.textContent, 'x');

    field.setValue('');
    assert.equal(field.close_button.disabled, true);
    assert.equal(field.dispatched.at(-1).name, 'change');
});

test('Wirecloud.ui.MACField close button click clears current value', () => {
    resetLegacyRuntime();
    const {MACField} = setupMACField();
    const field = new MACField({});
    field.setValue('value');

    field.close_button.fire('click');

    assert.equal(field.getValue(), '');
    assert.equal(field.name_preview.textContent, '');
});

test('Wirecloud.ui.MACField click opens selection dialog and handles wrapper click event cancel', () => {
    resetLegacyRuntime();
    const {MACField, MACSelectionWindowMenu} = setupMACField();
    const field = new MACField({scope: 'public', dialog_title: 'Title'});
    let stopped = 0;
    let prevented = 0;

    field.wrapperElement.dispatchEvent({
        type: 'click',
        target: field.wrapperElement,
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {
            prevented += 1;
        },
    });

    const dialog = MACSelectionWindowMenu.instances.at(-1);
    assert.equal(stopped, 1);
    assert.equal(prevented, 1);
    assert.equal(dialog.title, 'Title');
    assert.equal(dialog.options.scope, 'public');
    assert.equal(dialog.parentWindow.id, 'current');

    dialog.listeners.select(dialog, {uri: 'a', title: 'A'});
    assert.equal(field.getValue(), 'a');
});

test('Wirecloud.ui.MACField focus/blur listeners toggle class and dispatch events', () => {
    resetLegacyRuntime();
    const {MACField, Button} = setupMACField();
    const field = new MACField({});
    const closeButton = Button.instances[0];
    const searchButton = Button.instances[1];

    closeButton.fire('focus');
    assert.equal(field.wrapperElement.classList.contains('focus'), true);
    assert.equal(field.dispatched.at(-1).name, 'focus');
    searchButton.fire('blur');
    assert.equal(field.wrapperElement.classList.contains('focus'), false);
    assert.equal(field.dispatched.at(-1).name, 'blur');
});

test('Wirecloud.ui.MACField insertInto delegates to base insert and triggers repaint', () => {
    resetLegacyRuntime();
    const {MACField} = setupMACField();
    const field = new MACField({});
    const parent = document.createElement('div');

    field.insertInto(parent, null);

    assert.equal(field.insertCalls.length, 1);
    assert.equal(field.repaintCalls, 1);
});

test('Wirecloud.ui.MACInputInterface constructs inner MACField', () => {
    resetLegacyRuntime();
    const {MACInputInterface, MACField} = setupMACField();
    const iface = new MACInputInterface('field-id', {scope: 'x'});

    assert.equal(iface.inputElement instanceof MACField, true);
    assert.equal(iface.inputElement.scope, 'x');
});
