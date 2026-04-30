const test = require('node:test');
const assert = require('node:assert/strict');
const {
    bootstrapStyledElementsBase,
    loadLegacyScript,
    resetLegacyRuntime,
} = require('../../support/legacy-runtime.cjs');

const loadWirecloudUtils = () => {
    resetLegacyRuntime();
    bootstrapStyledElementsBase();
    global.gettext = (text) => `tr:${text}`;
    global.ngettext = (singular, plural, count) => count === 1 ? `sg:${singular}` : `pl:${plural}`;
    global.Wirecloud = {
        ui: {
            FullDragboardLayout: class FullDragboardLayout {},
            FreeLayout: class FreeLayout {},
        }
    };
    global.document.cookie = 'session=abc123; theme=dark';
    loadLegacyScript('src/wirecloud/commons/static/js/wirecloud/Utils.js');
};

test('Wirecloud.Utils reuses StyledElements helpers and translation globals', () => {
    loadWirecloudUtils();

    assert.equal(Wirecloud.Utils, StyledElements.Utils);
    assert.equal(Wirecloud.Utils.gettext('hello'), 'tr:hello');
    assert.equal(Wirecloud.Utils.ngettext('file', 'files', 2), 'pl:files');
});

test('Wirecloud.Utils.getLayoutMatrix reserves only non free-form widgets', () => {
    loadWirecloudUtils();

    const reserveCalls = [];
    const layout = {
        columns: 3,
        _reserveSpace2(matrix, marker, left, top, width, height) {
            reserveCalls.push({ marker, left, top, width, height, matrixColumns: matrix.length });
        }
    };
    const fixedWidget = {
        layout: {},
        model: {
            getLayoutConfigBySize(size) {
                assert.equal(size, 'desktop');
                return { left: 1, top: 2, width: 3, height: 4 };
            }
        }
    };
    const freeWidget = {
        layout: new Wirecloud.ui.FreeLayout(),
        model: {
            getLayoutConfigBySize() {
                throw new Error('should not be called');
            }
        }
    };
    const fullDragboardWidget = {
        layout: new Wirecloud.ui.FullDragboardLayout(),
        model: {
            getLayoutConfigBySize() {
                throw new Error('should not be called');
            }
        }
    };

    const matrix = Wirecloud.Utils.getLayoutMatrix(layout, [fixedWidget, freeWidget, fullDragboardWidget], 'desktop');
    assert.equal(matrix.length, 3);
    assert.deepEqual(reserveCalls, [{
        marker: 'NOTAWIDGET',
        left: 1,
        top: 2,
        width: 3,
        height: 4,
        matrixColumns: 3
    }]);
});

test('Wirecloud.Utils.getCookie returns values or null', () => {
    loadWirecloudUtils();

    assert.equal(Wirecloud.Utils.getCookie('theme'), 'dark');
    assert.equal(Wirecloud.Utils.getCookie('missing'), null);
});
