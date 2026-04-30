const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupPopUp = () => {
    class StyledElement {}

    class ObjectWithEvents {
        constructor(events) {
            this.availableEvents = events;
            this.listeners = {};
        }

        addEventListener(name, listener) {
            this.listeners[name] = this.listeners[name] || [];
            this.listeners[name].push(listener);
        }

        dispatchEvent(name) {
            (this.listeners[name] || []).forEach((listener) => listener());
        }
    }

    class Button {
        constructor() {
            this.listeners = {};
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        insertInto(parent) {
            parent.appendChild(document.createElement('button'));
        }
    }

    global.StyledElements = {
        StyledElement,
        ObjectWithEvents,
        Button,
    };
    global.Wirecloud = {
        Utils: {},
        ui: {
            Tutorial: {}
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/PopUp.js');

    return {
        PopUp: Wirecloud.ui.Tutorial.PopUp,
        WidgetElement: Wirecloud.ui.Tutorial.WidgetElement,
        StyledElement,
    };
};

const rect = ({ top = 10, left = 20, width = 40, height = 30, right, bottom }) => ({
    top,
    left,
    width,
    height,
    right: right != null ? right : left + width,
    bottom: bottom != null ? bottom : top + height,
});

test('PopUp constructor highlights plain elements and sets info style by default', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const element = document.createElement('div');

    const popup = new PopUp(element, {
        highlight: true,
        msg: 'hello',
        position: 'downRight',
        closable: false
    });

    assert.equal(element.classList.contains('tuto_highlight'), true);
    assert.equal(popup.wrapperElement.classList.contains('alert-info'), true);
    assert.equal(popup.textElement.innerHTML, 'hello');
    assert.equal(popup.arrow.classList.contains('downRight'), true);
});

test('PopUp constructor with user mode and empty message adds warning and empty classes', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const element = document.createElement('div');

    const popup = new PopUp(element, {
        highlight: false,
        msg: null,
        position: 'topLeft',
        user: true,
        closable: false
    });

    assert.equal(popup.wrapperElement.classList.contains('alert-warning'), true);
    assert.equal(popup.wrapperElement.classList.contains('empty'), true);
});

test('PopUp constructor with closable button dispatches close after destroy', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const element = document.createElement('div');
    const popup = new PopUp(element, {
        highlight: false,
        msg: 'x',
        position: 'topLeft',
        closable: true
    });
    let closeEvents = 0;
    popup.addEventListener('close', () => {
        closeEvents += 1;
    });

    popup.cancelButton.listeners.click();

    assert.equal(closeEvents, 1);
    assert.equal(popup.wrapperElement, null);
});

test('PopUp constructor uses StyledElement addClassName branch', () => {
    resetLegacyRuntime();
    const { PopUp, StyledElement } = setupPopUp();
    const element = new StyledElement();
    element.added = 0;
    element.addClassName = () => {
        element.added += 1;
    };
    element.getBoundingClientRect = () => rect({});

    const popup = new PopUp(element, {
        highlight: true,
        msg: 'x',
        position: 'downLeft',
        closable: false
    });

    assert.equal(element.added, 1);
    assert.ok(popup.wrapperElement);
});

test('PopUp repaint covers all position branches', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const element = document.createElement('div');
    element.getBoundingClientRect = () => rect({ top: 10, left: 20, width: 40, height: 30 });
    const popup = new PopUp(element, {
        highlight: false,
        msg: 'x',
        position: 'downRight',
        closable: false
    });
    popup.wrapperElement.getBoundingClientRect = () => rect({ width: 50, height: 60, top: 0, left: 0 });

    popup.repaint();
    assert.equal(popup.wrapperElement.style.top, '53px');
    assert.equal(popup.wrapperElement.style.left, '50px');

    popup.options.position = 'downLeft';
    popup.repaint();
    assert.equal(popup.wrapperElement.style.left, '-20px');

    popup.options.position = 'topRight';
    popup.repaint();
    assert.equal(popup.wrapperElement.style.top, '-63px');

    popup.options.position = 'topLeft';
    popup.repaint();
    assert.equal(popup.wrapperElement.style.left, '-20px');
});

test('PopUp repaint default branch behaves like downRight', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const element = document.createElement('div');
    element.getBoundingClientRect = () => rect({ top: 2, left: 6, width: 20, height: 10 });
    const popup = new PopUp(element, {
        highlight: false,
        msg: 'x',
        position: 'unknown',
        closable: false
    });
    popup.wrapperElement.getBoundingClientRect = () => rect({ width: 1, height: 1, top: 0, left: 0 });

    popup.repaint();

    assert.equal(popup.wrapperElement.style.top, '25px');
    assert.equal(popup.wrapperElement.style.left, '21px');
});

test('PopUp destroy removes highlight and detaches wrapper for plain elements', () => {
    resetLegacyRuntime();
    const { PopUp } = setupPopUp();
    const parent = document.createElement('div');
    const element = document.createElement('div');
    element.classList.add('tuto_highlight');
    const popup = new PopUp(element, {
        highlight: true,
        msg: 'x',
        position: 'downRight',
        closable: false
    });
    parent.appendChild(popup.wrapperElement);

    popup.destroy();

    assert.equal(element.classList.contains('tuto_highlight'), false);
    assert.equal(parent.childNodes.length, 0);
    assert.equal(popup.wrapperElement, null);
    assert.equal(popup.textElement, null);
    assert.equal(popup.arrow, null);
});

test('PopUp destroy handles StyledElement removeClassName and null wrapper early return', () => {
    resetLegacyRuntime();
    const { PopUp, StyledElement } = setupPopUp();
    const element = new StyledElement();
    element.addClassName = () => {};
    element.removed = 0;
    element.removeClassName = () => {
        element.removed += 1;
    };
    element.getBoundingClientRect = () => rect({});
    const popup = new PopUp(element, {
        highlight: true,
        msg: 'x',
        position: 'downRight',
        closable: false
    });

    popup.destroy();
    popup.destroy();

    assert.equal(element.removed, 1);
});

test('WidgetElement proxies geometry and event methods', () => {
    resetLegacyRuntime();
    const { WidgetElement } = setupPopUp();
    const widget = {
        wrapperElement: {
            getBoundingClientRect: () => rect({ left: 100, top: 200, width: 20, height: 20 }),
        }
    };
    const element = document.createElement('div');
    let addArgs = null;
    let removeArgs = null;
    element.getBoundingClientRect = () => rect({ left: 3, top: 4, width: 5, height: 6 });
    element.addEventListener = function () {
        addArgs = Array.from(arguments);
    };
    element.removeEventListener = function () {
        removeArgs = Array.from(arguments);
    };
    const wrapped = new WidgetElement(widget, element);

    const box = wrapped.getBoundingClientRect();
    wrapped.addEventListener('click', 1, 2);
    wrapped.removeEventListener('focus', 3);
    wrapped.classList.add('x');
    wrapped.classList.remove('x');

    assert.deepEqual(box, { left: 103, top: 204, width: 5, height: 6 });
    assert.deepEqual(addArgs, ['click', 1, 2]);
    assert.deepEqual(removeArgs, ['focus', 3]);
    assert.ok(Object.isFrozen(wrapped));
});
