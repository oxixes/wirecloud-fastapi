const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupTextArea = () => {
    class InputElement {
        constructor(initialValue, events) {
            this.value = initialValue;
            this.events = events;
            this.dispatched = [];
        }

        setValue(value) {
            this.value = value;
            if (this.inputElement) {
                this.inputElement.value = value;
            }
        }

        dispatchEvent(name, value) {
            this.dispatched.push({ name, value });
        }

        destroy() {
            this.destroyed = true;
        }
    }

    global.StyledElements = {
        InputElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {},
            stopInputKeydownPropagationListener: () => {},
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/TextArea.js');
    return StyledElements.TextArea;
};

test('StyledElements.TextArea initializes textarea wrapper with options', () => {
    resetLegacyRuntime();
    const TextArea = setupTextArea();
    const area = new TextArea({ class: 'custom', name: 'msg', id: 'msg-id', initialValue: 'hello' });

    assert.equal(area.wrapperElement.tagName, 'TEXTAREA');
    assert.equal(area.wrapperElement.className, 'se-text-area custom');
    assert.equal(area.inputElement.getAttribute('name'), 'msg');
    assert.equal(area.wrapperElement.getAttribute('id'), 'msg-id');
    assert.equal(area.inputElement.value, 'hello');
});

test('StyledElements.TextArea dispatches change/focus/blur events', () => {
    resetLegacyRuntime();
    const TextArea = setupTextArea();
    const area = new TextArea({});

    area.inputElement.dispatchEvent({ type: 'input' });
    area.inputElement.dispatchEvent({ type: 'focus' });
    area.inputElement.dispatchEvent({ type: 'blur' });

    assert.deepEqual(area.dispatched.map((entry) => entry.name), ['change', 'focus', 'blur']);
});

test('StyledElements.TextArea select delegates to native select', () => {
    resetLegacyRuntime();
    const TextArea = setupTextArea();
    const area = new TextArea({});
    let selected = 0;
    area.inputElement.select = () => {
        selected += 1;
    };

    area.select();

    assert.equal(selected, 1);
});

test('StyledElements.TextArea destroy removes handlers and calls base destroy', () => {
    resetLegacyRuntime();
    const TextArea = setupTextArea();
    const area = new TextArea({});

    area.destroy();

    assert.equal(area._oninput, undefined);
    assert.equal(area._onfocus, undefined);
    assert.equal(area._onblur, undefined);
    assert.equal(area.destroyed, true);
});
