const test = require('node:test');
const assert = require('node:assert/strict');
const { loadLegacyScript, resetLegacyRuntime } = require('../support/legacy-runtime.cjs');

class FakeFragment {
    constructor(children = []) {
        this.children = [];
        if (Array.isArray(children)) {
            children.forEach((child) => this.appendChild(child));
        } else {
            this.appendChild(children);
        }
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }
}

class FakeButton {
    constructor(options = {}) {
        this.options = options;
        this.disabled = false;
        this.listeners = {};
    }

    addEventListener(type, listener) {
        if (this.listeners[type] == null) {
            this.listeners[type] = [];
        }
        this.listeners[type].push(listener);
    }

    disable() {
        this.disabled = true;
        return this;
    }

    enable() {
        this.disabled = false;
        return this;
    }

    focus() {
        this.focused = true;
        return this;
    }

    trigger(type) {
        (this.listeners[type] || []).forEach((listener) => listener());
    }
}

class FakeTooltip {
    constructor(options) {
        this.options = options;
    }

    bind(element) {
        this.boundElement = element;
    }
}

class FakeGUIBuilder {
    constructor() {
        this.DEFAULT_OPENING = '<o>';
        this.DEFAULT_CLOSING = '</o>';
    }

    parse(template, context) {
        if (String(template).includes('alert')) {
            const div = document.createElement('div');
            div.textContent = context.message;
            return div;
        }

        this.lastContext = context;
        const root = document.createElement('div');
        const clickable = document.createElement('a');
        const titleNode = document.createElement('span');
        root.appendChild(clickable);
        root.appendChild(titleNode);

        root.matches = (selector) => selector === '.click_for_details';
        root.querySelectorAll = (selector) => selector === '.click_for_details' ? [clickable] : [];
        root.querySelector = (selector) => selector === '.title-tooltip' ? titleNode : null;
        clickable.matches = () => false;
        clickable.querySelectorAll = () => [];
        clickable.querySelector = () => null;

        return { elements: [root, clickable, 'ignored'] };
    }
}

const createEnvironment = (extraContext = { extra: 'ctx' }) => {
    resetLegacyRuntime();

    const openedUrls = [];
    global.window.open = (url, target) => openedUrls.push({ url, target });
    global.moment = (date) => ({ fromNow: () => `from:${date}` });

    const commands = [];
    const utils = {
        gettext: (text) => text,
        interpolate: (pattern, values) => pattern.replace('%(type)s', values.type || '').replace('%(tag)s', values.tag || '').replace('%(rating)s', values.rating || ''),
        clone: (value) => JSON.parse(JSON.stringify(value)),
        merge: (target, source) => Object.assign({}, target, source),
        formatSize: (size) => `${size}B`,
    };

    global.StyledElements = {
        GUIBuilder: FakeGUIBuilder,
        Fragment: FakeFragment,
        Button: FakeButton,
        Tooltip: FakeTooltip,
    };

    global.Wirecloud = {
        Utils: utils,
        ui: {},
        LocalCatalogue: {
            getResource: (vendor, name, version) => ({ vendor, name, version }),
            resourceExists: () => true,
        },
        UserInterfaceManager: {
            changeCurrentView: (view) => commands.push(['changeCurrentView', view]),
            views: {
                myresources: {
                    createUserCommand: (name, resource, view) => () => commands.push([name, resource.uri, !!view]),
                },
            },
        },
        activeWorkspace: {
            view: {
                activeTab: {
                    createWidget: (widget) => commands.push(['createWidget', widget.name]),
                },
            },
        },
    };

    loadLegacyScript('src/wirecloud/catalogue/static/js/wirecloud/ui/ResourcePainter.js');

    const container = new FakeFragment();
    container.clear = function clear() {
        this.children = [];
    };

    const catalogueView = {
        catalogue: global.Wirecloud.LocalCatalogue,
        createUserCommand: (name, resource) => () => commands.push([name, resource.uri]),
    };

    const painter = new global.Wirecloud.ui.ResourcePainter(catalogueView, '<template/>', container, extraContext);

    return { painter, commands, openedUrls, container };
};

const buildResource = (type, extra = {}) => ({
    title: 'Resource',
    name: 'resource',
    uri: `acme/resource/${type}`,
    vendor: 'acme',
    version: { text: '1.0' },
    authors: [{ name: 'Alice' }],
    contributors: [{ name: 'Bob' }],
    description: 'desc',
    longdescription: '<p>long</p>',
    type,
    date: '2026-01-01',
    homepage: 'https://home.example',
    issuetracker: 'https://issues.example',
    license: 'MIT',
    licenseurl: 'https://license.example',
    rating: 3.5,
    image: 'https://cdn.example/image.png',
    tags: [{ value: 'zeta', apparences: 1 }, { value: 'alpha', apparences: 5 }],
    size: 128,
    description_url: 'https://download.example',
    getAllVersions: () => [{ text: '1.0' }, { text: '0.9' }],
    isAllow: (permission) => ['uninstall', 'uninstall-all', 'delete', 'delete-all'].includes(permission),
    ...extra,
});

test('ResourcePainter covers main rendering, commands, and error states', async () => {
    const { painter, commands, container } = createEnvironment();

    const timerQueue = [];
    const originalSetTimeout = global.setTimeout;
    global.setTimeout = (fn) => {
        timerQueue.push(fn);
        return 0;
    };

    try {
        ['widget', 'operator', 'mashup', 'pack'].forEach((type) => {
            const resource = buildResource(type);
            const element = painter.paint(resource);
            assert.equal(Array.isArray(element.elements), true);

            const ctx = painter.builder.lastContext;
            const longdescription = ctx.longdescription();
            assert.equal(longdescription instanceof FakeFragment, true);

            const typeNode = ctx.type();
            assert.equal(typeNode.className.includes('label'), true);

            const homeButton = ctx.home();
            const issueButton = ctx.issuetracker();
            const licenseButton = ctx.license_home();
            homeButton.trigger('click');
            issueButton.trigger('click');
            licenseButton.trigger('click');

            const image = ctx.image();
            const wrapper = document.createElement('div');
            wrapper.appendChild(image);
            if (typeof image.onerror === 'function') {
                image.onerror({ target: image });
            }

            const tags = ctx.tags({ max: 1 });
            assert.equal(tags.children.length, 2);
            assert.equal(ctx.lastupdate(), 'from:2026-01-01');
            assert.equal(ctx.size(), '128B');
            assert.equal(ctx.versions(), 'v1.0, v0.9');
            assert.equal(ctx.authors({ class: 'p' }).children.length, 1);
            assert.equal(ctx.contributors({ class: 'p' }).children.length, 1);
        });

        const noLinks = buildResource('operator', {
            title: '',
            homepage: '',
            issuetracker: '',
            license: '',
            licenseurl: '',
            image: '',
            rating: 0,
            authors: [],
            contributors: [],
            tags: [],
            getAllVersions: () => [{ text: '1.0' }],
            isAllow: () => false,
        });
        painter.paint(noLinks);
        const emptyCtx = painter.builder.lastContext;
        assert.equal(emptyCtx.home().disabled, true);
        assert.equal(emptyCtx.issuetracker().disabled, true);
        assert.equal(emptyCtx.license_home().disabled, true);

        const noImage = emptyCtx.image();
        assert.equal(noImage.getAttribute('alt'), 'resource');
        const noImageWrapper = document.createElement('div');
        noImageWrapper.appendChild(noImage);

        timerQueue.splice(0).forEach((fn) => fn());
        assert.equal(noImageWrapper.classList.contains('se-thumbnail-missing'), true);

        const advanced = painter.renderAdvancedOperations(buildResource('widget'));
        assert.equal(advanced.children.length >= 6, true);
        advanced.children.forEach((button) => button.trigger?.('click'));

        const tagList = painter.renderTagList(buildResource('pack'), null, 1);
        assert.equal(tagList.children.length, 1);
        const allTags = painter.renderTagList(buildResource('pack'));
        assert.equal(allTags.children.length, 2);

        const emptyPeople = painter.get_people_list([], { class: 'x' });
        assert.equal(emptyPeople.textContent, 'N/A');
        const people = painter.get_people_list([{ name: 'Ada' }, { name: 'Linus' }], { class: 'y' });
        assert.equal(people.children.length, 2);

        const starsZero = painter.get_popularity_html(null);
        assert.equal(starsZero.classList.contains('disabled'), true);
        const starsHalf = painter.get_popularity_html(4.5);
        assert.equal(starsHalf.childNodes.length, 5);

        const holder = document.createElement('div');
        holder.matches = () => false;
        holder.querySelectorAll = () => [];
        assert.throws(() => painter.create_simple_command(holder, '.missing', 'click', () => {}, true));

        const infoNode = painter.paintInfo('Info message');
        assert.equal(infoNode.textContent, 'Info message');
        const infoWithContext = painter.paintInfo('Hello %(name)s', { name: 'Alice' });
        assert.equal(Boolean(infoWithContext), true);

        painter.setError('boom');
        assert.equal(container.children.length, 1);

        assert.equal(commands.length > 0, true);
    } finally {
        global.setTimeout = originalSetTimeout;
    }
});

test('ResourcePainter uses function extra_context and falls back to an empty object', () => {
    const functionCalls = [];
    const { painter: fnPainter } = createEnvironment((resource) => {
        functionCalls.push(resource.uri);
        return { marker: 'fn-context' };
    });

    fnPainter.paint(buildResource('widget'));
    assert.deepEqual(functionCalls, ['acme/resource/widget']);
    assert.equal(fnPainter.builder.lastContext.marker, 'fn-context');

    const { painter: fallbackPainter } = createEnvironment(1);
    assert.deepEqual(fallbackPainter.extra_context, {});
});

test('ResourcePainter renderAdvancedOperations includes Publish for local catalogue', () => {
    const { painter, commands } = createEnvironment();
    const resource = buildResource('widget');
    const advanced = painter.renderAdvancedOperations(resource);

    const publishButton = advanced.children.find((button) => button?.options?.text === 'Publish');
    assert.equal(Boolean(publishButton), true);
    publishButton.trigger('click');
    assert.equal(commands.some((entry) => entry[0] === 'publishOtherMarket'), true);
});











