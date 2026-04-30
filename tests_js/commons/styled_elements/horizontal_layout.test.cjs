const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupHorizontalLayout = () => {
    class StyledElement {
        constructor(events) {
            this.events = events;
        }
    }

    class Container {
        constructor(options) {
            this.options = options;
        }

        insertInto(parent) {
            parent.appendChild(document.createElement('section'));
            this.parent = parent;
        }

        repaint(temporal) {
            this.repaintArgs = temporal;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            appendWord: (className, word) => className ? `${className} ${word}` : word,
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/HorizontalLayout.js');
    return StyledElements.HorizontalLayout;
};

test('StyledElements.HorizontalLayout creates wrapper and west/center/east containers', () => {
    resetLegacyRuntime();
    const HorizontalLayout = setupHorizontalLayout();
    const layout = new HorizontalLayout({ class: 'custom' });

    assert.equal(layout.wrapperElement.className, 'custom se-horizontal-layout');
    assert.equal(layout.west.options.class, 'se-hl-west-container');
    assert.equal(layout.center.options.class, 'se-hl-center-container');
    assert.equal(layout.east.options.class, 'se-hl-east-container');
});

test('StyledElements.HorizontalLayout repaint delegates to all child containers', () => {
    resetLegacyRuntime();
    const HorizontalLayout = setupHorizontalLayout();
    const layout = new HorizontalLayout();

    layout.repaint(true);

    assert.equal(layout.west.repaintArgs, true);
    assert.equal(layout.center.repaintArgs, true);
    assert.equal(layout.east.repaintArgs, true);
});

test('StyledElements.HorizontalLayout deprecated getters return matching containers', () => {
    resetLegacyRuntime();
    const HorizontalLayout = setupHorizontalLayout();
    const layout = new HorizontalLayout();

    assert.equal(layout.getWestContainer(), layout.west);
    assert.equal(layout.getCenterContainer(), layout.center);
    assert.equal(layout.getEastContainer(), layout.east);
});
