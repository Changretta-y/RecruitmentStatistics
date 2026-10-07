import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: '.',
  testMatch: 'test_web_app_010_logo.e2e.spec.ts',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  workers: 1,
  reporter: [['list']],
  outputDir: './.artifacts/web-app-010-logo',
  use: {
    baseURL: 'http://127.0.0.1:5200',
    ...devices['Desktop Edge'],
    channel: 'msedge',
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5200 --strictPort',
    url: 'http://127.0.0.1:5200',
    cwd: resolve(dirname(fileURLToPath(import.meta.url)), '..'),
    timeout: 60_000,
  },
});
