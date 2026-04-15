const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const installXRegExpStub = () => {
    const XRegExp = (pattern, flags = '') => {
        const normalizedFlags = flags.includes('u') ? flags : `${flags}u`;
        return new RegExp(pattern, normalizedFlags);
    };
    XRegExp.replace = (text, pattern, replacement) => text.replace(pattern, replacement);
    global.XRegExp = XRegExp;
};

const loadURLify = () => {
    resetLegacyRuntime();
    installXRegExpStub();
    loadLegacyScript('src/wirecloud/commons/static/js/lib/urlify.js');
    return global.URLify;
};

test('URLify normalizes latin text, stop words, symbols and truncation', () => {
    const URLify = loadURLify();

    assert.equal(URLify('Árbol and the sea', 80, false), 'arbol-and-sea');
    assert.equal(URLify('© Hello, World!', 80, false), 'c-hello-world');
    assert.equal(URLify('  This is   A Test  ', 80, false), 'test');
    assert.equal(URLify('hello world', 6, false), 'hello');
});

test('URLify keeps unicode letters when allowUnicode is true', () => {
    const URLify = loadURLify();

    assert.equal(URLify('niño 123 !', 80, true), 'niño-123');
    assert.equal(URLify('Привет мир', 80, true), 'привет-мир');
});

test('URLify reuses the initialized downcoder across calls', () => {
    const URLify = loadURLify();

    assert.equal(URLify('Über', 80, false), 'uber');
    assert.equal(URLify('Çedilla', 80, false), 'cedilla');
});
