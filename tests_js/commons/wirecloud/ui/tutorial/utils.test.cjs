const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../../support/legacy-runtime.cjs');

const setupUtils = () => {
    const scheduledTimeouts = [];
    const scheduledIntervals = [];

    global.setTimeout = (fn) => {
        scheduledTimeouts.push(fn);
        return scheduledTimeouts.length;
    };
    global.setInterval = (fn) => {
        scheduledIntervals.push(fn);
        return scheduledIntervals.length;
    };
    global.clearInterval = () => {};
    global.KeyboardEvent = function KeyboardEvent(type, init) {
        return { type, ...init };
    };

    const merge = (base, extra) => Object.assign({}, base, extra || {});

    global.Wirecloud = {
        URLs: {
            LOCAL_REPOSITORY: '/repo',
        },
        Utils: {
            merge,
            interpolate(template, data) {
                return template
                    .replace('%(type)s', data.type)
                    .replace('%(id)s', data.id);
            },
        },
        UserInterfaceManager: {
            changedViews: [],
            currentWindowMenu: {
                form: {
                    fieldInterfaces: {},
                },
            },
            views: {
                wiring: {
                    behaviourEngine: { name: 'behaviour-engine' },
                    connectionEngine: { name: 'connection-engine' },
                },
            },
            changeCurrentView(view) {
                this.changedViews.push(view);
            },
        },
        LocalCatalogue: {
            exists: false,
            resourceExistsId() {
                return this.exists;
            },
            addComponentCalls: [],
            addComponent(entry) {
                this.addComponentCalls.push(entry);
                return Promise.resolve();
            },
        },
        activeWorkspace: {
            widgets: [
                {
                    id: 321,
                    wrapperElement: {
                        contentDocument: {
                            querySelector(selector) {
                                return { selector };
                            },
                        },
                    },
                },
            ],
        },
        ui: {
            Tutorial: {
                WidgetElement: class WidgetElement {
                    constructor(widget, element) {
                        this.widget = widget;
                        this.element = element;
                    }
                },
            },
        },
        createWorkspace() {
            return Promise.resolve('workspace-1');
        },
        changeActiveWorkspace() {
            return Promise.resolve();
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/Tutorial/Utils.js');

    return {
        Utils: Wirecloud.ui.Tutorial.Utils,
        scheduledTimeouts,
        scheduledIntervals,
    };
};

const flushScheduled = async (scheduled) => {
    while (scheduled.length > 0) {
        const fn = scheduled.shift();
        fn();
        await Promise.resolve();
    }
};

test('Tutorial.Utils basic_actions cover async workflows and DOM branches', async () => {
    resetLegacyRuntime();
    const { Utils, scheduledTimeouts, scheduledIntervals } = setupUtils();

    const autoAction = {
        nextCalls: 0,
        errorCalls: 0,
    };
    autoAction.nextHandler = () => {
        autoAction.nextCalls += 1;
    };
    autoAction.errorHandler = () => {
        autoAction.errorCalls += 1;
    };

    // sleep
    Utils.basic_actions.sleep(100)(autoAction, null);
    // click
    const clickTarget = { clicked: 0, click() { this.clicked += 1; } };
    Utils.basic_actions.click(50)(autoAction, clickTarget);

    // create workspace success + error branch
    Utils.basic_actions.create_workspace({ name: 'demo' })(autoAction, null);
    await Promise.resolve();
    await Promise.resolve();
    Wirecloud.createWorkspace = () => ({
        then(resolve, reject) {
            reject(new Error('boom'));
        },
    });
    Utils.basic_actions.create_workspace({})(autoAction, null);

    // input path using container + fill_input + send
    const realInput = document.createElement('input');
    let dispatchedKeyboard = null;
    realInput.dispatchEvent = (event) => {
        dispatchedKeyboard = event;
    };
    const wrapper = document.createElement('div');
    wrapper.querySelector = () => realInput;
    Utils.basic_actions.input('abcdef', {
        timeout: 20,
        step: 10,
        send: true,
        padding: 1,
    })(autoAction, wrapper);

    // input path using textarea directly
    const textarea = document.createElement('textarea');
    textarea.tagName = 'textarea';
    Utils.basic_actions.input('xy', { timeout: 100, step: 50, send: false, padding: 1 })(autoAction, textarea);

    // scrollIntoView and switch_view
    let scrolled = 0;
    Utils.basic_actions.scrollIntoView(() => ({ scrollIntoView() { scrolled += 1; } }))(autoAction);
    Utils.basic_actions.switch_view('wiring')(autoAction);

    // uploadComponent branches
    Wirecloud.LocalCatalogue.exists = false;
    Utils.basic_actions.uploadComponent('my/id')(autoAction, null);
    await Promise.resolve();
    Wirecloud.LocalCatalogue.exists = true;
    Utils.basic_actions.uploadComponent('my/id')(autoAction, null);

    // wait_transitions + editor + sidebar waiters
    const transitionEl = document.createElement('div');
    transitionEl.classList.add('se-on-transition');
    let queryCalls = 0;
    document.querySelector = (selector) => {
        queryCalls += 1;
        if (selector === '.se-on-transition') {
            return queryCalls < 2 ? transitionEl : null;
        }
        if (selector === '.wc-workspace .wc-resource-results:not(.disabled)') {
            return queryCalls > 2 ? document.createElement('div') : null;
        }
        if (selector === '.we-panel-components .wc-resource-results:not(.disabled)') {
            return queryCalls > 3 ? document.createElement('div') : null;
        }
        return null;
    };

    Utils.basic_actions.wait_transitions()(autoAction, null);
    Utils.basic_actions.editorView.wait_mac_wallet_ready()(autoAction, null);
    Utils.basic_actions.wiringView.wait_sidebar_ready()(autoAction, null);

    // open component sidebar both inactive and active branches
    const sidebarBtn = document.createElement('button');
    const typeBtn = document.createElement('button');
    let sidebarClicks = 0;
    let typeClicks = 0;
    sidebarBtn.click = () => {
        sidebarClicks += 1;
        sidebarBtn.classList.add('active');
    };
    typeBtn.click = () => {
        typeClicks += 1;
        typeBtn.classList.add('active');
    };

    Utils.basic_selectors.toolbar_button = () => () => sidebarBtn;
    Utils.basic_selectors.button = (selector) => () => selector.includes('btn-list') ? typeBtn : sidebarBtn;
    Utils.basic_actions.wiringView.open_component_sidebar('widget')(autoAction, null);
    Utils.basic_actions.wiringView.open_component_sidebar('widget')(autoAction, null);
    Utils.basic_actions.wiringView.open_component_sidebar('operator')(autoAction, null);

    await flushScheduled(scheduledTimeouts);
    scheduledIntervals.forEach((callback) => {
        callback();
        callback();
        callback();
    });

    assert.equal(clickTarget.clicked, 1);
    assert.equal(scrolled, 1);
    assert.deepEqual(Wirecloud.UserInterfaceManager.changedViews, ['wiring']);
    assert.equal(sidebarClicks, 1);
    assert.equal(typeClicks, 1);
    assert.equal(Wirecloud.LocalCatalogue.addComponentCalls[0].url, '/repo/static/tutorial-data/my_id.wgt');
    assert.equal(dispatchedKeyboard.key, 'Enter');
    assert.equal(autoAction.nextCalls > 5, true);
    assert.equal(autoAction.errorCalls, 1);
});

test('Tutorial.Utils basic_selectors return expected elements and null branches', () => {
    resetLegacyRuntime();
    const { Utils } = setupUtils();

    const plain = document.createElement('span');
    const button = document.createElement('button');
    button.classList.add('se-btn');
    plain.parentElement = button;

    const menuA = document.createElement('div');
    const menuB = document.createElement('div');
    menuA.textContent = 'one';
    menuB.textContent = 'target';

    const resourceTitle = document.createElement('div');
    resourceTitle.textContent = 'My Widget';
    const resourcePanel = document.createElement('div');
    resourcePanel.querySelector = () => ({ main: true });
    resourcePanel.appendChild(resourceTitle);

    const component = document.createElement('div');
    const endpoint = document.createElement('div');
    endpoint.setAttribute('data-name', 'slot');
    const anchor = document.createElement('div');
    anchor.classList.add('endpoint-anchor');
    endpoint.querySelector = () => anchor;
    component.querySelectorAll = () => [endpoint];

    const behaviour = document.createElement('div');
    behaviour.querySelector = () => ({ prefs: true });

    const group = document.createElement('div');
    group.querySelectorAll = () => [{ comp: 1 }, { comp: 2 }];

    const widgetNode = document.createElement('div');
    const headingText = document.createElement('span');
    headingText.textContent = 'Shown';
    widgetNode.querySelector = () => headingText;

    document.querySelector = (selector) => {
        if (selector === '#wirecloud_header .wc-back-button') return plain;
        if (selector === '#wirecloud_header .wc-toolbar .demo-btn') return plain;
        if (selector === '.exists') return plain;
        if (selector === '.btn-direct') return button;
        if (selector === '.missing') return null;
        if (selector === '.wiring-diagram .component-widget[data-id="321"]') return component;
        if (selector === '.wc-workspace-wiring .we-panel-components .we-component-group[data-id="group"]') return group;
        return null;
    };

    document.querySelectorAll = (selector) => {
        if (selector === '.wc-workspace .we-component-meta .panel-heading') return [resourceTitle];
        if (selector === '.se-popup-menu-item') return [menuA, menuB];
        if (selector === '.wc-workspace .wc-widget') return [widgetNode];
        if (selector === '.we-panel-behaviours .behaviour') return [behaviour];
        return [];
    };

    Wirecloud.UserInterfaceManager.currentWindowMenu.form.fieldInterfaces.myField = {
        inputElement: { inputElement: { id: 'field-input' } },
    };

    const buttonSelector = Utils.basic_selectors.button('.exists');
    const directButtonSelector = Utils.basic_selectors.button('.btn-direct');
    const missingSelector = Utils.basic_selectors.button('.missing');

    assert.equal(Utils.basic_selectors.back_button()(), button);
    assert.equal(buttonSelector(), button);
    assert.equal(directButtonSelector(), button);
    assert.equal(missingSelector(), null);
    assert.equal(Utils.basic_selectors.element('.x')(), null);
    assert.equal(Utils.basic_selectors.form_field('myField')().id, 'field-input');
    assert.equal(Utils.basic_selectors.mac_wallet_input()(), null);
    assert.equal(Utils.basic_selectors.mac_wallet_resource('my widget')().querySelector('.panel-body .wc-create-resource-component').main, true);
    assert.throws(() => Utils.basic_selectors.mac_wallet_resource('unknown')(), /parentNode/);
    assert.equal(Utils.basic_selectors.mac_wallet_resource_mainbutton('my widget')().main, true);
    assert.equal(Utils.basic_selectors.toolbar_button('demo-btn')(), button);
    assert.equal(Utils.basic_selectors.menu_item('target')(), menuB);
    assert.equal(Utils.basic_selectors.menu_item('missing')(), null);

    const workspaceWidget = Utils.basic_selectors.workspaceView.widget_by_title('Shown')();
    assert.equal(workspaceWidget, widgetNode);
    assert.equal(Utils.basic_selectors.workspaceView.widget_by_title('Nope')(), null);

    const wrappedElement = Utils.basic_selectors.workspaceView.widget_element(0, '.needle')();
    assert.equal(wrappedElement.widget.id, 321);
    assert.equal(wrappedElement.element.selector, '.needle');

    assert.equal(Utils.basic_selectors.wiringView.behaviour_engine()().name, 'behaviour-engine');
    assert.equal(Utils.basic_selectors.wiringView.connection_engine()().name, 'connection-engine');
    assert.equal(Utils.basic_selectors.wiringView.component_by_id('widget', 0)(), component);
    assert.equal(Utils.basic_selectors.wiringView.component_by_id('operator', 'abc')(), null);
    assert.equal(Utils.basic_selectors.wiringView.endpoint_by_name('widget', 0, 'source', 'slot')(), anchor);
    assert.equal(Utils.basic_selectors.wiringView.endpoint_by_name('widget', 0, 'source', 'missing')(), null);

    const prefsButton = Utils.basic_selectors.wiringView.show_behaviour_prefs_button(0)();
    assert.equal(prefsButton.prefs, true);
    assert.equal(Utils.basic_selectors.wiringView.create_behaviour_button()(), null);
    assert.equal(Utils.basic_selectors.wiringView.enable_behaviours_button()(), null);
    assert.equal(Utils.basic_selectors.wiringView.show_behaviours_button()(), null);
    assert.equal(Utils.basic_selectors.wiringView.sidebar_input()(), null);
    assert.equal(Utils.basic_selectors.wiringView.sidebarcomponentgroup_by_id('group')(), group);
    assert.deepEqual(Utils.basic_selectors.wiringView.sidebarcomponent_by_id('group', 1)(), { comp: 2 });

    document.querySelector = () => null;
    assert.equal(Utils.basic_selectors.wiringView.sidebarcomponent_by_id('group', 1)(), null);
});


