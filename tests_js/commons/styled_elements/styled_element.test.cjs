const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const createTestElementClass = () => class TestElement extends StyledElements.StyledElement {

    constructor() {
        super(['custom']);
        this.wrapperElement = document.createElement('div');
        this.enabledTransitions = [];
        this.hiddenTransitions = [];
    }

    _onenabled(value) {
        this.enabledTransitions.push(value);
    }

    _onhidden(value) {
        this.hiddenTransitions.push(value);
    }

};

test.beforeEach(() => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    StyledElements.Fragment = class Fragment {
        constructor(elements) {
            this.elements = elements;
        }
    };
});

test('StyledElement base no-op hooks are callable', () => {
    const element = new StyledElements.StyledElement();
    element.wrapperElement = document.createElement('div');
    assert.equal(element._onenabled(true), undefined);
    assert.equal(element._onhidden(false), undefined);
    element.enabled = true;
    element.hidden = false;
    element.disable();
    element.disable();
    element.enable();
    element.enable();
});

test('StyledElement manages classes, styles, visibility, and enabled state', () => {
    const TestElement = createTestElementClass();
    const element = new TestElement();
    const events = [];
    element.addEventListener('hide', () => events.push('hide'));
    element.addEventListener('show', () => events.push('show'));

    assert.equal(element.enabled, true);
    assert.equal(element.hidden, false);
    element.addClassName(null);
    element.addClassName('alpha beta');
    element.addClassName(['gamma']);
    assert.equal(element.hasClassName('alpha'), true);
    assert.equal(element.hasClassName('gamma'), true);

    element.toggleClassName('alpha');
    element.toggleClassName('zeta');
    element.toggleClassName('delta', true);
    element.toggleClassName('beta', false);
    assert.throws(() => element.toggleClassName(null), /split is not a function/);
    element.toggleClassName('   ');
    element.replaceClassName('gamma', 'epsilon');
    assert.equal(element.hasClassName('alpha'), false);
    assert.equal(element.hasClassName('zeta'), true);
    assert.equal(element.hasClassName('delta'), true);
    assert.equal(element.hasClassName('beta'), false);
    assert.equal(element.hasClassName('epsilon'), true);

    element.style('width', '10px');
    element.style('border', null);
    element.style({ height: '20px', display: 'block' });
    assert.equal(element.style('width'), '10px');
    assert.equal(element.style('height'), '20px');
    assert.equal(element.style('border'), '');

    element.hide();
    element.hide();
    element.show();
    element.show();
    assert.deepEqual(events, ['hide', 'show']);
    assert.deepEqual(element.hiddenTransitions, [true, false]);

    element.disable();
    element.enable();
    element.setDisabled(true);
    element.setDisabled(false);
    assert.deepEqual(element.enabledTransitions, [false, true, false, true]);
    assert.equal(element.enabled, true);

    element.removeClassName('delta epsilon');
    element.removeClassName(['zeta']);
    element.toggleClassName([], true);
    element.removeClassName();
    assert.equal(element.get().className, '');
    assert.equal(element.hasClassName(null), false);
    assert.equal(element.repaint(), element);
});

test('StyledElement appends, prepends, removes, and resolves parent nodes', () => {
    const TestElement = createTestElementClass();
    const parentNode = document.createElement('section');
    const childA = new TestElement();
    const childB = new TestElement();
    const childC = new TestElement();
    const childD = new TestElement();

    childA.appendTo(parentNode);
    childB.prependTo(parentNode);
    childD.insertInto(parentNode);
    childC.insertInto(parentNode, childA.get());
    assert.deepEqual(parentNode.childNodes, [childB.get(), childC.get(), childA.get(), childD.get()]);
    assert.equal(childA.parent(), parentNode);

    childC.remove();
    assert.deepEqual(parentNode.childNodes, [childB.get(), childA.get(), childD.get()]);

    const styledParent = {
        appended: [],
        prepended: [],
        removed: [],
        appendChild(child, ref) {
            this.appended.push({ child, ref });
        },
        prependChild(child, ref) {
            this.prepended.push({ child, ref });
        },
        removeChild(child) {
            this.removed.push(child);
        }
    };
    Object.setPrototypeOf(styledParent, StyledElements.StyledElement.prototype);
    styledParent.wrapperElement = document.createElement('div');

    childA.parentElement = styledParent;
    childA.remove();
    childA.appendTo(styledParent);
    childA.prependTo(styledParent, childB);
    assert.equal(styledParent.removed[0], childA);
    assert.equal(styledParent.appended[0].child, childA);
    assert.equal(styledParent.prepended[0].ref, childB);

    const plainStyledParent = new StyledElements.StyledElement();
    plainStyledParent.wrapperElement = document.createElement('div');
    const bareAppendChild = new TestElement();
    const barePrependChild = new TestElement();
    const bareRemoveChild = new TestElement();
    bareAppendChild.appendTo(plainStyledParent);
    barePrependChild.prependTo(plainStyledParent);
    bareRemoveChild.appendTo(plainStyledParent);
    bareRemoveChild.parentElement = plainStyledParent;
    bareRemoveChild.remove();
    assert.equal(plainStyledParent.get().childNodes.includes(bareRemoveChild.get()), false);
});

test('StyledElement computes usable dimensions and destroy clears event state', () => {
    const TestElement = createTestElementClass();
    const parent = document.createElement('div');
    const element = new TestElement();
    parent.offsetHeight = 100;
    parent.offsetWidth = 80;
    parent.style.display = 'block';
    parent.appendChild(element.get());
    element.get().offsetHeight = 10;
    element.get().offsetWidth = 20;

    const originalGetComputedStyle = document.defaultView.getComputedStyle;
    document.defaultView.getComputedStyle = (target) => ({
        getPropertyValue(name) {
            return target.style[name] || '';
        },
        getPropertyCSSValue(name) {
            const map = {
                display: target.style.display ? { getFloatValue: () => 0 } : null,
                'padding-top': { getFloatValue: () => 1 },
                'padding-bottom': { getFloatValue: () => 2 },
                'padding-left': { getFloatValue: () => 3 },
                'padding-right': { getFloatValue: () => 4 },
                'border-top-width': { getFloatValue: () => 5 },
                'border-bottom-width': { getFloatValue: () => 6 },
                'margin-top': { getFloatValue: () => 7 },
                'margin-bottom': { getFloatValue: () => 8 },
            };
            return map[name] ?? { getFloatValue: () => 0 };
        }
    });

    assert.equal(element._getUsableHeight(), 100 - 1 - 2 - 1 - 2 - 5 - 6 - 7 - 8);
    assert.equal(element._getUsableWidth(), 80 - 3 - 4 - 3 - 4);
    assert.deepEqual(element.getBoundingClientRect(), { top: 0, left: 0, width: 20, height: 10 });

    const detached = new TestElement();
    assert.equal(detached._getUsableHeight(), null);
    assert.equal(detached._getUsableWidth(), null);
    document.defaultView.getComputedStyle = () => ({
        getPropertyValue() {
            return '';
        },
        getPropertyCSSValue() {
            return null;
        }
    });
    parent.appendChild(detached.get());
    assert.equal(detached._getUsableHeight(), null);
    detached.parentElement = { get() { return parent; } };
    assert.equal(detached.parent(), parent);

    document.defaultView.getComputedStyle = originalGetComputedStyle;
    element.destroy();
    assert.equal(element.events, null);
});
