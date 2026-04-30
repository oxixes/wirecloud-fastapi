const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupAlternatives = () => {
    class StyledElement {
        constructor(events) {
            this.wrapperElement = document.createElement('div');
            this._events = {};
            (events || []).forEach((name) => {
                this._events[name] = [];
            });
        }

        addEventListener(name, listener) {
            if (!this._events[name]) {
                this._events[name] = [];
            }
            this._events[name].push(listener);
            return this;
        }

        dispatchEvent(name, ...args) {
            (this._events[name] || []).forEach((listener) => listener(...args));
        }
    }

    class Alternative {
        constructor(altId, options) {
            this.altId = altId;
            this.options = options;
            this.wrapperElement = document.createElement('div');
            this.classNames = new Set();
            this.visible = false;
            this.repaintCalls = [];
            this.parentElement = null;
        }

        _normalizeClasses(classList) {
            if (Array.isArray(classList)) {
                return classList;
            }
            return String(classList || '').split(/\s+/).filter(Boolean);
        }

        addClassName(classList) {
            this._normalizeClasses(classList).forEach((name) => {
                this.classNames.add(name);
                this.wrapperElement.classList.add(name);
            });
            return this;
        }

        removeClassName(classList) {
            this._normalizeClasses(classList).forEach((name) => {
                this.classNames.delete(name);
                this.wrapperElement.classList.remove(name);
            });
            return this;
        }

        show() {
            this.visible = true;
            return this;
        }

        hide() {
            this.visible = false;
            return this;
        }

        setVisible(visible) {
            this.visible = !!visible;
            return this;
        }

        insertInto(parent) {
            parent.appendChild(this.wrapperElement);
            return this;
        }

        repaint(temporal) {
            this.repaintCalls.push(temporal);
            return this;
        }

        get() {
            return this.wrapperElement;
        }
    }

    class CommandQueue {
        constructor(context, initFunc) {
            this.context = context;
            this.initFunc = initFunc;
        }

        addCommand(command) {
            return Promise.resolve().then(() => this.initFunc(this.context, command));
        }
    }

    global.StyledElements = {
        StyledElement,
        Alternative,
        CommandQueue,
        Utils: {
            clone(value) {
                if (Array.isArray(value)) {
                    return value.slice(0);
                }
                return Object.assign({}, value);
            },
            merge(base, extra) {
                return Object.assign({}, base, extra || {});
            },
            update(base, extra) {
                return Object.assign({}, base, extra || {});
            },
            prependWord(word, base) {
                return [base, word].filter(Boolean).join(' ');
            },
            callCallback(callback, context, ...args) {
                if (typeof callback === 'function') {
                    callback.apply(context, args);
                }
            },
            waitTransition() {
                return Promise.resolve();
            },
            timeoutPromise(promise) {
                return promise;
            },
        },
    };

    const originalSetTimeout = global.setTimeout;
    global.setTimeout = (callback) => {
        callback();
        return 0;
    };

    loadLegacyScript('src/wirecloud/commons/static/js/StyledElements/Alternatives.js');

    return {
        Alternatives: StyledElements.Alternatives,
        Alternative,
        restoreTimers() {
            global.setTimeout = originalSetTimeout;
        },
    };
};

test('StyledElements.Alternatives constructor, getters, repaint and same-alternative transition path', async () => {
    resetLegacyRuntime();
    const { Alternatives, restoreTimers } = setupAlternatives();

    const alternatives = new Alternatives({
        id: 'alts',
        class: 'custom',
        full: true,
    });

    try {
        assert.equal(alternatives.wrapperElement.getAttribute('id'), 'alts');
        assert.equal(alternatives.wrapperElement.classList.contains('se-alternatives'), true);
        assert.equal(alternatives.wrapperElement.classList.contains('custom'), true);
        assert.equal(alternatives.wrapperElement.classList.contains('full'), true);
        assert.equal(alternatives.defaultEffect, Alternatives.NONE);

        const first = alternatives.createAlternative();
        const second = alternatives.createAlternative();

        assert.equal(first.visible, true);
        assert.equal(second.visible, false);
        assert.equal(alternatives.getCurrentAlternative(), first);
        assert.equal(alternatives.visibleAlt, first);

        const altMapCopy = alternatives.alternatives;
        delete altMapCopy[first.altId];
        assert.equal(alternatives.alternatives[first.altId] != null, true);

        const altListCopy = alternatives.alternativeList;
        altListCopy.pop();
        assert.equal(alternatives.alternativeList.length, 2);

        alternatives.repaint('truthy');
        assert.deepEqual(first.repaintCalls, [true]);

        let completed = 0;
        const result = await alternatives.showAlternative(first, {
            onComplete(outAlternative, inAlternative) {
                completed += 1;
                assert.equal(outAlternative, first);
                assert.equal(inAlternative, first);
            },
        });
        assert.equal(result.in, first);
        assert.equal(result.out, first);
        assert.equal(completed, 1);
    } finally {
        restoreTimers();
    }
});

test('StyledElements.Alternatives showAlternative supports none/slide/dissolve and validates inputs', async () => {
    resetLegacyRuntime();
    const { Alternatives, Alternative, restoreTimers } = setupAlternatives();

    const alternatives = new Alternatives({ full: false });
    const first = alternatives.createAlternative();
    const second = alternatives.createAlternative();
    const third = alternatives.createAlternative();

    const transitions = [];
    alternatives.addEventListener('preTransition', (outAlternative, inAlternative) => {
        transitions.push(['pre', outAlternative.altId, inAlternative.altId]);
    });
    alternatives.addEventListener('postTransition', (outAlternative, inAlternative) => {
        transitions.push(['post', outAlternative.altId, inAlternative.altId]);
    });

    try {
        await alternatives.showAlternative(second.altId, { effect: Alternatives.NONE });
        assert.equal(alternatives.visibleAlt, second);
        assert.equal(first.visible, false);
        assert.equal(second.visible, true);

        await alternatives.showAlternative(first, { effect: Alternatives.HORIZONTAL_SLIDE });
        assert.equal(alternatives.visibleAlt, first);
        assert.equal(second.visible, false);
        assert.equal(first.visible, true);
        assert.equal(first.wrapperElement.classList.contains('slide'), false);
        assert.equal(second.wrapperElement.classList.contains('slide'), false);
        assert.equal(first.wrapperElement.classList.contains('left'), false);
        assert.equal(first.wrapperElement.classList.contains('right'), false);

        await alternatives.showAlternative(second, { effect: Alternatives.HORIZONTAL_SLIDE });
        assert.equal(alternatives.visibleAlt, second);
        assert.equal(first.wrapperElement.classList.contains('slide'), false);
        assert.equal(second.wrapperElement.classList.contains('slide'), false);

        await alternatives.showAlternative(third, { effect: Alternatives.CROSS_DISSOLVE });
        assert.equal(alternatives.visibleAlt, third);
        assert.equal(first.visible, false);
        assert.equal(third.visible, true);
        assert.equal(third.wrapperElement.classList.contains('fade'), false);

        assert.equal(transitions.length >= 6, true);
        assert.equal(alternatives.wrapperElement.classList.contains('se-on-transition'), false);
        await alternatives.showAlternative(first, { effect: 'unknown-effect' });
        assert.equal(alternatives.visibleAlt, first);

        assert.throws(() => alternatives.showAlternative(9999), TypeError);
        assert.throws(() => alternatives.showAlternative(new Alternative(123, {})), TypeError);
    } finally {
        restoreTimers();
    }
});

test('StyledElements.Alternatives removeAlternative handles id/object variants and visible fallback', async () => {
    resetLegacyRuntime();
    const { Alternatives, Alternative, restoreTimers } = setupAlternatives();

    const alternatives = new Alternatives({});
    const first = alternatives.createAlternative();
    const second = alternatives.createAlternative();
    const third = alternatives.createAlternative();

    try {
        let noopCallback = 0;
        await alternatives.removeAlternative(999, {
            onComplete() {
                noopCallback += 1;
            },
        });
        assert.equal(noopCallback, 1);

        assert.throws(() => alternatives.removeAlternative(new Alternative(77, {})), TypeError);

        await alternatives.removeAlternative(first, { effect: Alternatives.NONE });
        assert.equal(alternatives.visibleAlt, second);
        assert.equal(alternatives.alternatives[first.altId], undefined);

        await alternatives.removeAlternative(second.altId, { effect: Alternatives.NONE });
        assert.equal(alternatives.visibleAlt, third);

        await alternatives.removeAlternative(third, { effect: Alternatives.NONE });
        assert.equal(alternatives.visibleAlt, null);
        assert.equal(alternatives.alternativeList.length, 0);
        assert.equal(alternatives.wrapperElement.childNodes.length, 0);
    } finally {
        restoreTimers();
    }
});

test('StyledElements.Alternatives removeAlternative uses previous alternative fallback when needed', async () => {
    resetLegacyRuntime();
    const { Alternatives, restoreTimers } = setupAlternatives();

    const alternatives = new Alternatives({});
    const first = alternatives.createAlternative();
    const second = alternatives.createAlternative();
    const third = alternatives.createAlternative();

    try {
        await alternatives.showAlternative(third, { effect: Alternatives.NONE });
        await alternatives.removeAlternative(third, { effect: Alternatives.NONE });

        assert.equal(alternatives.visibleAlt, second);
        assert.equal(first.visible, false);
        assert.equal(second.visible, true);
    } finally {
        restoreTimers();
    }
});

test('StyledElements.Alternatives createAlternative validates constructor type and clear resets state', () => {
    resetLegacyRuntime();
    const { Alternatives, Alternative, restoreTimers } = setupAlternatives();

    class SubAlternative extends Alternative {}
    class InvalidAlternative {}

    const alternatives = new Alternatives({});

    try {
        assert.throws(() => {
            alternatives.createAlternative({
                alternative_constructor: InvalidAlternative,
            });
        }, TypeError);

        const first = alternatives.createAlternative({
            alternative_constructor: SubAlternative,
            initiallyVisible: true,
        });
        assert.equal(first instanceof SubAlternative, true);
        assert.equal(first.altId, 1);

        let requestedAlternative = null;
        alternatives.showAlternative = (alternative) => {
            requestedAlternative = alternative;
            return Promise.resolve();
        };
        const second = alternatives.createAlternative({ initiallyVisible: true });
        assert.equal(requestedAlternative, second);

        alternatives.clear();
        assert.equal(alternatives.alternativeList.length, 0);
        assert.equal(alternatives.visibleAlt, null);

        const afterClear = alternatives.createAlternative();
        assert.equal(afterClear.altId, 0);
    } finally {
        restoreTimers();
    }
});


