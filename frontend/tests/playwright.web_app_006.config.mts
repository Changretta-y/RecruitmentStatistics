import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: '.',
  testMatch: 'test_web_app_006.e2e.spec.ts',
  timeout: 30_000,
  expect: { timeout: 4_000 },
  workers: 1,
  reporter: [['list']],
  outputDir: './.artifacts/web-app-006',
  use: {
    baseURL: 'http://127.0.0.1:5189',
    ...devices['Desktop Edge'],
    channel: 'msedge',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5189 --strictPort',
    url: 'http://127.0.0.1:5189',
    cwd: resolve(dirname(fileURLToPath(import.meta.url)), '..'),
    env: { VITE_API_PROXY_TARGET: 'http://127.0.0.1:8019', VITE_DEV_PORT: '5189', VITE_API_BASE_URL: '' },
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
