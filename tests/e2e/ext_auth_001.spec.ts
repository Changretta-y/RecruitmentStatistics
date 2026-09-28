/** Public delivery ZIP + real Chromium MV3 UI, with all HTTP confined to a local proxy. */
import { test, expect, chromium, type BrowserContext, type Page } from '@playwright/test';
import { createServer, type Server } from 'node:http';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { execFileSync, execSync } from 'node:child_process';

const ROOT = resolve(__dirname, '../..');
const ORIGIN = 'http://115.190.240.84:5173';
const ZIP = join(ROOT, 'artifacts/recruitment-capture-extension-v0.1.0.zip');

function unpackArtifact() {
  const workspace = mkdtempSync(join(tmpdir(), 'ext-auth-001-'));
  const unpacked = join(workspace, 'extension');
  execFileSync('uv', ['run', '--no-sync', 'python', '-c',
    'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])', ZIP, unpacked],
    { cwd: join(ROOT, 'backend'), stdio: 'pipe' });
  return { workspace, unpacked };
}

function cleanupArtifact(workspace: string) {
  if (dirname(workspace) !== tmpdir() || !basename(workspace).startsWith('ext-auth-001-')) throw new Error('unsafe temporary path');
  rmSync(workspace, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

type Observation = { origin: string; path: string; method: string; authenticated: boolean };
type Fixture = {
  context: BrowserContext; page: Page; manifest: any; calls: Observation[];
  expireAccess: () => void; rejectNetwork: () => void;
  secrets: string[]; messages: string[]; username: string;
};

async function fixture(): Promise<Fixture & { close: () => Promise<void> }> {
  const { workspace, unpacked } = unpackArtifact();
  const manifest = JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8'));
  const username = `fixture-${randomUUID().slice(0, 8)}`;
  const password = randomUUID();
  const jwt = (type: string, seconds: number) => [
    Buffer.from(JSON.stringify({alg: 'HS256', typ: 'JWT'})).toString('base64url'),
    Buffer.from(JSON.stringify({user_id: 101, token_type: type, exp: Math.floor(Date.now()/1000)+seconds, jti: randomUUID()})).toString('base64url'),
    Buffer.from(randomUUID()).toString('base64url'),
  ].join('.');
  const access = jwt('access', 1800);
  const refresh = jwt('refresh', 604800);
  const rotatedAccess = jwt('access', 1800);
  const rotatedRefresh = jwt('refresh', 604800);
  let expired = false;
  let offline = false;
  const calls: Observation[] = [];
  const user = { id: 101, username, email: 'synthetic@example.invalid' };
  const server: Server = createServer(async (request, response) => {
    // This proxy never forwards: every browser request ends here, including old origins.
    const url = new URL(request.url || '/', `http://${request.headers.host}`);
    const chunks: Buffer[] = [];
    for await (const chunk of request) chunks.push(Buffer.from(chunk));
    let body: any = {};
    try { body = JSON.parse(Buffer.concat(chunks).toString() || '{}'); } catch { /* invalid input */ }
    const auth = request.headers.authorization;
    calls.push({ origin: url.origin, path: url.pathname, method: request.method || 'GET', authenticated: !!auth });
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type');
    if (request.method === 'OPTIONS') { response.writeHead(204).end(); return; }
    response.setHeader('Content-Type', 'application/json');
    const reply = (status: number, output: unknown) => { response.writeHead(status).end(JSON.stringify(output)); };
    if (offline) { reply(503, { code: 'UNAVAILABLE', message: '隔离服务不可达', details: {} }); return; }
    if (url.pathname === '/api/v1/health/') { reply(200, { status: 'ok' }); return; }
    if (url.pathname === '/api/v1/auth/login/') {
      if (body.username !== username || body.password !== password) {
        reply(401, { code: 'INVALID_CREDENTIALS', message: '用户名或密码错误', details: {} }); return;
      }
      expired = false;
      reply(200, { access, refresh, access_expires_in: 1800, refresh_expires_in: 604800, user }); return;
    }
    if (url.pathname === '/api/v1/auth/refresh/') {
      if (body.refresh !== refresh) { reply(401, { code: 'INVALID_TOKEN', message: '令牌无效', details: {} }); return; }
      reply(200, { access: rotatedAccess, refresh: rotatedRefresh, access_expires_in: 1800, refresh_expires_in: 604800 }); return;
    }
    if (auth !== `Bearer ${rotatedAccess}` && !(auth === `Bearer ${access}` && !expired)) {
      reply(401, { code: 'UNAUTHORIZED', message: '需要登录', details: {} }); return;
    }
    if (url.pathname === '/api/v1/auth/me/') { reply(200, user); return; }
    if (url.pathname === '/api/v1/applications/' && request.method === 'GET') {
      reply(200, { count: 0, page: 1, page_size: 20, total_pages: 0, next: null, previous: null, results: [] }); return;
    }
    if (url.pathname === '/api/v1/applications/' && request.method === 'POST') {
      reply(201, { ...body, id: 201, user: user.id }); return;
    }
    reply(404, { code: 'NOT_FOUND', message: '隔离服务不存在此路径', details: {} });
  });
  server.on('connect', (_request, socket) => socket.destroy()); // No HTTPS tunnels / external traffic.
  await new Promise<void>(resolveReady => server.listen(0, '127.0.0.1', resolveReady));
  const port = (server.address() as { port: number }).port;
  let context: BrowserContext | undefined;
  try {
    const channel = process.env.EXT_AUTH_BROWSER_CHANNEL || 'chromium';
    if (!['chromium', 'chrome', 'msedge'].includes(channel)) throw new Error('unsupported test browser channel');
    context = await chromium.launchPersistentContext(join(workspace, 'profile'), {
      channel, headless: true,
      ignoreDefaultArgs: ['--disable-extensions'],
      proxy: { server: `http://127.0.0.1:${port}`, bypass: '<-loopback>' },
      args: [`--disable-extensions-except=${unpacked}`, `--load-extension=${unpacked}`,
        '--host-resolver-rules=MAP * 127.0.0.1, EXCLUDE localhost', '--disable-background-networking'],
    });
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 10_000 });
    const extensionId = new URL(worker.url()).host;
    const page = await context.newPage();
    const messages: string[] = [];
    context.on('console', entry => messages.push(entry.text()));
    await page.goto(`chrome-extension://${extensionId}/${manifest.action.default_popup}`);
    await expect(page.locator('#login-view')).toBeVisible();
    return {
      context, page, manifest, calls, messages, username, secrets: [password, access, refresh, rotatedAccess, rotatedRefresh],
      expireAccess: () => { expired = true; }, rejectNetwork: () => { offline = true; },
      close: async () => {
        await context.close();
        server.closeAllConnections();
        await new Promise<void>(resolveClosed => server.close(() => resolveClosed()));
        // Verify temporary path before recursive cleanup on Windows.
        cleanupArtifact(workspace);
      },
    };
  } catch (error) {
    await context?.close();
    server.closeAllConnections();
    await new Promise<void>(resolveClosed => server.close(() => resolveClosed()));
    cleanupArtifact(workspace);
    throw error;
  }
}

// Credentials remain closure-scoped in the proxy. Inject the synthetic pair only into this test UI.
async function authenticate(f: Fixture) {
  // Fixture username is intentionally represented as a non-secret independent value in the test.
  await f.page.locator('#username').fill(f.username);
  await f.page.locator('#password').fill(f.secrets[0]);
  await f.page.locator('#login-button').click();
  await expect(f.page.locator('#capture-view')).toBeVisible();
}

test('delivery manifest permits platform proxy origin', async () => {
  const {workspace, unpacked} = unpackArtifact();
  try {
    const manifest = JSON.parse(readFileSync(join(unpacked, 'manifest.json'), 'utf8'));
    expect(manifest.host_permissions).toContain(ORIGIN + '/*');
  } finally { cleanupArtifact(workspace); }
});

test('popup defaults to the deployed platform origin', async () => {
  const f = await fixture();
  try { await expect(f.page.locator('#api-origin')).toHaveValue(ORIGIN); }
  finally { await f.close(); }
});

test('delivery popup initial server selection exposes the platform proxy origin', async () => {
  const {workspace, unpacked} = unpackArtifact();
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext();
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    // Observe public delivery markup as rendered configuration; this does not emulate MV3 APIs.
    await page.setContent(readFileSync(join(unpacked, 'popup.html'), 'utf8'));
    await expect(page.locator('#api-origin')).toHaveValue(ORIGIN);
  } finally { await browser.close(); cleanupArtifact(workspace); }
});

test('documented repository build recreates the delivery ZIP without content drift', () => {
  const readme = readFileSync(join(ROOT, 'README.md'), 'utf8');
  expect(readme.includes('frontend/src/browser-extension/')).toBe(true);
  expect(readme.includes('recruitment-capture-extension-v0.1.0.zip')).toBe(true);
  expect(readme.includes('npm run build:extension')).toBe(true);
  const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
  expect(typeof pkg.scripts?.['build:extension']).toBe('string');
  const snapshot = () => JSON.parse(execFileSync('uv', ['run', '--no-sync', 'python', '-c',
    'import sys,zipfile,hashlib,json; z=zipfile.ZipFile(sys.argv[1]); print(json.dumps({n:hashlib.sha256(z.read(n)).hexdigest() for n in sorted(z.namelist()) if not n.endswith("/")}))', ZIP],
    { cwd: join(ROOT, 'backend'), encoding: 'utf8', stdio: 'pipe' }));
  const delivered = snapshot();
  execSync('npm run build:extension', { cwd: ROOT, stdio: 'pipe' });
  const first = snapshot();
  execSync('npm run build:extension', { cwd: ROOT, stdio: 'pipe' });
  const second = snapshot();
  expect(first).toEqual(delivered);
  expect(second).toEqual(first);
});

test('invalid synthetic credentials stay logged out without disclosing secrets', async () => {
  const f = await fixture();
  try {
    await f.page.locator('#username').fill('invalid-synthetic-user');
    await f.page.locator('#password').fill(randomUUID());
    await f.page.locator('#login-button').click();
    await expect.poll(() => f.calls.some(call => call.path === '/api/v1/auth/login/')).toBe(true);
    await expect(f.page.locator('#global-message')).toBeVisible();
    await expect(f.page.locator('#capture-view')).toBeHidden();
    expect(f.calls.filter(call => call.path.startsWith('/api/')).every(call => call.origin === ORIGIN)).toBe(true);
  } finally { await f.close(); }
});

test('valid synthetic login, refresh, me and application calls share the proxy origin', async () => {
  const f = await fixture();
  try {
    await authenticate(f);
    f.expireAccess();
    await f.page.reload();
    await expect(f.page.locator('#capture-view')).toBeVisible();
    await f.page.locator('#company-name').fill('隔离测试公司');
    await f.page.locator('#position-name').fill('合成测试岗位');
    await f.page.locator('#application-url').fill('https://example.invalid/jobs/1');
    await f.page.locator('#preview-button').click();
    await expect(f.page.locator('#preview-panel')).toBeVisible();
    await f.page.locator('#confirm-button').click();
    await expect.poll(() => f.calls.some(call => call.path === '/api/v1/applications/' && call.method === 'POST')).toBe(true);
    for (const path of ['/api/v1/auth/login/', '/api/v1/auth/refresh/', '/api/v1/auth/me/', '/api/v1/applications/']) {
      expect(f.calls.some(call => call.path === path)).toBe(true);
    }
    expect(f.calls.filter(call => call.path.startsWith('/api/')).every(call => call.origin === ORIGIN)).toBe(true);
    const visibleText = await f.page.locator('body').innerText();
    expect(f.secrets.every(secret => !visibleText.includes(secret) && !f.messages.some(message => message.includes(secret)))).toBe(true);
  } finally { await f.close(); }
});

test('unavailable isolated proxy service never reports login success', async () => {
  const f = await fixture();
  try {
    f.rejectNetwork();
    await f.page.locator('#username').fill('synthetic-unavailable');
    await f.page.locator('#password').fill(randomUUID());
    await f.page.locator('#login-button').click();
    await expect(f.page.locator('#global-message')).toBeVisible();
    await expect(f.page.locator('#capture-view')).toBeHidden();
  } finally { await f.close(); }
});
