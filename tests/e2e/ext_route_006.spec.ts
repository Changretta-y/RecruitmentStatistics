/** EXT-ROUTE-006 black-box top navigation through the public v0.2.0 ZIP. */
import { test, expect, chromium, type BrowserContext, type Page } from '@playwright/test';
import { createServer, type Server } from 'node:http';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = resolve(__dirname, '../..');
const ORIGIN = 'http://115.190.240.84:5173';
const ZIP = join(ROOT, 'artifacts/recruitment-capture-extension-v0.2.0.zip');
const records = [
  { id: 801, company_id: 81, company_name: 'Orbit Labs', positions: [{ id: 811, position_name: 'Platform Engineer', notes: '' }] },
  { id: 802, company_id: 82, company_name: 'Nimbus Works', positions: [{ id: 821, position_name: 'QA Analyst', notes: '' }] },
];
type Call = { path: string; method: string; body: Record<string, unknown> };

function unpackArtifact() {
  const workspace = mkdtempSync(join(tmpdir(), 'ext-route-006-'));
  const unpacked = join(workspace, 'extension');
  execFileSync('uv', [
    'run', '--no-sync', 'python', '-c',
    'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
    ZIP, unpacked,
  ], { cwd: join(ROOT, 'backend'), stdio: 'pipe' });
  return { workspace, unpacked, manifest: JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8')) };
}

function cleanupArtifact(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-route-006-')) {
    throw new Error('unsafe temporary path');
  }
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function jwt(type: string, seconds: number) {
  return [
    Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url'),
    Buffer.from(JSON.stringify({ user_id: 805, token_type: type, exp: Math.floor(Date.now() / 1000) + seconds, jti: randomUUID() })).toString('base64url'),
    Buffer.from(randomUUID()).toString('base64url'),
  ].join('.');
}

async function scenario() {
  const { workspace, unpacked, manifest } = unpackArtifact();
  const username = `entry-fixture-${randomUUID().slice(0, 8)}`;
  const password = randomUUID();
  const access = jwt('access', 1800);
  const refresh = jwt('refresh', 604800);
  const calls: Call[] = [];
  const server: Server = createServer(async (request, response) => {
    const url = new URL(request.url || '/', `http://${request.headers.host}`);
    const chunks: Buffer[] = [];
    for await (const chunk of request) chunks.push(Buffer.from(chunk));
    let body: Record<string, unknown> = {};
    try { body = JSON.parse(Buffer.concat(chunks).toString() || '{}') as Record<string, unknown>; } catch { /* no JSON */ }
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type');
    response.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,OPTIONS');
    if (request.method === 'OPTIONS') { response.writeHead(204).end(); return; }
    const send = (status: number, payload: unknown) => {
      response.setHeader('Content-Type', 'application/json');
      response.writeHead(status).end(JSON.stringify(payload));
    };
    if (url.pathname.startsWith('/api/')) calls.push({ path: url.pathname, method: request.method || 'GET', body });
    if (url.pathname === '/api/v1/auth/login/' && request.method === 'POST') {
      if (body.username !== username || body.password !== password) return send(401, { code: 'INVALID_CREDENTIALS' });
      return send(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user: { id: 805, username } });
    }
    if (url.pathname === '/api/v1/auth/me/' && request.method === 'GET') return send(200, { id: 805, username });
    if (url.pathname === '/api/v1/applications/' && request.method === 'GET') {
      return send(200, { count: 2, page: 1, page_size: 20, total_pages: 1, next: null, previous: null, results: records });
    }
    if (url.pathname === '/api/v1/applications/' && request.method === 'POST') {
      return send(201, { id: 803, ...body, positions: [{ id: 831, position_name: body.position_name, application_status: body.application_status || 'applied', notes: body.notes || '' }] });
    }
    if (url.pathname.startsWith('/api/')) return send(404, { code: 'NOT_FOUND' });
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.writeHead(200).end('<!doctype html><title>Synthetic job page</title><main>Black-box job listing</main>');
  });
  server.on('connect', (_request, socket) => socket.destroy());
  await new Promise<void>(ready => server.listen(0, '127.0.0.1', ready));
  const port = (server.address() as { port: number }).port;
  let context: BrowserContext | undefined;
  try {
    context = await chromium.launchPersistentContext(join(workspace, 'profile'), {
      channel: process.env.EXT_AUTH_BROWSER_CHANNEL || 'msedge',
      headless: true,
      ignoreDefaultArgs: ['--disable-extensions'],
      proxy: { server: `http://127.0.0.1:${port}`, bypass: '<-loopback>' },
      args: [`--disable-extensions-except=${unpacked}`, `--load-extension=${unpacked}`, '--host-resolver-rules=MAP * 127.0.0.1, EXCLUDE localhost', '--disable-background-networking'],
    });
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 10_000 });
    const extensionId = new URL(worker.url()).host;
    const target = await context.newPage();
    await target.goto(`${ORIGIN}/jobs/synthetic`);
    const popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/${manifest.action.default_popup}`);
    await expect(popup.locator('#login-view')).toBeVisible();
    return { popup, target, calls, username, password, close: async () => {
      await context?.close(); server.closeAllConnections();
      await new Promise<void>(closed => server.close(() => closed()));
      cleanupArtifact(workspace);
    } };
  } catch (error) {
    await context?.close(); server.closeAllConnections();
    await new Promise<void>(closed => server.close(() => closed()));
    cleanupArtifact(workspace);
    throw error;
  }
}

async function login(f: Awaited<ReturnType<typeof scenario>>) {
  await f.popup.locator('#username').fill(f.username);
  await f.popup.locator('#password').fill(f.password);
  await f.popup.locator('#login-button').click();
  await expect(f.popup.locator('#login-view')).toBeHidden();
}

const recordsEntry = (page: Page) => page.getByRole('button', { name: '查看投递记录', exact: true });
const captureEntry = (page: Page) => page.getByRole('button', { name: '新增投递', exact: true });
const search = (page: Page) => page.getByRole('searchbox').or(page.getByRole('textbox', { name: /搜索.*(公司|岗位)|(公司|岗位).*搜索/ }));

test('signed-out popup and invalid credentials never reveal the authenticated navigation', async () => {
  const f = await scenario();
  try {
    await expect(recordsEntry(f.popup)).toHaveCount(0);
    await expect(captureEntry(f.popup)).toHaveCount(0);
    await f.popup.locator('#username').fill(f.username);
    await f.popup.locator('#password').fill('invalid-synthetic-secret');
    await f.popup.locator('#login-button').click();
    await expect(f.popup.locator('#login-view')).toBeVisible();
    await expect(recordsEntry(f.popup)).toHaveCount(0);
  } finally { await f.close(); }
});

async function buttonAppearance(page: Page, label: string) {
  const button = page.getByRole('button', { name: label, exact: true });
  return button.evaluate(element => {
    const style = getComputedStyle(element);
    return [element.className, element.getAttribute('aria-pressed'), element.getAttribute('aria-current'),
      style.backgroundColor, style.backgroundImage, style.color, style.borderColor, style.boxShadow].join('|');
  });
}

test('login defaults to capture with two top buttons, no home or back, and visible selected state', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.locator('#company-name')).toBeVisible();
    await expect(recordsEntry(f.popup)).toBeVisible();
    await expect(captureEntry(f.popup)).toBeVisible();
    await expect(f.popup.getByRole('button', { name: /返回|回到入口/ })).toHaveCount(0);
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeHidden();
    const nav = await recordsEntry(f.popup).boundingBox();
    const form = await f.popup.locator('#company-name').boundingBox();
    expect(nav && form && nav.y < form.y).toBe(true);
    const captureSelected = await buttonAppearance(f.popup, '新增投递');
    const recordsUnselected = await buttonAppearance(f.popup, '查看投递记录');
    expect(captureSelected).not.toBe(recordsUnselected);
  } finally { await f.close(); }
});

test('top buttons switch mutually exclusive views without a return action or lost login', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.locator('#company-name')).toBeVisible();
    const captureBefore = await buttonAppearance(f.popup, '新增投递');
    const recordsBefore = await buttonAppearance(f.popup, '查看投递记录');
    await recordsEntry(f.popup).click();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Platform Engineer', { exact: true })).toBeVisible();
    await expect(f.popup.locator('#company-name')).toBeHidden();
    await expect(recordsEntry(f.popup)).toBeVisible();
    await expect(captureEntry(f.popup)).toBeVisible();
    await expect(f.popup.getByRole('button', { name: /返回|回到入口/ })).toHaveCount(0);
    await recordsEntry(f.popup).evaluate(element => (element as HTMLElement).blur());
    expect(await buttonAppearance(f.popup, '新增投递')).not.toBe(captureBefore);
    expect(await buttonAppearance(f.popup, '查看投递记录')).not.toBe(recordsBefore);
    await captureEntry(f.popup).click();
    await expect(f.popup.locator('#company-name')).toBeVisible();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeHidden();
    await expect(f.popup.locator('#login-view')).toBeHidden();
  } finally { await f.close(); }
});

test('record search and manual refresh remain usable through the top navigation', async () => {
  const f = await scenario();
  try {
    await login(f);
    await recordsEntry(f.popup).click();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await search(f.popup).fill('NIMBUS');
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeHidden();
    const before = f.calls.filter(call => call.path === '/api/v1/applications/' && call.method === 'GET').length;
    await f.popup.getByRole('button', { name: /刷新/ }).click();
    await expect.poll(() => f.calls.filter(call => call.path === '/api/v1/applications/' && call.method === 'GET').length).toBeGreaterThan(before);
    await search(f.popup).fill('');
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
  } finally { await f.close(); }
});

test('capture preview and save still work, then logout clears authenticated state', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.locator('#company-name')).toBeVisible();
    await f.popup.locator('#company-name').fill('Fresh Example Company');
    await f.popup.locator('#position-name').fill('New Engineer Role');
    await f.popup.locator('#application-url').fill('https://jobs.example.test/new-role');
    await f.popup.locator('#preview-button').click();
    await expect(f.popup.locator('#preview-panel')).toBeVisible();
    await f.popup.locator('#confirm-button').click();
    await expect.poll(() => f.calls.filter(call => call.path === '/api/v1/applications/' && call.method === 'POST').length).toBe(1);
    await f.popup.getByRole('button', { name: /退出登录|退出|登出/ }).click();
    await expect(f.popup.locator('#login-view')).toBeVisible();
    await expect(f.popup.locator('#company-name')).toBeHidden();
    await expect(recordsEntry(f.popup)).toHaveCount(0);
    await expect(captureEntry(f.popup)).toHaveCount(0);
  } finally { await f.close(); }
});
