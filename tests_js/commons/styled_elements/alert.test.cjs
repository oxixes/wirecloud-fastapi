const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupAlert = () => {
    class StyledElement {
        constructor() {
            this.wrapperElement = document.createElement('div');
        }

        addClassName(className) {
            this.wrapperElement.classList.add(className);
            return this;
        }

        appendTo(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }
    }

    class Container extends StyledElement {
        constructor(options = {}) {
            super();
            this.wrapperElement = document.createElement('div');
            if (options.class) {
                this.wrapperElement.className = options.class;
            }
        }

        appendChild(content) {
            if (content instanceof StyledElement) {
                content.appendTo(this.wrapperElement);
            } else if (content != null) {
                this.wrapperElement.innerHTML = String(content);
            }
            return this;
        }

        clear() {
            this.wrapperElement.innerHTML = '';
            this.wrapperElement.textContent = '';
            return this;
        }

        insertInto(parentNode) {
            parentNode.appendChild(this.wrapperElement);
            return this;
        }
    }

    global.StyledElements = {
        StyledElement,
        Container,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Alert.js');
    return StyledElements.Alert;
};

test('StyledElements.Alert builds base role and state classes', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({
        state: 'danger',
        alignment: 'left',
        class: 'extra',
        title: 'Title',
        message: 'Message'
    });

    assert.equal(alert.wrapperElement.getAttribute('role'), 'alert');
    assert.equal(alert.wrapperElement.classList.contains('alert-danger'), true);
    assert.equal(alert.wrapperElement.classList.contains('se-alert-left'), true);
    assert.equal(alert.wrapperElement.classList.contains('extra'), true);
});

test('StyledElements.Alert skips empty state class', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({
        state: '   ',
        title: 'Title',
        message: 'Message'
    });

    assert.equal(alert.wrapperElement.classList.contains('alert-   '), false);
});

test('StyledElements.Alert defaults to warning state when options are missing', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert();

    assert.equal(alert.wrapperElement.classList.contains('alert-warning'), true);
});

test('StyledElements.Alert addNote appends note content from plain strings', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({title: '', message: ''});

    const blockquote = alert.addNote('<b>note</b>');

    assert.equal(blockquote.getAttribute('role'), 'note');
    assert.equal(blockquote.innerHTML, '<b>note</b>');
});

test('StyledElements.Alert addNote appends note content from StyledElement instances', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({title: '', message: ''});
    const note = new StyledElements.StyledElement();
    note.wrapperElement.className = 'note-styled';

    const blockquote = alert.addNote(note);

    assert.equal(blockquote.childNodes.length, 1);
    assert.equal(blockquote.childNodes[0].className, 'note-styled');
});

test('StyledElements.Alert setMessage replaces body content', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({title: '', message: 'old'});

    alert.setMessage('new-message');

    assert.equal(alert.body.wrapperElement.innerHTML, 'new-message');
});

test('StyledElements.Alert show and hide update display style', () => {
    resetLegacyRuntime();
    const Alert = setupAlert();
    const alert = new Alert({title: '', message: ''});

    alert.hide();
    assert.equal(alert.wrapperElement.style.display, 'none');
    alert.show();
    assert.equal(alert.wrapperElement.style.display, '');
});
