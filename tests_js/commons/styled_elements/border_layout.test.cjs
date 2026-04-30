const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupBorderLayout = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
        }
    }

    class Container extends StyledElement {
        constructor(options = {}) {
            super();
            this.wrapperElement = document.createElement('div');
            if (options.class) {
                this.wrapperElement.className = options.class;
            }
            this.repaintCalls = 0;
        }

        insertInto(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }

        repaint() {
            this.repaintCalls += 1;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            appendWord(initial, word) {
                return `${initial ? `${initial} ` : ''}${word}`;
            }
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/BorderLayout.js');
    return StyledElements.BorderLayout;
};

test('StyledElements.BorderLayout builds fixed region containers', () => {
    resetLegacyRuntime();
    const BorderLayout = setupBorderLayout();
    const layout = new BorderLayout({class: 'extra'});

    assert.equal(layout.wrapperElement.className.includes('se-border-layout'), true);
    assert.equal(layout.wrapperElement.className.includes('extra'), true);
    assert.equal(layout.north != null, true);
    assert.equal(layout.west != null, true);
    assert.equal(layout.center != null, true);
    assert.equal(layout.east != null, true);
    assert.equal(layout.south != null, true);
});

test('StyledElements.BorderLayout repaint updates geometry and repaints all regions', () => {
    resetLegacyRuntime();
    const BorderLayout = setupBorderLayout();
    const layout = new BorderLayout({});
    layout.wrapperElement.offsetWidth = 300;
    layout.wrapperElement.offsetHeight = 200;
    layout.north.wrapperElement.offsetHeight = 20;
    layout.south.wrapperElement.offsetHeight = 30;
    layout.west.wrapperElement.offsetWidth = 40;
    layout.east.wrapperElement.offsetWidth = 50;

    layout.repaint('temporal');

    assert.equal(layout.west.wrapperElement.style.top, '20px');
    assert.equal(layout.west.wrapperElement.style.height, '150px');
    assert.equal(layout.center.wrapperElement.style.width, '210px');
    assert.equal(layout.center.wrapperElement.style.left, '40px');
    assert.equal(layout.east.wrapperElement.style.left, '250px');
    assert.equal(layout.south.wrapperElement.style.top, '170px');
    assert.equal(layout.north.repaintCalls, 1);
    assert.equal(layout.west.repaintCalls, 1);
    assert.equal(layout.center.repaintCalls, 1);
    assert.equal(layout.east.repaintCalls, 1);
    assert.equal(layout.south.repaintCalls, 1);
});

test('StyledElements.BorderLayout repaint clamps negative center area to zero', () => {
    resetLegacyRuntime();
    const BorderLayout = setupBorderLayout();
    const layout = new BorderLayout({});
    layout.wrapperElement.offsetWidth = 40;
    layout.wrapperElement.offsetHeight = 30;
    layout.north.wrapperElement.offsetHeight = 20;
    layout.south.wrapperElement.offsetHeight = 20;
    layout.west.wrapperElement.offsetWidth = 30;
    layout.east.wrapperElement.offsetWidth = 30;

    layout.repaint();

    assert.equal(layout.center.wrapperElement.style.height, '0px');
    assert.equal(layout.center.wrapperElement.style.width, '0px');
});

test('StyledElements.BorderLayout deprecated getters return matching containers', () => {
    resetLegacyRuntime();
    const BorderLayout = setupBorderLayout();
    const layout = new BorderLayout({});

    assert.equal(layout.getNorthContainer(), layout.north);
    assert.equal(layout.getWestContainer(), layout.west);
    assert.equal(layout.getCenterContainer(), layout.center);
    assert.equal(layout.getEastContainer(), layout.east);
    assert.equal(layout.getSouthContainer(), layout.south);
});
