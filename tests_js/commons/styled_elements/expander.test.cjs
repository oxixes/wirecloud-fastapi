const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupExpander = () => {
    global.CSSPrimitiveValue = {CSS_PX: 5};

    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.dispatched = [];
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        removeClassName(className) {
            this.wrapperElement.classList.remove(className);
            return this;
        }

        hasClassName(className) {
            return this.wrapperElement.classList.contains(className);
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }
    }

    class Container extends StyledElement {
        constructor(options = {}) {
            super();
            this.wrapperElement = document.createElement('div');
            if (options.class) {
                this.wrapperElement.className = options.class;
            }
            this.children = [];
            this.repaintCalls = 0;
            this.removeCalls = 0;
            this.clearCalls = 0;
        }

        insertInto(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }

        appendChild(element) {
            this.children.push(element);
            return this;
        }

        removeChild(element) {
            this.removeCalls += 1;
            this.children = this.children.filter((item) => item !== element);
        }

        clear() {
            this.clearCalls += 1;
            this.children = [];
        }

        repaint() {
            this.repaintCalls += 1;
        }
    }

    class ToggleButton extends StyledElement {
        constructor() {
            super();
            this.listeners = {};
            this._active = false;
            this.insertCalls = 0;
        }

        insertInto(parentNode) {
            this.insertCalls += 1;
            parentNode.appendChild(this.wrapperElement);
            return this;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        get active() {
            return this._active;
        }

        set active(value) {
            this._active = value;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        ToggleButton,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            appendWord: (left, right) => `${left} ${right}`.trim(),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Expander.js');
    return StyledElements.Expander;
};

test('StyledElements.Expander validates constructor options for toggling mechanism', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();

    assert.throws(() => new Expander({expandButton: false, listenOnTitle: false}), TypeError);
});

test('StyledElements.Expander constructor initializes header, title and content areas', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({title: 'Title', state: 'primary'});
    const header = expander.wrapperElement.childNodes[0];

    assert.equal(expander.wrapperElement.classList.contains('panel-primary'), true);
    assert.equal(header.getAttribute('role'), 'button');
    assert.equal(header.getAttribute('aria-expanded'), 'false');
    assert.equal(header.getAttribute('aria-controls') != null, true);
    assert.equal(expander.titleContainer.children[0].textContent, 'Title');
});

test('StyledElements.Expander skips state class when state is blank', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({state: '  '});

    assert.equal(expander.wrapperElement.classList.contains('panel-  '), false);
});

test('StyledElements.Expander supports constructors without toggle button', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({expandButton: false, listenOnTitle: true});

    assert.equal(expander.toggleButton, null);
});

test('StyledElements.Expander toggle button click toggles expansion state', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});

    expander.toggleButton.listeners.click();

    assert.equal(expander.isExpanded(), true);
    assert.equal(expander.dispatched.at(-1).name, 'expandChange');
    assert.equal(expander.dispatched.at(-1).args[0], true);
});

test('StyledElements.Expander title click toggles expansion when listenOnTitle is enabled', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({listenOnTitle: true});
    const header = expander.wrapperElement.childNodes[0];

    header.dispatchEvent({type: 'click'});

    assert.equal(expander.isExpanded(), true);
});

test('StyledElements.Expander setExpanded updates classes, aria, and toggle button active state', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});
    const header = expander.wrapperElement.childNodes[0];
    expander.wrapperElement.querySelector = (selector) => selector === '.panel-heading' ? header : null;

    expander.setExpanded(true);
    assert.equal(expander.isExpanded(), true);
    assert.equal(expander.toggleButton.active, true);
    assert.equal(header.getAttribute('aria-expanded'), 'true');

    expander.setExpanded(false);
    assert.equal(expander.isExpanded(), false);
    assert.equal(expander.contentContainer.wrapperElement.style.height, '');
    assert.equal(expander.toggleButton.active, false);
    assert.equal(header.getAttribute('aria-expanded'), 'false');
});

test('StyledElements.Expander setExpanded is no-op when requested state is unchanged', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});

    expander.setExpanded(false);

    assert.equal(expander.dispatched.length, 0);
});

test('StyledElements.Expander repaint returns early when collapsed or height is unavailable', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});

    assert.equal(expander.repaint(), undefined);
    expander.setExpanded(true);
    expander.wrapperElement.clientHeight = null;
    assert.equal(expander.repaint(), undefined);
});

test('StyledElements.Expander repaint adjusts content height and repaints content container', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});
    expander.setExpanded(true);
    expander.wrapperElement.clientHeight = 200;
    expander.titleContainer.wrapperElement.offsetHeight = 40;

    expander.repaint('temporal');
    assert.equal(expander.contentContainer.wrapperElement.style.height, '160px');
    assert.equal(expander.contentContainer.repaintCalls, 1);

    expander.wrapperElement.clientHeight = 10;
    expander.titleContainer.wrapperElement.offsetHeight = 40;
    expander.repaint();
    assert.equal(expander.contentContainer.wrapperElement.style.height, '0px');
});

test('StyledElements.Expander delegates content container helper methods', () => {
    resetLegacyRuntime();
    const Expander = setupExpander();
    const expander = new Expander({});
    const child = {id: 'x'};

    assert.equal(expander.getTitleContainer(), expander.titleContainer);
    expander.appendChild(child);
    assert.deepEqual(expander.contentContainer.children, [child]);
    expander.removeChild(child);
    assert.equal(expander.contentContainer.removeCalls, 1);
    expander.clear();
    assert.equal(expander.contentContainer.clearCalls, 1);
});
