const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupButton = () => {
    bootstrapStyledElementsBase();

    class FakeTooltip {
        constructor(options) {
            this.options = options;
            this.bindTarget = null;
            this.destroyCalls = 0;
        }

        bind(target) {
            this.bindTarget = target;
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    StyledElements.Tooltip = FakeTooltip;

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Button.js');

    return {
        Button: StyledElements.Button,
        FakeTooltip,
    };
};

test('StyledElements.Button constructor configures structure, icon stack and initial properties', () => {
    resetLegacyRuntime();
    const { Button, FakeTooltip } = setupButton();

    const button = new Button({
        usedInForm: true,
        id: 'btn-main',
        class: 'custom highlighted',
        plain: true,
        iconClass: 'fa fa-play',
        stackedIconClass: 'fa-circle',
        stackedIconPlacement: 'top-left',
        text: 'Run',
        title: 'Run operation',
        state: 'primary',
        depth: 2,
        tabindex: 3,
    });

    assert.equal(button.wrapperElement.tagName, 'BUTTON');
    assert.equal(button.wrapperElement.getAttribute('type'), 'button');
    assert.equal(button.wrapperElement.getAttribute('id'), 'btn-main');
    assert.equal(button.wrapperElement.classList.contains('se-btn'), true);
    assert.equal(button.wrapperElement.classList.contains('plain'), true);
    assert.equal(button.wrapperElement.classList.contains('custom'), true);
    assert.equal(button.wrapperElement.classList.contains('highlighted'), true);
    assert.equal(button.wrapperElement.classList.contains('btn-primary'), true);
    assert.equal(button.wrapperElement.classList.contains('z-depth-2'), true);
    assert.equal(button.wrapperElement.getAttribute('tabindex'), '3');

    assert.equal(button.label.textContent, 'Run');
    assert.equal(button.icon.classList.contains('se-icon'), true);
    assert.equal(button.icon.classList.contains('fa'), true);
    assert.equal(button.icon.classList.contains('fa-play'), true);
    assert.equal(button.stackedIcon.classList.contains('se-stacked-icon'), true);
    assert.equal(button.stackedIcon.classList.contains('top-left'), true);
    assert.equal(button.stackedIcon.classList.contains('fa-circle'), true);

    assert.equal(button.tooltip instanceof FakeTooltip, true);
    assert.equal(button.tooltip.bindTarget, button);
    assert.equal(button.wrapperElement.hasAttribute('aria-label'), false);
});

test('StyledElements.Button state and depth setters add and remove classes for valid/invalid values', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    const button = new Button({ state: 'invalid-state', depth: -1, id: '   ' });

    assert.equal(button.wrapperElement.tagName, 'DIV');
    assert.equal(button.wrapperElement.getAttribute('role'), 'button');
    assert.equal(button.state, '');
    assert.equal(button.depth, null);

    button.state = 'success';
    assert.equal(button.state, 'success');
    assert.equal(button.wrapperElement.classList.contains('btn-success'), true);

    button.state = 'danger';
    assert.equal(button.wrapperElement.classList.contains('btn-success'), false);
    assert.equal(button.wrapperElement.classList.contains('btn-danger'), true);

    button.state = 'broken';
    assert.equal(button.state, '');
    assert.equal(button.wrapperElement.classList.contains('btn-danger'), false);

    button.depth = 1;
    assert.equal(button.wrapperElement.classList.contains('z-depth-1'), true);
    button.depth = 4;
    assert.equal(button.wrapperElement.classList.contains('z-depth-1'), false);
    assert.equal(button.wrapperElement.classList.contains('z-depth-4'), true);

    button.depth = 'nope';
    assert.equal(button.depth, null);
    assert.equal(button.wrapperElement.classList.contains('z-depth-4'), false);
});

test('StyledElements.Button label, icon and title helpers update aria and tooltip as expected', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    const button = new Button({ title: 'Only tooltip' });
    assert.equal(button.wrapperElement.getAttribute('aria-label'), 'Only tooltip');

    button.setLabel('Visible text');
    assert.equal(button.label.textContent, 'Visible text');
    assert.equal(button.wrapperElement.hasAttribute('aria-label'), false);

    button.setLabel('');
    assert.equal(button.label, null);
    assert.equal(button.wrapperElement.getAttribute('aria-label'), 'Only tooltip');

    button.addIconClassName('fa fa-cog');
    assert.equal(button.hasIconClassName('fa'), true);
    assert.equal(button.hasIconClassName('fa-cog'), true);
    button.replaceIconClassName('fa-cog', 'fa-play');
    assert.equal(button.hasIconClassName('fa-cog'), false);
    assert.equal(button.hasIconClassName('fa-play'), true);

    button.removeIconClassName(['fa-play']);
    assert.equal(button.hasIconClassName('fa-play'), false);
    button.removeIconClassName('');
    assert.equal(button.icon, null);

    button.removeIconClassName(['unused']);
    button.addIconClassName([]);

    const returned = button.addIconClassName(null);
    assert.equal(returned, button);

    button.addIconClassName('fa-temp');
    button.removeIconClassName('fa-temp');
    assert.equal(button.icon, null);

    const oldTooltip = button.tooltip;
    button.setTitle('Updated tooltip');
    assert.equal(button.tooltip, oldTooltip);
    assert.equal(button.tooltip.options.content, 'Updated tooltip');
    assert.equal(button.wrapperElement.getAttribute('aria-label'), 'Updated tooltip');

    button.setTitle('');
    assert.equal(button.tooltip, null);
    assert.equal(oldTooltip.destroyCalls, 1);
    assert.equal(button.wrapperElement.hasAttribute('aria-label'), false);
});

test('StyledElements.Button setBadge inserts and removes status and alert badges', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    const button = new Button({ depth: 2 });

    button.setBadge('9', 'warning', true);
    assert.equal(button.badgeElement.getAttribute('role'), 'alert');
    assert.equal(button.badgeElement.getAttribute('aria-live'), 'assertive');
    assert.equal(button.badgeElement.classList.contains('badge-warning'), true);
    assert.equal(button.badgeElement.classList.contains('z-depth-3'), true);
    assert.equal(button.wrapperElement.classList.contains('has-alert'), true);
    assert.equal(button.badgeElement.textContent, '9');

    button.setBadge('3', 'unknown', false);
    assert.equal(button.badgeElement.getAttribute('role'), 'alert');
    assert.equal(button.badgeElement.getAttribute('aria-live'), 'assertive');
    assert.equal(button.badgeElement.classList.contains('badge-unknown'), false);
    assert.equal(button.wrapperElement.classList.contains('has-alert'), false);

    button.setBadge('');
    assert.equal(button.badgeElement, null);
    assert.equal(button.wrapperElement.classList.contains('has-alert'), false);

    const statusButton = new Button({ depth: 0 });
    statusButton.setBadge('1', 'info', false);
    assert.equal(statusButton.badgeElement.getAttribute('role'), 'status');
    assert.equal(statusButton.badgeElement.getAttribute('aria-live'), 'polite');
});

test('StyledElements.Button click, dblclick, keyboard and pointer events depend on enabled state', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    const button = new Button({});
    const seen = [];
    button.addEventListener('click', () => seen.push('click'));
    button.addEventListener('dblclick', () => seen.push('dblclick'));
    button.addEventListener('focus', () => seen.push('focus'));
    button.addEventListener('blur', () => seen.push('blur'));
    button.addEventListener('mouseenter', () => seen.push('mouseenter'));
    button.addEventListener('mouseleave', () => seen.push('mouseleave'));

    let inputClicks = 0;
    button.inputElement = {
        click() {
            inputClicks += 1;
        },
    };

    button._clickCallback({
        target: button.inputElement,
        preventDefault() {
            throw new Error('must not call preventDefault when click comes from input element');
        },
        stopPropagation() {
            throw new Error('must not call stopPropagation when click comes from input element');
        },
    });

    let prevented = 0;
    let stopped = 0;
    button._clickCallback({
        target: button.wrapperElement,
        preventDefault() {
            prevented += 1;
        },
        stopPropagation() {
            stopped += 1;
        },
    });
    assert.equal(prevented, 1);
    assert.equal(stopped, 1);
    assert.equal(inputClicks, 1);
    assert.equal(seen.includes('click'), true);

    button.disable();
    button._clickCallback({
        target: button.wrapperElement,
        preventDefault() {},
        stopPropagation() {},
    });
    button.click();
    assert.equal(inputClicks, 1);

    button.enable();
    assert.equal(button.focus(), button);
    button.click();
    button._onkeydown_bound({
        key: 'Enter',
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        preventDefault() {
            prevented += 1;
        },
        stopPropagation() {
            stopped += 1;
        },
    });
    assert.equal(inputClicks, 2);

    const clicksBefore = seen.filter((entry) => entry === 'click').length;
    button._onkeydown_bound({
        key: 'a',
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        preventDefault() {},
        stopPropagation() {},
    });
    assert.equal(seen.filter((entry) => entry === 'click').length, clicksBefore);
    button._onkeydown_bound({
        key: ' ',
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        preventDefault() {},
        stopPropagation() {},
    });

    button.wrapperElement.dispatchEvent(new Event('dblclick', { bubbles: true, cancelable: true }));
    button.wrapperElement.dispatchEvent(new Event('focus', { bubbles: true }));
    button.wrapperElement.dispatchEvent(new Event('blur', { bubbles: true }));
    button.wrapperElement.dispatchEvent(new Event('mouseenter', { bubbles: true }));
    button.wrapperElement.dispatchEvent(new Event('mouseleave', { bubbles: true }));
    assert.equal(seen.includes('dblclick'), true);
    assert.equal(seen.includes('focus'), true);
    assert.equal(seen.includes('blur'), true);
    assert.equal(seen.includes('mouseenter'), true);
    assert.equal(seen.includes('mouseleave'), true);

    button.disable();
    const dblBefore = seen.filter((entry) => entry === 'dblclick').length;
    button.wrapperElement.dispatchEvent(new Event('dblclick', { bubbles: true, cancelable: true }));
    assert.equal(seen.filter((entry) => entry === 'dblclick').length, dblBefore);
});

test('StyledElements.Button _onenabled updates tabindex, triggers blur, and destroy cleans internals', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    const button = new Button({ tabindex: 9 });

    let blurCalls = 0;
    button.blur = () => {
        blurCalls += 1;
        return button;
    };

    button.disable();
    assert.equal(button.wrapperElement.getAttribute('tabindex'), '-1');
    assert.equal(blurCalls, 1);

    button.enable();
    assert.equal(button.wrapperElement.getAttribute('tabindex'), '9');

    button._onkeydown({ preventDefault() {}, stopPropagation() {} }, 'Unhandled');

    button.destroy();
    assert.equal('_clickCallback' in button, false);
    assert.equal('_onkeydown_bound' in button, false);
});

test('StyledElements.Button icon helpers handle null/empty class inputs', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();
    const button = new Button({});

    assert.equal(button.hasIconClassName(null), false);
    button.addIconClassName('fa fa-star');
    assert.equal(button.hasIconClassName('fa-star'), true);
    button.removeIconClassName(null);
    assert.equal(button.icon, null);
});

test('StyledElements.Button honors subclass _clickCallback override', () => {
    resetLegacyRuntime();
    const { Button } = setupButton();

    class CustomButton extends Button {
        _clickCallback(event) {
            this.customClickEvent = event;
        }
    }

    const button = new CustomButton({});
    const event = { marker: true };
    button.wrapperElement.dispatchEvent(new Event('click', { bubbles: true }));
    button._clickCallback(event);

    assert.equal(button.customClickEvent, event);
});


