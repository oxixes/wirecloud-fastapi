const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { repoRoot } = require('../../../support/legacy-runtime.cjs');

const shimPath = path.join(repoRoot, 'src/wirecloud/commons/static/js/wirecloud/shims/classList.js');
const shimSource = fs.readFileSync(shimPath, 'utf8');

const runShim = ({ hasSVGElement = true, nativeClassList = false } = {}) => {
    const originalWindow = global.window;
    const originalDocument = global.document;
    const originalDOMException = global.DOMException;

    class FakeSVGElement {
        constructor() {
            this.attrs = {};
        }

        getAttribute(name) {
            return this.attrs[name] ?? null;
        }

        setAttribute(name, value) {
            this.attrs[name] = String(value);
        }
    }

    const windowObject = {};
    if (hasSVGElement) {
        windowObject.SVGElement = FakeSVGElement;
    }

    global.window = windowObject;
    global.document = {
        createElementNS() {
            const element = new FakeSVGElement();
            if (nativeClassList) {
                element.classList = {};
            }
            return element;
        }
    };
    global.DOMException = {
        SYNTAX_ERR: 12,
        INVALID_CHARACTER_ERR: 5,
    };

    vm.runInThisContext(shimSource, { filename: shimPath });

    return {
        windowObject,
        restore() {
            global.window = originalWindow;
            global.document = originalDocument;
            global.DOMException = originalDOMException;
        }
    };
};

test('classList shim returns early when SVGElement is unavailable', () => {
    const runtime = runShim({ hasSVGElement: false });
    try {
        assert.equal('SVGElement' in runtime.windowObject, false);
    } finally {
        runtime.restore();
    }
});

test('classList shim returns early when native classList already exists', () => {
    const runtime = runShim({ nativeClassList: true });
    try {
        assert.equal(Object.getOwnPropertyDescriptor(runtime.windowObject.SVGElement.prototype, 'classList'), undefined);
    } finally {
        runtime.restore();
    }
});

test('classList shim provides add/remove/toggle APIs and token validation', () => {
    const runtime = runShim();
    try {
        const emptyElement = new runtime.windowObject.SVGElement();
        assert.equal(emptyElement.classList.toString(), '');
        assert.equal(emptyElement.classList.item(0), null);

        const element = new runtime.windowObject.SVGElement();
        element.setAttribute('class', 'one two');

        const classList = element.classList;
        assert.equal(classList.item(0), 'one');
        assert.equal(classList.item(9), null);
        assert.equal(classList.contains('two'), true);

        classList.add('three', 'one');
        assert.equal(element.getAttribute('class'), 'one two three');

        classList.remove('two', 'missing');
        assert.equal(element.getAttribute('class'), 'one three');

        assert.equal(classList.toggle('three'), false);
        assert.equal(element.getAttribute('class'), 'one');
        assert.equal(classList.toggle('new', false), true);
        assert.equal(element.getAttribute('class'), 'one');
        assert.equal(classList.toggle('new', true), true);
        assert.equal(element.getAttribute('class'), 'one new');
        assert.equal(classList.toString(), 'one new');

        assert.throws(
            () => classList.add('bad token'),
            (error) => error?.name === 'INVALID_CHARACTER_ERR'
        );
        assert.throws(
            () => classList.remove(''),
            (error) => error?.name === 'SYNTAX_ERR'
        );
    } finally {
        runtime.restore();
    }
});
