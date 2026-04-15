const test = require('node:test');
const assert = require('node:assert/strict');
const { loadLegacyScript, resetLegacyRuntime } = require('../support/legacy-runtime.cjs');

class FakeAlternative {
    constructor(_id, options) {
        this.options = options;
        this.children = [];
    }

    clear() {
        this.children = [];
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }
}

class FakeSelect {
    constructor() {
        this.listeners = {};
        this.entries = [];
        this.value = null;
    }

    addEntries(entries) {
        this.entries = entries;
    }

    setDisabled(disabled) {
        this.disabled = disabled;
    }

    setValue(value) {
        this.value = value;
    }

    getValue() {
        return this.value;
    }

    addEventListener(type, listener) {
        this.listeners[type] = listener;
    }

    emit(type) {
        if (this.listeners[type]) {
            this.listeners[type](this);
        }
    }
}

class FakeTab {
    constructor(label) {
        this.label = label;
        this.listeners = {};
        this.children = [];
    }

    addEventListener(type, listener) {
        this.listeners[type] = listener;
    }

    appendChild(child) {
        this.children.push(child);
    }

    clear() {
        this.children = [];
    }

    disable() {
        this.disabled = true;
    }

    enable() {
        this.disabled = false;
    }

    show() {
        if (this.listeners.show) {
            this.listeners.show(this);
        }
    }
}

class FakeNotebook {
    constructor() {
        this.listeners = {};
        this.tabs = [];
        this.visibleTab = { label: 'Main Info' };
    }

    addEventListener(type, listener) {
        this.listeners[type] = listener;
    }

    addButton(button) {
        this.select = button;
    }

    createTab(options) {
        const tab = new FakeTab(options.label);
        this.tabs.push(tab);
        return tab;
    }

    getTabByLabel(label) {
        return this.tabs.find((tab) => tab.label === label) || this.tabs[0];
    }

    goToTab(tab, options) {
        this.visibleTab = tab;
        if (this.listeners.changed) {
            this.listeners.changed(this, null, tab, options?.context);
        }
    }
}

class FakeResourcePainter {
    constructor(_mainview, _template, _owner, extraContext) {
        this.extraContext = extraContext;
    }

    paint(resource) {
        return { painted: resource.uri };
    }
}

const createEnv = () => {
    resetLegacyRuntime();

    const requests = [];
    const pushedStates = [];
    const dispatched = [];
    const commands = [];

    global.StyledElements = {
        Alternative: FakeAlternative,
        Notebook: FakeNotebook,
        Select: FakeSelect,
    };

    global.Wirecloud = {
        Utils: { gettext: (text) => text },
        ui: {
            ResourcePainter: FakeResourcePainter,
            WirecloudCatalogue: {},
        },
        currentTheme: {
            templates: {
                'wirecloud/catalogue/main_resource_details': '<main/>',
                'wirecloud/catalogue/resource_details': '<details/>',
            },
        },
        HistoryManager: {
            pushState: (state) => pushedStates.push(state),
        },
        io: {
            makeRequest: (url, options) => {
                requests.push(url);
                options.onSuccess({ responseText: `<h1>${url}</h1>` });
                options.onComplete();
            },
        },
        dispatchEvent: (eventName) => dispatched.push(eventName),
    };

    loadLegacyScript('src/wirecloud/catalogue/static/js/wirecloud/ui/WirecloudCatalogue/ResourceDetailsView.js');

    const catalogue = {
        RESOURCE_CHANGELOG_ENTRY: {
            evaluate: (resource) => `/changelog/${resource.uri}`,
        },
    };

    const mainView = {
        catalogue,
        buildStateData: () => ({ from: 'mainview' }),
        createUserCommand: (name, resource) => () => commands.push([name, resource.version.text]),
    };

    const view = new global.Wirecloud.ui.WirecloudCatalogue.ResourceDetailsView('details', { catalogue: mainView });
    return { view, requests, pushedStates, dispatched, commands };
};

const makeResource = () => ({
    uri: 'acme/widget/1.0',
    version: { text: '1.0' },
    doc: 'guide.md',
    changelog: 'changes.md',
    catalogue: {
        RESOURCE_USERGUIDE_ENTRY: {
            evaluate: (resource) => `/doc/${resource.uri}`,
        },
    },
    getAllVersions: () => [{ text: '1.0' }, { text: '0.9' }],
    changeVersion(next) {
        this.version = { text: next };
    },
});

test('ResourceDetailsView covers details, tabs, and state handling', () => {
    const { view, requests, pushedStates, dispatched, commands } = createEnv();
    const resource = makeResource();

    const detailsBuilder = view.resource_details_painter.extraContext(resource).details;
    const notebook = detailsBuilder();
    assert.equal(notebook.tabs.length >= 3, true);

    notebook.listeners.changed(notebook, null, notebook.tabs[0], {});
    assert.deepEqual(pushedStates[0], { from: 'mainview' });

    notebook.listeners.changed(notebook, null, notebook.tabs[0], { init: true });
    assert.equal(pushedStates.length, 1);

    notebook.select.setValue('0.9');
    notebook.select.emit('change');
    assert.deepEqual(commands[0], ['showDetails', '0.9']);

    notebook.tabs[1].show();
    notebook.tabs[2].show();
    assert.deepEqual(requests, ['/doc/acme/widget/1.0', '/changelog/acme/widget/1.0']);

    view.currentNotebook = notebook;
    view.currentEntry = resource;
    const state = {};
    view.buildStateData(state);
    assert.deepEqual(state, { resource: 'acme/widget/1.0', tab: notebook.visibleTab.label });

    view.paint(resource);
    view.paint(resource, { tab: 'Change Log' });
    assert.equal(dispatched.includes('viewcontextchanged'), true);

    const nestedMainView = {
        mainview: {
            buildStateData: () => ({ nested: true }),
        },
        catalogue: view.mainview.catalogue,
        createUserCommand: view.mainview.createUserCommand,
    };
    view.mainview = nestedMainView;
    notebook.listeners.changed(notebook, null, notebook.tabs[0], {});
    assert.deepEqual(pushedStates.at(-1), { nested: true });
});


