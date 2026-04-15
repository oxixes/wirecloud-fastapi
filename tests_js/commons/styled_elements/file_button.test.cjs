const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupFileButton = () => {
    class Event {}

    class Button {
        constructor() {
            this.wrapperElement = document.createElement('button');
            this.events = {};
            this.dispatched = [];
            this.destroyCalls = 0;
        }

        dispatchEvent(name, ...args) {
            this.dispatched.push({name, args});
        }

        destroy() {
            this.destroyCalls += 1;
        }
    }

    global.StyledElements = {
        Event,
        Button,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/FileButton.js');
    return StyledElements.FileButton;
};

test('StyledElements.FileButton configures file input defaults', () => {
    resetLegacyRuntime();
    const FileButton = setupFileButton();
    const button = new FileButton();

    assert.equal(button.inputElement.getAttribute('type'), 'file');
    assert.equal(button.inputElement.getAttribute('tabindex'), '-1');
    assert.equal(button.inputElement.multiple, true);
    assert.equal(button.events.fileselect instanceof StyledElements.Event, true);
});

test('StyledElements.FileButton supports disabling multiple selection', () => {
    resetLegacyRuntime();
    const FileButton = setupFileButton();
    const button = new FileButton({multiple: false});

    assert.equal(button.inputElement.multiple, false);
});

test('StyledElements.FileButton dispatches fileselect when files are selected', () => {
    resetLegacyRuntime();
    const FileButton = setupFileButton();
    const button = new FileButton();
    const files = [{name: 'a.txt'}];
    button.inputElement.files = files;
    button.inputElement.value = 'fake-path';

    button.inputElement.dispatchEvent({type: 'change'});

    assert.equal(button.dispatched[0].name, 'fileselect');
    assert.equal(button.dispatched[0].args[0], files);
    assert.equal(button.inputElement.value, '');
});

test('StyledElements.FileButton ignores change events when files is missing', () => {
    resetLegacyRuntime();
    const FileButton = setupFileButton();
    const button = new FileButton();
    button.inputElement.files = null;
    button.inputElement.value = 'keep';

    button.inputElement.dispatchEvent({type: 'change'});

    assert.equal(button.dispatched.length, 0);
    assert.equal(button.inputElement.value, 'keep');
});

test('StyledElements.FileButton destroy removes listener and calls parent destroy', () => {
    resetLegacyRuntime();
    const FileButton = setupFileButton();
    const button = new FileButton();

    button.destroy();

    assert.equal(button._onchange, undefined);
    assert.equal(button.destroyCalls, 1);
});
