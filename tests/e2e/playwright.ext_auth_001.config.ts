import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'ext_auth_001.spec.ts',
  workers: 1,
  fullyParallel: false,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  reporter: 'list',
  use: { trace: 'off', screenshot: 'off', video: 'off' },
});
