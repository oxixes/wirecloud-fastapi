const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupAddon = () => {
    class Container {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.enabled = true;
            this.destroyCalls = 0;
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class Tooltip {
        constructor(options) {
            this.options = options;
            this.boundElements = [];
            this.destroyCalls = 0;
            Tooltip.instances.push(this);
        }

        bind(element) {
            this.boundElements.push(element);
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }
    Tooltip.instances = [];

    global.StyledElements = {
        Container,
        Tooltip,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            stopPropagationListener: () => {}
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Addon.js');
    return StyledElements.Addon;
};

test('StyledElements.Addon initializes label, class and listeners by default', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon({
        text: 'A',
        class: 'extra'
    });

    assert.equal(addon.wrapperElement.tagName, 'SPAN');
    assert.equal(addon.wrapperElement.classList.contains('se-add-on'), true);
    assert.equal(addon.wrapperElement.classList.contains('extra'), true);
    assert.equal(addon.wrapperElement.textContent, 'A');
    assert.equal(addon.wrapperElement.listeners.click.length, 1);
});

test('StyledElements.Addon can disable listener registration', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon({listeners: false});

    assert.equal(addon.wrapperElement.listeners.click, undefined);
    assert.equal(addon.wrapperElement.listeners.mousedown, undefined);
});

test('StyledElements.Addon setLabel updates text and is chainable', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon();

    const result = addon.setLabel('new-label');

    assert.equal(result, addon);
    assert.equal(addon.wrapperElement.textContent, 'new-label');
});

test('StyledElements.Addon setTitle creates and updates tooltip for non-empty titles', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon();

    addon.setTitle('hello');
    const tooltip = StyledElements.Tooltip.instances[0];
    addon.setTitle('world');

    assert.equal(StyledElements.Tooltip.instances.length, 1);
    assert.equal(tooltip.boundElements[0], addon.wrapperElement);
    assert.equal(tooltip.options.content, 'world');
});

test('StyledElements.Addon setTitle destroys tooltip when title becomes empty', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon();

    addon.setTitle('tooltip');
    const tooltip = StyledElements.Tooltip.instances[0];
    addon.setTitle('');

    assert.equal(addon.setTitle(null), addon);
    assert.equal(tooltip.destroyCalls, 1);
});

test('StyledElements.Addon click focuses assigned input only when enabled', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon();
    const relatedInput = {
        focusCalls: 0,
        focus() {
            this.focusCalls += 1;
        }
    };
    addon.assignInput(relatedInput);

    addon.wrapperElement.dispatchEvent({
        type: 'click',
        preventDefault() {},
        stopPropagation() {}
    });
    addon.enabled = false;
    addon.wrapperElement.dispatchEvent({
        type: 'click',
        preventDefault() {},
        stopPropagation() {}
    });

    assert.equal(relatedInput.focusCalls, 1);
});

test('StyledElements.Addon destroy removes listeners and delegates to container destroy', () => {
    resetLegacyRuntime();
    const Addon = setupAddon();
    const addon = new Addon();

    addon.destroy();

    assert.equal(addon._clickCallback, undefined);
    assert.equal(addon.destroyCalls, 1);
});
