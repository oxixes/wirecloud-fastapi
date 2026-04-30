const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupPopupButton = () => {
    class PopupMenu {
        constructor() {
            this.wrapperElement = document.createElement('div');
            this.visible = false;
            this.listeners = {};
            this.showCalls = [];
            this.hideCalls = 0;
            this.destroyCalls = 0;
            this.clearCalls = 0;
            this.moveFocusDownCalls = 0;
            this.moveFocusUpCalls = 0;
            this.hasEnabled = false;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        clearEventListeners(name) {
            this.clearCalls += 1;
            delete this.listeners[name];
        }

        isVisible() {
            return this.visible;
        }

        show(target) {
            this.showCalls.push(target);
            this.visible = true;
            return this;
        }

        hide() {
            this.hideCalls += 1;
            this.visible = false;
            return this;
        }

        moveFocusDown() {
            this.moveFocusDownCalls += 1;
            return this;
        }

        moveFocusUp() {
            this.moveFocusUpCalls += 1;
            return this;
        }

        hasEnabledItem() {
            return this.hasEnabled;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    class Button {
        constructor() {
            this.wrapperElement = document.createElement('button');
            this.listeners = {};
            this.destroyCalls = 0;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
        }

        _clickCallback(event) {
            if (this.listeners.click) {
                this.listeners.click(event);
            }
        }

        getBoundingClientRect() {
            return {left: 1, top: 2};
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {
        PopupMenu,
        Button,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/PopupButton.js');
    return StyledElements.PopupButton;
};

test('StyledElements.PopupButton creates owned popup menu and aria attributes', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});

    assert.equal(button._owned_popup_menu, true);
    assert.equal(button.wrapperElement.getAttribute('aria-haspopup'), 'true');
    assert.equal(button.wrapperElement.getAttribute('aria-expanded'), 'false');
    assert.equal(button.wrapperElement.getAttribute('aria-controls') != null, true);
});

test('StyledElements.PopupButton uses provided popup menu without owning it', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const externalMenu = new StyledElements.PopupMenu();
    externalMenu.wrapperElement.setAttribute('id', 'existing-id');
    const button = new PopupButton({menu: externalMenu});

    assert.equal(button._owned_popup_menu, false);
    assert.equal(button.getPopupMenu(), externalMenu);
    assert.equal(button.wrapperElement.getAttribute('aria-controls'), 'existing-id');
});

test('StyledElements.PopupButton click toggles popup visibility', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});

    button.listeners.click();
    assert.equal(button.popup_menu.showCalls.length, 1);
    button.popup_menu.visible = true;
    button.listeners.click();
    assert.equal(button.popup_menu.hideCalls, 1);
});

test('StyledElements.PopupButton visibilityChange listener toggles open class and aria-expanded', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});

    button.popup_menu.visible = true;
    button.popup_menu.listeners.visibilityChange();
    assert.equal(button.wrapperElement.classList.contains('open'), true);
    assert.equal(button.wrapperElement.getAttribute('aria-expanded'), 'true');

    button.popup_menu.visible = false;
    button.popup_menu.listeners.visibilityChange();
    assert.equal(button.wrapperElement.classList.contains('open'), false);
    assert.equal(button.wrapperElement.getAttribute('aria-expanded'), 'false');
});

test('StyledElements.PopupButton _onkeydown handles ArrowDown and ArrowUp', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});
    const event = {
        prevented: 0,
        preventDefault() {
            this.prevented += 1;
        }
    };

    button._onkeydown(event, 'ArrowDown');
    button._onkeydown(event, 'ArrowUp');

    assert.equal(event.prevented, 2);
    assert.equal(button.popup_menu.moveFocusDownCalls, 1);
    assert.equal(button.popup_menu.moveFocusUpCalls, 1);
});

test('StyledElements.PopupButton _onkeydown routes Enter and Space to click callback', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});
    let clicks = 0;
    button._clickCallback = () => {
        clicks += 1;
    };

    button._onkeydown({}, 'Enter');
    button._onkeydown({}, ' ');

    assert.equal(clicks, 2);
});

test('StyledElements.PopupButton _onkeydown handles Tab only when menu has enabled items', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});
    const event = {
        prevented: 0,
        preventDefault() {
            this.prevented += 1;
        }
    };

    button.popup_menu.hasEnabled = false;
    button._onkeydown(event, 'Tab');
    button.popup_menu.hasEnabled = true;
    button._onkeydown(event, 'Tab');

    assert.equal(event.prevented, 1);
    assert.equal(button.popup_menu.moveFocusDownCalls, 1);
});

test('StyledElements.PopupButton _onkeydown ignores unrelated keys', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});

    assert.equal(button._onkeydown({}, 'Escape'), undefined);
});

test('StyledElements.PopupButton replacePopupMenu destroys owned previous menu', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const button = new PopupButton({});
    const oldMenu = button.popup_menu;
    const newMenu = new StyledElements.PopupMenu();
    newMenu.visible = true;

    button.replacePopupMenu(newMenu);

    assert.equal(oldMenu.destroyCalls, 1);
    assert.equal(button._owned_popup_menu, false);
    assert.equal(button.wrapperElement.getAttribute('aria-expanded'), 'true');
    assert.equal(button.wrapperElement.getAttribute('aria-controls') != null, true);
});

test('StyledElements.PopupButton replacePopupMenu clears listeners for non-owned previous menu', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const firstMenu = new StyledElements.PopupMenu();
    const button = new PopupButton({menu: firstMenu});
    const secondMenu = new StyledElements.PopupMenu();

    button.replacePopupMenu(secondMenu);
    button.replacePopupMenu(null);

    assert.equal(firstMenu.clearCalls, 1);
    assert.equal(button.wrapperElement.getAttribute('aria-controls'), null);
});

test('StyledElements.PopupButton destroy delegates to base and owned/non-owned popup cleanup', () => {
    resetLegacyRuntime();
    const PopupButton = setupPopupButton();
    const ownedButton = new PopupButton({});
    const ownedMenu = ownedButton.popup_menu;
    ownedButton.destroy();
    assert.equal(ownedButton.destroyCalls, 1);
    assert.equal(ownedMenu.destroyCalls, 1);
    assert.equal(ownedButton.popup_menu, null);

    const externalMenu = new StyledElements.PopupMenu();
    const nonOwnedButton = new PopupButton({menu: externalMenu});
    nonOwnedButton.destroy();
    assert.equal(nonOwnedButton.destroyCalls, 1);
    assert.equal(externalMenu.clearCalls, 1);
    assert.equal(nonOwnedButton.popup_menu, null);
});
