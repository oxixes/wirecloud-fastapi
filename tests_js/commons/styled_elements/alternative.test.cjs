const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupAlternative = () => {
    class Container {
        constructor(options, events) {
            this.options = options;
            this.events = events;
            this.hidden = false;
            this.repaintCalls = [];
        }

        addClassName(name) {
            this.lastClassName = name;
        }

        _onhidden(hidden) {
            this.hidden = hidden;
            return `base:${hidden}`;
        }

        repaint(temporal) {
            this.repaintCalls.push(temporal);
        }

        show() {
            this.hidden = false;
            return this;
        }

        hide() {
            this.hidden = true;
            return this;
        }
    }

    global.StyledElements = {
        Container,
        Utils: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Alternative.js');
    return StyledElements.Alternative;
};

test('StyledElements.Alternative stores id and starts hidden', () => {
    resetLegacyRuntime();
    const Alternative = setupAlternative();
    const alt = new Alternative(5, { class: 'x' });

    assert.equal(alt.altId, 5);
    assert.equal(alt.lastClassName, 'hidden');
});

test('StyledElements.Alternative _onhidden repaints when becoming visible', () => {
    resetLegacyRuntime();
    const Alternative = setupAlternative();
    const alt = new Alternative(1);

    const result = alt._onhidden(false);

    assert.deepEqual(alt.repaintCalls, [false]);
    assert.equal(result, 'base:false');
});

test('StyledElements.Alternative _onhidden does not repaint when hidden', () => {
    resetLegacyRuntime();
    const Alternative = setupAlternative();
    const alt = new Alternative(1);

    alt._onhidden(true);

    assert.deepEqual(alt.repaintCalls, []);
});

test('StyledElements.Alternative setVisible delegates to show/hide', () => {
    resetLegacyRuntime();
    const Alternative = setupAlternative();
    const alt = new Alternative(1);

    assert.equal(alt.setVisible(true), alt);
    assert.equal(alt.hidden, false);
    assert.equal(alt.setVisible(false), alt);
    assert.equal(alt.hidden, true);
});

test('StyledElements.Alternative isVisible reflects hidden state', () => {
    resetLegacyRuntime();
    const Alternative = setupAlternative();
    const alt = new Alternative(1);

    alt.hidden = false;
    assert.equal(alt.isVisible(), true);
    alt.hidden = true;
    assert.equal(alt.isVisible(), false);
});
