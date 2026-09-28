import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: '.',
  testMatch: 'test_web_share_001.e2e.spec.ts',
  timeout: 25_000,
  expect: { timeout: 4_000 },
  workers: 1,
  reporter: 'list',
  outputDir: '../../test-results/web-share-001',
  use: { baseURL: 'http://127.0.0.1:4176', ...devices['Desktop Chrome'] },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4176 --strictPort',
    url: 'http://127.0.0.1:4176',
    cwd: resolve(dirname(fileURLToPath(import.meta.url)), '..'),
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
