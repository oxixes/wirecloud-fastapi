const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupCodeArea = () => {
    class InputElement {
        constructor(defaultValue) {
            this.defaultValue = defaultValue;
            this.events = {
                blur: { listeners: [] },
                change: { listeners: [] },
                focus: { listeners: [] },
            };
            this.dispatched = [];
        }

        dispatchEvent(name) {
            this.dispatched.push(name);
        }

        destroy() {
            this.destroyed = true;
        }
    }

    class Button {
        constructor() {
            this.listeners = {};
            this.iconOps = [];
            this.titles = [];
            this.destroyCalls = 0;
        }

        addEventListener(name, listener) {
            this.listeners[name] = listener;
            return this;
        }

        insertInto(parent) {
            parent.appendChild(document.createElement('button'));
            return this;
        }

        removeIconClassName(classList) {
            this.iconOps.push(['remove', classList]);
            return this;
        }

        addIconClassName(className) {
            this.iconOps.push(['add', className]);
            return this;
        }

        setTitle(title) {
            this.titles.push(title);
            return this;
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    const callbackStore = {
        onMouseDown: null,
        onDidChangeContent: null,
        onDidFocusEditorWidget: null,
        onDidBlurEditorWidget: null,
    };

    const editor = {
        value: 'initial',
        hasWidgetFocus: false,
        layoutCalls: [],
        updateOptionsCalls: [],
        focused: 0,
        disposed: 0,
        selection: null,
        onMouseDown(callback) {
            callbackStore.onMouseDown = callback;
        },
        onDidFocusEditorWidget(callback) {
            callbackStore.onDidFocusEditorWidget = callback;
        },
        onDidBlurEditorWidget(callback) {
            callbackStore.onDidBlurEditorWidget = callback;
        },
        getModel() {
            return {
                onDidChangeContent(callback) {
                    callbackStore.onDidChangeContent = callback;
                },
                getFullModelRange() {
                    return { full: true };
                },
            };
        },
        getValue() {
            return this.value;
        },
        setValue(value) {
            this.value = value;
        },
        updateOptions(options) {
            this.updateOptionsCalls.push(options);
        },
        layout(args) {
            this.layoutCalls.push(args || null);
        },
        focus() {
            this.focused += 1;
        },
        setSelection(range) {
            this.selection = range;
        },
        dispose() {
            this.disposed += 1;
        },
    };

    global.requestAnimationFrame = (callback) => callback();
    global.StyledElements = {
        InputElement,
        Button,
        Utils: {
            merge(base, extra) {
                return Object.assign({}, base, extra || {});
            },
            gettext(text) {
                return text;
            },
            stopPropagationListener(event) {
                event.stopped = true;
            },
        },
    };

    global.__wirecloud_test_imports['monaco-editor/esm/vs/editor/editor.api'] = {
        editor: {
            create() {
                return editor;
            },
        },
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/CodeArea.js');

    return {
        CodeArea: StyledElements.CodeArea,
        callbackStore,
        editor,
    };
};

test('StyledElements.CodeArea handles editor lifecycle, events and fullscreen toggle', () => {
    resetLegacyRuntime();
    const { CodeArea, callbackStore, editor } = setupCodeArea();

    const area = new CodeArea({
        initialValue: 'const x = 1;',
        class: 'custom',
        language: 'javascript',
        name: 'snippet',
        id: 'code-1',
    });

    callbackStore.onMouseDown({ event: { browserEvent: {} } });
    callbackStore.onDidChangeContent();
    callbackStore.onDidFocusEditorWidget();
    callbackStore.onDidBlurEditorWidget();

    assert.equal(area.wrapperElement.classList.contains('focused'), false);
    assert.deepEqual(area.dispatched, ['change', 'focus', 'blur']);

    assert.equal(area.getValue(), 'initial');
    area.setValue('updated');
    assert.equal(editor.value, 'updated');

    area.enable();
    area.disable();
    assert.deepEqual(editor.updateOptionsCalls, [{ readOnly: false }, { readOnly: true }]);

    editor.hasWidgetFocus = true;
    let blurred = 0;
    document.activeElement.blur = () => { blurred += 1; };
    area.blur();
    area.focus();
    area.select();

    assert.equal(blurred, 1);
    assert.equal(editor.focused, 1);
    assert.deepEqual(editor.selection, { full: true });

    const monacoRoot = document.createElement('div');
    monacoRoot.className = 'monaco-editor';
    monacoRoot.style.width = '100px';
    monacoRoot.style.height = '200px';
    area.wrapperElement.appendChild(monacoRoot);
    area.wrapperElement.querySelector = () => monacoRoot;

    area._fullscreenButton.listeners.click();
    assert.equal(area.wrapperElement.classList.contains('se-code-area-fullscreen'), true);

    area._fullscreenButton.listeners.click();
    assert.equal(area.wrapperElement.classList.contains('se-code-area-fullscreen'), false);
    assert.equal(monacoRoot.style.width, '');
    assert.equal(monacoRoot.style.height, '');

    area.wrapperElement.querySelector = () => null;
    area._fullscreenButton.listeners.click();
    area._fullscreenButton.listeners.click();

    assert.equal(editor.layoutCalls.length >= 4, true);
    assert.equal(area._fullscreenButton.titles.includes('Full screen'), true);
    assert.equal(area._fullscreenButton.titles.includes('Exit full screen'), true);

    area.destroy();
    assert.equal(editor.disposed, 1);
    assert.equal(area.destroyed, true);
});



