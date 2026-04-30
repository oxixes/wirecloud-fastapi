const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupMultivaluedInputInterface = () => {
    class InputInterface {
        constructor(fieldId) {
            this.fieldId = fieldId;
        }
    }

    class Container {
        constructor() {
            this.wrapperElement = document.createElement('div');
        }
    }

    class Form {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.data = null;
            this.destroyCalls = 0;
        }

        insertInto(parent) {
            parent.appendChild(this.wrapperElement);
            return this;
        }

        setData(data) {
            this.data = data;
        }

        getData() {
            return this.data;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class Button {
        constructor() {
            this.listeners = {};
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
            return this;
        }

        insertInto(parent) {
            this.parent = parent;
            parent.appendChild(document.createElement('button'));
            return this;
        }
    }

    global.StyledElements = {
        InputInterface,
        Container,
        Form,
        Button,
        Utils: {
            removeFromArray(collection, value) {
                const index = collection.indexOf(value);
                if (index !== -1) {
                    collection.splice(index, 1);
                }
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/MultivaluedInputInterface.js');

    return {
        MultivaluedInputInterface: StyledElements.MultivaluedInputInterface,
    };
};

test('MultivaluedInputInterface constructor, add/remove entries and getValue work', () => {
    resetLegacyRuntime();
    const { MultivaluedInputInterface } = setupMultivaluedInputInterface();

    const field = new MultivaluedInputInterface('f', {
        fields: {
            name: { type: 'text' },
        },
    });

    assert.equal(field.entries.length, 1);
    field.entries[0].form.setData({ name: 'first' });

    field.entries[0].addRowButton.listeners.click();
    assert.equal(field.entries.length, 2);
    field.entries[1].form.setData({ name: 'second' });

    field.entries[1].removeRowButton.listeners.click();
    assert.equal(field.entries.length, 1);
    assert.deepEqual(field.getValue(), [{ name: 'first' }]);
});

test('MultivaluedInputInterface clear, parse, setValue and setError branches', () => {
    resetLegacyRuntime();
    const { MultivaluedInputInterface } = setupMultivaluedInputInterface();

    const field = new MultivaluedInputInterface('f', {
        fields: {
            value: { type: 'text' },
        },
    });

    field._setValue([{ value: 1 }, { value: 2 }]);
    assert.equal(field.entries.length, 2);
    assert.deepEqual(field.getValue(), [{ value: 1 }, { value: 2 }]);

    field._setValue('invalid');
    assert.equal(field.entries.length, 1);
    field.entries[0].removeRowButton.listeners.click();
    assert.equal(field.entries.length, 1);

    const entry = field.entries[0];
    field.clear();
    assert.equal(field.entries.length, 0);
    assert.equal(entry.form.destroyCalls, 1);

    assert.deepEqual(MultivaluedInputInterface.parse('[1,2]'), [1, 2]);
    assert.equal(field._setError(true), field);
});


