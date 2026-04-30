const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const createMeasuredTooltipElement = (withId = false) => {
    const element = document.createElement('div');
    if (withId) {
        element.setAttribute('id', 'existing-tooltip-id');
    }
    element.className = 'se-tooltip fade';
    element.offsetWidth = 40;
    element.offsetHeight = 20;
    element.style.left = '0px';
    element.style.top = '0px';
    element.getBoundingClientRect = () => {
        const left = parseInt(element.style.left || '0', 10);
        const top = parseInt(element.style.top || '0', 10);
        const width = element.offsetWidth;
        const height = element.offsetHeight;
        return {
            left,
            top,
            right: left + width,
            bottom: top + height,
            width,
            height,
        };
    };
    return element;
};

const setupTooltip = () => {
    class StyledElement {
        constructor() {
            this.repaintCalls = 0;
        }

        repaint() {
            this.repaintCalls += 1;
            return this;
        }
    }

    class GUIBuilder {
        parse() {
            return {
                elements: [GUIBuilder.factory()],
            };
        }
    }
    GUIBuilder.factory = () => createMeasuredTooltipElement(false);

    const fullscreenElement = document.createElement('div');
    fullscreenElement.getBoundingClientRect = () => ({
        left: 0,
        top: 0,
        right: 200,
        bottom: 200,
        width: 200,
        height: 200,
    });

    global.getComputedStyle = (element) => ({
        getPropertyValue(name) {
            return element.style[name] || '';
        },
    });

    global.StyledElements = {
        StyledElement,
        GUIBuilder,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
            getFullscreenElement: () => fullscreenElement,
        },
    };

    global.Wirecloud = {
        UserInterfaceManager: {
            registerCalls: 0,
            unregisterCalls: 0,
            _registerTooltip() {
                this.registerCalls += 1;
            },
            _unregisterTooltip() {
                this.unregisterCalls += 1;
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Tooltip.js');
    return {
        Tooltip: StyledElements.Tooltip,
        GUIBuilder: StyledElements.GUIBuilder,
        fullscreenElement,
    };
};

test('StyledElements.Tooltip constructor sets defaults and visible getter', () => {
    resetLegacyRuntime();
    const {Tooltip} = setupTooltip();
    const tooltip = new Tooltip();

    assert.equal(tooltip.options.content, '');
    assert.deepEqual(tooltip.options.placement, ['right', 'bottom', 'left', 'top']);
    assert.equal(tooltip.visible, false);
});

test('StyledElements.Tooltip bind attaches aria-describedby and listeners', () => {
    resetLegacyRuntime();
    const {Tooltip} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});
    const element = document.createElement('button');
    element.setAttribute('aria-describedby', 'existing-id');

    tooltip.bind(element);

    const describedBy = element.getAttribute('aria-describedby');
    assert.equal(describedBy.startsWith('existing-id '), true);
    assert.equal(element.listeners.focus.length > 0, true);
    assert.equal(element.listeners.blur.length > 0, true);
    assert.equal(element.listeners.mouseenter.length > 0, true);
    assert.equal(element.listeners.mouseleave.length > 0, true);
    assert.equal(element.listeners.click.length > 0, true);
});

test('StyledElements.Tooltip show creates tooltip, sets id, positions and registers in Wirecloud', () => {
    resetLegacyRuntime();
    const {Tooltip, fullscreenElement} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello', placement: ['top', 'right', 'bottom', 'left']});
    const ref = {
        left: 50,
        top: 60,
        width: 20,
        height: 10,
        right: 70,
        bottom: 70,
    };

    const result = tooltip.show(ref);

    assert.equal(result, tooltip);
    assert.equal(tooltip.visible, true);
    assert.equal(fullscreenElement.childNodes.length, 1);
    assert.equal(tooltip.options.content, 'hello');
    assert.equal(Wirecloud.UserInterfaceManager.registerCalls, 1);
    assert.equal(fullscreenElement.firstChild.getAttribute('id') != null, true);
});

test('StyledElements.Tooltip show reuses existing element and repaints', () => {
    resetLegacyRuntime();
    const {Tooltip} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});

    tooltip.show({left: 10, top: 10, width: 10, height: 10, right: 20, bottom: 20});
    const result = tooltip.show({left: 15, top: 15, width: 10, height: 10, right: 25, bottom: 25});

    assert.equal(result, tooltip);
    assert.equal(tooltip.repaintCalls, 1);
});

test('StyledElements.Tooltip show supports element references and aria-describedby update branches', () => {
    resetLegacyRuntime();
    const {Tooltip} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});
    const bound = document.createElement('div');
    const target = document.createElement('div');
    target.setAttribute('aria-describedby', 'existing-token');
    tooltip.bind(bound);

    target.getBoundingClientRect = () => ({
        left: 10,
        top: 10,
        right: 20,
        bottom: 20,
        width: 10,
        height: 10,
    });

    tooltip.show(target);
    const describedBy = target.getAttribute('aria-describedby');
    assert.equal(describedBy.includes('existing-token'), true);
    assert.equal(describedBy.split(' ').length >= 2, true);

    const targetWithoutDescribedBy = document.createElement('div');
    targetWithoutDescribedBy.getBoundingClientRect = () => ({
        left: 12,
        top: 12,
        right: 22,
        bottom: 22,
        width: 10,
        height: 10,
    });
    tooltip.show(targetWithoutDescribedBy);
    assert.equal(targetWithoutDescribedBy.getAttribute('aria-describedby') != null, true);

    tooltip.show(target);
    assert.equal(target.getAttribute('aria-describedby'), describedBy);
});

test('StyledElements.Tooltip show keeps parser-provided id when available', () => {
    resetLegacyRuntime();
    const {Tooltip, GUIBuilder, fullscreenElement} = setupTooltip();
    GUIBuilder.factory = () => createMeasuredTooltipElement(true);
    const tooltip = new Tooltip({content: 'hello'});

    tooltip.show({left: 0, top: 0, width: 10, height: 10, right: 10, bottom: 10});

    assert.equal(fullscreenElement.firstChild.getAttribute('id'), 'existing-tooltip-id');
});

test('StyledElements.Tooltip toggle switches between show and hide', () => {
    resetLegacyRuntime();
    const {Tooltip, fullscreenElement} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});
    const ref = {left: 0, top: 0, width: 10, height: 10, right: 10, bottom: 10};

    tooltip.toggle(ref);
    assert.equal(tooltip.visible, true);
    fullscreenElement.firstChild.style.opacity = '0';
    tooltip.toggle(ref);
    assert.equal(tooltip.visible, false);
});

test('StyledElements.Tooltip hide waits for transition end when opacity is not zero', () => {
    resetLegacyRuntime();
    const {Tooltip, fullscreenElement} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});

    tooltip.show({left: 10, top: 10, width: 10, height: 10, right: 20, bottom: 20});
    const element = fullscreenElement.firstChild;
    element.style.opacity = '1';
    tooltip.hide();

    assert.equal(tooltip.visible, true);
    element.dispatchEvent({type: 'transitionend'});
    assert.equal(tooltip.visible, false);
    assert.equal(Wirecloud.UserInterfaceManager.unregisterCalls, 1);
});

test('StyledElements.Tooltip hide forces removal when opacity is zero and handles no-op hide', () => {
    resetLegacyRuntime();
    const {Tooltip, fullscreenElement} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});

    const resultNoop = tooltip.hide();
    assert.equal(resultNoop, tooltip);

    tooltip.show({left: 10, top: 10, width: 10, height: 10, right: 20, bottom: 20});
    fullscreenElement.firstChild.style.opacity = '0';
    tooltip.hide();

    assert.equal(tooltip.visible, false);
    assert.equal(Wirecloud.UserInterfaceManager.unregisterCalls, 1);
});

test('StyledElements.Tooltip destroy delegates to hide', () => {
    resetLegacyRuntime();
    const {Tooltip, fullscreenElement} = setupTooltip();
    const tooltip = new Tooltip({content: 'hello'});

    tooltip.show({left: 10, top: 10, width: 10, height: 10, right: 20, bottom: 20});
    fullscreenElement.firstChild.style.opacity = '0';
    tooltip.destroy();

    assert.equal(tooltip.visible, false);
});

test('StyledElements.Tooltip fixPosition branch executes for overflowing placements', () => {
    resetLegacyRuntime();
    const {Tooltip, GUIBuilder, fullscreenElement} = setupTooltip();
    fullscreenElement.getBoundingClientRect = () => ({
        left: 0,
        top: 0,
        right: 20,
        bottom: 20,
        width: 20,
        height: 20,
    });
    GUIBuilder.factory = () => createMeasuredTooltipElement(false);
    const tooltip = new Tooltip({content: 'overflow', placement: ['bottom', 'left', 'right', 'top']});

    tooltip.show({left: 100, top: 100, width: 10, height: 10, right: 110, bottom: 110});

    const element = fullscreenElement.firstChild;
    assert.equal(element.style.left !== '0px' || element.style.top !== '0px', true);
});

test('StyledElements.Tooltip show falls back to document.body when fullscreen element is unavailable', () => {
    resetLegacyRuntime();
    const {Tooltip} = setupTooltip();
    StyledElements.Utils.getFullscreenElement = () => null;
    const tooltip = new Tooltip({content: 'fallback'});

    tooltip.show({left: 5, top: 5, width: 10, height: 10, right: 15, bottom: 15});

    assert.equal(document.body.childNodes.length, 1);
});
