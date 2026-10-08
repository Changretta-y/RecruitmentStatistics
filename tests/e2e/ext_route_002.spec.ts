/**
 * EXT-ROUTE-002 black-box matching tests.
 *
 * The only extension input is the public delivery ZIP.  The HTTP server is an
 * in-memory contract stub: it never forwards requests to the platform.
 */
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

type ApiCall = {
  origin: string;
  path: string;
  search: string;
  method: string;
  body: Record<string, unknown>;
};

type Fixture = {
  context: BrowserContext;
  popup: Page;
  target: Page;
  calls: ApiCall[];
  readCompany: () => Record<string, unknown>;
  close: () => Promise<void>;
};

function unpackArtifact() {
  const workspace = mkdtempSync(join(tmpdir(), 'ext-route-002-'));
  const unpacked = join(workspace, 'extension');
  execFileSync(
    'uv',
    [
      'run',
      '--no-sync',
      'python',
      '-c',
      'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',
      ZIP,
      unpacked,
    ],
    { cwd: join(ROOT, 'backend'), stdio: 'pipe' },
  );
  return { workspace, unpacked };
}

function cleanupArtifact(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-route-002-')) {
    throw new Error('unsafe temporary path');
  }
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function jwt(type: string, seconds: number) {
  return [
    Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url'),
    Buffer.from(
      JSON.stringify({
        user_id: 701,
        token_type: type,
        exp: Math.floor(Date.now() / 1000) + seconds,
        jti: randomUUID(),
      }),
    ).toString('base64url'),
    Buffer.from(randomUUID()).toString('base64url'),
  ].join('.');
}

async function makeScenario(
  targetUrl: string,
  existingPositionName: string | null = null,
  existingUrl = 'https://example.invalid/old-link',
  duplicateExistingPosition = false,
) {
  const { workspace, unpacked } = unpackArtifact();
  const manifest = JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8'));
  const username = `route-fixture-${randomUUID().slice(0, 8)}`;
  const password = randomUUID();
  const calls: ApiCall[] = [];
  let existing: Record<string, unknown> = {
    id: 701,
    company_id: 17,
    company_name: '黑盒公司',
    position_name: existingPositionName,
    application_status: 'applied',
    application_url: existingUrl,
    notes: '原岗位备注',
    positions: existingPositionName ? [
      { id: 711, position_name: existingPositionName, application_status: 'applied', notes: '原岗位备注' },
      ...(duplicateExistingPosition ? [{ id: 713, position_name: existingPositionName, application_status: 'in_progress', notes: '第二条同名岗位备注' }] : []),
    ] : [],
  };
  const access = jwt('access', 1800);
  const refresh = jwt('refresh', 604800);
  const server: Server = createServer(async (request, response) => {
    const requestUrl = new URL(request.url || '/', `http://${request.headers.host}`);
    const chunks: Buffer[] = [];
    for await (const chunk of request) chunks.push(Buffer.from(chunk));
    let body: Record<string, unknown> = {};
    try { body = JSON.parse(Buffer.concat(chunks).toString() || '{}') as Record<string, unknown>; } catch { /* no JSON */ }
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type');
    response.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,PUT,OPTIONS');
    if (request.method === 'OPTIONS') { response.writeHead(204).end(); return; }
    const send = (status: number, payload: unknown) => {
      response.setHeader('Content-Type', 'application/json');
      response.writeHead(status).end(JSON.stringify(payload));
    };
    if (requestUrl.pathname.startsWith('/api/')) {
      calls.push({ origin: requestUrl.origin, path: requestUrl.pathname, search: requestUrl.search, method: request.method || 'GET', body });
    }
    if (requestUrl.pathname === '/api/v1/auth/login/' && request.method === 'POST') {
      if (body.username !== username || body.password !== password) { send(401, { code: 'INVALID_CREDENTIALS' }); return; }
      send(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user: { id: 701, username } });
      return;
    }
    if (requestUrl.pathname === '/api/v1/auth/me/' && request.method === 'GET') { send(200, { id: 701, username }); return; }
    if (requestUrl.pathname === '/api/v1/applications/' && request.method === 'GET') {
      send(200, { count: existingPositionName ? 1 : 0, page: 1, page_size: 20, total_pages: existingPositionName ? 1 : 0, next: null, previous: null, results: existingPositionName ? [existing] : [] });
      return;
    }
    if (requestUrl.pathname === '/api/v1/applications/' && request.method === 'POST') {
      const newPosition = String(body.position_name || (body.positions as Array<Record<string, unknown>> | undefined)?.[0]?.position_name || '');
      if (existingPositionName) {
        existing = { ...existing, positions: [...existing.positions as Array<Record<string, unknown>>, { id: 712, position_name: newPosition, application_status: body.application_status || 'applied', notes: body.notes || '' }] };
      } else {
        existing = { ...existing, ...body, id: 801, positions: [{ id: 712, position_name: newPosition, application_status: body.application_status || 'applied', notes: body.notes || '' }] };
      }
      send(201, existing);
      return;
    }
    if (requestUrl.pathname === '/api/v1/applications/701/' && ['PATCH', 'PUT'].includes(request.method || '')) {
      existing = { ...existing, ...body };
      send(200, existing);
      return;
    }
    if (!requestUrl.pathname.startsWith('/api/')) {
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.writeHead(200).end('<!doctype html><title>Route fixture</title><main>黑盒路由页面</main>');
      return;
    }
    send(404, { code: 'NOT_FOUND' });
  });
  server.on('connect', (_request, socket) => socket.destroy());
  await new Promise<void>((resolveReady) => server.listen(0, '127.0.0.1', resolveReady));
  const port = (server.address() as { port: number }).port;
  let context: BrowserContext | undefined;
  try {
    const channel = process.env.EXT_AUTH_BROWSER_CHANNEL || 'msedge';
    context = await chromium.launchPersistentContext(join(workspace, 'profile'), {
      channel, headless: true, ignoreDefaultArgs: ['--disable-extensions'],
      proxy: { server: `http://127.0.0.1:${port}`, bypass: '<-loopback>' },
      args: [`--disable-extensions-except=${unpacked}`, `--load-extension=${unpacked}`, '--host-resolver-rules=MAP * 127.0.0.1, EXCLUDE localhost', '--disable-background-networking'],
    });
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 10_000 });
    const extensionId = new URL(worker.url()).host;
    const target = await context.newPage();
    await target.goto(targetUrl);
    const popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/${manifest.action.default_popup}`);
    await expect(popup.locator('#login-view')).toBeVisible();
    const fixture: Fixture = { context, popup, target, calls, readCompany: () => existing, close: async () => {
      await context?.close(); server.closeAllConnections();
      await new Promise<void>((resolveClosed) => server.close(() => resolveClosed()));
      cleanupArtifact(workspace);
    }};
    return { fixture, username, password };
  } catch (error) {
    await context?.close(); server.closeAllConnections();
    await new Promise<void>((resolveClosed) => server.close(() => resolveClosed()));
    cleanupArtifact(workspace);
    throw error;
  }
}

async function authenticateAndCapture(fixture: Fixture, username: string, password: string) {
  await fixture.target.bringToFront();
  await fixture.popup.locator('#username').fill(username);
  await fixture.popup.locator('#password').fill(password);
  await fixture.popup.locator('#login-button').click();
  await expect(fixture.popup.locator('#capture-view')).toBeVisible();
  await fixture.target.bringToFront();
  await fixture.popup.locator('#recapture-button').click();
}

async function saveFromPreview(fixture: Fixture, company: string, position: string) {
  await fixture.popup.locator('#company-name').fill(company);
  await fixture.popup.locator('#position-name').fill(position);
  await fixture.popup.locator('#preview-button').click();
  await expect(fixture.popup.locator('#preview-panel')).toBeVisible();
  const previewText = await fixture.popup.locator('#preview-panel').innerText();
  if (!previewText) throw new Error('preview did not display an operation');
  await fixture.popup.locator('#confirm-button').click();
  await expect.poll(() => fixture.calls.some((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET')).toBe(true);
  return previewText;
}

test('same company, different position, same recruitment URL appends instead of overwriting', async () => {
  const targetUrl = `${ORIGIN}/jobs/shared-entry`;
  const scenario = await makeScenario(targetUrl, '原岗位', targetUrl);
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    await expect.poll(() => scenario.fixture.popup.locator('#application-url').inputValue()).toBe(targetUrl);
    const preview = await saveFromPreview(scenario.fixture, '黑盒公司', '新增岗位');
    expect(preview).toMatch(/新建|新增|创建/);
    const writes = scenario.fixture.calls.filter((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET');
    expect(writes).toHaveLength(1);
    expect(writes[0].method).toBe('POST');
    expect(writes[0].path).toBe('/api/v1/applications/');
    expect(writes[0].body.application_url).toBe(targetUrl);
    expect(writes[0].body.position_name || (writes[0].body.positions as Array<Record<string, unknown>>)?.[0]?.position_name).toBe('新增岗位');
    const company = scenario.fixture.readCompany();
    const positions = company.positions as Array<Record<string, unknown>>;
    expect(positions.map((item) => item.position_name)).toEqual(['原岗位', '新增岗位']);
    expect(positions[0].notes).toBe('原岗位备注');
    expect(positions[0].id).toBe(711);
  } finally { await scenario.fixture.close(); }
});

test('same company and same position still updates when the URL changes', async () => {
  const targetUrl = `${ORIGIN}/#/jobs/new-hash?tab=detail`;
  const scenario = await makeScenario(targetUrl, '目标岗位', 'https://example.invalid/old-link');
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    const preview = await saveFromPreview(scenario.fixture, '黑盒公司', '目标岗位');
    expect(preview).toMatch(/更新|修改/);
    const writes = scenario.fixture.calls.filter((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET');
    expect(writes).toHaveLength(1);
    expect(writes[0].method).toBe('PATCH');
    expect(writes[0].path).toBe('/api/v1/applications/701/');
    expect(writes[0].body.application_url).toBe(targetUrl);
    expect((scenario.fixture.readCompany().positions as Array<Record<string, unknown>>)[0].position_name).toBe('目标岗位');
  } finally { await scenario.fixture.close(); }
});

test('company and position identity matches after trimming and case folding', async () => {
  const targetUrl = `${ORIGIN}/jobs/updated-role`;
  const scenario = await makeScenario(targetUrl, 'Target Role', 'https://example.invalid/old-link');
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    await saveFromPreview(scenario.fixture, '  黑盒公司  ', ' target role ');
    const writes = scenario.fixture.calls.filter((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET');
    expect(writes).toHaveLength(1);
    expect(writes[0].method).toBe('PATCH');
    expect(writes[0].path).toBe('/api/v1/applications/701/');
  } finally { await scenario.fixture.close(); }
});

test('same company, different position and different URL also appends', async () => {
  const targetUrl = `${ORIGIN}/jobs/another-position?utm_source=mail&ref=board#/detail`;
  const normalizedUrl = `${ORIGIN}/jobs/another-position?ref=board#/detail`;
  const scenario = await makeScenario(targetUrl, '已有岗位', 'https://example.invalid/old-link');
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    await expect.poll(() => scenario.fixture.popup.locator('#application-url').inputValue()).toBe(normalizedUrl);
    await saveFromPreview(scenario.fixture, '黑盒公司', '另一岗位');
    const writes = scenario.fixture.calls.filter((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET');
    expect(writes).toHaveLength(1);
    expect(writes[0].method).toBe('POST');
    expect(writes[0].body.application_url).toBe(normalizedUrl);
    expect((scenario.fixture.readCompany().positions as Array<Record<string, unknown>>).map((item) => item.position_name)).toEqual(['已有岗位', '另一岗位']);
  } finally { await scenario.fixture.close(); }
});

test('two existing same-name positions are never silently patched by one preview', async () => {
  const targetUrl = `${ORIGIN}/jobs/shared-entry`;
  const scenario = await makeScenario(targetUrl, '重复岗位', targetUrl, true);
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    await scenario.fixture.popup.locator('#company-name').fill('黑盒公司');
    await scenario.fixture.popup.locator('#position-name').fill('重复岗位');
    await scenario.fixture.popup.locator('#preview-button').click();
    await expect(scenario.fixture.popup.locator('#preview-panel')).toBeVisible();
    if (await scenario.fixture.popup.locator('#confirm-button').isEnabled()) {
      await scenario.fixture.popup.locator('#confirm-button').click();
      await scenario.fixture.popup.waitForTimeout(300);
    } else {
      await expect(scenario.fixture.popup.locator('#preview-panel')).toContainText(/选择|多条|新建/);
    }
    const writes = scenario.fixture.calls.filter((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET');
    expect(writes.some((call) => call.method === 'PATCH' || call.method === 'PUT')).toBe(false);
    expect((scenario.fixture.readCompany().positions as Array<Record<string, unknown>>).slice(0, 2).map((item) => item.notes)).toEqual(['原岗位备注', '第二条同名岗位备注']);
  } finally { await scenario.fixture.close(); }
});

test('failed login cannot reach application matching or write requests', async () => {
  const scenario = await makeScenario(`${ORIGIN}/jobs/shared-entry`, '已有岗位');
  try {
    await scenario.fixture.popup.locator('#username').fill(scenario.username);
    await scenario.fixture.popup.locator('#password').fill('incorrect-password');
    await scenario.fixture.popup.locator('#login-button').click();
    await expect(scenario.fixture.popup.locator('#login-view')).toBeVisible();
    await expect(scenario.fixture.popup.locator('#capture-view')).not.toBeVisible();
    expect(scenario.fixture.calls.some((call) => call.path === '/api/v1/auth/login/' && call.method === 'POST')).toBe(true);
    expect(scenario.fixture.calls.some((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET')).toBe(false);
  } finally { await scenario.fixture.close(); }
});

test('missing company or position never selects an unrelated existing application', async () => {
  const scenario = await makeScenario(`${ORIGIN}/jobs/shared-entry`, '已有岗位');
  try {
    await authenticateAndCapture(scenario.fixture, scenario.username, scenario.password);
    await scenario.fixture.popup.locator('#company-name').fill('');
    await scenario.fixture.popup.locator('#position-name').fill('');
    const previewButton = scenario.fixture.popup.locator('#preview-button');
    if (await previewButton.isEnabled()) await previewButton.click();
    const confirmButton = scenario.fixture.popup.locator('#confirm-button');
    if (await confirmButton.isVisible() && await confirmButton.isEnabled()) {
      await scenario.fixture.popup.locator('#confirm-button').click();
    }
    await scenario.fixture.popup.waitForTimeout(300);
    expect(scenario.fixture.calls.some((call) => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET')).toBe(false);
  } finally { await scenario.fixture.close(); }
});


