const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupToggleButton = () => {
    class Event {
        constructor(context) {
            this.context = context;
        }
    }

    class Button {
        constructor(options) {
            this.options = options;
            this.enabled = true;
            this.events = { click: true };
            this.wrapperElement = document.createElement('button');
            this.classNames = new Set();
            this.dispatched = [];
        }

        hasClassName(name) {
            return this.classNames.has(name);
        }

        toggleClassName(name, value) {
            if (value) {
                this.classNames.add(name);
            } else {
                this.classNames.delete(name);
            }
        }

        dispatchEvent(name, value) {
            this.dispatched.push({ name, value });
        }
    }

    global.StyledElements = {
        Button,
        Event,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects)
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/ToggleButton.js');
    return StyledElements.ToggleButton;
};

test('StyledElements.ToggleButton initializes with default inactive state', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({});

    assert.equal(button.active, false);
    assert.equal(button.wrapperElement.getAttribute('aria-pressed'), 'false');
});

test('StyledElements.ToggleButton supports initiallyChecked option', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({ initiallyChecked: true });

    assert.equal(button.active, true);
    assert.equal(button.wrapperElement.getAttribute('aria-pressed'), 'true');
});

test('StyledElements.ToggleButton active setter toggles class and dispatches event', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({});

    button.active = true;

    assert.equal(button.active, true);
    assert.equal(button.wrapperElement.getAttribute('aria-pressed'), 'true');
    assert.deepEqual(button.dispatched.at(-1), { name: 'active', value: true });
});

test('StyledElements.ToggleButton active setter is no-op when value does not change', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({ initiallyChecked: false });
    const previousDispatchCount = button.dispatched.length;

    button.active = false;

    assert.equal(button.dispatched.length, previousDispatchCount);
});

test('StyledElements.ToggleButton _clickCallback stops propagation and triggers click', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({});
    let stopped = 0;

    button._clickCallback({
        stopPropagation() {
            stopped += 1;
        }
    });

    assert.equal(stopped, 1);
    assert.equal(button.dispatched.some((entry) => entry.name === 'click'), true);
});

test('StyledElements.ToggleButton click toggles active only when enabled', () => {
    resetLegacyRuntime();
    const ToggleButton = setupToggleButton();
    const button = new ToggleButton({});

    button.enabled = false;
    button.click();
    assert.equal(button.active, false);

    button.enabled = true;
    button.click();
    assert.equal(button.active, true);
});
