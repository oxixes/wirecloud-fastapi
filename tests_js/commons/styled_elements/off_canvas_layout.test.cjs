const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupOffCanvasLayout = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.dispatched = [];
        }

        hasClassName(className) {
            return this.wrapperElement.classList.contains(className);
        }

        toggleClassName(className, active) {
            this.wrapperElement.classList.toggle(className, active);
            return this;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
            return this;
        }

        show() {
            this.wrapperElement.style.display = '';
            return this;
        }

        hide() {
            this.wrapperElement.style.display = 'none';
            return this;
        }
    }

    class Container extends StyledElement {
        constructor(options = {}) {
            super();
            this.children = [];
            if (options.class) {
                this.wrapperElement.className = options.class;
            }
            this.repaintCalls = 0;
        }

        appendTo(node) {
            node.appendChild(this.wrapperElement);
            return this;
        }

        appendChild(child) {
            this.children.push(child);
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/OffCanvasLayout.js');
    return StyledElements.OffCanvasLayout;
};

const makeSidebarEntry = () => ({
    hideCalls: 0,
    showCalls: 0,
    hide() {
        this.hideCalls += 1;
        return this;
    },
    show() {
        this.showCalls += 1;
        return this;
    },
});

test('StyledElements.OffCanvasLayout constructor initializes wrappers and defaults', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();

    assert.equal(layout.wrapperElement.className, 'se-offcanvas left-sideway');
    assert.equal(layout.sidebar.wrapperElement.getAttribute('aria-hidden'), 'true');
    assert.equal(layout.index, -1);
    assert.equal(layout.slipped, false);
});

test('StyledElements.OffCanvasLayout constructor supports custom sideway', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout({sideway: 'right'});

    assert.equal(layout.wrapperElement.className, 'se-offcanvas right-sideway');
});

test('StyledElements.OffCanvasLayout appendChild stores first appended index', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();

    const first = makeSidebarEntry();
    const second = makeSidebarEntry();
    layout.appendChild(first);
    layout.appendChild(second);

    assert.equal(layout.index, 0);
    assert.equal(layout.sidebar.children.length, 2);
});

test('StyledElements.OffCanvasLayout slideIn without children toggles slipped and emits event', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();

    layout.slideIn();

    assert.equal(layout.slipped, true);
    assert.equal(layout.sidebar.wrapperElement.getAttribute('aria-hidden'), 'false');
    assert.equal(layout.dispatched.at(-1).name, 'slideIn');
    assert.equal(layout.dispatched.at(-1).args[0], undefined);
});

test('StyledElements.OffCanvasLayout slideIn hides all entries and shows selected index', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();
    const first = makeSidebarEntry();
    const second = makeSidebarEntry();
    layout.appendChild(first);
    layout.appendChild(second);

    layout.slideIn(1);

    assert.equal(layout.index, 1);
    assert.equal(first.hideCalls, 1);
    assert.equal(second.hideCalls, 1);
    assert.equal(first.showCalls, 0);
    assert.equal(second.showCalls, 1);
    assert.equal(layout.dispatched.at(-1).name, 'slideIn');
    assert.equal(layout.dispatched.at(-1).args[0], second);
});

test('StyledElements.OffCanvasLayout slideOut updates index optionally and emits event', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();
    layout.index = 0;

    layout.slideOut(3);

    assert.equal(layout.index, 3);
    assert.equal(layout.slipped, false);
    assert.equal(layout.sidebar.wrapperElement.getAttribute('aria-hidden'), 'true');
    assert.equal(layout.dispatched.at(-1).name, 'slideOut');
});

test('StyledElements.OffCanvasLayout repaint repaints content always and sidebar only when slipped', () => {
    resetLegacyRuntime();
    const OffCanvasLayout = setupOffCanvasLayout();
    const layout = new OffCanvasLayout();

    layout.repaint();
    assert.equal(layout.sidebar.repaintCalls, 0);
    assert.equal(layout.content.repaintCalls, 1);

    layout.slideIn();
    layout.repaint();
    assert.equal(layout.sidebar.repaintCalls, 1);
    assert.equal(layout.content.repaintCalls, 2);
});
