import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'ext_route_005.spec.ts',
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 8_000 },
  reporter: 'list',
  use: { trace: 'off', screenshot: 'off', video: 'off' },
});
