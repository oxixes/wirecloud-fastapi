const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const setWindowParent = (value) => {
    Object.defineProperty(window, 'parent', {
        value,
        configurable: true,
        writable: true,
    });
};

const setupObjectStorageApi = () => {
    const requests = [];
    const openStackCalls = [];

    const platform = {
        OpenStackManager: {
            get_openstack_token_from_idm_token(url, resolve) {
                openStackCalls.push(url);
                resolve('idm-token');
            },
        },
    };

    const parent = {
        MashupPlatform: {
            http: {
                makeRequest(url, options) {
                    requests.push({ url, options });
                },
            },
        },
    };

    global.Wirecloud = {
        APIRequirements: {},
    };
    setWindowParent(window);
    loadLegacyScript('src/wirecloud/fiware/static/js/ObjectStorage/ObjectStorageAPI.js');
    Wirecloud.APIRequirements.OpenStorage(parent, platform);

    return {
        parent,
        requests,
        openStackCalls,
        internals: parent.__OpenStorageAPIInternals,
        KeystoneAPI: parent.KeystoneAPI,
        ObjectStorageAPI: parent.ObjectStorageAPI,
    };
};

test('ObjectStorageAPI requirement exports KeystoneAPI and ObjectStorageAPI', () => {
    resetLegacyRuntime();
    const { KeystoneAPI, ObjectStorageAPI, internals } = setupObjectStorageApi();
    assert.equal(typeof KeystoneAPI, 'function');
    assert.equal(typeof ObjectStorageAPI, 'function');
    assert.equal(typeof internals.initHeaders, 'function');
    assert.equal(typeof internals.get_auth_project_data, 'function');
});

test('ObjectStorageAPI internals keep legacy behavior for dead branches', () => {
    resetLegacyRuntime();
    const { internals } = setupObjectStorageApi();

    assert.throws(() => internals.initHeaders({}), TypeError);
    const projectData = internals.get_auth_project_data('legacy');
    assert.equal('project' in projectData, true);
    assert.equal(projectData.project, undefined);
});

test('ObjectStorageAPI initializes directly when running inside iframe', () => {
    resetLegacyRuntime();

    const requests = [];
    const platform = {
        OpenStackManager: {
            get_openstack_token_from_idm_token(url, resolve) {
                resolve('idm-token');
            },
        },
    };
    const fakeParent = {
        MashupPlatform: {
            http: {
                makeRequest(url, options) {
                    requests.push({ url, options });
                },
            },
        },
    };

    global.Wirecloud = { APIRequirements: {} };
    setWindowParent(fakeParent);
    loadLegacyScript('src/wirecloud/fiware/static/js/ObjectStorage/ObjectStorageAPI.js');
    assert.equal(typeof window.KeystoneAPI, 'function');
    assert.equal(typeof window.ObjectStorageAPI, 'function');
    assert.equal(Wirecloud.APIRequirements.OpenStorage, undefined);
    assert.equal(requests.length, 0);
});

test('KeystoneAPI constructor normalizes url and getTenants/getAuthToken flows', () => {
    resetLegacyRuntime();
    const { KeystoneAPI, requests, openStackCalls } = setupObjectStorageApi();

    const api = new KeystoneAPI('https://keystone.example/v3/', {
        token: 'tok-1',
        use_user_fiware_token: true,
    });
    assert.equal(api.url, 'https://keystone.example/');
    assert.throws(() => new KeystoneAPI(null, {}), /url must be a string/);
    const apiNoOptions = new KeystoneAPI('https://keystone.example/v3');
    assert.equal(apiNoOptions.url, 'https://keystone.example/');

    const tenantResults = [];
    api.getTenants({
        onSuccess(data) {
            tenantResults.push(data.tenants.length);
        },
        onFailure(reason) {
            tenantResults.push(`fail:${reason}`);
        },
        onComplete() {
            tenantResults.push('done');
        },
    });
    assert.equal(openStackCalls.length, 1);
    assert.equal(requests[0].url, 'https://keystone.example/v2.0/tenants');
    assert.equal(requests[0].options.method, 'GET');
    assert.equal(requests[0].options.requestHeaders['X-Auth-Token'], 'idm-token');

    requests[0].options.onSuccess({ responseText: JSON.stringify({ tenants: [{ id: 'a' }] }) });
    requests[0].options.onComplete({});
    assert.deepEqual(tenantResults, [1, 'done']);

    const failReasons = [];
    api.getTenants({
        token: 'tok-2',
        use_user_fiware_token: false,
        onFailure(reason) {
            failReasons.push(reason);
        },
    });
    requests[1].options.onFailure({ status: 503 });
    requests[1].options.onFailure({ status: 401 });
    requests[1].options.onFailure({ status: 0 });
    requests[1].options.onFailure({ status: 500 });
    assert.deepEqual(failReasons, [api.ERROR.SERVICE_UNAVAILABLE, api.ERROR.UNAUTHORIZED, api.ERROR.CONNECTION_REFUSED, api.ERROR.UNKNOWN]);

    const authResults = [];
    api.getAuthToken({
        tenantId: 'tenant-1',
        token: 'tok-3',
        onSuccess(tokenId, response) {
            authResults.push(tokenId);
            authResults.push(response.access.token.id);
        },
    });
    const authReq = requests[2];
    assert.equal(authReq.url, 'https://keystone.example/v2.0/tokens');
    assert.equal(JSON.parse(authReq.options.postBody).auth.tenantId, 'tenant-1');
    authReq.options.onSuccess({
        responseText: JSON.stringify({ access: { token: { id: 'auth-123' } } }),
    });
    authReq.options.onFailure({ status: 503 });
    authReq.options.onComplete({});
    assert.deepEqual(authResults, ['auth-123', 'auth-123']);

    const authFailReasons = [];
    api.getAuthToken({
        tenantId: 'tenant-f',
        token: 'tok-f',
        onFailure(reason) {
            authFailReasons.push(reason);
        },
        onComplete() {
            authFailReasons.push('done');
        },
    });
    requests[3].options.onFailure({ status: 401 });
    requests[3].options.onComplete({});
    assert.deepEqual(authFailReasons, [api.ERROR.UNAUTHORIZED, 'done']);

    api.getAuthToken({
        tenantId: 'tenant-2',
        use_user_fiware_token: true,
    });
    assert.equal(openStackCalls.length, 1);
    assert.equal(JSON.parse(requests[4].options.postBody).auth.token.id, 'tok-1');

    const apiNoToken = new KeystoneAPI('https://keystone.example/v3/', {
        use_user_fiware_token: true,
    });
    apiNoToken.getAuthToken({
        tenantId: 'tenant-3',
        use_user_fiware_token: true,
    });
    assert.equal(openStackCalls.length, 2);
    assert.equal(JSON.parse(requests[5].options.postBody).auth.token.id, 'idm-token');

    api.getAuthToken({
        tenantId: 'tenant-pass',
        passwordCredentials: true,
        user: 'alice',
        pass: 'secret',
    });
    const passBody = JSON.parse(requests[6].options.postBody);
    assert.equal(passBody.auth.passwordCredentials.username, 'alice');
    assert.equal(passBody.auth.passwordCredentials.password, 'secret');

    assert.throws(() => api.getAuthToken({ token: 'x' }), TypeError);
    const apiNoAuth = new KeystoneAPI('https://keystone.example/v3/', {});
    assert.throws(() => apiNoAuth.getAuthToken({ tenantId: 't' }), Error);
    apiNoAuth.getTenants({ use_user_fiware_token: false });
});

test('ObjectStorageAPI CRUD methods build requests and validate options', () => {
    resetLegacyRuntime();
    const { ObjectStorageAPI, requests } = setupObjectStorageApi();

    assert.throws(() => new ObjectStorageAPI(null), /url must be a string/);
    const api = new ObjectStorageAPI('https://swift.example/root', { token: 'tok-os' });
    assert.equal(api.url, 'https://swift.example/root/');

    const events = [];
    const opts = {
        onSuccess(data) {
            events.push(['ok', data]);
        },
        onFailure(reason) {
            events.push(['fail', reason]);
        },
        onComplete() {
            events.push(['done']);
        },
    };

    api.getContainerList(opts);
    assert.equal(requests[0].options.method, 'GET');
    assert.equal(requests[0].options.requestHeaders['X-Auth-Token'], 'tok-os');
    requests[0].options.onSuccess({ responseText: JSON.stringify([{ name: 'a' }]) });
    requests[0].options.onFailure({ status: 500 });
    requests[0].options.onComplete({});

    api.createContainer('my container', opts);
    assert.equal(requests[1].url.includes('my%20container'), true);
    requests[1].options.onSuccess({ status_code: 204 });
    requests[1].options.onFailure({ status: 503 });
    requests[1].options.onComplete({});

    api.listContainer('my container', opts);
    assert.equal(requests[2].url.endsWith('my%20container/'), true);
    requests[2].options.onSuccess({ responseText: JSON.stringify([{ name: 'file1' }]) });
    requests[2].options.onFailure({ status: 401 });
    requests[2].options.onComplete({});

    api.deleteContainer('my container', opts);
    assert.equal(requests[3].options.method, 'DELETE');
    requests[3].options.onSuccess({});
    requests[3].options.onFailure({ status: 0 });
    requests[3].options.onComplete({});

    api.getFile('my container', 'file.txt', { ...opts, response_type: 'text' });
    assert.equal(requests[4].options.responseType, 'text');
    requests[4].options.onSuccess({ response: 'data' });
    requests[4].options.onFailure({ status: 500 });
    requests[4].options.onComplete({});
    assert.throws(() => api.getFile('c', 'f', { token: 't', response_type: 'json' }), /Invalid response_type/);

    const file = { type: 'text/plain', name: 'doc.txt' };
    api.uploadFile('my container', file, opts);
    assert.equal(requests[5].options.method, 'PUT');
    assert.equal(requests[5].options.contentType, 'text/plain');
    requests[5].options.onSuccess({});
    requests[5].options.onFailure({ status: 503 });
    requests[5].options.onComplete({});
    api.uploadFile('my container', { type: 'text/plain', name: 'ignored' }, { ...opts, file_name: 'forced.txt' });
    assert.equal(requests[6].url.endsWith('/forced.txt'), true);
    assert.throws(() => api.uploadFile('c', null, opts), /file must be an instance of Blob/);
    assert.throws(() => api.uploadFile('c', { type: 'x' }, opts), /Missing file name/);

    api.deleteFile('my container', 'file.txt', opts);
    assert.equal(requests[7].options.method, 'DELETE');
    requests[7].options.onSuccess({});
    requests[7].options.onFailure({ status: 401 });
    requests[7].options.onComplete({});

    const tokenless = new ObjectStorageAPI('https://swift.example/root');
    tokenless.getContainerList({});

    assert.equal(events.length > 0, true);
});
