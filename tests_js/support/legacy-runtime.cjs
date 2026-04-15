const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { installBrowserShim } = require('./browser-shim.cjs');

const repoRoot = path.resolve(__dirname, '..', '..');
const loadedScripts = new Set();

const normalizeScriptPath = (scriptPath) => {
    return path.isAbsolute(scriptPath) ? scriptPath : path.join(repoRoot, scriptPath);
};

const transformImports = (source) => {
    return source.replace(
        /^import\s+\*\s+as\s+([A-Za-z_$][\w$]*)\s+from\s+['"]([^'"]+)['"];?\s*$/gm,
        (_, bindingName, moduleName) => `const ${bindingName} = globalThis.__wirecloud_test_imports[${JSON.stringify(moduleName)}];`
    );
};

const loadLegacyScript = (scriptPath) => {
    const absolutePath = normalizeScriptPath(scriptPath);
    if (loadedScripts.has(absolutePath)) {
        return absolutePath;
    }

    const source = fs.readFileSync(absolutePath, 'utf8');
    const transformedSource = transformImports(source);
    vm.runInThisContext(transformedSource, { filename: absolutePath });
    loadedScripts.add(absolutePath);

    return absolutePath;
};

const loadLegacyScripts = (scriptPaths) => {
    scriptPaths.forEach((scriptPath) => loadLegacyScript(scriptPath));
};

const resetLegacyRuntime = () => {
    loadedScripts.clear();
    delete global.StyledElements;
    delete global.Wirecloud;
    delete global.__wirecloud_test_imports;
    global.gettext = (text) => text;
    global.ngettext = (singular, plural, count) => count === 1 ? singular : plural;
    installBrowserShim();
    global.__wirecloud_test_imports = {};
};

const bootstrapStyledElementsBase = () => {
    if (global.StyledElements != null && global.StyledElements.StyledElement != null) {
        return global.StyledElements;
    }

    loadLegacyScripts([
        'src/wirecloud/commons/static/js/StyledElements/Utils.js',
        'src/wirecloud/commons/static/js/StyledElements/Event.js',
        'src/wirecloud/commons/static/js/StyledElements/ObjectWithEvents.js',
        'src/wirecloud/commons/static/js/StyledElements/StyledElements.js',
    ]);

    return global.StyledElements;
};

const bootstrapWirecloudVersion = () => {
    bootstrapStyledElementsBase();

    if (global.Wirecloud == null) {
        global.Wirecloud = {
            Utils: global.StyledElements.Utils,
            WirecloudCatalogue: {},
        };
    } else if (global.Wirecloud.Utils == null) {
        global.Wirecloud.Utils = global.StyledElements.Utils;
    }

    if (global.Wirecloud.WirecloudCatalogue == null) {
        global.Wirecloud.WirecloudCatalogue = {};
    }

    if (global.Wirecloud.Version == null) {
        loadLegacyScript('src/wirecloud/platform/static/js/wirecloud/Version.js');
    }

    return global.Wirecloud;
};

resetLegacyRuntime();

module.exports = {
    bootstrapStyledElementsBase,
    bootstrapWirecloudVersion,
    loadLegacyScript,
    loadLegacyScripts,
    repoRoot,
    resetLegacyRuntime,
};
