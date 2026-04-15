import { readdirSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import process from 'node:process';

const rootDir = process.cwd();
const testsRoot = path.join(rootDir, 'tests_js');

const findTestFiles = (directory) => {
    const testFiles = [];

    for (const entry of readdirSync(directory, { withFileTypes: true })) {
        const entryPath = path.join(directory, entry.name);

        if (entry.isDirectory()) {
            testFiles.push(...findTestFiles(entryPath));
        } else if (entry.isFile() && entry.name.endsWith('.test.cjs')) {
            testFiles.push(entryPath);
        }
    }

    return testFiles;
};

const testFiles = findTestFiles(testsRoot).sort();
if (testFiles.length === 0) {
    console.error('No JavaScript tests found under tests_js/.');
    process.exit(1);
}

const result = spawnSync(process.execPath, [
    '--test',
    '--test-concurrency=1',
    '--test-isolation=process',
    '--test-reporter=spec',
    ...testFiles,
], {
    cwd: rootDir,
    env: process.env,
    stdio: 'inherit',
});

if (result.error) {
    throw result.error;
}

process.exit(result.status ?? 1);
