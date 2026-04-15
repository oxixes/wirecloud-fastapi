const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

const setupTutorialCatalogue = () => {
    class Tutorial {}
    class Fragment {
        constructor(nodes) {
            this.nodes = nodes;
        }
    }

    global.StyledElements = { Fragment };
    global.Wirecloud = {
        ui: { Tutorial },
        Utils: {
            gettext: (text) => text,
            interpolate: (template, context) => template.replace('%(tutorial)s', context.tutorial),
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/TutorialCatalogue.js');
    return { Tutorial, catalogue: Wirecloud.TutorialCatalogue };
};

test('Wirecloud.TutorialCatalogue.add rejects non Tutorial instances', () => {
    resetLegacyRuntime();
    const { catalogue } = setupTutorialCatalogue();
    assert.throws(() => catalogue.add('bad', {}), /must be an instance/);
});

test('Wirecloud.TutorialCatalogue.add and get store tutorials by id', () => {
    resetLegacyRuntime();
    const { Tutorial, catalogue } = setupTutorialCatalogue();

    class DemoTutorial extends Tutorial {
        constructor(label) {
            super();
            this.label = label;
        }
    }

    const tutorial = new DemoTutorial('Demo');
    catalogue.add('demo', tutorial);

    assert.equal(catalogue.get('demo'), tutorial);
    assert.deepEqual(catalogue.tutorials, [tutorial]);
});

test('Wirecloud.TutorialCatalogue.buildTutorialReferences returns description and list nodes', () => {
    resetLegacyRuntime();
    const { Tutorial, catalogue } = setupTutorialCatalogue();

    class DemoTutorial extends Tutorial {
        constructor(label) {
            super();
            this.label = label;
        }
    }

    catalogue.add('demo', new DemoTutorial('Demo'));
    const fragment = catalogue.buildTutorialReferences(['demo']);

    assert.equal(fragment.nodes[0].tagName, 'P');
    assert.equal(fragment.nodes[1].tagName, 'UL');
});

test('Wirecloud.TutorialCatalogue links trigger tutorial start', () => {
    resetLegacyRuntime();
    const { Tutorial, catalogue } = setupTutorialCatalogue();
    let started = 0;

    class DemoTutorial extends Tutorial {
        constructor(label) {
            super();
            this.label = label;
        }

        start() {
            started += 1;
        }
    }

    catalogue.add('demo', new DemoTutorial('Demo'));
    const fragment = catalogue.buildTutorialReferences(['demo']);
    fragment.nodes[1].firstChild.firstChild.dispatchEvent({
        type: 'click',
        stopPropagation() {},
        preventDefault() {},
    });

    assert.equal(started, 1);
});
