const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupSelect = () => {
    const originalCreateElement = document.createElement.bind(document);
    document.createElement = (tagName) => {
        const element = originalCreateElement(tagName);
        const normalizedTag = String(tagName).toLowerCase();

        if (normalizedTag === 'option') {
            Object.defineProperty(element, 'value', {
                configurable: true,
                enumerable: true,
                get() {
                    const value = this.getAttribute('value');
                    return value != null ? value : this.textContent;
                },
                set(newValue) {
                    this.setAttribute('value', String(newValue));
                },
            });
            Object.defineProperty(element, 'text', {
                configurable: true,
                enumerable: true,
                get() {
                    return this.textContent;
                },
            });
        }

        if (normalizedTag === 'select') {
            element._selectedIndex = -1;
            element._value = '';
            const originalAppendChild = element.appendChild.bind(element);
            element.appendChild = (child) => {
                const result = originalAppendChild(child);
                const index = element.childNodes.length - 1;
                element[index] = child;
                if (child.getAttribute != null && child.getAttribute('selected') != null) {
                    element.selectedIndex = index;
                } else if (element._selectedIndex === -1) {
                    element.selectedIndex = 0;
                }
                return result;
            };
            Object.defineProperty(element, 'options', {
                configurable: true,
                enumerable: true,
                get() {
                    const options = element.childNodes;
                    options.selectedIndex = element.selectedIndex;
                    return options;
                },
            });
            Object.defineProperty(element, 'selectedIndex', {
                configurable: true,
                enumerable: true,
                get() {
                    return element._selectedIndex;
                },
                set(index) {
                    const normalized = Number(index);
                    if (Number.isNaN(normalized) || normalized < 0 || normalized >= element.childNodes.length) {
                        element._selectedIndex = -1;
                        element._value = '';
                        return;
                    }
                    element._selectedIndex = normalized;
                    element._value = element.childNodes[normalized].value;
                },
            });
            Object.defineProperty(element, 'value', {
                configurable: true,
                enumerable: true,
                get() {
                    return element._value;
                },
                set(newValue) {
                    const normalized = String(newValue);
                    element._value = normalized;
                    const index = element.childNodes.findIndex((option) => option.value === normalized);
                    element._selectedIndex = index;
                },
            });
        }

        return element;
    };

    class InputElement {
        constructor(defaultValue, events = []) {
            this.defaultValue = defaultValue;
            this.events = {};
            events.forEach((name) => {
                this.events[name] = true;
            });
            this.enabled = true;
            this.dispatched = [];
            this.destroyed = false;
        }

        addClassName(className) {
            if (className) {
                this.wrapperElement.classList.add(className);
            }
            return this;
        }

        removeClassName(className) {
            this.wrapperElement.classList.remove(className);
            return this;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
            return this;
        }

        setValue(newValue) {
            const oldValue = this.inputElement.value;
            this.inputElement.value = newValue;
            if ('change' in this.events && oldValue !== newValue) {
                this.dispatchEvent('change');
            }
            return this;
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
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Select.js');
    return StyledElements.Select;
};

test('StyledElements.Select constructor builds wrapper and initializes selected label', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        class: 'extra',
        name: 'my-name',
        id: 'my-id',
        initialEntries: [['a', 'A'], ['b', 'B']],
        initialValue: 'b',
    });

    assert.equal(select.wrapperElement.className.includes('se-select'), true);
    assert.equal(select.wrapperElement.className.includes('extra'), true);
    assert.equal(select.inputElement.getAttribute('name'), 'my-name');
    assert.equal(select.wrapperElement.getAttribute('id'), 'my-id');
    assert.equal(select.getLabel(), 'B');
    assert.equal(select.getValue(), 'b');
});

test('StyledElements.Select change listener updates label and dispatches only when enabled', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        initialEntries: [['a', 'A'], ['b', 'B']],
        initialValue: 'a',
    });

    select.inputElement.selectedIndex = 1;
    select.inputElement.dispatchEvent({type: 'change', target: select.inputElement});
    assert.equal(select.getLabel(), 'B');
    assert.equal(select.dispatched.at(-1).name, 'change');

    const eventsBefore = select.dispatched.length;
    select.enabled = false;
    select.inputElement.selectedIndex = 0;
    select.inputElement.dispatchEvent({type: 'change', target: select.inputElement});
    assert.equal(select.dispatched.length, eventsBefore);
    assert.equal(select.getLabel(), 'B');
});

test('StyledElements.Select focus and blur listeners toggle focus class and dispatch events', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({initialEntries: ['x']});

    select.inputElement.dispatchEvent({type: 'focus'});
    assert.equal(select.wrapperElement.classList.contains('focus'), true);
    assert.equal(select.dispatched.at(-1).name, 'focus');

    select.inputElement.dispatchEvent({type: 'blur'});
    assert.equal(select.wrapperElement.classList.contains('focus'), false);
    assert.equal(select.dispatched.at(-1).name, 'blur');
});

test('StyledElements.Select setValue supports non-string values through idFunc', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const idFunc = (value) => `id:${value.id}`;
    const select = new Select({
        idFunc,
        initialEntries: [
            {value: {id: 1}, label: 'One'},
            {value: {id: 2}, label: 'Two'},
        ],
        initialValue: {id: 1},
    });

    select.setValue({id: 2});

    assert.equal(select.inputElement.value, 'id:2');
    assert.equal(select.getLabel(), 'Two');
    assert.equal(select.getValue().id, 2);
});

test('StyledElements.Select setValue falls back to default value when requested value is unknown', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        initialEntries: [['x', 'X'], ['y', 'Y']],
        initialValue: 'y',
    });

    select.setValue('missing');

    assert.equal(select.inputElement.value, 'y');
    assert.equal(select.getLabel(), 'Y');
});

test('StyledElements.Select setValue falls back to first option when there is no default value', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        initialEntries: ['x', 'y'],
        initialValue: null,
    });

    select.setValue('missing');

    assert.equal(select.inputElement.value, 'x');
    assert.equal(select.getLabel(), 'x');
});

test('StyledElements.Select setValue handles idFunc errors and empty option list branch', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        idFunc: (value) => {
            if (value == null) {
                return '';
            }
            throw new TypeError('boom');
        },
    });

    select.setValue({id: 9});

    assert.equal(select.inputElement.value, '');
    assert.equal(select.getLabel(), '');
});

test('StyledElements.Select addEntries handles array/object/plain entries and null or empty input', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const idFunc = (value) => value == null ? '' : `id-${value.id}`;
    const select = new Select({
        idFunc,
        initialEntries: null,
    });
    select.addEntries([]);
    assert.equal(select.inputElement.options.length, 0);

    select.addEntries([
        ['a', 'A'],
        {value: {id: 10}, label: 'Obj'},
        {value: 'naked', label: ''},
        'plain',
    ]);

    assert.equal(select.inputElement.options.length, 4);
    assert.equal(select.optionsByValue.a, 'A');
    assert.equal(select.optionsByValue['id-10'], 'Obj');
    assert.equal(select.optionsByValue.naked, 'naked');
    assert.equal(select.optionValues['id-10'].id, 10);
});

test('StyledElements.Select addEntries supports undefined defaultValue branch', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({initialEntries: []});
    select.defaultValue = undefined;

    select.addEntries([['x', 'X']]);

    assert.equal(select.inputElement.options.length, 1);
    assert.equal(select.getLabel(), 'X');
});

test('StyledElements.Select clear resets options, label and maps', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({
        initialEntries: [['a', 'A']],
        initialValue: 'a',
    });

    select.clear();

    assert.equal(select.getLabel(), '');
    assert.deepEqual(select.optionsByValue, {});
    assert.deepEqual(select.optionValues, {});
});

test('StyledElements.Select destroy removes listeners and calls base destroy', () => {
    resetLegacyRuntime();
    const Select = setupSelect();
    const select = new Select({initialEntries: ['x']});

    select.destroy();
    select.inputElement.dispatchEvent({type: 'focus'});

    assert.equal(select._onchange, undefined);
    assert.equal(select._onfocus, undefined);
    assert.equal(select._onblur, undefined);
    assert.equal(select.destroyed, true);
    assert.equal(select.dispatched.some((entry) => entry.name === 'focus'), false);
});
