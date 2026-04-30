const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapWirecloudVersion,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../support/legacy-runtime.cjs');

test.beforeEach(() => {
    resetLegacyRuntime();
    bootstrapWirecloudVersion();
    loadLegacyScript('src/wirecloud/catalogue/static/js/wirecloud/WirecloudCatalogue/ResourceDetails.js');
});

test('WirecloudCatalogue.ResourceDetails exposes the newest version by default', () => {
    const catalogue = { name: 'local' };
    const resource = new Wirecloud.WirecloudCatalogue.ResourceDetails({
        vendor: 'acme',
        name: 'weather',
        type: 'widget',
        versions: [
            {
                version: '1.0',
                authors: ['Alice'],
                contributors: ['Bob'],
                permissions: { uninstall: true, delete: false },
                image: 'one.png',
                uriTemplate: '/resource/1.0',
                description: 'Stable',
                longdescription: 'Stable build',
                homepage: 'https://example.org',
                doc: 'docs',
                changelog: 'changes',
                size: 128,
                title: 'Weather widget',
                date: '2026-01-10T00:00:00Z',
                license: 'AGPL',
                licenseurl: 'https://example.org/license',
                issuetracker: 'https://example.org/issues'
            },
            {
                version: '1.1rc1',
                authors: ['Alice'],
                contributors: [],
                permissions: { uninstall: false, delete: true },
                image: 'two.png',
                uriTemplate: '/resource/1.1rc1',
                description: 'Preview',
                longdescription: 'Preview build',
                homepage: '',
                doc: 'docs-rc',
                changelog: 'changes-rc',
                size: 256,
                title: 'Weather widget RC',
                date: '2026-02-15T00:00:00Z',
                license: 'AGPL',
                licenseurl: '',
                issuetracker: ''
            }
        ]
    }, catalogue);

    assert.equal(resource.catalogue, catalogue);
    assert.equal(resource.version.text, '1.1rc1');
    assert.equal(resource.uri, 'acme/weather/1.1rc1');
    assert.deepEqual(resource.getAllVersions().map((version) => version.text), ['1.1rc1', '1.0']);
    assert.equal(resource.isAllow('delete'), true);
    assert.equal(resource.isAllow('uninstall'), false);
});

test('WirecloudCatalogue.ResourceDetails can switch versions by object or string', () => {
    const resource = new Wirecloud.WirecloudCatalogue.ResourceDetails({
        vendor: 'acme',
        name: 'maps',
        type: 'widget',
        versions: [
            {
                version: '2.0',
                authors: [],
                contributors: [],
                permissions: { uninstall: true, delete: true },
                image: '',
                uriTemplate: '/resource/2.0',
                description: 'Latest',
                longdescription: 'Latest',
                homepage: '',
                doc: '',
                changelog: '',
                size: 64,
                title: 'Maps',
                date: '2026-03-01T00:00:00Z',
                license: '',
                licenseurl: '',
                issuetracker: ''
            },
            {
                version: '1.5',
                authors: [],
                contributors: [],
                permissions: { uninstall: false, delete: false },
                image: '',
                uriTemplate: '/resource/1.5',
                description: 'Previous',
                longdescription: 'Previous',
                homepage: '',
                doc: '',
                changelog: '',
                size: 32,
                title: 'Maps legacy',
                date: '2026-02-01T00:00:00Z',
                license: '',
                licenseurl: '',
                issuetracker: ''
            }
        ]
    }, {});

    resource.changeVersion('1.5');
    assert.equal(resource.version.text, '1.5');
    assert.equal(resource.isAllow('delete-all'), false);

    resource.changeVersion(new Wirecloud.Version('2.0'));
    assert.equal(resource.version.text, '2.0');
    assert.equal(resource.isAllow('uninstall-all'), true);
});

test('WirecloudCatalogue.ResourceDetails falls back to latest version for unknown requests', () => {
    const resource = new Wirecloud.WirecloudCatalogue.ResourceDetails({
        vendor: 'acme',
        name: 'tracker',
        type: 'operator',
        versions: [
            {
                version: '1.0',
                authors: ['Alice'],
                contributors: ['Bob'],
                permissions: { uninstall: true, delete: true },
                image: 'logo.png',
                uriTemplate: '/resource/1.0',
                description: 'desc',
                longdescription: 'long',
                homepage: 'https://example.org',
                doc: 'doc',
                changelog: 'changes',
                size: 100,
                title: 'Tracker',
                date: '2026-01-01T00:00:00Z',
                license: 'MIT',
                licenseurl: 'https://example.org/license',
                issuetracker: 'https://example.org/issues'
            }
        ]
    }, { source: 'catalogue' });

    resource.changeVersion('9.9');
    assert.equal(resource.getLastVersion().text, '1.0');
    assert.equal(resource.version.text, '1.0');
    assert.equal(resource.uri, 'acme/tracker/1.0');
    assert.equal(resource.image, 'logo.png');
    assert.equal(resource.description_url, '/resource/1.0');
    assert.equal(resource.description, 'desc');
    assert.equal(resource.longdescription, 'long');
    assert.equal(resource.homepage, 'https://example.org');
    assert.equal(resource.doc, 'doc');
    assert.equal(resource.changelog, 'changes');
    assert.deepEqual(resource.authors, ['Alice']);
    assert.deepEqual(resource.contributors, ['Bob']);
    assert.equal(resource.size, 100);
    assert.equal(resource.title, 'Tracker');
    assert.deepEqual(resource.tags, []);
    assert.equal(resource.rating, 0);
    assert.equal(resource.date.toISOString(), '2026-01-01T00:00:00.000Z');
    assert.equal(resource.license, 'MIT');
    assert.equal(resource.licenseurl, 'https://example.org/license');
    assert.equal(resource.issuetracker, 'https://example.org/issues');
    assert.equal(resource.isAllow('unknown'), undefined);
});
