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

const buildPlatform = () => {
    const connectionCalls = [];
    function Connection(component, url, options) {
        this.component = component;
        this.url = url;
        this.options = options;
        connectionCalls.push({ component, url, options });
    }

    return {
        connectionCalls,
        platform: {
            MashupPlatform: {
                priv: {
                    resource: { id: 'resource-1' },
                },
            },
            NGSIManager: {
                Connection,
                NGSI: {
                    ProxyConnectionError: class ProxyConnectionError extends Error {},
                    InvalidResponseError: class InvalidResponseError extends Error {},
                    InvalidRequestError: class InvalidRequestError extends Error {},
                    ConnectionError: class ConnectionError extends Error {},
                },
            },
        },
    };
};

test('NGSIAPI registers API requirement when running outside iframe', () => {
    resetLegacyRuntime();
    setWindowParent(window);
    global.Wirecloud = { APIRequirements: {} };

    loadLegacyScript('src/wirecloud/fiware/static/js/WirecloudAPI/NGSIAPI.js');

    assert.equal(typeof Wirecloud.APIRequirements.NGSI, 'function');

    const { platform, connectionCalls } = buildPlatform();
    const apiHost = {
        MashupPlatform: platform.MashupPlatform,
    };
    Wirecloud.APIRequirements.NGSI(apiHost, platform);

    assert.equal(Object.isFrozen(apiHost.NGSI), true);
    assert.equal(typeof apiHost.NGSI.Connection, 'function');

    const conn = new apiHost.NGSI.Connection('https://broker.example/v2', { a: 1 });
    assert.equal(conn instanceof platform.NGSIManager.Connection, true);
    assert.equal(connectionCalls.length, 1);
    assert.equal(connectionCalls[0].component.id, 'resource-1');
    assert.equal(connectionCalls[0].url, 'https://broker.example/v2');
    assert.deepEqual(connectionCalls[0].options, { a: 1 });

    assert.equal(apiHost.NGSI.ProxyConnectionError, platform.NGSIManager.NGSI.ProxyConnectionError);
    assert.equal(apiHost.NGSI.InvalidResponseError, platform.NGSIManager.NGSI.InvalidResponseError);
    assert.equal(apiHost.NGSI.InvalidRequestError, platform.NGSIManager.NGSI.InvalidRequestError);
    assert.equal(apiHost.NGSI.ConnectionError, platform.NGSIManager.NGSI.ConnectionError);
});

test('NGSIAPI initializes global NGSI when running inside iframe', () => {
    resetLegacyRuntime();
    const { platform } = buildPlatform();
    setWindowParent(platform);
    window.MashupPlatform = platform.MashupPlatform;
    global.Wirecloud = { APIRequirements: {} };

    loadLegacyScript('src/wirecloud/fiware/static/js/WirecloudAPI/NGSIAPI.js');

    assert.equal(typeof window.NGSI, 'object');
    assert.equal(typeof window.NGSI.Connection, 'function');
    assert.equal(Wirecloud.APIRequirements.NGSI, undefined);
});
