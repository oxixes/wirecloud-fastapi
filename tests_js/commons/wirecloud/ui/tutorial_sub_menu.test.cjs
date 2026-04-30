const test = require('node:test');
const assert = require('node:assert/strict');
const {
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../../support/legacy-runtime.cjs');

test('Wirecloud.ui.TutorialSubMenu builds menu entries from TutorialCatalogue', () => {
    resetLegacyRuntime();

    class FakeSubMenuItem {
        constructor(label) {
            this.label = label;
            this.appended = [];
            this.menuitem = {
                addIconClass: (value) => {
                    this.iconClass = value;
                }
            };
        }

        append(entry) {
            this.appended.push(entry);
        }
    }

    class FakeMenuItem {
        constructor(label, callback) {
            this.label = label;
            this.callback = callback;
        }
    }

    const firstTutorial = {
        label: 'First',
        start() {
            return 'first';
        }
    };
    const secondTutorial = {
        label: 'Second',
        start() {
            return 'second';
        }
    };

    global.StyledElements = {
        SubMenuItem: FakeSubMenuItem,
        MenuItem: FakeMenuItem,
    };
    global.Wirecloud = {
        Utils: {
            gettext(text) {
                return `tx:${text}`;
            }
        },
        ui: {},
        TutorialCatalogue: {
            tutorials: [firstTutorial, secondTutorial]
        }
    };

    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/ui/TutorialSubMenu.js');

    const submenu = new Wirecloud.ui.TutorialSubMenu();
    assert.equal(submenu.label, 'tx:Tutorials');
    assert.equal(submenu.iconClass, 'far fa-map');
    assert.deepEqual(submenu.appended.map((entry) => entry.label), ['First', 'Second']);
    assert.equal(submenu.appended[0].callback(), 'first');
    assert.equal(submenu.appended[1].callback(), 'second');
});
