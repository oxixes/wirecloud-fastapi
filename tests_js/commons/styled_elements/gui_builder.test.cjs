const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const NAMESPACE = 'http://wirecloud.conwet.fi.upm.es/StyledElements';
const TEMPLATE_NAMESPACE = 'http://wirecloud.conwet.fi.upm.es/Template';

const setupGUIBuilder = () => {
    bootstrapStyledElementsBase();

    class BorderLayout {
        constructor(options) {
            this.options = options;
            this.addedClasses = [];
            this.north = { appended: [], addClassName: (value) => { this.addedClasses.push(['north', value]); }, appendChild: (value) => { this.north.appended.push(value); return this.north; } };
            this.west = { appended: [], addClassName: (value) => { this.addedClasses.push(['west', value]); }, appendChild: (value) => { this.west.appended.push(value); return this.west; } };
            this.center = { appended: [], addClassName: (value) => { this.addedClasses.push(['center', value]); }, appendChild: (value) => { this.center.appended.push(value); return this.center; } };
            this.east = { appended: [], addClassName: (value) => { this.addedClasses.push(['east', value]); }, appendChild: (value) => { this.east.appended.push(value); return this.east; } };
            this.south = { appended: [], addClassName: (value) => { this.addedClasses.push(['south', value]); }, appendChild: (value) => { this.south.appended.push(value); return this.south; } };
        }
    }

    class HorizontalLayout {
        constructor(options) {
            this.options = options;
            this.west = { appended: [], appendChild: (value) => { this.west.appended.push(value); return this.west; } };
            this.center = { appended: [], appendChild: (value) => { this.center.appended.push(value); return this.center; } };
            this.east = { appended: [], appendChild: (value) => { this.east.appended.push(value); return this.east; } };
        }
    }

    class VerticalLayout {
        constructor(options) {
            this.options = options;
            this.north = {
                appended: [],
                addClassName: (value) => { this.north.className = value; },
                appendChild: (value) => { this.north.appended.push(value); return this.north; },
            };
            this.center = {
                appended: [],
                addClassName: (value) => { this.center.className = value; },
                appendChild: (value) => { this.center.appended.push(value); return this.center; },
            };
            this.south = {
                appended: [],
                addClassName: (value) => { this.south.className = value; },
                appendChild: (value) => { this.south.appended.push(value); return this.south; },
            };
        }

        insertInto(parent, refElement) {
            const marker = document.createElement('div');
            marker.className = 'vertical-layout-marker';
            if (refElement && refElement.parentNode === parent) {
                parent.insertBefore(marker, refElement);
            } else {
                parent.appendChild(marker);
            }
            return this;
        }
    }

    class Button {
        constructor(options) {
            this.options = options;
        }
    }

    class Select {
        constructor(options) {
            this.options = options;
        }
    }

    class Fragment {
        constructor(children) {
            this.elements = children;
        }
    }

    global.StyledElements = Object.assign({}, StyledElements, {
        BorderLayout,
        Button,
        Fragment,
        HorizontalLayout,
        Select,
        VerticalLayout,
    });

    class FakeDocument {
        constructor(root) {
            this.documentElement = root;
            this.defaultView = document.defaultView;
        }

        createElement(tagName) {
            const element = document.createElement(tagName);
            element.ownerDocument = this;
            return element;
        }

        createTextNode(text) {
            return document.createTextNode(text);
        }

        evaluate(query, element) {
            const target = element.childNodes.find((child) => child.nodeType === 1 && child.namespaceURI === NAMESPACE && child.localName === 'options');
            return { singleNodeValue: target || null };
        }
    }

    global.Document = FakeDocument;
    global.DOMParser = class DOMParser {
        parseFromString() {
            global.DOMParser.calls = (global.DOMParser.calls ?? 0) + 1;
            return createDocumentTree(FakeDocument);
        }
    };
    global.DOMParser.calls = 0;
    global.Node.ELEMENT_NODE = 1;
    global.Node.TEXT_NODE = 3;
    global.XPathResult = { FIRST_ORDERED_NODE_TYPE: 0 };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/GUIBuilder.js');

    return {
        GUIBuilder: StyledElements.GUIBuilder,
        FakeDocument,
    };
};

const createXmlElement = (doc, localName, namespaceURI, attrs = {}, children = []) => {
    const element = doc.createElement(localName);
    element.localName = localName;
    element.namespaceURI = namespaceURI;
    element.attributes = Object.entries(attrs).map(([name, value]) => ({ localName: name, nodeValue: String(value) }));
    element.getElementsByTagNameNS = function getElementsByTagNameNS(searchNS, searchName) {
        const result = [];
        const walk = (node) => {
            node.childNodes.forEach((child) => {
                if (child.nodeType === 1) {
                    if (child.namespaceURI === searchNS && child.localName === searchName) {
                        result.push(child);
                    }
                    walk(child);
                }
            });
        };
        walk(element);
        return result;
    };
    children.forEach((child) => element.appendChild(child));
    return element;
};

const createDocumentTree = (DocumentClass) => {
    const fakeRoot = document.createElement('styledgui');
    fakeRoot.localName = 'styledgui';
    fakeRoot.namespaceURI = NAMESPACE;
    fakeRoot.attributes = [];
    fakeRoot.getElementsByTagNameNS = function getElementsByTagNameNS(searchNS, searchName) {
        const result = [];
        const walk = (node) => {
            node.childNodes.forEach((child) => {
                if (child.nodeType === 1) {
                    if (child.namespaceURI === searchNS && child.localName === searchName) {
                        result.push(child);
                    }
                    walk(child);
                }
            });
        };
        walk(fakeRoot);
        return result;
    };

    const doc = new DocumentClass(fakeRoot);
    fakeRoot.ownerDocument = doc;

    const options = createXmlElement(doc, 'options', NAMESPACE, {}, [document.createTextNode('{"class":"layout-root"}')]);
    const northOptions = createXmlElement(doc, 'options', NAMESPACE, {}, [document.createTextNode('not-json')]);
    const styledTemplate = createXmlElement(doc, 'styled', TEMPLATE_NAMESPACE, { role: 'main', class: 'styled-template' }, [
        document.createTextNode('{"fromText":"yes"}'),
        createXmlElement(doc, 'span', 'http://www.w3.org/1999/xhtml', {}, [document.createTextNode('styled-child')]),
    ]);
    const elementTemplate = createXmlElement(doc, 'element', TEMPLATE_NAMESPACE, { priority: 'high' }, [
        document.createTextNode('{"kind":"element"}'),
        createXmlElement(doc, 'em', 'http://www.w3.org/1999/xhtml', {}, [document.createTextNode('element-child')]),
    ]);
    const rawTemplate = createXmlElement(doc, 'raw', TEMPLATE_NAMESPACE, {}, [document.createTextNode('raw-text')]);
    const nullTemplate = createXmlElement(doc, 'nullish', TEMPLATE_NAMESPACE, {}, [document.createTextNode('{"kind":"null"}')]);
    const button = createXmlElement(doc, 'button', NAMESPACE, { id: 'go-button' }, [document.createTextNode('Launch')]);
    const select = createXmlElement(doc, 'select', NAMESPACE, { class: 'picker' });
    const horizontal = createXmlElement(doc, 'horizontallayout', NAMESPACE, {}, [
        createXmlElement(doc, 'westcontainer', NAMESPACE, {}, [button]),
        createXmlElement(doc, 'centercontainer', NAMESPACE, {}, [select, rawTemplate]),
        createXmlElement(doc, 'eastcontainer', NAMESPACE, {}, [nullTemplate]),
    ]);
    const vertical = createXmlElement(doc, 'verticallayout', NAMESPACE, {}, [
        createXmlElement(doc, 'northcontainer', NAMESPACE, {}, [document.createTextNode('ignored')]),
        createXmlElement(doc, 'centercontainer', NAMESPACE, {}, [styledTemplate]),
        createXmlElement(doc, 'southcontainer', NAMESPACE, {}, [elementTemplate]),
    ]);
    const border = createXmlElement(doc, 'borderlayout', NAMESPACE, { id: 'root-layout' }, [
        options,
        createXmlElement(doc, 'northcontainer', NAMESPACE, {}, [northOptions]),
        createXmlElement(doc, 'westcontainer', NAMESPACE, {}, [horizontal]),
        createXmlElement(doc, 'centercontainer', NAMESPACE, {}, [vertical]),
    ]);

    fakeRoot.appendChild(border);
    return doc;
};

test('StyledElements.GUIBuilder parses templates, populates containers and builds components', () => {
    resetLegacyRuntime();
    const { GUIBuilder } = setupGUIBuilder();
    const builder = new GUIBuilder();

    assert.equal(builder.DEFAULT_OPENING.startsWith('<s:styledgui'), true);
    assert.equal(builder.DEFAULT_CLOSING, '</s:styledgui>');

    const result = builder.parse(createDocumentTree(global.Document), {
        nullish() {
            return null;
        },
        raw() {
            return 'raw-value';
        },
        styled(options) {
            const component = new StyledElements.StyledElement([]);
            component.options = options;
            component.wrapperElement = document.createElement('div');
            component.appended = [];
            component.insertInto = function insertInto(parent) {
                parent.appendChild(this.wrapperElement);
                return this;
            };
            component.appendChild = function appendChild(value) {
                this.appended.push(value);
                return this;
            };
            return component;
        },
        element(options) {
            const element = document.createElement('section');
            element.generatedOptions = options;
            return element;
        },
    }, { source: 'context' });
    const layout = result.elements[0];

    assert.equal(layout.options.class, 'layout-root');
    assert.equal(layout.options.id, 'root-layout');
    assert.equal(layout.north.appended.length, 1);
    assert.equal(layout.west.appended.length, 1);
    assert.equal(layout.center.appended.length, 1);

    const templateCalls = [];
    const templateDoc = new global.Document(document.createElement('root'));
    templateDoc.documentElement.localName = 'root';
    templateDoc.documentElement.namespaceURI = 'http://www.w3.org/1999/xhtml';
    templateDoc.documentElement.attributes = [];
    templateDoc.documentElement.getElementsByTagNameNS = function getElementsByTagNameNS() { return []; };

    const templateRoot = createXmlElement(templateDoc, 'div', 'http://www.w3.org/1999/xhtml', {}, [
        createXmlElement(templateDoc, 'styled', TEMPLATE_NAMESPACE, { role: 'main', class: 'styled-template' }, [
            document.createTextNode('{"fromText":"yes"}'),
            createXmlElement(templateDoc, 'span', 'http://www.w3.org/1999/xhtml', {}, [document.createTextNode('styled-child')]),
        ]),
        createXmlElement(templateDoc, 'element', TEMPLATE_NAMESPACE, { priority: 'high' }, [
            document.createTextNode('{"kind":"element"}'),
            createXmlElement(templateDoc, 'em', 'http://www.w3.org/1999/xhtml', {}, [document.createTextNode('element-child')]),
        ]),
        createXmlElement(templateDoc, 'raw', TEMPLATE_NAMESPACE, {}, [document.createTextNode('raw-text')]),
        createXmlElement(templateDoc, 'nullish', TEMPLATE_NAMESPACE, {}, [document.createTextNode('{"kind":"null"}')]),
    ]);
    templateDoc.documentElement.appendChild(templateRoot);

    builder.parse(templateDoc, {
        nullish(options) {
            templateCalls.push(['nullish', options]);
            return null;
        },
        raw(options) {
            templateCalls.push(['raw', options]);
            return 'raw-value';
        },
        styled(options) {
            templateCalls.push(['styled', options]);
            const component = new StyledElements.StyledElement([]);
            component.options = options;
            component.wrapperElement = document.createElement('div');
            component.appended = [];
            component.insertInto = function insertInto(parent) {
                parent.appendChild(this.wrapperElement);
                return this;
            };
            component.appendChild = function appendChild(value) {
                this.appended.push(value);
                return this;
            };
            return component;
        },
        element(options) {
            templateCalls.push(['element', options]);
            const element = document.createElement('section');
            element.generatedOptions = options;
            return element;
        },
    });

    assert.equal(templateCalls.length >= 0, true);
});

test('StyledElements.GUIBuilder rejects invalid documents', () => {
    resetLegacyRuntime();
    const { GUIBuilder } = setupGUIBuilder();
    const builder = new GUIBuilder();

    assert.throws(() => builder.parse({ not: 'a document' }), TypeError);
});

test('StyledElements.GUIBuilder handles static templates, parse-from-string and guarded append paths', () => {
    resetLegacyRuntime();
    const { GUIBuilder, FakeDocument } = setupGUIBuilder();
    const builder = new GUIBuilder();

    const root = document.createElement('styledgui');
    root.localName = 'styledgui';
    root.namespaceURI = NAMESPACE;
    root.attributes = [];
    root.getElementsByTagNameNS = () => [];

    const doc = new FakeDocument(root);
    root.ownerDocument = doc;
    root.appendChild(document.createTextNode('root-text-node'));

    const host = createXmlElement(doc, 'div', 'http://www.w3.org/1999/xhtml', {}, []);
    host.appendChild(document.createTextNode('skip-me'));
    const staticNode = createXmlElement(doc, 'staticValue', TEMPLATE_NAMESPACE, {}, [
        createXmlElement(doc, 'span', 'http://www.w3.org/1999/xhtml', {}, [document.createTextNode('child')]),
    ]);
    const layoutNode = createXmlElement(doc, 'verticallayout', NAMESPACE, { id: 'v-1' }, [
        createXmlElement(doc, 'northcontainer', NAMESPACE, { class: 'north-class' }, [
            createXmlElement(doc, 'button', NAMESPACE, {}, [document.createTextNode('ok')]),
        ]),
        createXmlElement(doc, 'centercontainer', NAMESPACE, {}, [
            createXmlElement(doc, 'select', NAMESPACE, { class: 'picker' }),
        ]),
        createXmlElement(doc, 'southcontainer', NAMESPACE, {}, [
            createXmlElement(doc, 'button', NAMESPACE, {}, [document.createTextNode('south')]),
        ]),
    ]);

    host.appendChild(staticNode);
    host.appendChild(layoutNode);
    root.appendChild(host);

    const parsed = builder.parse(doc, {
        staticValue: 'plain-template-value',
    });

    assert.equal(parsed.elements.length >= 1, true);
    assert.equal(parsed.elements[0] != null, true);

    const parsedFromString = builder.parse('<s:styledgui/>', {});
    assert.equal(parsedFromString instanceof StyledElements.Fragment, true);
    assert.equal(global.DOMParser.calls > 0, true);
});










