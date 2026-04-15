const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupAccordion = () => {
    global.CSSPrimitiveValue = {CSS_PX: 5};

    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this._usableHeight = null;
            this.destroyCalls = 0;
        }

        _getUsableHeight() {
            return this._usableHeight;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class Expander {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.listeners = {};
            this.setExpandedCalls = [];
            this.repaintCalls = 0;
            this.destroyCalls = 0;
        }

        insertInto(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        setExpanded(value) {
            this.setExpandedCalls.push(value);
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {
        StyledElement,
        Expander,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            appendWord(initial, word) {
                return `${initial ? `${initial} ` : ''}${word}`;
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Accordion.js');
    return StyledElements.Accordion;
};

test('StyledElements.Accordion constructor applies defaults and class names', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({class: 'extra'});

    assert.equal(accordion.exclusive, true);
    assert.equal(accordion.full, true);
    assert.equal(accordion.children.length, 0);
    assert.equal(accordion.wrapperElement.className.includes('styled_accordion'), true);
    assert.equal(accordion.wrapperElement.className.includes('extra'), true);
});

test('StyledElements.Accordion createContainer expands first container by default', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({});

    const expander = accordion.createContainer({});

    assert.equal(accordion.children.length, 1);
    assert.equal(accordion.currentContainer, undefined);
    assert.deepEqual(expander.setExpandedCalls, [true]);
});

test('StyledElements.Accordion exclusive mode collapses previous container on expand', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({exclusive: true});
    const first = accordion.createContainer({});
    const second = accordion.createContainer({});
    accordion.currentContainer = first;
    accordion.repaintCalls = 0;
    accordion.repaint = function () {
        this.repaintCalls += 1;
    };

    second.listeners.expandChange(second, true);

    assert.equal(accordion.currentContainer, second);
    assert.equal(first.setExpandedCalls.includes(false), true);
    assert.equal(first.wrapperElement.style.height, '');
    assert.equal(accordion.repaintCalls, 1);
});

test('StyledElements.Accordion exclusive mode clears current container when collapsed', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({exclusive: true});
    const first = accordion.createContainer({});
    accordion.currentContainer = first;

    first.listeners.expandChange(first, false);

    assert.equal(accordion.currentContainer, null);
    assert.equal(first.wrapperElement.style.height, '');
});

test('StyledElements.Accordion non-exclusive full mode repaints on expand changes', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({exclusive: false, full: true});
    const expander = accordion.createContainer({});
    accordion.repaintCalls = 0;
    accordion.repaint = function () {
        this.repaintCalls += 1;
    };

    expander.listeners.expandChange(true);

    assert.equal(accordion.repaintCalls, 1);
});

test('StyledElements.Accordion repaint exits early when usable height is null', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({});
    accordion._usableHeight = null;
    accordion.currentContainer = accordion.createContainer({});

    assert.equal(accordion.repaint(), undefined);
});

test('StyledElements.Accordion repaint exits early when there is no current container', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({});
    accordion._usableHeight = 200;
    accordion.currentContainer = null;

    assert.equal(accordion.repaint(), undefined);
});

test('StyledElements.Accordion repaint updates current container height and delegates repaint', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({});
    const first = accordion.createContainer({});
    const second = accordion.createContainer({});
    accordion.currentContainer = second;
    accordion._usableHeight = 300;
    first.wrapperElement.offsetHeight = 40;

    accordion.repaint('temporal');

    assert.equal(second.wrapperElement.style.height, '260px');
    assert.equal(second.repaintCalls, 1);
});

test('StyledElements.Accordion destroy destroys children and delegates to parent destroy', () => {
    resetLegacyRuntime();
    const Accordion = setupAccordion();
    const accordion = new Accordion({});
    const first = accordion.createContainer({});
    const second = accordion.createContainer({});

    accordion.destroy();

    assert.equal(first.destroyCalls, 1);
    assert.equal(second.destroyCalls, 1);
    assert.equal(accordion.children, null);
    assert.equal(accordion.destroyCalls, 1);
});
