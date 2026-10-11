/** EXT-ROUTE-007 black-box checks against the delivered extension archive. */
import { test, expect, chromium } from '@playwright/test';
import { createServer } from 'node:http';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve, sep } from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = resolve(__dirname, '../..');
const ZIP_NAME = 'recruitment-capture-extension-v0.2.0.zip';
const ZIP_PATH = join(ROOT, 'artifacts', ZIP_NAME);
const LOGO_PATH = join(ROOT, 'frontend', 'public', 'logo.png');

function unpackDelivery() {
  const workspace = mkdtempSync(join(tmpdir(), 'ext-route-007-'));
  const unpacked = join(workspace, 'extension');
  const archive = join(workspace, ZIP_NAME);
  try {
    // The committed delivery remains testable even if another task has removed
    // the worktree copy.  At READY_FOR_TEST the worktree archive takes priority.
    const bytes = existsSync(ZIP_PATH)
      ? readFileSync(ZIP_PATH)
      : execFileSync('git', ['show', `HEAD:artifacts/${ZIP_NAME}`], { cwd: ROOT });
    writeFileSync(archive, bytes);
    execFileSync('uv', [
      'run', '--no-sync', 'python', '-c',
      'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
      archive, unpacked,
    ], { cwd: join(ROOT, 'backend'), stdio: 'pipe' });
    return { workspace, unpacked, manifest: JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8')) };
  } catch (error) {
    cleanup(workspace);
    throw error;
  }
}

function cleanup(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-route-007-')) {
    throw new Error('unsafe temporary path');
  }
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function iconPaths(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  expect(value).toBeTruthy();
  expect(typeof value).toBe('object');
  const paths = Object.values(value as Record<string, unknown>);
  expect(paths.length).toBeGreaterThan(0);
  expect(paths.every(path => typeof path === 'string')).toBe(true);
  return paths as string[];
}

function expectBundledPlatformLogo(paths: string[], unpacked: string) {
  const platformLogo = readFileSync(LOGO_PATH);
  for (const path of paths) {
    expect(path).not.toMatch(/^(?:https?:|\/|\\)|\.\./i);
    const bundled = resolve(unpacked, path);
    expect(bundled.startsWith(unpacked + sep)).toBe(true);
    expect(existsSync(bundled)).toBe(true);
    expect(readFileSync(bundled).equals(platformLogo)).toBe(true);
  }
}

test('delivered extension remains at manifest version 0.2.0', () => {
  const delivery = unpackDelivery();
  try {
    expect(delivery.manifest.version).toBe('0.2.0');
    expect(delivery.manifest.manifest_version).toBe(3);
  } finally { cleanup(delivery.workspace); }
});

test('manifest extension icons point to bundled byte-identical platform logo', () => {
  const delivery = unpackDelivery();
  try {
    expectBundledPlatformLogo(iconPaths(delivery.manifest.icons), delivery.unpacked);
  } finally { cleanup(delivery.workspace); }
});

test('manifest action icon points to bundled byte-identical platform logo', () => {
  const delivery = unpackDelivery();
  try {
    expectBundledPlatformLogo(iconPaths(delivery.manifest.action?.default_icon), delivery.unpacked);
  } finally { cleanup(delivery.workspace); }
});

test('delivered extension still logs in and opens capture with synthetic credentials', async () => {
  const delivery = unpackDelivery();
  const username = `logo-fixture-${randomUUID().slice(0, 8)}`;
  const password = randomUUID();
  const access = randomUUID();
  const refresh = randomUUID();
  const calls: string[] = [];
  const server = createServer(async (request, response) => {
    const url = new URL(request.url || '/', `http://${request.headers.host}`);
    const chunks: Buffer[] = [];
    for await (const chunk of request) chunks.push(Buffer.from(chunk));
    let body: Record<string, unknown> = {};
    try { body = JSON.parse(Buffer.concat(chunks).toString() || '{}') as Record<string, unknown>; } catch { /* no JSON */ }
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type');
    response.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    if (request.method === 'OPTIONS') { response.writeHead(204).end(); return; }
    if (url.pathname.startsWith('/api/')) calls.push(`${request.method} ${url.pathname}`);
    const send = (status: number, data: unknown) => {
      response.setHeader('Content-Type', 'application/json');
      response.writeHead(status).end(JSON.stringify(data));
    };
    if (url.pathname === '/api/v1/auth/login/' && request.method === 'POST') {
      if (body.username !== username || body.password !== password) return send(401, { code: 'INVALID_CREDENTIALS' });
      return send(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user: { id: 807, username } });
    }
    if (url.pathname === '/api/v1/auth/me/' && request.method === 'GET') return send(200, { id: 807, username });
    if (url.pathname === '/api/v1/applications/' && request.method === 'GET') {
      return send(200, { count: 0, page: 1, page_size: 20, total_pages: 0, next: null, previous: null, results: [] });
    }
    if (url.pathname.startsWith('/api/')) return send(404, { code: 'NOT_FOUND' });
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.writeHead(200).end('<!doctype html><title>Synthetic logo fixture</title>');
  });
  server.on('connect', (_request, socket) => socket.destroy());
  await new Promise<void>(ready => server.listen(0, '127.0.0.1', ready));
  const port = (server.address() as { port: number }).port;
  let context: Awaited<ReturnType<typeof chromium.launchPersistentContext>> | undefined;
  try {
    context = await chromium.launchPersistentContext(join(delivery.workspace, 'profile'), {
      channel: process.env.EXT_AUTH_BROWSER_CHANNEL || 'msedge',
      headless: true,
      ignoreDefaultArgs: ['--disable-extensions'],
      proxy: { server: `http://127.0.0.1:${port}`, bypass: '<-loopback>' },
      args: [`--disable-extensions-except=${delivery.unpacked}`, `--load-extension=${delivery.unpacked}`, '--host-resolver-rules=MAP * 127.0.0.1, EXCLUDE localhost', '--disable-background-networking'],
    });
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 10_000 });
    const extensionId = new URL(worker.url()).host;
    const popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/${delivery.manifest.action.default_popup}`);
    await expect(popup.locator('#login-view')).toBeVisible();
    await popup.locator('#username').fill(username);
    await popup.locator('#password').fill(password);
    await popup.locator('#login-button').click();
    await expect(popup.locator('#company-name')).toBeVisible();
    expect(calls).toContain('POST /api/v1/auth/login/');
  } finally {
    await context?.close();
    server.closeAllConnections();
    await new Promise<void>(closed => server.close(() => closed()));
    cleanup(delivery.workspace);
  }
});
