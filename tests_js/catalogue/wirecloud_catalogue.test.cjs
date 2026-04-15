const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../support/legacy-runtime.cjs');

const decorateTaskPromise = (promise, titles) => {
    promise.toTask = (title) => {
        titles.push(title);
        return promise;
    };
    return promise;
};

const createCatalogueEnvironment = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();

    const requests = [];
    const taskTitles = [];
    const parseErrors = [];
    Promise.prototype.toTask = function toTask(title) {
        taskTitles.push(title);
        return this;
    };

    global.Wirecloud = {
        Utils: StyledElements.Utils,
        URLs: {
            LOCAL_REPOSITORY: '/local/',
            LOCAL_RESOURCE_COLLECTION: '/api/local/resources',
        },
        io: {
            makeRequest(url, options) {
                let resolveRequest;
                const promise = decorateTaskPromise(new Promise((resolve) => {
                    resolveRequest = resolve;
                }), taskTitles);
                const request = { url, options, promise };
                requests.push(request);
                request.resolve = (response) => resolveRequest(response);
                return request.promise;
            }
        },
        GlobalLogManager: {
            parseErrorResponse(response) {
                parseErrors.push(response.status);
                return `parsed:${response.status}`;
            }
        },
        WirecloudCatalogue: {}
    };

    loadLegacyScript('src/wirecloud/catalogue/static/js/wirecloud/WirecloudCatalogue.js');

    return {
        WirecloudCatalogue: global.Wirecloud.WirecloudCatalogue,
        requests,
        taskTitles,
        parseErrors,
    };
};

test('WirecloudCatalogue constructor and isAllow normalize defaults', () => {
    const { WirecloudCatalogue } = createCatalogueEnvironment();

    const local = new WirecloudCatalogue();
    assert.equal(local.url, '/local/');
    assert.equal(local.name, 'local');
    assert.equal(local.title, 'local');
    assert.equal(local.RESOURCE_ENTRY.evaluate({ vendor: 'acme', name: 'widget', version: '1.0' }), '/local/catalogue/resource/acme/widget/1.0');
    assert.equal(local.isAllow('delete'), false);

    const remote = new WirecloudCatalogue({
        url: 'https://catalogue.example/api',
        name: 'remote',
        title: 'Remote catalogue',
        permissions: { install: true }
    });
    assert.equal(remote.url, 'https://catalogue.example/api/');
    assert.equal(remote.title, 'Remote catalogue');
    assert.equal(remote.isAllow('install'), true);
});

test('WirecloudCatalogue search validates options and maps successful responses', async () => {
    const { WirecloudCatalogue, requests, taskTitles } = createCatalogueEnvironment();
    const catalogue = new WirecloudCatalogue();

    assert.throws(() => catalogue.search({ scope: 'bad' }), /invalid scope value/);
    assert.throws(() => catalogue.search({ maxresults: 10 }), /invalid maxresults value/);
    assert.throws(() => catalogue.search({ pagenum: -1 }), /invalid pagenum value/);

    const task = catalogue.search({
        lang: 'en',
        search_criteria: 'maps',
        scope: 'widget',
        order_by: 'name',
        maxresults: 20,
        pagenum: 2
    });

    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, '/local/catalogue/resources');
    assert.deepEqual(requests[0].options, {
        method: 'GET',
        requestHeaders: { Accept: 'application/json' },
        parameters: {
            lang: 'en',
            q: 'maps',
            scope: 'widget',
            orderby: 'name',
            maxresults: 20,
            pagenum: 2
        }
    });

    requests[0].resolve({
        status: 200,
        responseText: JSON.stringify({
            results: [{ id: 'widget-1' }],
            pagenum: '2',
            total: '9',
            corrected_q: 'maps+'
        })
    });

    const result = await task;
    assert.deepEqual(result, {
        resources: [{ id: 'widget-1' }],
        current_page: 2,
        total_count: 9,
        corrected_query: 'maps+'
    });
    assert.deepEqual(taskTitles, ['Doing catalogue search']);
});

test('WirecloudCatalogue search rejects unexpected and parsed error responses', async () => {
    const { WirecloudCatalogue, requests, parseErrors } = createCatalogueEnvironment();
    const catalogue = new WirecloudCatalogue();

    let task = catalogue.search();
    requests[0].resolve({ status: 418, responseText: '{}' });
    await assert.rejects(task, /Unexpected response from server/);

    task = catalogue.search({ scope: 'all', search_criteria: '', order_by: '' });
    requests[1].resolve({ status: 403, responseText: '{}' });
    await assert.rejects(task, /parsed:403/);
    assert.deepEqual(parseErrors, [403]);
});

test('WirecloudCatalogue getResourceDetails builds resource instances', async () => {
    const { WirecloudCatalogue, requests } = createCatalogueEnvironment();
    const catalogue = new WirecloudCatalogue();

    global.Wirecloud.WirecloudCatalogue.ResourceDetails = class FakeResourceDetails {
        constructor(data, source) {
            this.data = data;
            this.source = source;
        }
    };

    const task = catalogue.getResourceDetails('acme', 'maps');
    requests[0].resolve({
        status: 200,
        responseText: JSON.stringify({ name: 'maps' })
    });

    const result = await task;
    assert.equal(requests[0].url, '/local/catalogue/resource/acme/maps');
    assert.deepEqual(result.data, { name: 'maps' });
    assert.equal(result.source, catalogue);
});

test('WirecloudCatalogue addComponent validates inputs and handles file uploads', async () => {
    const { WirecloudCatalogue, requests, taskTitles, parseErrors } = createCatalogueEnvironment();
    const localCatalogue = new WirecloudCatalogue();
    const remoteCatalogue = new WirecloudCatalogue({ url: 'https://catalogue.example', name: 'remote' });

    assert.throws(() => localCatalogue.addComponent(), /missing options parameter/);
    assert.throws(() => remoteCatalogue.addComponent({ market_endpoint: 'market' }), /market_endpoint option can only be used on local catalogues/);
    assert.throws(() => localCatalogue.addComponent({}), /at least one of the following options/);

    let task = localCatalogue.addComponent({
        file: { name: 'widget.wgt' },
        install_embedded_resources: true,
        force_create: true
    });
    requests[0].resolve({
        status: 201,
        responseText: JSON.stringify({ id: 'new-widget' })
    });

    const uploadResult = await task;
    assert.deepEqual(uploadResult, { id: 'new-widget' });
    assert.equal(requests[0].url, '/api/local/resources');
    assert.equal(requests[0].options.contentType, 'application/octet-stream');
    assert.deepEqual(requests[0].options.parameters, {
        install_embedded_resources: 'true',
        force_create: 'true'
    });
    assert.equal(taskTitles[0], 'Uploading packaged component widget.wgt');

    task = remoteCatalogue.addComponent({
        url: 'https://example.org/widget.wgt',
        headers: { Authorization: 'Bearer x' },
        market_endpoint: null,
        forceCreate: true,
        install_embedded_resources: false
    });
    requests[1].resolve({
        status: 400,
        responseText: JSON.stringify({ detail: 'bad request' })
    });
    await assert.rejects(task, /parsed:400/);
    assert.equal(parseErrors.at(-1), 400);
    assert.equal(requests[1].url, 'https://catalogue.example/catalogue/resources');
    assert.equal(requests[1].options.contentType, 'application/json');
    assert.equal(taskTitles[1], 'Installing component from https://example.org/widget.wgt');

    task = remoteCatalogue.addComponent({ url: 'https://example.org/widget.wgt' });
    requests[2].resolve({ status: 418, responseText: '{}' });
    await assert.rejects(task, /Unexpected response from server/);
});

test('WirecloudCatalogue deleteResource handles url selection and response parsing', async () => {
    const { WirecloudCatalogue, requests, taskTitles } = createCatalogueEnvironment();
    const catalogue = new WirecloudCatalogue();
    const resource = {
        vendor: 'acme',
        name: 'maps',
        title: 'Maps',
        group_id: 'acme/maps',
        uri: 'acme/maps/1.0',
        version: { text: '1.0' }
    };

    let task = catalogue.deleteResource(resource);
    requests[0].resolve({
        status: 200,
        responseText: JSON.stringify({})
    });
    const singleVersion = await task;
    assert.equal(requests[0].url, '/local/catalogue/resource/acme/maps/1.0');
    assert.deepEqual(singleVersion, { affectedVersions: ['1.0'] });
    assert.equal(taskTitles[0], 'Deleting Maps (acme/maps/1.0)');

    task = catalogue.deleteResource(resource, { allversions: true });
    requests[1].resolve({
        status: 200,
        responseText: JSON.stringify({ affectedVersions: ['1.0', '0.9'] })
    });
    const allVersions = await task;
    assert.equal(requests[1].url, '/local/catalogue/resource/acme/maps');
    assert.deepEqual(allVersions, { affectedVersions: ['1.0', '0.9'] });
    assert.equal(taskTitles[1], 'Deleting all versions of Maps (acme/maps)');

    task = catalogue.deleteResource(resource);
    requests[2].resolve({ status: 500, responseText: '{}' });
    await assert.rejects(task, /Unexpected response from server/);

    task = catalogue.deleteResource(resource);
    requests[3].resolve({ status: 200, responseText: '{bad json' });
    await assert.rejects(task, /Unexpected response from server/);
});
