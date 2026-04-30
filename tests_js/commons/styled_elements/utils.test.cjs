const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const createChildElementClass = () => class ChildElement extends StyledElements.StyledElement {

    constructor(tagName = 'div') {
        super();
        this.wrapperElement = document.createElement(tagName);
    }

};

test.beforeEach(() => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    StyledElements.Fragment = class Fragment {
        constructor(elements) {
            this.elements = elements;
        }
    };
});

test('StyledElements.Utils appendChild, prependChild, and removeChild handle styled and raw nodes', () => {
    const ChildElement = createChildElementClass();
    const parent = new ChildElement('section');
    const first = new ChildElement();
    const second = new ChildElement();
    const fragA = document.createElement('span');
    const fragB = document.createElement('em');
    const fragment = new StyledElements.Fragment([fragA, fragB]);

    StyledElements.Utils.appendChild(parent, first);
    StyledElements.Utils.appendChild(parent, 'text');
    StyledElements.Utils.appendChild(parent, document.createElement('label'), first);
    StyledElements.Utils.prependChild(parent, second, first);
    StyledElements.Utils.appendChild(parent, new ChildElement('aside'), fragment);
    StyledElements.Utils.prependChild(parent, 'lead', fragment);

    assert.equal(parent.get().childNodes[0], second.get());
    assert.equal(parent.get().childNodes[1], first.get());
    assert.equal(parent.get().childNodes.at(-1).textContent, 'lead');
    assert.equal(first.parentElement, parent);
    assert.equal(second.parentElement, parent);

    StyledElements.Utils.removeChild(parent, first);
    assert.equal(first.parentElement, null);

    const rawParent = document.createElement('div');
    const rawChild = document.createElement('span');
    StyledElements.Utils.appendChild(rawParent, rawChild);
    StyledElements.Utils.prependChild(rawParent, 'raw-text');
    StyledElements.Utils.appendChild(rawParent, document.createElement('i'), rawParent.childNodes[0]);
    StyledElements.Utils.prependChild(rawParent, document.createElement('b'), fragment);
    assert.equal(rawParent.childNodes[0].textContent, 'raw-text');
    StyledElements.Utils.removeChild(rawParent, rawChild);
    assert.equal(rawParent.childNodes.includes(rawChild), false);

    const mixedRawChild = document.createElement('strong');
    StyledElements.Utils.appendChild(parent, mixedRawChild);
    StyledElements.Utils.prependChild(parent, document.createElement('small'));
    StyledElements.Utils.removeChild(parent, mixedRawChild);
    assert.equal(parent.get().childNodes.includes(mixedRawChild), false);

    const wrapperless = new StyledElements.StyledElement();
    wrapperless.children = [document.createElement('u'), document.createElement('b')];
    StyledElements.Utils.appendChild(rawParent, wrapperless);
    assert.equal(rawParent.childNodes.includes(wrapperless.children[0]), true);
    assert.equal(rawParent.childNodes.includes(wrapperless.children[1]), true);
});

test('StyledElements.Utils object and collection helpers work as expected', async () => {
    const ChildElement = createChildElementClass();
    const target = { a: 1, b: 2 };
    assert.deepEqual(StyledElements.Utils.update(target, { a: 9, c: 3 }, null), { a: 9, b: 2 });
    assert.throws(() => StyledElements.Utils.update(null, { a: 1 }), /object argument must be an object/);

    assert.equal(StyledElements.Utils.gettext('hello'), 'hello');
    assert.equal(StyledElements.Utils.ngettext('one', 'many', 1), 'one');
    assert.equal(StyledElements.Utils.ngettext('one', 'many', 2), 'many');
    assert.equal(StyledElements.Utils.interpolate('%(greet)s %(name)s', { greet: 'Hi', name: 'Bob' }), 'Hi Bob');
    assert.equal(new StyledElements.Utils.Template('/%(id)s').evaluate({ id: '42' }), '/42');

    let stopped = false;
    let prevented = false;
    StyledElements.Utils.stopPropagationListener({ stopPropagation() { stopped = true; } });
    StyledElements.Utils.preventDefaultListener({ preventDefault() { prevented = true; } });
    assert.equal(stopped, true);
    assert.equal(prevented, true);

    assert.equal(StyledElements.Utils.callCallback((a, b) => a + b, 2, 3), 5);
    assert.equal(StyledElements.Utils.callCallback(() => { throw new Error('ignored'); }), undefined);
    assert.equal(StyledElements.Utils.callCallback(null, 1), undefined);

    const originalDocument = global.document;
    global.document = { fullscreenElement: 'full' };
    assert.equal(StyledElements.Utils.getFullscreenElement(), 'full');
    global.document = { msFullscreenElement: 'ms-full' };
    assert.equal(StyledElements.Utils.getFullscreenElement(), 'ms-full');
    global.document = { mozFullScreenElement: 'moz-full' };
    assert.equal(StyledElements.Utils.getFullscreenElement(), 'moz-full');
    global.document = { webkitFullscreenElement: 'wk-full' };
    assert.equal(StyledElements.Utils.getFullscreenElement(), 'wk-full');
    global.document = { fullscreenEnabled: true };
    assert.equal(StyledElements.Utils.isFullscreenSupported(), true);
    global.document = { mozFullScreenEnabled: false };
    assert.equal(StyledElements.Utils.isFullscreenSupported(), false);
    global.document = { webkitFullscreenEnabled: true };
    assert.equal(StyledElements.Utils.isFullscreenSupported(), true);
    global.document = originalDocument;

    const listenerTarget = new ChildElement();
    const callback = () => {};
    StyledElements.Utils.onFullscreenChange(listenerTarget, callback);
    StyledElements.Utils.removeFullscreenChangeCallback(listenerTarget, callback);
    StyledElements.Utils.onFullscreenChange(listenerTarget.get(), callback);
    StyledElements.Utils.removeFullscreenChangeCallback(listenerTarget.get(), callback);
    assert.equal(Array.isArray(document.listeners.fullscreenchange), true);

    assert.equal(StyledElements.Utils.removeWord('alpha beta gamma', 'beta'), 'alpha gamma');
    assert.equal(StyledElements.Utils.appendWord('alpha beta', 'beta'), 'alpha beta');
    assert.equal(StyledElements.Utils.prependWord('alpha beta', 'beta'), 'beta alpha');
    assert.equal(StyledElements.Utils.escapeRegExp('a+b?'), 'a\\+b\\?');
    assert.equal(StyledElements.Utils.escapeHTML('<b>bold</b>'), '&lt;b&gt;bold&lt;/b&gt;');

    const p1 = document.createElement('div');
    const p2 = document.createElement('div');
    p1.getBoundingClientRect = () => ({ left: 10, top: 30 });
    p2.getBoundingClientRect = () => ({ left: 4, top: 9 });
    assert.deepEqual(StyledElements.Utils.getRelativePosition(p1, p2), { x: 6, y: 21 });
    assert.deepEqual(StyledElements.Utils.getRelativePosition(p1, p1), { x: 0, y: 0 });

    assert.deepEqual(StyledElements.Utils.clone([1, { a: 2 }], true), [1, { a: 2 }]);
    assert.deepEqual(StyledElements.Utils.clone({ a: 1 }, false), { a: 1 });
    assert.equal(StyledElements.Utils.clone(7), 7);

    assert.deepEqual(StyledElements.Utils.cloneObject(null), {});
    assert.throws(() => StyledElements.Utils.cloneObject([]), /\[error description\]/);
    assert.deepEqual(StyledElements.Utils.cloneObject({ a: { b: 2 }, c: [1, 2], d: 3, e: null }), { a: { b: 2 }, c: [1, 2], d: 3, e: null });

    document.body.focus();
    assert.equal(StyledElements.Utils.hasFocus(document.body), true);

    assert.equal(StyledElements.Utils.isPlainObject({}), true);
    assert.equal(StyledElements.Utils.isPlainObject(null), false);
    assert.equal(StyledElements.Utils.isPlainObject(new Date()), false);

    function Parent(name) { this.name = name; }
    Parent.prototype.describe = function describe() { return this.name; };
    function Child(name) { Parent.call(this, name); }
    StyledElements.Utils.inherit(Child, Parent, {
        shout() { return this.name.toUpperCase(); }
    });
    const inherited = new Child('alice');
    assert.equal(inherited instanceof Parent, true);
    assert.equal(inherited.shout(), 'ALICE');

    assert.equal(StyledElements.Utils.highlight('Hello world', 'world'), 'Hello <strong class=\"text-highlighted\">world</strong>');
    assert.equal(StyledElements.Utils.capitalize('wirecloud'), 'Wirecloud');
    assert.equal(StyledElements.Utils.formatSize(null), 'N/A');
    assert.equal(StyledElements.Utils.formatSize(1024), '1 KiB');

    assert.deepEqual(StyledElements.Utils.extractModifiers({ altKey: true, ctrlKey: false, metaKey: true, shiftKey: false }), {
        altKey: true,
        ctrlKey: false,
        metaKey: true,
        shiftKey: false
    });
    let propagationStops = 0;
    StyledElements.Utils.stopInputKeydownPropagationListener({
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        key: 'a',
        stopPropagation() { propagationStops += 1; }
    });
    StyledElements.Utils.stopInputKeydownPropagationListener({
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        key: 'Enter',
        stopPropagation() { propagationStops += 1; }
    });
    StyledElements.Utils.stopInputKeydownPropagationListener({
        altKey: false,
        ctrlKey: false,
        metaKey: false,
        shiftKey: false,
        key: 'Backspace',
        stopPropagation() { propagationStops += 1; }
    });
    assert.equal(propagationStops, 2);

    assert.equal(StyledElements.Utils.isEmpty(null), true);
    assert.equal(StyledElements.Utils.isEmpty({}), true);
    assert.equal(StyledElements.Utils.isEmpty({ a: 1 }), false);
    assert.deepEqual(StyledElements.Utils.values({ one: 1, two: 2 }).sort(), [1, 2]);

    const setA = new Set([1]);
    const setB = new Set([2, 3]);
    assert.equal(StyledElements.Utils.setupdate(setA, setB), setA);
    assert.deepEqual(Array.from(setA.values()).sort(), [1, 2, 3]);

    const arr = [1, 2, 3];
    StyledElements.Utils.removeFromArray(arr, 2);
    StyledElements.Utils.removeFromArray(arr, 9);
    assert.deepEqual(arr, [1, 3]);

    assert.equal(StyledElements.Utils.normalizeKey({ key: 'Spacebar', altKey: false }), ' ');
    assert.equal(StyledElements.Utils.normalizeKey({ key: '', altKey: true, keyCode: 13 }), 'Enter');

    const element = document.createElement('div');
    assert.equal(StyledElements.Utils.isElement(element), true);
    assert.equal(StyledElements.Utils.isElement({}), false);

    assert.equal(await StyledElements.Utils.timeoutPromise(Promise.resolve('ok'), 10), 'ok');
    assert.equal(await StyledElements.Utils.timeoutPromise(new Promise(() => {}), 0, 'fallback'), 'fallback');
    await assert.rejects(StyledElements.Utils.timeoutPromise(new Promise(() => {}), 0), /Timed out in 0ms/);
});

test('StyledElements.Utils updateObject merges according to source types', () => {
    function Base() {}
    function Derived() {}
    StyledElements.Utils.inherit(Derived, Base);

    const merged = StyledElements.Utils.updateObject(
        {
            nullable: null,
            fn: Base,
            plain: { a: 1 },
            arr: [1],
            scalar: 3,
        },
        {
            nullable: null,
            fn: Derived,
            plain: { b: 2 },
            arr: [2, 3],
            scalar: 5,
        }
    );

    assert.equal(merged.nullable, null);
    assert.equal(merged.fn, Derived);
    assert.deepEqual(merged.plain, { a: 1, b: 2 });
    assert.deepEqual(merged.arr, [1, 2, 3]);
    assert.equal(merged.scalar, 5);

    const arraysFromNull = StyledElements.Utils.updateObject({ arr: null }, { arr: [9] });
    assert.deepEqual(arraysFromNull.arr, [9]);

    function Left() {}
    function Right() {}
    const unchangedFn = StyledElements.Utils.updateObject({ fn: Left }, { fn: Right });
    assert.equal(unchangedFn.fn, Left);
    const scalarMismatch = StyledElements.Utils.updateObject({ scalar: 1 }, { scalar: 'two' });
    assert.equal(scalarMismatch.scalar, 1);

    assert.throws(() => StyledElements.Utils.updateObject({ fn: {} }, { fn: Right }), /Cannot access 'found' before initialization/);
});

test('StyledElements.Utils.waitTransition resolves for detached, hidden, and transitioned elements', async () => {
    const detached = document.createElement('div');
    await StyledElements.Utils.waitTransition(detached);

    const hidden = document.createElement('div');
    document.body.appendChild(hidden);
    hidden.style.display = 'none';
    await StyledElements.Utils.waitTransition(hidden);

    const visible = document.createElement('div');
    document.body.appendChild(visible);
    visible.style.display = 'block';
    const pending = StyledElements.Utils.waitTransition(visible);
    visible.dispatchEvent({ type: 'transitionend' });
    await pending;
});
