const test = require('node:test');
const assert = require('node:assert/strict');
const { loadLegacyScript, resetLegacyRuntime } = require('../support/legacy-runtime.cjs');

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

class FakeButton {
    constructor(options = {}) {
        this.options = options;
        this.listeners = {};
        this.disabled = false;
    }

    addEventListener(type, listener) {
        if (this.listeners[type] == null) {
            this.listeners[type] = [];
        }
        this.listeners[type].push(listener);
    }

    trigger(type, ...args) {
        (this.listeners[type] || []).forEach((listener) => listener(this, ...args));
    }

    setDisabled(value) {
        this.disabled = value;
    }

    disable() {
        this.disabled = true;
        return this;
    }

    enable() {
        this.disabled = false;
        return this;
    }

    focus() {
        this.focused = true;
        return this;
    }

    insertInto(parent) {
        parent.appendChild(document.createElement('button'));
    }
}

class FakeFileButton extends FakeButton {}

class FakeGUIBuilder {
    parse(_template, context) {
        const wrapper = {
            insertInto: (target) => {
                const button = context.uploadfilebutton();
                target.appendChild(document.createElement('section'));
                target._uploadButton = button;
            },
        };
        return wrapper;
    }
}

class FakeModelSource {
    constructor() {
        this.elements = [];
    }

    get length() {
        return this.elements.length;
    }

    getElements() {
        return this.elements;
    }

    addElement(entry) {
        this.elements.push(entry);
    }

    changeElements(entries) {
        this.elements = entries;
    }
}

class FakeModelTable {
    constructor(columns, options) {
        this.columns = columns;
        this.options = options;
        this.source = new FakeModelSource();
        this.statusBar = document.createElement('div');
    }

    insertInto(parent) {
        parent.appendChild(document.createElement('table'));
    }

    repaint() {
        this.repainted = true;
    }
}

class FakeWindowMenu {
    constructor(_title, className) {
        this.htmlElement = document.createElement('div');
        this.htmlElement.className = className;
        this.windowContent = document.createElement('div');
        this.windowBottom = document.createElement('div');
        this.htmlElement.appendChild(this.windowContent);
        this.htmlElement.appendChild(this.windowBottom);
    }

    show() {
        this.wasShown = true;
    }

    hide() {
        this.wasHidden = true;
    }

    _closeListener() {
        this.wasClosed = true;
    }
}

class FakeTask {
    constructor(_title, tasks) {
        this.promise = Promise.all(tasks);
    }

    catch(listener) {
        return this.promise.catch(listener);
    }

    then(listener) {
        return this.promise.then(listener);
    }
}

class FakeFragment {
    constructor(children = []) {
        this.children = children;
    }
}

const createEnvironment = () => {
    resetLegacyRuntime();

    const addComponentCalls = [];
    const monitored = [];
    const refreshCalls = [];
    const messages = [];

    global.StyledElements = {
        GUIBuilder: FakeGUIBuilder,
        FileButton: FakeFileButton,
        ModelTable: FakeModelTable,
        Button: FakeButton,
        Fragment: FakeFragment,
    };

    global.Wirecloud = {
        Utils: {
            gettext: (text) => text,
            formatSize: (size) => `${size}B`,
            preventDefaultListener: () => {},
        },
        constants: {
            LOGGING: {
                ERROR_MSG: 'error',
            },
        },
        currentTheme: {
            templates: {
                'wirecloud/catalogue/modals/upload': '<upload/>',
            },
        },
        Task: FakeTask,
        UserInterfaceManager: {
            monitorTask: (task) => monitored.push(task),
        },
        ui: {
            WindowMenu: FakeWindowMenu,
            MessageWindowMenu: class MessageWindowMenu {
                constructor(message, level) {
                    this.message = message;
                    this.level = level;
                }

                show() {
                    messages.push([this.message, this.level]);
                }
            },
            WirecloudCatalogue: {},
        },
    };

    loadLegacyScript('src/wirecloud/catalogue/static/js/wirecloud/ui/WirecloudCatalogue/UploadWindowMenu.js');

    const catalogue = {
        addComponent: (options) => {
            addComponentCalls.push(options.file.name);
            if (String(options.file.name).includes('bad')) {
                return Promise.reject(new Error('broken package'));
            }
            return Promise.resolve({ ok: true });
        },
    };

    const menu = new global.Wirecloud.ui.WirecloudCatalogue.UploadWindowMenu({
        catalogue,
        mainview: {
            viewsByName: {
                search: {
                    refresh_if_needed: () => refreshCalls.push('refresh'),
                },
            },
        },
    });

    return { menu, addComponentCalls, monitored, refreshCalls, messages };
};

const createDnDEvent = (hasContains, hasFiles, effectAllowed = 'copy') => ({
    type: 'dragover',
    dataTransfer: {
        effectAllowed,
        dropEffect: '',
        types: hasContains
            ? { contains: (value) => hasFiles && value === 'Files' }
            : ['Text', ...(hasFiles ? ['Files'] : [])],
        files: [{ name: 'dragged.wgt', size: 1 }],
    },
    preventDefault() {},
    stopPropagation() {},
});

test('UploadWindowMenu covers file upload flow, drag-and-drop, and closing', async () => {
    const { menu, addComponentCalls, monitored, refreshCalls, messages } = createEnvironment();

    menu.show();
    menu.setFocus();
    assert.equal(menu.fileButton.focused, true);
    assert.equal(menu.fileTable.repainted, true);

    menu.fileButton.trigger('fileselect', [{ name: 'good.wgt', size: 10 }, { name: 'bad.wgt', size: 20 }]);
    assert.equal(menu.fileTable.source.length, 2);

    assert.equal(menu.fileTable.columns[1].contentBuilder({ size: 33 }), '33B');

    const removeButton = menu.fileTable.columns[2].contentBuilder({ file: menu.fileTable.source.getElements()[0].file });
    removeButton.trigger('click');
    assert.equal(menu.fileTable.source.length, 1);

    const addMoreButton = menu.fileTable.statusBar.childNodes.find((node) => typeof node.trigger === 'function');
    addMoreButton.trigger('fileselect', [{ name: 'added-later.wgt', size: 30 }]);
    assert.equal(menu.fileTable.source.length, 2);

    menu.removeFile({ name: 'unknown.wgt' });
    assert.equal(menu.fileTable.source.length, 2);
    const addedLaterEntry = menu.fileTable.source.getElements().find((entry) => entry.name === 'added-later.wgt');
    menu.removeFile(addedLaterEntry.file);
    assert.equal(menu.fileTable.source.length, 1);

    const dragWithContains = createDnDEvent(true, true, 'move');
    menu.htmlElement.dispatchEvent(dragWithContains);
    assert.equal(menu.htmlElement.classList.contains('drag-hover'), true);
    global.document.listeners.drop[0]({ preventDefault() {} });

    const dragFallback = createDnDEvent(false, true, 'linkMove');
    menu.htmlElement.dispatchEvent(dragFallback);
    global.document.listeners.dragleave[0]({ stopPropagation() {} });
    assert.equal(menu.htmlElement.classList.contains('drag-hover'), false);

    const dragCopy = createDnDEvent(true, true, 'copy');
    menu.htmlElement.dispatchEvent(dragCopy);
    assert.equal(dragCopy.dataTransfer.dropEffect, 'copy');
    global.document.listeners.drop[0]({ preventDefault() {} });

    menu.windowContent.dispatchEvent({
        type: 'drop',
        dataTransfer: { files: [{ name: 'drop-ok.wgt', size: 5 }] },
        stopPropagation() {},
        preventDefault() {},
    });
    assert.equal(menu.fileTable.source.length >= 2, true);

    menu.acceptButton.trigger('click');
    await flush();
    await flush();

    assert.equal(addComponentCalls.includes('bad.wgt'), true);
    assert.equal(monitored.length, 1);
    assert.equal(refreshCalls.length, 1);
    assert.equal(messages.length, 1);
    assert.equal(menu.wasHidden, true);

    menu._closeListener();
    assert.equal(menu.fileTable.source.length, 0);
    assert.equal(menu.wasClosed, true);
});






