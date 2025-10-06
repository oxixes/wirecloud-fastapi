import { merge } from 'webpack-merge';
import baseConfig from './webpack.base';
import { createCSSEntries, getOrderedScriptsEntries, getScriptAliases } from './entries';
import MonacoWebpackPlugin from 'monaco-editor-webpack-plugin';
import { Configuration, IgnorePlugin } from 'webpack';

const config: Configuration = merge(baseConfig, {
    entry: Object.assign({}, createCSSEntries(), getOrderedScriptsEntries()),

    resolve: {
        alias: getScriptAliases(),
        fallback: {
            "whatwg-url": false
        }
    },

    plugins: [
        new MonacoWebpackPlugin({
            filename: 'js/[name].worker.js',
        }),
        new IgnorePlugin({
            resourceRegExp: /^whatwg-url$/
        })
    ]
});

export default config;