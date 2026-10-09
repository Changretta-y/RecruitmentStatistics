/** EXT-ROUTE-004: public delivery ZIP identity and existing popup login behavior. */
import { test, expect, chromium } from '@playwright/test';
import { createServer } from 'node:http';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = resolve(__dirname, '../..');
const ARTIFACTS = join(ROOT, 'artifacts');
const EXPECTED_ZIP = 'recruitment-capture-extension-v0.2.0.zip';
const OLD_ZIP = 'recruitment-capture-extension-v0.1.0.zip';

function deliveredZip() {
  const current = join(ARTIFACTS, EXPECTED_ZIP);
  return existsSync(current) ? current : join(ARTIFACTS, OLD_ZIP);
}

function unpackDelivery() {
  const zip = deliveredZip();
  expect(existsSync(zip)).toBe(true);
  const workspace = mkdtempSync(join(tmpdir(), 'ext-route-004-'));
  const unpacked = join(workspace, 'extension');
  try {
    execFileSync('uv', [
      'run', '--no-sync', 'python', '-c',
      'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
      zip, unpacked,
    ], { cwd: join(ROOT, 'backend'), stdio: 'pipe' });
    return { zip, workspace, unpacked, manifest: JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8')) };
  } catch (error) {
    cleanup(workspace);
    throw error;
  }
}

function cleanup(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-route-004-')) {
    throw new Error('unsafe temporary path');
  }
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

test('delivered loadable ZIP filename advertises version 0.2.0', () => {
  const delivery = unpackDelivery();
  try {
    expect(basename(delivery.zip)).toBe(EXPECTED_ZIP);
  } finally { cleanup(delivery.workspace); }
});

test('delivered ZIP manifest declares version 0.2.0', () => {
  const delivery = unpackDelivery();
  try {
    expect(delivery.manifest.version).toBe('0.2.0');
    expect(delivery.manifest.manifest_version).toBe(3);
  } finally { cleanup(delivery.workspace); }
});

test('delivered extension still accepts synthetic login and opens the capture view', async () => {
  const delivery = unpackDelivery();
  const username = `version-fixture-${randomUUID().slice(0, 8)}`;
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
    const send = (status: number, payload: unknown) => {
      response.setHeader('Content-Type', 'application/json');
      response.writeHead(status).end(JSON.stringify(payload));
    };
    if (url.pathname === '/api/v1/auth/login/' && request.method === 'POST') {
      if (body.username !== username || body.password !== password) return send(401, { code: 'INVALID_CREDENTIALS' });
      return send(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user: { id: 704, username } });
    }
    if (url.pathname === '/api/v1/auth/me/' && request.method === 'GET') return send(200, { id: 704, username });
    if (url.pathname === '/api/v1/applications/' && request.method === 'GET') {
      return send(200, { count: 0, page: 1, page_size: 20, total_pages: 0, next: null, previous: null, results: [] });
    }
    if (url.pathname.startsWith('/api/')) return send(404, { code: 'NOT_FOUND' });
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.writeHead(200).end('<!doctype html><title>Synthetic fixture</title>');
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
    await expect(popup.locator('#capture-view')).toBeVisible();
    expect(calls).toContain('POST /api/v1/auth/login/');
  } finally {
    await context?.close();
    server.closeAllConnections();
    await new Promise<void>(closed => server.close(() => closed()));
    cleanup(delivery.workspace);
  }
});
