const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupUserGroupTypeahead = () => {
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
                        results: [
                            { type: 'user', username: 'alice', fullname: 'Alice User' },
                            { type: 'group', name: 'team-a', fullname: 'Team A' },
                            { type: 'organization', name: 'org-a' },
                        ]
                    })
                });
            }
        },
        ui: {}
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/UserGroupTypeahead.js');
    return {
        TypeaheadClass: Wirecloud.ui.UserGroupTypeahead,
        getLastRequest: () => receivedOptions
    };
};

test('Wirecloud.ui.UserGroupTypeahead defaults autocomplete to true', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserGroupTypeahead();

    const typeahead = new TypeaheadClass();
    assert.equal(typeahead.config.autocomplete, true);
});

test('Wirecloud.ui.UserGroupTypeahead lookup requests usergroup namespace', async () => {
    resetLegacyRuntime();
    const { TypeaheadClass, getLastRequest } = setupUserGroupTypeahead();

    const typeahead = new TypeaheadClass();
    const results = await typeahead.config.lookup('team');

    assert.equal(results.length, 3);
    assert.deepEqual(getLastRequest().parameters, { namespace: 'usergroup', q: 'team' });
});

test('Wirecloud.ui.UserGroupTypeahead build uses username for user type', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserGroupTypeahead();

    const typeahead = new TypeaheadClass();
    const entry = typeahead.config.build(typeahead, { type: 'user', username: 'alice', fullname: 'Alice User' });
    assert.equal(entry.value, 'alice');
    assert.equal(entry.iconClass, 'fas fa-user');
});

test('Wirecloud.ui.UserGroupTypeahead build uses group/organization name for non-user types', () => {
    resetLegacyRuntime();
    const { TypeaheadClass } = setupUserGroupTypeahead();

    const typeahead = new TypeaheadClass();
    const groupEntry = typeahead.config.build(typeahead, { type: 'group', name: 'team-a', fullname: 'Team A' });
    const orgEntry = typeahead.config.build(typeahead, { type: 'organization', name: 'org-a' });

    assert.equal(groupEntry.value, 'team-a');
    assert.equal(groupEntry.iconClass, 'fas fa-users');
    assert.equal(orgEntry.value, 'org-a');
    assert.equal(orgEntry.iconClass, 'fas fa-building');
});
