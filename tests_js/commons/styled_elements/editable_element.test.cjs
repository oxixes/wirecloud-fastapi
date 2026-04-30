const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupEditableElement = () => {
    class StyledElement {
        constructor(events = []) {
            this.events = {};
            events.forEach((name) => {
                this.events[name] = true;
            });
            this.dispatched = [];
            this.destroyCalls = 0;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {
        StyledElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {}
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/EditableElement.js');
    return StyledElements.EditableElement;
};

test('StyledElements.EditableElement initializes role, tabindex and content', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement({initialContent: 'hello'});

    assert.equal(element.wrapperElement.getAttribute('role'), 'textbox');
    assert.equal(element.wrapperElement.getAttribute('tabindex'), '0');
    assert.equal(element.wrapperElement.textContent, 'hello');
});

test('StyledElements.EditableElement editing getter reflects contenteditable state', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement();

    assert.equal(element.editing, false);
    element.enableEdition();
    assert.equal(element.editing, true);
    element.disableEdition();
    assert.equal(element.editing, false);
});

test('StyledElements.EditableElement setTextContent is chainable', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement();

    const result = element.setTextContent('new-value');

    assert.equal(result, element);
    assert.equal(element.wrapperElement.textContent, 'new-value');
});

test('StyledElements.EditableElement focus selects content and arms blur listener', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement();

    element.wrapperElement.dispatchEvent({type: 'focus'});

    assert.equal(document.listeners.mousedown.length > 0, true);
});

test('StyledElements.EditableElement blur dispatches change when content changed', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement({initialContent: 'before'});
    element.enableEdition();
    element.wrapperElement.textContent = 'after';

    element.wrapperElement.dispatchEvent({type: 'blur'});

    assert.equal(element.dispatched.length, 1);
    assert.equal(element.dispatched[0].name, 'change');
    assert.equal(element.dispatched[0].args[0], 'after');
    assert.equal(element.editing, false);
});

test('StyledElements.EditableElement blur is ignored when not in editing mode', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement({initialContent: 'same'});

    element.wrapperElement.dispatchEvent({type: 'blur'});

    assert.equal(element.dispatched.length, 0);
});

test('StyledElements.EditableElement keydown enter ends edition', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement({initialContent: 'start'});
    element.enableEdition();

    element.wrapperElement.dispatchEvent({type: 'keydown', keyCode: 13});

    assert.equal(element.editing, false);
});

test('StyledElements.EditableElement keydown escape restores previous content', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement({initialContent: 'start'});
    element.enableEdition();
    element.wrapperElement.textContent = 'edited';

    element.wrapperElement.dispatchEvent({type: 'keydown', keyCode: 27});

    assert.equal(element.wrapperElement.textContent, 'start');
    assert.equal(element.editing, false);
});

test('StyledElements.EditableElement disableEdition is safe when already disabled', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement();

    element.disableEdition();

    assert.equal(element.editing, false);
});

test('StyledElements.EditableElement destroy clears handlers and calls parent destroy', () => {
    resetLegacyRuntime();
    const EditableElement = setupEditableElement();
    const element = new EditableElement();

    element.destroy();

    assert.equal(element._onFocus, null);
    assert.equal(element._onKeydown, null);
    assert.equal(element._onBlur, null);
    assert.equal(element.destroyCalls, 1);
});
