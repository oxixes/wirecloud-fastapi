const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const createMeasuredPopoverElement = () => {
    const element = document.createElement('div');
    element.className = 'popover fade';
    element.offsetWidth = 320;
    element.offsetHeight = 260;
    element.style.left = '0px';
    element.style.top = '0px';
    element.style.opacity = '0';
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

const setupPopover = () => {
    bootstrapStyledElementsBase();

    class GUIBuilder {
        parse(template, data) {
            GUIBuilder.lastParse = { template, data };
            const element = createMeasuredPopoverElement();
            element.parsedTitle = data.title;
            element.parsedContent = data.content;
            return { elements: [element] };
        }
    }
    GUIBuilder.lastParse = null;

    const fullscreenElement = document.createElement('div');
    fullscreenElement.getBoundingClientRect = () => ({
        left: 0,
        top: 0,
        right: 200,
        bottom: 200,
        width: 200,
        height: 200,
    });

    global.StyledElements = Object.assign({}, StyledElements, {
        GUIBuilder,
    });

    global.getComputedStyle = (element) => ({
        getPropertyValue(name) {
            return element.style[name] || '';
        },
    });

    global.setTimeout = (callback) => {
        callback();
        return 0;
    };

    global.Wirecloud = {
        UserInterfaceManager: {
            registerCalls: 0,
            unregisterCalls: 0,
            _registerPopup() {
                this.registerCalls += 1;
            },
            _unregisterPopup() {
                this.unregisterCalls += 1;
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Popover.js');

    return {
        Popover: StyledElements.Popover,
        GUIBuilder,
        fullscreenElement,
    };
};

const createWidget = () => {
    const listeners = {};
    return {
        contextManager: {
            adds: 0,
            removes: 0,
            addCallback(callback) {
                this.adds += 1;
                this.lastCallback = callback;
            },
            removeCallback(callback) {
                this.removes += 1;
                this.lastRemoved = callback;
            },
        },
        listeners,
        addEventListener(name, listener) {
            listeners[name] = listener;
        },
        removeEventListener(name, listener) {
            if (listeners[name] === listener) {
                delete listeners[name];
            }
        },
    };
};

test('StyledElements.Popover bind wires aria attributes and validates modes', () => {
    resetLegacyRuntime();
    const { Popover } = setupPopover();
    const popover = new Popover({ title: 'Title', content: 'Body' });
    const clickTarget = document.createElement('button');
    const hoverTarget = document.createElement('a');

    popover.bind(clickTarget, 'click');
    popover.bind(hoverTarget, 'hover');

    assert.equal(clickTarget.getAttribute('aria-describedby').includes('se-popover-'), true);
    assert.equal(clickTarget.getAttribute('aria-expanded'), 'false');
    assert.equal(hoverTarget.getAttribute('aria-describedby').includes('se-popover-'), true);
    assert.equal(typeof clickTarget.listeners.click[0], 'function');
    assert.equal(typeof hoverTarget.listeners.focus[0], 'function');
    assert.throws(() => popover.bind(document.createElement('span'), 'bad'), TypeError);

    const predescribed = document.createElement('div');
    predescribed.setAttribute('aria-describedby', 'existing-id');
    popover.bind(predescribed, 'hover');
    assert.equal(predescribed.getAttribute('aria-describedby').includes('existing-id'), true);
    assert.equal(predescribed.getAttribute('aria-describedby').includes('se-popover-'), true);
});

test('StyledElements.Popover show/update/hide covers positioning, fullscreen and tracking branches', () => {
    resetLegacyRuntime();
    const { Popover, GUIBuilder, fullscreenElement } = setupPopover();
    const widget = createWidget();
    const popover = new Popover({
        title: 'Initial title',
        content: 'Initial content',
        placement: ['top', 'right', 'bottom', 'left'],
        refContainer: widget,
        sticky: false,
    });
    const refElement = document.createElement('button');
    refElement.setAttribute('aria-describedby', 'existing');
    refElement.getBoundingClientRect = () => ({
        left: 20,
        top: 20,
        right: 40,
        bottom: 40,
        width: 20,
        height: 20,
    });

    document.fullscreenElement = fullscreenElement;
    document.body.getBoundingClientRect = () => ({
        left: 0,
        top: 0,
        right: 200,
        bottom: 200,
        width: 200,
        height: 200,
    });

    assert.equal(popover.visible, false);
    popover.disablePointerEvents();
    popover.enablePointerEvents();
    popover.show(refElement);

    assert.equal(popover.visible, true);
    assert.equal(Wirecloud.UserInterfaceManager.registerCalls, 1);
    assert.equal(widget.contextManager.adds, 1);
    assert.equal(widget.listeners.unload != null, true);

    popover.disablePointerEvents();
    assert.equal(popover.visible, true);
    assert.equal(popover.repaint(), popover);
    popover.enablePointerEvents();
    assert.equal(popover.toggle(refElement), popover);
    assert.equal(GUIBuilder.lastParse.data.title, 'Initial title');
    assert.equal(GUIBuilder.lastParse.data.content, 'Initial content');
    assert.equal(popover.toggle(refElement), popover);
    assert.equal(popover.visible, true);

    popover.update('Updated title', 'Updated content');
    assert.equal(GUIBuilder.lastParse.data.title, 'Updated title');
    assert.equal(GUIBuilder.lastParse.data.content, 'Updated content');
    assert.equal(popover.show(refElement), popover);
    assert.equal(popover.visible, true);

    document.fullscreenElement = null;
    document.listeners.fullscreenchange[0]({ type: 'fullscreenchange' });
    assert.equal(popover.show(refElement), popover);
    assert.equal(popover.visible, true);
    assert.equal(popover.hide(), popover);
    assert.equal(popover.visible, false);
    assert.equal(Wirecloud.UserInterfaceManager.unregisterCalls >= 1, true);
    assert.equal(widget.contextManager.removes >= 1, true);
    assert.equal(popover.hide(), popover);
});

test('StyledElements.Popover tracks widget visibility callback', () => {
    resetLegacyRuntime();
    const { Popover } = setupPopover();
    const widget = createWidget();
    const popover = new Popover({
        title: 'Track',
        content: 'Visibility',
        refContainer: widget,
    });
    const refElement = document.createElement('button');
    refElement.getBoundingClientRect = () => ({
        left: 10,
        top: 10,
        right: 20,
        bottom: 20,
        width: 10,
        height: 10,
    });

    popover.show(refElement);
    const callback = widget.contextManager.lastCallback;
    assert.equal(typeof callback, 'function');

    callback({ visible: false });
    assert.equal(popover.visible, true);
    assert.equal(document.body.childNodes.some((node) => node.classList?.contains('hidden')), true);

    callback({ visible: true });
    assert.equal(document.body.childNodes.some((node) => node.classList?.contains('hidden')), false);

    popover.hide();
});

test('StyledElements.Popover document click and unload callbacks close the popover', () => {
    resetLegacyRuntime();
    const { Popover } = setupPopover();
    const widget = createWidget();
    const popover = new Popover({
        title: 'Sticky?',
        content: 'Content',
        refContainer: widget,
        sticky: false,
    });
    const refElement = document.createElement('button');
    refElement.getBoundingClientRect = () => ({
        left: 1,
        top: 1,
        right: 2,
        bottom: 2,
        width: 1,
        height: 1,
    });

    popover.show(refElement);
    assert.equal(popover.visible, true);

    const clickListener = document.listeners.click.at(-1);
    clickListener({ button: 1 });
    assert.equal(popover.visible, true);

    clickListener({ button: 0 });
    assert.equal(popover.visible, false);

    popover.show(refElement);
    widget.listeners.unload();
    assert.equal(popover.visible, false);
});
