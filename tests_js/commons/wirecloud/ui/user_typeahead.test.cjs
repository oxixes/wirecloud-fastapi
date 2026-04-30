const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupUserTypeahead = () => {
    let receivedOptions;

    class Typeahead {
        constructor(config) {
            this.config = config;
        }
    }

    global.StyledElements = {
        Typeahead,
        Utils: {
            merge: (...objects) => Object.assign({}, ...objects),
        }
    };
    global.Wirecloud = {
        URLs: { SEARCH_SERVICE: '/search' },
        io: {
            makeRequest(url, options) {
                assert.equal(url, '/search');
                receivedOptions = options;
                return Promise.resolve({
                    responseText: JSON.stringify({
                        results: [{ username: 'alice', fullname: 'Alice', organization: 'Acme' }]
                    })
                });
            }
        },
        ui: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/UserTypeahead.js');
    return {
        TypeaheadClass: Wirecloud.ui.UserTypeahead,
        getLastRequest: () => receivedOptions
    };
};

test('Wirecloud.ui.UserTypeahead applies explicit autocomplete option', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserTypeahead();

    const typeahead = new TypeaheadClass({ autocomplete: false });
    assert.equal(typeahead.config.autocomplete, false);
});

test('Wirecloud.ui.UserTypeahead lookup requests user namespace', async () => {
    resetLegacyRuntime();
    const { TypeaheadClass, getLastRequest } = setupUserTypeahead();

    const typeahead = new TypeaheadClass();
    const results = await typeahead.config.lookup('alice');

    assert.equal(results.length, 1);
    assert.deepEqual(getLastRequest().parameters, { namespace: 'user', q: 'alice' });
});

test('Wirecloud.ui.UserTypeahead build uses organization icon when present', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserTypeahead();

    const typeahead = new TypeaheadClass();
    const entry = typeahead.config.build(typeahead, { username: 'alice', fullname: 'Alice', organization: 'Acme' });
    assert.equal(entry.iconClass, 'fas fa-building');
});

test('Wirecloud.ui.UserTypeahead build falls back to user icon without organization', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserTypeahead();

    const typeahead = new TypeaheadClass();
    const entry = typeahead.config.build(typeahead, { username: 'bob', fullname: 'Bob', organization: null });
    assert.equal(entry.iconClass, 'fa fa-user');
});
