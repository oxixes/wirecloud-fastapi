import { rmSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import process from 'node:process';

const rootDir = process.cwd();
const coverageRoot = path.join(rootDir, 'coverage', 'js');
const c8Bin = path.join(rootDir, 'node_modules', '.bin', process.platform === 'win32' ? 'c8.cmd' : 'c8');

const listFromEnv = (name) => (process.env[name] || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);

const coverageIncludes = listFromEnv('JS_TEST_COVERAGE_INCLUDE');
const coverageExcludes = listFromEnv('JS_TEST_COVERAGE_EXCLUDE');
const excludes = coverageExcludes.length > 0 ? coverageExcludes : [
    '**/*.min.js',
    '**/themes/**',
    '**/commons/static/js/lib/urlify.js',
    '**/fiware/static/js/NGSI/NGSI.js',
];

rmSync(coverageRoot, { recursive: true, force: true });

const c8Args = [
    '--all',
    '--reporter=text',
    '--reporter=lcov',
    '--reports-dir',
    coverageRoot,
    '--temp-directory',
    path.join(coverageRoot, 'tmp'),
    '--src',
    'src/wirecloud',
];

if (coverageIncludes.length > 0) {
    coverageIncludes.forEach((pattern) => {
        c8Args.push('--include', pattern);
    });
} else {
    c8Args.push('--include', '**/static/js/**/*.js');
}

excludes.forEach((pattern) => {
    c8Args.push('--exclude', pattern);
});

const thresholds = {
    lines: process.env.JS_TEST_COVERAGE_LINES,
    branches: process.env.JS_TEST_COVERAGE_BRANCHES,
    functions: process.env.JS_TEST_COVERAGE_FUNCTIONS,
};

if (Object.values(thresholds).some(Boolean)) {
    c8Args.push('--check-coverage');
    Object.entries(thresholds).forEach(([metric, value]) => {
        if (value) {
            c8Args.push(`--${metric}`, value);
        }
    });
}

const result = spawnSync(c8Bin, [
    ...c8Args,
    process.execPath,
    './scripts/run-js-tests.mjs',
], {
    cwd: rootDir,
    env: process.env,
    stdio: 'inherit',
});

if (result.error) {
    throw result.error;
}

process.exit(result.status ?? 1);
