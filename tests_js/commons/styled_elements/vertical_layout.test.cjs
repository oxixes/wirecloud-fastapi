const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupVerticalLayout = () => {
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

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/VerticalLayout.js');
    return StyledElements.VerticalLayout;
};

test('StyledElements.VerticalLayout creates wrapper and region containers', () => {
    resetLegacyRuntime();
    const VerticalLayout = setupVerticalLayout();
    const layout = new VerticalLayout({ class: 'custom' });

    assert.equal(layout.wrapperElement.className, 'custom se-vertical-layout');
    assert.equal(layout.north.options.class, 'se-vl-north-container');
    assert.equal(layout.center.options.class, 'se-vl-center-container');
    assert.equal(layout.south.options.class, 'se-vl-south-container');
});

test('StyledElements.VerticalLayout repaint delegates to all child containers', () => {
    resetLegacyRuntime();
    const VerticalLayout = setupVerticalLayout();
    const layout = new VerticalLayout();

    layout.repaint(true);

    assert.equal(layout.north.repaintArgs, true);
    assert.equal(layout.center.repaintArgs, true);
    assert.equal(layout.south.repaintArgs, true);
});
