const test = require('node:test');
const assert = require('node:assert/strict');
const { loadLegacyScript, resetLegacyRuntime } = require('../../support/legacy-runtime.cjs');

const createComponent = (id, type) => {
    const listeners = {};
    return {
        id,
        meta: { type },
        addEventListener(name, handler) {
            listeners[name] = handler;
        },
        removeEventListener(name, handler) {
            if (listeners[name] === handler) {
                delete listeners[name];
            }
        },
        dispatch(name) {
            if (listeners[name] != null) {
                listeners[name].call(this, this);
            }
        },
    };
};

test('NGSIManager.Connection wires defaults and proxy lifecycle', async () => {
    resetLegacyRuntime();

    const connectionCtorCalls = [];
    const proxyCloses = [];
    const unloadHandlers = [];
    let callbackSeq = 0;

    function BaseConnection(url, options) {
        connectionCtorCalls.push({ url, options });
        this.url = url;
        this.options = options;
    }

    class ProxyConnection {
        constructor(url, requestFunction) {
            this.url = String(url);
            this.requestFunction = requestFunction;
            this.connected = true;
            this.connecting = false;
            this.subscriptionCallbacks = {};
            this.callbackSubscriptionsVersioned = {};
            this.closedCallbacks = [];
        }

        connect(options) {
            return Promise.resolve({ connected: true, options });
        }

        requestCallback() {
            callbackSeq += 1;
            return Promise.resolve({ callback_id: `cb-${callbackSeq}` });
        }

        closeCallback(callbackId) {
            this.closedCallbacks.push(callbackId);
            return Promise.resolve();
        }

        associateSubscriptionId(callbackId, subscriptionId, version) {
            this.subscriptionCallbacks[subscriptionId] = callbackId;
            this.callbackSubscriptionsVersioned[callbackId] = { id: subscriptionId, version };
        }

        closeSubscriptionCallback(subscriptionId) {
            const callbackId = this.subscriptionCallbacks[subscriptionId];
            delete this.subscriptionCallbacks[subscriptionId];
            return this.closeCallback(callbackId);
        }

        close(force) {
            if (force === false) {
                throw new Error('close failed');
            }
            proxyCloses.push(this.url);
        }
    }

    global.NGSI = {
        Connection: BaseConnection,
        ProxyConnection,
        ConnectionError: class ConnectionError extends Error {},
    };

    global.Wirecloud = {
        location: { base: 'https://wirecloud.example/' },
        URLs: {
            PROXY: {
                evaluate() {
                    return '/proxy/x/xx';
                },
            },
        },
        Utils: {
            gettext(text) {
                return text;
            },
            inherit(ctor, base) {
                ctor.prototype = Object.create(base.prototype);
                ctor.prototype.constructor = ctor;
            },
        },
        io: {
            makeRequest(url, options) {
                return Promise.resolve({
                    status: 200,
                    request: { url },
                    responseText: '{}',
                    getHeader() {
                        return 'proxy-header';
                    },
                    options,
                });
            },
        },
        addEventListener(name, handler) {
            if (name === 'unload') {
                unloadHandlers.push(handler);
            }
        },
    };

    loadLegacyScript('src/wirecloud/fiware/static/js/NGSI/NGSIManager.js');
    const manager = window.NGSIManager;
    assert.equal(typeof manager.NGSI.Connection, 'function');

    const componentA = createComponent('comp-a', 'widget');
    const componentB = createComponent('comp-b', 'widget');

    const connectionA = new manager.Connection(componentA, 'https://orion.example', {
        ngsi_proxy_url: 'https://proxy.example/root',
        use_user_fiware_token: true,
    });
    assert.equal(connectionCtorCalls[0].options.request_headers['FIWARE-OAuth-Token'], 'true');
    assert.equal(connectionCtorCalls[0].options.request_headers['FIWARE-OAuth-Header-Name'], 'Authorization');
    assert.equal(connectionCtorCalls[0].options.ngsi_proxy_url, undefined);

    const wrappedProxyA = connectionCtorCalls[0].options.ngsi_proxy_connection;
    assert.equal(wrappedProxyA.connected, true);
    assert.equal(wrappedProxyA.connecting, false);
    assert.equal(wrappedProxyA.url, 'https://proxy.example/root/');

    await wrappedProxyA.connect({ force: true });
    const cb1 = await wrappedProxyA.requestCallback(() => {});
    assert.throws(() => wrappedProxyA.closeCallback('missing-cb'), TypeError);
    await wrappedProxyA.closeCallback(cb1.callback_id);

    const cb2 = await wrappedProxyA.requestCallback(() => {});
    wrappedProxyA.associateSubscriptionId(cb2.callback_id, 'sub-1', 'v1');
    await wrappedProxyA.closeSubscriptionCallback('sub-1');
    await wrappedProxyA.closeSubscriptionCallback('unknown-sub');

    new manager.Connection(componentB, 'https://orion.example', {
        ngsi_proxy_url: 'https://proxy.example/root',
    });

    connectionA.ld = { deleteSubscription() {} };
    connectionA.v2 = { deleteSubscription() {} };
    connectionA.cancelAvailabilitySubscription = () => {};
    connectionA.cancelSubscription = () => {};

    const cbLd = await wrappedProxyA.requestCallback(() => {});
    const cbV2 = await wrappedProxyA.requestCallback(() => {});
    const cbAv = await wrappedProxyA.requestCallback(() => {});
    const cbV1 = await wrappedProxyA.requestCallback(() => {});
    const cbDefault = await wrappedProxyA.requestCallback(() => {});
    wrappedProxyA.associateSubscriptionId(cbLd.callback_id, 'sub-ld', 'ld');
    wrappedProxyA.associateSubscriptionId(cbV2.callback_id, 'sub-v2', 'v2');
    wrappedProxyA.associateSubscriptionId(cbAv.callback_id, 'sub-a', 'v1-availability');
    wrappedProxyA.associateSubscriptionId(cbV1.callback_id, 'sub-v1', 'v1');
    wrappedProxyA.associateSubscriptionId(cbDefault.callback_id, 'sub-default', 'unknown-version');
    wrappedProxyA.close();

    const oldClose = wrappedProxyA.close;
    wrappedProxyA.close = () => {
        throw new Error('wrapped close failed');
    };
    unloadHandlers.forEach((handler) => handler());
    componentA.dispatch('unload');
    wrappedProxyA.close = oldClose;
    componentB.dispatch('unload');
    assert.equal(proxyCloses.includes('https://proxy.example/root/'), true);

    const proxiedRequest = connectionCtorCalls[0].options.requestFunction;
    await proxiedRequest('https://wirecloud.example/proxy/x/xx/test', {});

    global.Wirecloud.io.makeRequest = () => Promise.resolve({
        status: 0,
        request: { url: 'https://wirecloud.example/proxy/x/xx/test' },
        getHeader() {
            return null;
        },
        responseText: '{}',
    });
    await assert.rejects(proxiedRequest('https://wirecloud.example/proxy/x/xx/test', {}), /Error connecting/);

    global.Wirecloud.io.makeRequest = () => Promise.resolve({
        status: 403,
        request: { url: 'https://wirecloud.example/proxy/x/xx/test' },
        getHeader() {
            return null;
        },
        responseText: '{}',
    });
    await assert.rejects(proxiedRequest('https://wirecloud.example/proxy/x/xx/test', {}), /aren't allowed/);

    global.Wirecloud.io.makeRequest = () => Promise.resolve({
        status: 502,
        request: { url: 'https://wirecloud.example/proxy/x/xx/test' },
        getHeader() {
            return null;
        },
        responseText: JSON.stringify({ description: 'proxy gateway issue' }),
    });
    await assert.rejects(proxiedRequest('https://wirecloud.example/proxy/x/xx/test', {}), /proxy gateway issue/);

    global.Wirecloud.io.makeRequest = () => Promise.resolve({
        status: 418,
        request: { url: 'https://wirecloud.example/proxy/x/xx/test' },
        getHeader() {
            return null;
        },
        responseText: '{}',
    });
    await assert.rejects(proxiedRequest('https://wirecloud.example/proxy/x/xx/test', {}), /Unexpected response/);

    new manager.Connection(createComponent('comp-c', 'operator'), 'https://orion.example');
    unloadHandlers.forEach((handler) => handler());
});
