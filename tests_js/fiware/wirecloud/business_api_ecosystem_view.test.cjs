const test = require('node:test');
const assert = require('node:assert/strict');
const { loadLegacyScript, resetLegacyRuntime } = require('../../support/legacy-runtime.cjs');

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

test('BusinessAPIEcosystemView registers and handles lifecycle', async () => {
    resetLegacyRuntime();

    const addedTypes = [];
    let shouldFailLoad = false;
    const loadedWorkspaces = [];

    class WorkspaceView {
        constructor(id, options) {
            this.id = id;
            this.options = options;
            this.listeners = {};
        }

        addEventListener(name, handler) {
            this.listeners[name] = handler;
        }

        dispatch(name) {
            if (this.listeners[name]) {
                this.listeners[name].call(this);
            }
        }

        loadWorkspace(workspace) {
            this.model = workspace;
        }
    }

    global.Wirecloud = {
        FiWare: {},
        Utils: {},
        ui: { WorkspaceView },
        loadWorkspace({ owner, name }) {
            if (shouldFailLoad) {
                return Promise.reject(new Error('boom'));
            }
            return Promise.resolve({
                owner,
                name,
                unload() {
                    loadedWorkspaces.push(`${owner}/${name}:unloaded`);
                },
            });
        },
        MarketManager: {
            addMarketType(type, label, viewCtor) {
                addedTypes.push({ type, label, viewCtor });
            },
        },
    };

    loadLegacyScript('src/wirecloud/fiware/static/js/wirecloud/FiWare/BusinessAPIEcosystemView.js');
    assert.equal(addedTypes.length, 1);
    assert.equal(addedTypes[0].type, 'fiware-bae');
    assert.equal(addedTypes[0].label, 'FIWARE Business API Ecosystem');

    const View = Wirecloud.FiWare.BusinessAPIEcosystemView;
    const view = new View('view-1', {
        marketplace_desc: {
            user: 'alice',
            name: 'market',
            title: 'Alice Market',
            permissions: {
                read: true,
                write: false,
            },
        },
    });

    assert.equal(view.options.class, 'catalogue fiware');
    assert.equal(view.market_id, 'alice/market');
    assert.equal(view.workspaceview, 'alice/market');
    assert.equal(view.getLabel(), 'Alice Market');
    assert.equal(view.isAllow('read'), true);
    assert.equal(view.isAllow('write'), false);
    assert.equal(view.isAllow('unknown'), false);
    assert.equal(view.goUp(), false);
    assert.equal(view.getPublishEndpoints(), null);

    let readyCalled = false;
    view.wait_ready(() => {
        readyCalled = true;
    });
    assert.equal(readyCalled, true);

    assert.equal(view.status, 'unloaded');
    view.dispatch('show');
    assert.equal(view.status, 'loading');
    await flush();
    assert.equal(view.status, 'loading');
    assert.equal(view.loaded, 'loaded');

    view.destroy();
    assert.equal(view.status, 'loading');
    assert.deepEqual(loadedWorkspaces, []);

    view.status = 'loaded';
    view.destroy();
    assert.equal(view.status, 'unloaded');
    assert.deepEqual(loadedWorkspaces, ['alice/market:unloaded']);

    shouldFailLoad = true;
    view.status = 'unloaded';
    view.dispatch('show');
    await flush();
    assert.equal(view.status, 'unloaded');

    const viewNoTitle = new View('view-2', {
        marketplace_desc: {
            user: 'bob',
            name: 'catalog',
            permissions: {},
        },
    });
    assert.equal(viewNoTitle.getLabel(), 'catalog');
    viewNoTitle.destroy();
    assert.equal(viewNoTitle.status, 'unloaded');
});
