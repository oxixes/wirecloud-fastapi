// -*- coding: utf-8 -*-

// Copyright (c) 2024 Future Internet Consulting and Development Solutions S.L.

// This file is part of Wirecloud.

// Wirecloud is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Wirecloud is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

import * as path from 'path';
import * as fs from 'fs';

const VIEWS: { [key: string]: string } = {
    'classic': 'platform',
    'smartphone': 'platform',
    'embedded': 'platform',
    'widget': 'widget',
    'index': 'platform'
};

const JS_VIEWS: string[] = ['classic', 'smartphone', 'embedded', 'widget', 'bootstrap'];

interface Theme {
    parent: string | null;
    get_css: (view: string) => string[];
    get_scripts: (view: string) => string[];
}

interface Plugin {
    get_scripts: (view: string) => string[];
    scripts_location: string | null;
}

const themePath = path.resolve(__dirname, '../themes');
const pluginPath = path.resolve(__dirname, '../');

const themes: { [key: string]: Theme } = {};
const plugins: { [key: string]: Plugin } = {};

// Search for theme directories in the themes directory. A theme is valid if it contains a theme.js file.
fs.readdirSync(themePath).forEach((theme) => {
    const themeDir = path.resolve(themePath, theme);
    const themeFile = path.resolve(themeDir, 'theme.ts');

    if (fs.existsSync(themeFile)) {
        // Import the theme file
        themes[theme] = require(themeFile).default;
    }
});

// Search for plugin directories in the wirecloud directory. A plugin is valid if it contains a plugin.js file.
fs.readdirSync(pluginPath).forEach((plugin) => {
    const pluginDir = path.resolve(pluginPath, plugin);
    const pluginFile = path.resolve(pluginDir, 'plugin.ts');

    if (fs.existsSync(pluginFile)) {
        // Import the plugin file
        plugins[plugin] = require(pluginFile).default;
    }
});

const resolveCSSIncludePaths = (theme: string): string[] => {
    const includePaths = [];
    let currentTheme: string | null = theme;

    while (currentTheme) {
        const resultingPath = path.resolve(__dirname, `../themes/${currentTheme}/static/css`);
        if (fs.existsSync(resultingPath)) {
            includePaths.push(resultingPath);
        }

        currentTheme = themes[currentTheme].parent;
    }

    return includePaths;
};

const createCSSEntries = (): { [key: string]: any } => {
    const entries: { [key: string]: any } = {};

    Object.keys(themes).forEach((theme) => {
        Object.keys(VIEWS).forEach((view) => {
            const entryKey = `${theme}_${view}_${VIEWS[view]}`;

            const css_files = new Set<string>();
            let currentTheme: string | null = theme;

            while (currentTheme) {
                themes[currentTheme].get_css(view).forEach((file) => {
                    css_files.add(file);
                });

                currentTheme = themes[currentTheme].parent;
            }

            const files = Array.from(css_files).map((file) => {
                let currentTheme: string | null = theme;

                let absolutePath = path.resolve(__dirname, `../themes/${currentTheme}/static/${file}`);
                while (!fs.existsSync(absolutePath) && currentTheme) {
                    currentTheme = themes[currentTheme].parent;
                    absolutePath = path.resolve(__dirname, `../themes/${currentTheme}/static/${file}`);
                }

                return (fs.existsSync(absolutePath)) ? absolutePath : null;
            });

            const filteredFiles = files.filter((file) => file !== null);
            if (filteredFiles.length > 0) {
                entries[entryKey] = {
                    import: filteredFiles,
                    layer: theme
                };
            }
        });
    });

    return entries;
};

const getOrderedScriptsEntries = (): { [key: string]: any } => {
    const entries: { [key: string]: any } = {};
    const pluginMaps: { [key: string]: Map<string, [string, number, boolean]> } = {};

    JS_VIEWS.forEach((view) => {
        // The order of the scripts is important
        const scripts = new Map<string, [string, number, boolean]>();

        let accumulatedOrder = 0;
        Object.keys(plugins).forEach((plugin) => {
            let addedScripts = 0;
            plugins[plugin].get_scripts(view).forEach((script, i) => {
                if (scripts.has(script)) {
                    return;
                }

                // NOTE: Plugins may import scripts from other plugins, while this will be changed in the future,
                // for now, we will need to search in all the plugins directories
                for (const key of Object.keys(plugins)) {
                    const scriptPath = path.resolve(__dirname, `../${key}/static/${script}`);
                    if (fs.existsSync(scriptPath)) {
                        scripts.set(script, [scriptPath, i + accumulatedOrder, false]);
                        addedScripts += 1;
                        break;
                    }
                }
            });

            accumulatedOrder += addedScripts;
        });

        pluginMaps[view] = scripts;
    });

    Object.keys(themes).forEach((theme) => {
        JS_VIEWS.forEach((view) => {
            // Duplicate the plugin scripts map
            const scripts = new Map<string, [string, number, boolean]>(
                Array.from(pluginMaps[view]).map(([key, value]) => [key, [...value] as [string, number, boolean]])
            );

            let accumulatedOrder = scripts.size;

            let currentTheme: string | null = theme;
            while (currentTheme) {
                themes[currentTheme].get_scripts(view).forEach((script, i) => {
                    const scriptPath = path.resolve(__dirname, `../themes/${currentTheme}/static/${script}`);
                    if (fs.existsSync(scriptPath)) {
                        if (scripts.has(script) && !scripts.get(script)![2]) {
                            scripts.get(script)![0] = scriptPath;
                            scripts.get(script)![2] = true;
                        } else if (!scripts.has(script)) {
                            scripts.set(script, [scriptPath, i + accumulatedOrder, true]);
                        }
                    }
                });

                accumulatedOrder += themes[currentTheme].get_scripts(view).length;
                currentTheme = themes[currentTheme].parent;
            }

            entries[`main-${theme}-${view}`] = {
                import: Array.from(scripts.values())
                    .sort((a, b) => a[1] - b[1])
                    .map((value) => value[0]),
                layer: theme
            };
        });
    });

    return entries;
};

const getScriptAliases = (): { [key: string]: string } => {
    const aliases: { [key: string]: string } = {};

    Object.keys(plugins).forEach((plugin) => {
        const scriptsLocation = plugins[plugin].scripts_location;
        if (scriptsLocation) {
            aliases[plugin] = path.resolve(__dirname, `../${plugin}/static/${scriptsLocation}`);
        }
    });

    return aliases;
};

const getThemeNames = (): string[] => {
    return Object.keys(themes);
}

export { createCSSEntries, resolveCSSIncludePaths, getOrderedScriptsEntries, getScriptAliases, getThemeNames };