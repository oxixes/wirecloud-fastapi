const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupContainer = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.enabled = true;
        }

        get() {
            return this.wrapperElement;
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }
    }

    global.StyledElements = {
        StyledElement,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            appendChild(container, newElement, refElement) {
                const target = container.get();
                const normalized = [];
                if (newElement == null) {
                    return normalized;
                }
                if (typeof newElement === 'string') {
                    const textNode = document.createTextNode(newElement);
                    target.insertBefore(textNode, refElement || null);
                    normalized.push(textNode);
                } else if (newElement instanceof StyledElement) {
                    target.insertBefore(newElement.get(), refElement || null);
                    normalized.push(newElement);
                } else {
                    target.insertBefore(newElement, refElement || null);
                    normalized.push(newElement);
                }
                return normalized;
            },
            prependChild(container, newElement, refElement) {
                const target = container.get();
                const normalized = [];
                if (newElement == null) {
                    return normalized;
                }
                const reference = refElement || target.firstChild;
                if (typeof newElement === 'string') {
                    const textNode = document.createTextNode(newElement);
                    target.insertBefore(textNode, reference || null);
                    normalized.push(textNode);
                } else if (newElement instanceof StyledElement) {
                    target.insertBefore(newElement.get(), reference || null);
                    normalized.push(newElement);
                } else {
                    target.insertBefore(newElement, reference || null);
                    normalized.push(newElement);
                }
                return normalized;
            },
            removeChild(container, childElement) {
                const target = container.get();
                if (childElement instanceof StyledElement) {
                    target.removeChild(childElement.get());
                } else {
                    target.removeChild(childElement);
                }
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Container.js');
    return {Container: StyledElements.Container, StyledElement};
};

test('StyledElements.Container constructor applies id, class and tagname', () => {
    resetLegacyRuntime();
    const {Container} = setupContainer();
    const container = new Container({id: 'c1', class: 'extra', tagname: 'section'});

    assert.equal(container.wrapperElement.tagName, 'SECTION');
    assert.equal(container.wrapperElement.getAttribute('id'), 'c1');
    assert.equal(container.wrapperElement.classList.contains('se-container'), true);
    assert.equal(container.wrapperElement.classList.contains('extra'), true);
    assert.deepEqual(container.children, []);
});

test('StyledElements.Container has supports StyledElement children and raw nodes', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    const styledChild = new StyledElement();
    const rawNode = document.createElement('span');

    container.appendChild(styledChild);
    container.appendChild(rawNode);

    assert.equal(container.has(styledChild), true);
    assert.equal(container.has(rawNode), true);
    assert.equal(container.has(document.createElement('div')), false);
});

test('StyledElements.Container appendChild tracks StyledElement children and keeps DOM order', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    const first = new StyledElement();
    const second = new StyledElement();

    container.appendChild(first);
    container.appendChild(second, first.get());

    assert.deepEqual(container.children, [second, first]);
});

test('StyledElements.Container prependChild supports text and styled children', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    const styled = new StyledElement();

    container.prependChild(styled);
    container.prependChild('hello');

    assert.equal(container.get().firstChild.textContent, 'hello');
    assert.deepEqual(container.children, [styled]);
});

test('StyledElements.Container removeChild removes StyledElement and raw children', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    const styled = new StyledElement();
    const raw = document.createElement('span');

    container.appendChild(styled);
    container.appendChild(raw);
    container.removeChild(styled);
    container.removeChild(raw);

    assert.deepEqual(container.children, []);
    assert.equal(container.get().childNodes.length, 0);
});

test('StyledElements.Container repaint delegates to child repaint methods', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    const child = new StyledElement();
    child.repaintCalls = 0;
    child.repaint = function (temporal) {
        this.repaintCalls += temporal ? 1 : 0;
    };
    container.appendChild(child);

    container.repaint(true);

    assert.equal(child.repaintCalls, 1);
});

test('StyledElements.Container clear removes children and resets scroll positions', () => {
    resetLegacyRuntime();
    const {Container, StyledElement} = setupContainer();
    const container = new Container({});
    container.appendChild(new StyledElement());
    container.get().scrollTop = 10;
    container.get().scrollLeft = 20;

    const result = container.clear();

    assert.equal(result, container);
    assert.deepEqual(container.children, []);
    assert.equal(container.get().scrollTop, 0);
    assert.equal(container.get().scrollLeft, 0);
});

test('StyledElements.Container clear preserves disabled layer if present', () => {
    resetLegacyRuntime();
    const {Container} = setupContainer();
    const container = new Container({});
    container._onenabled(false);

    container.clear();

    assert.equal(container.get().childNodes.length, 1);
});

test('StyledElements.Container text getter/setter works', () => {
    resetLegacyRuntime();
    const {Container} = setupContainer();
    const container = new Container({});

    container.text('abc');

    assert.equal(container.text(), 'abc');
});

test('StyledElements.Container isDisabled reflects enabled state', () => {
    resetLegacyRuntime();
    const {Container} = setupContainer();
    const container = new Container({});
    container.enabled = true;
    assert.equal(container.isDisabled(), false);
    container.enabled = false;
    assert.equal(container.isDisabled(), true);
});

test('StyledElements.Container _onenabled toggles disabled layer', () => {
    resetLegacyRuntime();
    const {Container} = setupContainer();
    const container = new Container({});

    container._onenabled(false);
    assert.equal(container.get().childNodes.length, 1);
    container._onenabled(true);
    assert.equal(container.get().childNodes.length, 0);
});
