const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setupOpenStackManager = () => {
    const requests = [];

    global.Wirecloud = {
        Utils: {
            callCallback(callback, ...args) {
                if (typeof callback === 'function') {
                    callback(...args);
                }
            },
        },
        io: {
            makeRequest(url, options) {
                requests.push({ url, options });
            },
        },
    };

    loadLegacyScript('src/wirecloud/fiware/static/js/ObjectStorage/OpenStackManager.js');

    return { requests, manager: window.OpenStackManager };
};

test('OpenStackManager fetches and caches OpenStack token with shared listeners', () => {
    resetLegacyRuntime();
    const { requests, manager } = setupOpenStackManager();
    const url = 'https://keystone.example/';

    const resolved = [];
    manager.get_openstack_token_from_idm_token(url, (token) => resolved.push(`a:${token}`), () => resolved.push('a:fail'));
    manager.get_openstack_token_from_idm_token(url, (token) => resolved.push(`b:${token}`), () => resolved.push('b:fail'));

    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, 'https://keystone.example/v3/auth/tokens');
    assert.equal(requests[0].options.method, 'POST');

    requests[0].options.onSuccess({
        getHeader(name) {
            return name === 'X-Subject-Token' ? 'token-1' : null;
        },
    });
    assert.deepEqual(resolved, ['a:token-1', 'b:token-1']);

    manager.get_openstack_token_from_idm_token(url, (token) => resolved.push(`c:${token}`), () => resolved.push('c:fail'));
    assert.equal(requests.length, 1);
    assert.equal(resolved[2], 'c:token-1');
});

test('OpenStackManager forwards failure callbacks', () => {
    resetLegacyRuntime();
    const { requests, manager } = setupOpenStackManager();
    const failed = [];
    const url = 'https://keystone.fail/';

    manager.get_openstack_token_from_idm_token(url, () => failed.push('ok'), () => failed.push('fail-1'));
    manager.get_openstack_token_from_idm_token(url, () => failed.push('ok2'), () => failed.push('fail-2'));

    assert.equal(requests.length, 1);
    requests[0].options.onFailure({ status: 503 });
    assert.deepEqual(failed, ['fail-1', 'fail-2']);
});

