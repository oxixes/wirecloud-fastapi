import { merge } from 'webpack-merge';
import baseConfig from './webpack.base';
import { createCSSEntries, getOrderedScriptsEntries, getScriptAliases } from './entries';
import * as MonacoWebpackPlugin from 'monaco-editor-webpack-plugin';
import { Configuration } from 'webpack';

const config: Configuration = merge(baseConfig, {
    entry: Object.assign({}, createCSSEntries(), getOrderedScriptsEntries()),

    resolve: {
        alias: getScriptAliases(),
    },

    plugins: [
        new MonacoWebpackPlugin({
            filename: 'js/[name].worker.js',
        })
    ]
});

export default config;