const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPanel = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.events = {};
            this.dispatched = [];
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        hasClassName(className) {
            return this.wrapperElement.classList.contains(className);
        }

        toggleClassName(className, value) {
            this.wrapperElement.classList.toggle(className, !!value);
            return this;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
            return this;
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
        }

        insertInto(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }

        appendChild(value) {
            this.children.push(value);
            return this;
        }

        clear() {
            this.children = [];
            return this;
        }

        text() {
            if (this.children.length === 0) {
                return '';
            }
            return String(this.children.at(-1));
        }

        repaint() {
            this.repaintCalls = (this.repaintCalls || 0) + 1;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Panel.js');
    return StyledElements.Panel;
};

test('StyledElements.Panel builds heading/body and applies state/selectable/classes', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({
        state: 'primary',
        selectable: true,
        class: 'extra-class',
    });

    assert.equal(panel.wrapperElement.classList.contains('panel-primary'), true);
    assert.equal(panel.wrapperElement.classList.contains('panel-selectable'), true);
    assert.equal(panel.wrapperElement.classList.contains('extra-class'), true);
    assert.equal(panel.body != null, true);
});

test('StyledElements.Panel supports noBody option', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({noBody: true});

    assert.equal(panel.body, undefined);
});

test('StyledElements.Panel setTitle initializes and updates title container', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});

    const result = panel.setTitle('My Title');

    assert.equal(result, panel);
    assert.equal(panel.heading.title != null, true);
    assert.equal(panel.title, 'My Title');
});

test('StyledElements.Panel setSubtitle initializes and updates subtitle container', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});

    const result = panel.setSubtitle('Subtitle');

    assert.equal(result, panel);
    assert.equal(panel.heading.subtitle != null, true);
    assert.equal(panel.heading.subtitle.text(), 'Subtitle');
});

test('StyledElements.Panel constructor appends button container when buttons are provided', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({buttons: ['a', 'b']});

    assert.equal(panel.buttons != null, true);
    assert.deepEqual(panel.buttons.children, ['a', 'b']);
});

test('StyledElements.Panel constructor initializes title and subtitle when provided', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({
        title: 'Initial title',
        subtitle: 'Initial subtitle',
    });

    assert.equal(panel.title, 'Initial title');
    assert.equal(panel.heading.subtitle.text(), 'Initial subtitle');
});

test('StyledElements.Panel clear delegates to body when present', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});
    panel.body.appendChild('value');

    const result = panel.clear();

    assert.equal(result, panel);
    assert.deepEqual(panel.body.children, []);
});

test('StyledElements.Panel clear is safe without body', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({noBody: true});

    assert.equal(panel.clear(), panel);
});

test('StyledElements.Panel active property toggles class and triggers _onactive only on changes', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});
    panel.onactiveCalls = [];
    panel._onactive = function (active) {
        this.onactiveCalls.push(active);
    };

    panel.active = true;
    panel.active = true;
    panel.active = false;

    assert.equal(panel.hasClassName('active'), false);
    assert.deepEqual(panel.onactiveCalls, [true, false]);
});

test('StyledElements.Panel _onclick stops propagation and dispatches click event', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});
    const event = {
        stopped: false,
        stopPropagation() {
            this.stopped = true;
        }
    };

    panel._onclick(event);

    assert.equal(event.stopped, true);
    assert.equal(panel.dispatched[0].name, 'click');
    assert.equal(panel.dispatched[0].args[0], event);
});

test('StyledElements.Panel _onactive default implementation is a safe no-op', () => {
    resetLegacyRuntime();
    const Panel = setupPanel();
    const panel = new Panel({});

    assert.equal(panel._onactive(true), undefined);
});
