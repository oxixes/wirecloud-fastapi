const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupFileField = () => {
    class InputElement {
        constructor(defaultValue) {
            this.defaultValue = defaultValue;
            this.dispatched = [];
            this.insertIntoCalls = 0;
            this.destroyCalls = 0;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }

        insertInto(element, refElement) {
            this.insertIntoCalls += 1;
            element.insertBefore(this.wrapperElement, refElement ?? null);
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class HorizontalLayout {
        constructor(options = {}) {
            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = options.class || '';
            this.repaintCalls = 0;
            this.center = {
                children: [],
                appendChild: (value) => {
                    this.center.children.push(value);
                }
            };
            this.east = {
                children: [],
                appendChild: (value) => {
                    this.east.children.push(value);
                }
            };
        }

        getCenterContainer() {
            return this.center;
        }

        getEastContainer() {
            return this.east;
        }

        repaint() {
            this.repaintCalls += 1;
        }
    }

    global.StyledElements = {
        InputElement,
        HorizontalLayout,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            gettext: (text) => text,
            stopPropagationListener: () => {}
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/FileField.js');
    return StyledElements.FileField;
};

test('StyledElements.FileField constructor initializes layout, attributes and preview/button areas', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({
        class: 'extra',
        name: 'upload',
        id: 'file-id',
    });

    assert.equal(field.wrapperElement.className.includes('se-file-field'), true);
    assert.equal(field.wrapperElement.className.includes('extra'), true);
    assert.equal(field.inputElement.getAttribute('name'), 'upload');
    assert.equal(field.wrapperElement.getAttribute('id'), 'file-id');
    assert.equal(field.name_preview.getAttribute('aria-label'), 'Selected file name');
    assert.equal(field.layout.getEastContainer().children.length, 1);
});

test('StyledElements.FileField constructor keeps optional attributes absent when not provided', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});

    assert.equal(field.inputElement.getAttribute('name'), null);
    assert.equal(field.wrapperElement.getAttribute('id'), null);
});

test('StyledElements.FileField click handler ignores clicks on native input', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    let clicked = 0;
    field.inputElement.click = () => {
        clicked += 1;
    };

    field.wrapperElement.dispatchEvent({
        type: 'click',
        target: field.inputElement,
        stopPropagation() {},
        preventDefault() {}
    });

    assert.equal(clicked, 0);
});

test('StyledElements.FileField click handler proxies click to input and cancels event', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    let clicked = 0;
    let stopped = 0;
    let prevented = 0;
    field.inputElement.click = () => {
        clicked += 1;
    };

    field.wrapperElement.dispatchEvent({
        type: 'click',
        target: field.wrapperElement,
        stopPropagation() {
            stopped += 1;
        },
        preventDefault() {
            prevented += 1;
        }
    });

    assert.equal(clicked, 1);
    assert.equal(stopped, 1);
    assert.equal(prevented, 1);
});

test('StyledElements.FileField change updates preview and dispatches change event', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    field.inputElement.files = [{name: 'report.pdf'}];

    field.inputElement.dispatchEvent({type: 'change'});

    assert.equal(field.name_preview.textContent, 'report.pdf');
    assert.equal(field.name_preview.getAttribute('title'), 'report.pdf');
    assert.equal(field.dispatched.at(-1).name, 'change');
});

test('StyledElements.FileField change handles missing files by clearing preview', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    field.inputElement.files = [];

    field.inputElement.dispatchEvent({type: 'change'});

    assert.equal(field.name_preview.textContent, '');
    assert.equal(field.name_preview.getAttribute('title'), '');
});

test('StyledElements.FileField focus and blur toggle class and dispatch events', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});

    field.inputElement.dispatchEvent({type: 'focus'});
    field.inputElement.dispatchEvent({type: 'blur'});

    assert.equal(field.wrapperElement.classList.contains('focus'), false);
    assert.equal(field.dispatched[0].name, 'focus');
    assert.equal(field.dispatched[1].name, 'blur');
});

test('StyledElements.FileField repaint delegates to horizontal layout', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});

    field.repaint();

    assert.equal(field.layout.repaintCalls, 1);
});

test('StyledElements.FileField insertInto calls base insert and triggers repaint', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    const parent = document.createElement('div');

    field.insertInto(parent);

    assert.equal(field.insertIntoCalls, 1);
    assert.equal(field.layout.repaintCalls, 1);
});

test('StyledElements.FileField getValue returns first file from input list', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});
    const file = {name: 'first.txt'};
    field.inputElement.files = [file, {name: 'second.txt'}];

    assert.equal(field.getValue(), file);
});

test('StyledElements.FileField destroy removes handlers and delegates to base destroy', () => {
    resetLegacyRuntime();
    const FileField = setupFileField();
    const field = new FileField({});

    field.destroy();

    assert.equal(field._onchange, undefined);
    assert.equal(field._onfocus, undefined);
    assert.equal(field._onblur, undefined);
    assert.equal(field.destroyCalls, 1);
});
