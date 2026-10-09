/** EXT-ROUTE-003: delivered ZIP, real MV3 popup, synthetic local HTTP only. */
import { test, expect, chromium, type BrowserContext, type Page } from '@playwright/test';
import { createServer, type Server } from 'node:http';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const ROOT = resolve(__dirname, '../..');
const ORIGIN = 'http://115.190.240.84:5173';
const ZIP = join(ROOT, 'artifacts/recruitment-capture-extension-v0.1.0.zip');
const APPLICATIONS = '/api/v1/applications/';

type Mode = 'filled' | 'empty' | 'unauthorized' | 'network';
type Call = { path: string; method: string; search: string; authorized: boolean };

function unpackArtifact() {
  const workspace = mkdtempSync(join(tmpdir(), 'ext-route-003-'));
  const unpacked = join(workspace, 'extension');
  execFileSync('uv', [
    'run', '--no-sync', 'python', '-c',
    'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
    ZIP, unpacked,
  ], { cwd: join(ROOT, 'backend'), stdio: 'pipe' });
  return { workspace, unpacked };
}

function cleanupArtifact(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-route-003-')) {
    throw new Error('unsafe temporary path');
  }
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function jwt(type: string, seconds: number) {
  return [
    Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url'),
    Buffer.from(JSON.stringify({ user_id: 703, token_type: type, exp: Math.floor(Date.now() / 1000) + seconds, jti: randomUUID() })).toString('base64url'),
    Buffer.from(randomUUID()).toString('base64url'),
  ].join('.');
}

const firstPage = [
  { id: 731, company_id: 31, company_name: 'Orbit Labs', positions: [
    { id: 7311, position_name: 'Platform Engineer', notes: 'PRIVATE_NOTE_ALPHA', application_status: 'applied' },
  ], notes: 'PRIVATE_NOTE_ALPHA', user_id: 703 },
  { id: 732, company_id: 31, company_name: 'Orbit Labs', positions: [
    { id: 7321, position_name: 'QA Analyst', notes: 'PRIVATE_NOTE_BETA', application_status: 'applied' },
  ], notes: 'PRIVATE_NOTE_BETA', user_id: 703 },
];
const secondPage = [
  { id: 733, company_id: 32, company_name: 'Nimbus Works', positions: [
    { id: 7331, position_name: 'Data Scientist', notes: 'PRIVATE_NOTE_GAMMA', application_status: 'applied' },
  ], notes: 'PRIVATE_NOTE_GAMMA', user_id: 703 },
];

async function scenario(initialMode: Mode = 'filled') {
  const { workspace, unpacked } = unpackArtifact();
  const manifest = JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8'));
  const username = `ext003-${randomUUID().slice(0, 8)}`;
  const password = randomUUID();
  const access = jwt('access', 1800);
  const refresh = jwt('refresh', 604800);
  let mode = initialMode;
  let revision = 0;
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
    if (url.pathname.startsWith('/api/')) {
      calls.push({ path: url.pathname, method: request.method || 'GET', search: url.search, authorized: request.headers.authorization === `Bearer ${access}` });
    }
    if (url.pathname === '/api/v1/auth/login/' && request.method === 'POST') {
      if (body.username !== username || body.password !== password) return send(401, { code: 'INVALID_CREDENTIALS' });
      return send(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user: { id: 703, username } });
    }
    if (url.pathname === '/api/v1/auth/refresh/' && request.method === 'POST') {
      return send(mode === 'unauthorized' ? 401 : 200, mode === 'unauthorized' ? { code: 'INVALID_TOKEN' } : { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800 });
    }
    if (url.pathname === '/api/v1/auth/me/' && request.method === 'GET') return send(200, { id: 703, username });
    if (url.pathname === APPLICATIONS && request.method === 'GET') {
      if (mode === 'network') { response.destroy(); return; }
      if (mode === 'unauthorized') return send(401, { code: 'UNAUTHORIZED', message: '请重新登录' });
      const page = Number(url.searchParams.get('page') || '1');
      const results = mode === 'empty' ? [] : page === 1 ? firstPage : secondPage.map(record => ({
        ...record, company_name: revision ? 'Nimbus Refreshed' : record.company_name,
      }));
      return send(200, {
        count: mode === 'empty' ? 0 : 3, page, page_size: 2,
        total_pages: mode === 'empty' ? 0 : 2,
        next: mode === 'empty' || page >= 2 ? null : '/api/v1/applications/?page=2&page_size=2',
        previous: page <= 1 ? null : '/api/v1/applications/?page=1&page_size=2',
        results,
      });
    }
    if (url.pathname.startsWith('/api/')) return send(404, { code: 'NOT_FOUND' });
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    response.writeHead(200).end('<!doctype html><title>Fixture</title><main>Safe synthetic job page</main>');
  });
  server.on('connect', (_request, socket) => socket.destroy());
  await new Promise<void>(resolveReady => server.listen(0, '127.0.0.1', resolveReady));
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
    return {
      popup, target, calls, username, password,
      setMode: (next: Mode) => { mode = next; },
      updateData: () => { revision += 1; },
      close: async () => {
        await context?.close(); server.closeAllConnections();
        await new Promise<void>(resolveClosed => server.close(() => resolveClosed()));
        cleanupArtifact(workspace);
      },
    };
  } catch (error) {
    await context?.close(); server.closeAllConnections();
    await new Promise<void>(resolveClosed => server.close(() => resolveClosed()));
    cleanupArtifact(workspace);
    throw error;
  }
}

async function login(f: Awaited<ReturnType<typeof scenario>>) {
  await f.popup.locator('#username').fill(f.username);
  await f.popup.locator('#password').fill(f.password);
  await f.popup.locator('#login-button').click();
  await expect(f.popup.locator('#capture-view')).toBeVisible();
}

const search = (page: Page) => page.getByRole('searchbox').or(
  page.getByRole('textbox', { name: /搜索.*(公司|岗位)|(公司|岗位).*搜索/ }),
);
const applicationsGet = (calls: Call[]) => calls.filter(call => call.path === APPLICATIONS && call.method === 'GET');

test('signed-out popup does not fetch private applications', async () => {
  const f = await scenario();
  try {
    await expect(f.popup.locator('#login-view')).toBeVisible();
    expect(applicationsGet(f.calls)).toHaveLength(0);
  } finally { await f.close(); }
});

test('signed-in list aggregates duplicate companies across pages and shows only company and position summaries', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.getByText('已投递公司', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toHaveCount(1);
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    for (const position of ['Platform Engineer', 'QA Analyst', 'Data Scientist']) {
      await expect(f.popup.getByText(position, { exact: true })).toBeVisible();
    }
    expect(await f.popup.locator('body').innerText()).toMatch(/(?:共|结果|公司)[^\n]{0,12}2|2[^\n]{0,12}(?:家|条|个|结果)/);
    const text = await f.popup.locator('body').innerText();
    expect(text).not.toMatch(/PRIVATE_NOTE_|703/);
    expect(applicationsGet(f.calls).length).toBeGreaterThanOrEqual(2);
    expect(applicationsGet(f.calls).every(call => call.authorized)).toBe(true);
    expect(f.calls.some(call => /sharing|users\/\d+\/applications/.test(call.path))).toBe(false);
    await expect(f.popup.locator('#company-name')).toBeVisible();
  } finally { await f.close(); }
});

test('search matches company and position case-insensitively, then clearing restores all companies without writes', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    await search(f.popup).fill('ORBIT');
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toHaveCount(0);
    await search(f.popup).fill('scientist');
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toHaveCount(0);
    await search(f.popup).fill('no such company');
    await expect(f.popup.getByText(/没有匹配|无匹配/)).toBeVisible();
    await search(f.popup).fill('');
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    expect(f.calls.filter(call => call.path.startsWith(APPLICATIONS) && call.method !== 'GET')).toHaveLength(0);
  } finally { await f.close(); }
});

test('manual refresh reloads the list and keeps the capture form', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    const before = applicationsGet(f.calls).length;
    await f.popup.locator('#company-name').fill('Unsaved capture company');
    f.updateData();
    await f.popup.getByRole('button', { name: /刷新/ }).click();
    await expect(f.popup.getByText('Nimbus Refreshed', { exact: true })).toBeVisible();
    expect(applicationsGet(f.calls).length).toBeGreaterThan(before);
    await expect(f.popup.locator('#company-name')).toHaveValue('Unsaved capture company');
  } finally { await f.close(); }
});

test('empty list and network failure have distinct states and preserve capture controls', async () => {
  const f = await scenario('empty');
  try {
    await login(f);
    await expect(f.popup.getByText(/暂无已投递公司|尚无已投递公司/)).toBeVisible();
    await expect(f.popup.locator('#company-name')).toBeVisible();
    f.setMode('network');
    await f.popup.getByRole('button', { name: /刷新/ }).click();
    await expect(f.popup.getByText(/网络|连接|加载失败/)).toBeVisible();
    await expect(f.popup.getByRole('button', { name: /重试/ })).toBeVisible();
    await expect(f.popup.locator('#company-name')).toBeVisible();
    f.setMode('filled');
    await f.popup.getByRole('button', { name: /重试/ }).click();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
  } finally { await f.close(); }
});

test('application 401 prompts re-login without erasing the existing capture draft', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await f.popup.locator('#company-name').fill('Unsaved capture draft');
    const before = applicationsGet(f.calls).length;
    f.setMode('unauthorized');
    await f.popup.getByRole('button', { name: /刷新/ }).click();
    await expect.poll(() => applicationsGet(f.calls).length).toBeGreaterThan(before);
    await expect(f.popup.getByText(/重新登录|登录已过期|认证失效/)).toBeVisible();
    expect(applicationsGet(f.calls).every(call => call.authorized)).toBe(true);
    await expect(f.popup.locator('#company-name')).toHaveValue('Unsaved capture draft');
  } finally { await f.close(); }
});

test('logout removes the previous account list and search state', async () => {
  const f = await scenario();
  try {
    await login(f);
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toBeVisible();
    await search(f.popup).fill('QA');
    await f.popup.getByRole('button', { name: /退出登录|退出|登出/ }).click();
    await expect(f.popup.locator('#login-view')).toBeVisible();
    await expect(f.popup.getByText('Orbit Labs', { exact: true })).toHaveCount(0);
    await expect(f.popup.getByText('QA Analyst', { exact: true })).toHaveCount(0);
    await login(f);
    await expect(f.popup.getByText('Nimbus Works', { exact: true })).toBeVisible();
    await expect(search(f.popup)).toHaveValue('');
  } finally { await f.close(); }
});
