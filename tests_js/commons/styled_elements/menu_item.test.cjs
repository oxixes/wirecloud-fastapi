const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupMenuItem = () => {
    class StyledElement {
        constructor(events = []) {
            this.__listeners = {};
            events.forEach((eventName) => {
                this.__listeners[eventName] = [];
            });
            this.wrapperElement = document.createElement('div');
            this._enabled = true;
            this.__destroyCalls = 0;
        }

        addEventListener(eventName, listener) {
            if (!(eventName in this.__listeners)) {
                this.__listeners[eventName] = [];
            }
            this.__listeners[eventName].push(listener);
            return this;
        }

        dispatchEvent(eventName, ...args) {
            (this.__listeners[eventName] || []).forEach((listener) => listener(this, ...args));
            return this;
        }

        hasClassName(className) {
            return this.wrapperElement.classList.contains(className);
        }

        toggleClassName(className, active) {
            this.wrapperElement.classList.toggle(className, active);
            return this;
        }

        get enabled() {
            return this._enabled;
        }

        set enabled(enabled) {
            this._enabled = !!enabled;
            this._onenabled(this._enabled);
        }

        disable() {
            this.enabled = false;
            return this;
        }

        enable() {
            this.enabled = true;
            return this;
        }

        hasFocus() {
            return StyledElements.Utils.hasFocus(this.wrapperElement);
        }

        destroy() {
            this.__destroyCalls += 1;
        }
    }

    class SubMenuItem {}

    global.StyledElements = {
        StyledElement,
        SubMenuItem,
        Utils: {
            normalizeKey: (event) => event.key,
            hasFocus: (element) => document.activeElement === element,
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/MenuItem.js');
    return {
        MenuItem: StyledElements.MenuItem,
        SubMenuItem,
    };
};

const keyEvent = (key, extra = {}) => ({
    type: 'keydown',
    key,
    preventDefaultCalls: 0,
    stopPropagationCalls: 0,
    preventDefault() {
        this.preventDefaultCalls += 1;
    },
    stopPropagation() {
        this.stopPropagationCalls += 1;
    },
    ...extra,
});

test('StyledElements.MenuItem constructor accepts function handler and context', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const handler = () => {};
    const context = {id: 1};
    const item = new MenuItem('Title', handler, context);

    assert.equal(item.title, 'Title');
    assert.equal(item.run, handler);
    assert.equal(item.context, context);
    assert.equal(item.wrapperElement.getAttribute('role'), 'menuitem');
    assert.equal(item.wrapperElement.getAttribute('tabindex'), '-1');
});

test('StyledElements.MenuItem constructor accepts options object and iconClass', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', {handler: () => {}, context: {x: 1}, enabled: false, iconClass: 'fa fa-star'});

    assert.equal(item.enabled, false);
    assert.equal(item.wrapperElement.getAttribute('tabindex'), null);
    assert.equal(item.wrapperElement.firstChild.classList.contains('se-popup-menu-item-thumbnail'), true);
    assert.equal(item.wrapperElement.firstChild.firstChild.className, 'se-icon fa fa-star');
});

test('StyledElements.MenuItem activate and deactivate toggle active class', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});

    item.activate();
    assert.equal(item.active, true);
    item.deactivate();
    assert.equal(item.active, false);
});

test('StyledElements.MenuItem active setter is no-op when disabled', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    item.disable();

    item.active = true;

    assert.equal(item.active, false);
});

test('StyledElements.MenuItem addIconClass reuses icon element on subsequent calls', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});

    item.addIconClass('a');
    const icon = item.wrapperElement.firstChild.firstChild;
    item.addIconClass('b');

    assert.equal(item.wrapperElement.firstChild.firstChild, icon);
    assert.equal(icon.className, 'se-icon b');
});

test('StyledElements.MenuItem setDescription handles text and StyledElement values', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    item.setDescription('text description');
    assert.equal(item.description, 'text description');

    class Description extends StyledElements.StyledElement {
        appendTo(element) {
            element.textContent = 'styled description';
        }
    }
    item.setDescription(new Description());
    assert.equal(item.description, 'styled description');
});

test('StyledElements.MenuItem setTitle handles text and StyledElement values', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Old', () => {});
    item.setTitle('New');
    assert.equal(item.title, 'New');

    class Title extends StyledElements.StyledElement {
        appendTo(element) {
            element.textContent = 'Styled title';
        }
    }
    item.setTitle(new Title());
    assert.equal(item.title, 'Styled title');
});

test('StyledElements.MenuItem click dispatches click only when enabled', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    let clickEvents = 0;
    item.addEventListener('click', () => {
        clickEvents += 1;
    });

    item.click();
    item.disable();
    item.click();

    assert.equal(clickEvents, 1);
});

test('StyledElements.MenuItem focus dispatches focus only when enabled and unfocused', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    let focusEvents = 0;
    item.addEventListener('focus', () => {
        focusEvents += 1;
    });

    item.focus();
    item.focus();
    item.disable();
    item.focus();

    assert.equal(focusEvents, 1);
});

test('StyledElements.MenuItem mouseenter, mouseleave, blur and focus events depend on enabled state', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    const events = {mouseenter: 0, mouseleave: 0, blur: 0, focus: 0};
    item.addEventListener('mouseenter', () => { events.mouseenter += 1; });
    item.addEventListener('mouseleave', () => { events.mouseleave += 1; });
    item.addEventListener('blur', () => { events.blur += 1; });
    item.addEventListener('focus', () => { events.focus += 1; });

    item.wrapperElement.dispatchEvent({type: 'mouseenter'});
    item.wrapperElement.dispatchEvent({type: 'mouseleave'});
    item.wrapperElement.dispatchEvent({type: 'blur'});
    item.wrapperElement.dispatchEvent({type: 'focus'});
    item.disable();
    item.wrapperElement.dispatchEvent({type: 'mouseenter'});
    item.wrapperElement.dispatchEvent({type: 'mouseleave'});
    item.wrapperElement.dispatchEvent({type: 'blur'});
    item.wrapperElement.dispatchEvent({type: 'focus'});

    assert.deepEqual(events, {mouseenter: 1, mouseleave: 1, blur: 1, focus: 1});
});

test('StyledElements.MenuItem click listener stops propagation and triggers click()', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    let clickEvents = 0;
    item.addEventListener('click', () => { clickEvents += 1; });
    const event = {type: 'click', stopPropagationCalls: 0, stopPropagation() { this.stopPropagationCalls += 1; }};

    item.wrapperElement.dispatchEvent(event);

    assert.equal(event.stopPropagationCalls, 1);
    assert.equal(clickEvents, 1);
});

test('StyledElements.MenuItem keydown handles enter and space', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    let clickEvents = 0;
    item.addEventListener('click', () => { clickEvents += 1; });

    const space = keyEvent(' ');
    item.wrapperElement.dispatchEvent(space);
    const enter = keyEvent('Enter');
    item.wrapperElement.dispatchEvent(enter);

    assert.equal(clickEvents, 2);
    assert.equal(space.preventDefaultCalls, 1);
    assert.equal(enter.preventDefaultCalls, 1);
});

test('StyledElements.MenuItem keydown handles escape with submenu parent focus', () => {
    resetLegacyRuntime();
    const {MenuItem, SubMenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    const parent = new SubMenuItem();
    parent.hideCalls = 0;
    parent.hide = () => { parent.hideCalls += 1; };
    parent.menuitem = {focusCalls: 0, focus() { this.focusCalls += 1; }};
    item.parentElement = parent;
    const escape = keyEvent('Escape');

    item.wrapperElement.dispatchEvent(escape);

    assert.equal(parent.hideCalls, 1);
    assert.equal(parent.menuitem.focusCalls, 1);
    assert.equal(escape.stopPropagationCalls, 1);
    assert.equal(escape.preventDefaultCalls, 1);
});

test('StyledElements.MenuItem keydown handles ArrowLeft with regular parent', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    const parent = {hideCalls: 0, hide() { this.hideCalls += 1; }};
    item.parentElement = parent;
    const left = keyEvent('ArrowLeft');

    item.wrapperElement.dispatchEvent(left);

    assert.equal(parent.hideCalls, 1);
    assert.equal(left.stopPropagationCalls, 1);
    assert.equal(left.preventDefaultCalls, 1);
});

test('StyledElements.MenuItem keydown handles ArrowUp and ArrowDown', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    const parent = {
        up: 0,
        down: 0,
        moveFocusUp() { this.up += 1; },
        moveFocusDown() { this.down += 1; },
    };
    item.parentElement = parent;
    const up = keyEvent('ArrowUp');
    const down = keyEvent('ArrowDown');

    item.wrapperElement.dispatchEvent(up);
    item.wrapperElement.dispatchEvent(down);

    assert.equal(parent.up, 1);
    assert.equal(parent.down, 1);
    assert.equal(up.preventDefaultCalls, 1);
    assert.equal(down.preventDefaultCalls, 1);
});

test('StyledElements.MenuItem keydown handles Tab in parent and visible submenu paths', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    const parent = {
        up: 0,
        down: 0,
        moveFocusUp() { this.up += 1; },
        moveFocusDown() { this.down += 1; },
    };
    item.parentElement = parent;

    item.wrapperElement.dispatchEvent(keyEvent('Tab', {shiftKey: true}));
    item.wrapperElement.dispatchEvent(keyEvent('Tab', {shiftKey: false}));

    item.submenu = {
        up: 0,
        down: 0,
        isVisible() { return true; },
        moveFocusUp() { this.up += 1; },
        moveFocusDown() { this.down += 1; },
    };
    item.wrapperElement.dispatchEvent(keyEvent('Tab', {shiftKey: true}));
    item.wrapperElement.dispatchEvent(keyEvent('Tab', {shiftKey: false}));

    assert.equal(parent.up, 1);
    assert.equal(parent.down, 1);
    assert.equal(item.submenu.up, 1);
    assert.equal(item.submenu.down, 1);
});

test('StyledElements.MenuItem keydown handles ArrowRight with submenu open and move focus', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const item = new MenuItem('Title', () => {});
    let hasEnabled = true;
    item.submenu = {
        showCalls: 0,
        downCalls: 0,
        show() { this.showCalls += 1; },
        hasEnabledItem() { return hasEnabled; },
        moveFocusDown() { this.downCalls += 1; },
    };
    item.getBoundingClientRect = () => ({left: 1, top: 2});

    item.wrapperElement.dispatchEvent(keyEvent('ArrowRight'));
    hasEnabled = false;
    item.wrapperElement.dispatchEvent(keyEvent('ArrowRight'));

    assert.equal(item.submenu.showCalls, 2);
    assert.equal(item.submenu.downCalls, 1);
});

test('StyledElements.MenuItem destroy removes element and delegates to StyledElement destroy', () => {
    resetLegacyRuntime();
    const {MenuItem} = setupMenuItem();
    const parent = document.createElement('div');
    const item = new MenuItem('Title', () => {});
    parent.appendChild(item.wrapperElement);

    item.destroy();

    assert.equal(parent.childNodes.includes(item.wrapperElement), false);
    assert.equal(item.__destroyCalls, 1);
});
