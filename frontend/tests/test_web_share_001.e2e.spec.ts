import { expect, test, type Page, type Route, type Locator } from '@playwright/test';

// Only public HTTP and accessible UI are observed; no production imports.
type PublicUser = { id: number; username: string; avatar: string; relationship: string };
const user = (id: number, relationship = 'none', avatar = 'avatar-01'): PublicUser =>
  ({ id, username: `共享用户${id}`, avatar, relationship });
const ME = { ...user(982, 'none', 'avatar-08'), username: 'sharing_test_user' };
const A = user(201, 'connected', 'avatar-02');
const B = user(202, 'connected', 'avatar-03');
const incomingUser = user(401, 'incoming_pending', 'avatar-04');
const outgoingUser = user(402, 'outgoing_pending', 'avatar-05');
const date = '2026-09-28T04:00:00Z';
const requestItem = (id: number, sender: PublicUser, recipient: PublicUser, status = 'pending') =>
  ({ id, sender, recipient, status, created_at: date, responded_at: status === 'pending' ? null : date });
const record = (owner: number, company = `用户${owner}专属公司`) => ({
  id: owner * 10, company_name: company, position_name: '测试工程师',
  application_status: 'first_interview', current_stage: 'first_interview',
  application_url: `https://jobs.example.com/role/${owner}`, application_time: date,
  ai_interview_time: date, ai_interview_duration_minutes: 30,
  written_test_time: date, written_test_duration_minutes: 45,
  first_interview_time: date, first_interview_duration_minutes: 60,
  second_interview_time: null, second_interview_duration_minutes: null,
  third_interview_time: null, third_interview_duration_minutes: null,
  hr_interview_time: null, hr_interview_duration_minutes: null,
  created_at: date, updated_at: date,
});
const pagination = (results: unknown[], page = 1, pageSize = 20, count = results.length) =>
  ({ results, count, page, page_size: pageSize, total_pages: Math.ceil(count / pageSize), next: null, previous: null });

async function json(route: Route, status: number, body?: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: body === undefined ? '' : JSON.stringify(body) });
}

async function mockApi(page: Page) {
  const state = {
    recommendations: Array.from({ length: 10 }, (_, i) => user(301 + i, 'none', `avatar-0${i % 8 + 1}`)),
    incoming: [requestItem(701, incomingUser, ME)],
    outgoing: [requestItem(702, ME, outgoingUser)],
    connections: [{ id: 601, user: A, created_at: date }, { id: 602, user: B, created_at: date }],
    calls: [] as { path: string; method: string; body: any; search: URLSearchParams }[],
    searchFailures: 0, mutationFailures: 0, recordFailures: 0, revoked: false,
    delayA: false, releaseA: (() => {}) as () => void,
  };
  await page.route('**/api/v1/**', async route => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace('/api/v1', '');
    const method = req.method();
    const body = req.postDataJSON();
    state.calls.push({ path, method, body, search: url.searchParams });
    if (path === '/auth/login/') return json(route, 200, { access: 'share-access', refresh: 'share-refresh', user: { ...ME, email: 'test@example.com' } });
    if (path === '/auth/me/') return json(route, 200, { ...ME, email: 'test@example.com' });
    if (path === '/auth/refresh/') return json(route, 401, { code: 'TOKEN_EXPIRED' });
    if (path === '/applications/') return json(route, 200, pagination([]));
    if (path === '/calendar/events/') return json(route, 200, { timezone: 'Asia/Shanghai', start: '2026-09-28', end: '2026-11-02', events: [] });
    if (path === '/sharing/me/') return json(route, 200, ME);
    if (path === '/sharing/users/recommendations/') return json(route, 200, { count: state.recommendations.length, results: state.recommendations });
    if (path === '/sharing/requests/' && method === 'GET') return json(route, 200, { incoming: state.incoming, outgoing: state.outgoing });
    if (path === '/sharing/connections/' && method === 'GET') return json(route, 200, { results: state.connections });
    if (method !== 'GET' && path.startsWith('/sharing/') && state.mutationFailures-- > 0)
      return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '共享操作失败，请重试' });
    if (path === '/sharing/requests/' && method === 'POST') {
      const recipient = state.recommendations.find(u => u.id === body.recipient_id) ?? user(body.recipient_id);
      recipient.relationship = 'outgoing_pending';
      const item = requestItem(800 + body.recipient_id, ME, recipient);
      state.outgoing.unshift(item);
      state.recommendations = state.recommendations.filter(u => u.id !== recipient.id);
      return json(route, 201, item);
    }
    const respond = path.match(/^\/sharing\/requests\/(\d+)\/respond\/$/);
    if (respond) {
      const item = state.incoming.find(r => r.id === Number(respond[1]));
      if (!item) return json(route, 404, { code: 'NOT_FOUND' });
      item.status = body.decision;
      item.responded_at = date;
      if (body.decision === 'accepted') {
        item.sender.relationship = 'connected';
        state.connections.push({ id: item.id, user: item.sender, created_at: date });
      }
      return json(route, 200, item);
    }
    const connection = path.match(/^\/sharing\/connections\/(\d+)\/$/);
    if (connection && method === 'DELETE') {
      state.connections = state.connections.filter(c => c.id !== Number(connection[1]));
      state.revoked = true;
      return json(route, 204);
    }
    const applications = path.match(/^\/sharing\/users\/(\d+)\/applications\/$/);
    if (applications) {
      const owner = Number(applications[1]);
      if (state.revoked) return json(route, 404, { code: 'NOT_FOUND', message: '共享已失效' });
      if (state.recordFailures-- > 0) return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '记录加载失败' });
      if (owner === A.id && state.delayA) await new Promise<void>(resolve => { state.releaseA = resolve; });
      const pageNo = Number(url.searchParams.get('page') ?? 1);
      const size = Number(url.searchParams.get('page_size') ?? 20);
      const search = url.searchParams.get('search') ?? '';
      return json(route, 200, pagination([record(owner, search ? `${search}匹配公司` : `用户${owner}专属公司第${pageNo}页`)], pageNo, size, 45));
    }
    const search = path.match(/^\/sharing\/users\/(\d+)\/$/);
    if (search) {
      if (state.searchFailures-- > 0) return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '搜索失败，请重试' });
      const id = Number(search[1]);
      if (id === 999999) return json(route, 404, { code: 'NOT_FOUND', message: '未找到用户' });
      return json(route, 200, state.connections.find(c => c.user.id === id)?.user ?? state.outgoing.find(r => r.recipient.id === id && r.status === 'pending')?.recipient ?? state.incoming.find(r => r.sender.id === id && r.status === 'pending')?.sender ?? user(id));
    }
    return json(route, 404, { code: 'NOT_FOUND' });
  });
  return state;
}
type State = Awaited<ReturnType<typeof mockApi>>;
const panel = (page: Page) => page.getByRole('region', { name: '共享用户面板', exact: true });
const records = (page: Page) => page.getByRole('region', { name: '共享投递记录', exact: true });
const member = (page: Page, username: string) => panel(page).getByRole('button', { name: username, exact: true });
async function signIn(page: Page) {
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(ME.username);
  await page.locator('input[name="password"]').fill('Sharing_test_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
}
async function openSharing(page: Page) {
  await signIn(page);
  await page.goto('/sharing');
  await expect(page.getByRole('heading', { name: '投递共享', exact: true })).toBeVisible();
  await expect(panel(page)).toBeVisible();
}
async function searchId(page: Page, id: string) {
  await panel(page).getByLabel('用户 ID', { exact: true }).fill(id);
  await panel(page).getByRole('button', { name: '搜索用户', exact: true }).click();
}
async function pick(page: Page, person = A) {
  await member(page, person.username).click();
  await expect(records(page).getByText(person.username, { exact: false }).first()).toBeVisible();
}
async function box(locator: Locator) {
  const bounds = await locator.boundingBox();
  expect(bounds).not.toBeNull();
  return bounds!;
}

test.describe('WEB-SHARE-001 public sharing page', () => {
  let state: State;
  test.beforeEach(async ({ page }) => { state = await mockApi(page); });

  test('entry, direct opening, reload, collapse and return preserve shared sidebar', async ({ page }) => {
    await signIn(page);
    const link = page.getByRole('link', { name: '投递共享', exact: true });
    await expect(link).toHaveAttribute('href', '/sharing');
    await link.click();
    await expect(panel(page)).toBeVisible();
    await page.goto('/sharing');
    await page.reload();
    await expect(page.getByRole('link', { name: '日历', exact: true })).toBeVisible();
    await page.getByRole('button', { name: '收起侧边栏', exact: true }).click();
    await expect(page.getByRole('link', { name: '日历', exact: true })).toBeHidden();
    await expect(panel(page)).toBeVisible();
    await page.getByRole('button', { name: '展开侧边栏', exact: true }).click();
    await page.getByRole('link', { name: /我的投递进度/, exact: false }).click();
    await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
    await link.click();
    await page.getByRole('link', { name: '日历', exact: true }).click();
    await expect(page).toHaveURL(/\/calendar/);
  });

  test('initial centered panel exposes ten users, IDs, consent rule, requests and refresh', async ({ page }) => {
    await openSharing(page);
    for (const title of ['推荐用户', '收到的申请', '发出的申请', '已共享用户'])
      await expect(panel(page).getByText(title, { exact: true })).toBeVisible();
    await expect(panel(page)).toContainText(`我的 ID`);
    await expect(panel(page)).toContainText(String(ME.id));
    await expect(panel(page)).toContainText(/同意后双方可互相查看/);
    await expect(panel(page)).toContainText(/个人备注不共享/);
    await expect(panel(page).getByRole('button', { name: '申请共享', exact: true })).toHaveCount(10);
    await expect(panel(page)).toContainText(incomingUser.username);
    await expect(panel(page)).toContainText(outgoingUser.username);
    const before = state.calls.filter(c => c.path.endsWith('/recommendations/')).length;
    await panel(page).getByRole('button', { name: '换一批', exact: true }).click();
    await expect.poll(() => state.calls.filter(c => c.path.endsWith('/recommendations/')).length).toBe(before + 1);
    expect(state.calls.some(c => /\/users\/\d+\/applications\/$/.test(c.path))).toBe(false);
  });

  test('ID search validates input, reports missing users, retries failure preserving ID and sends one request', async ({ page }) => {
    await openSharing(page);
    await searchId(page, '-1');
    expect(state.calls.some(c => /\/sharing\/users\/-1\/$/.test(c.path))).toBe(false);
    await searchId(page, '999999');
    await expect(panel(page)).toContainText('未找到用户');
    state.searchFailures = 1;
    await searchId(page, '501');
    await expect(panel(page)).toContainText(/失败|重试/);
    await expect(panel(page).getByLabel('用户 ID', { exact: true })).toHaveValue('501');
    await panel(page).getByRole('button', { name: '搜索用户', exact: true }).click();
    await expect(panel(page)).toContainText('共享用户501');
    await panel(page).getByRole('listitem').filter({ hasText: '共享用户501' }).getByRole('button', { name: '申请共享', exact: true }).click();
    await expect.poll(() => state.calls.filter(c => c.path === '/sharing/requests/' && c.method === 'POST' && c.body.recipient_id === 501).length).toBe(1);
    await expect(panel(page)).toContainText(/待对方同意|待处理/);
    expect(state.calls.some(c => c.path === '/sharing/users/501/applications/')).toBe(false);
  });

  test('recommendation sends request, handles operation failure and prevents duplicate requests', async ({ page }) => {
    await openSharing(page);
    state.mutationFailures = 1;
    await panel(page).getByRole('button', { name: '申请共享', exact: true }).first().click();
    await expect(panel(page)).toContainText(/失败|重试/);
    await panel(page).getByRole('button', { name: '申请共享', exact: true }).first().click();
    await expect.poll(() => state.outgoing.some(r => r.recipient.id === 301)).toBe(true);
    await expect(panel(page).getByRole('button', { name: '申请共享', exact: true })).toHaveCount(9);
    expect(state.calls.filter(c => c.method === 'POST' && c.path === '/sharing/requests/' && c.body.recipient_id === 301)).toHaveLength(2);
  });

  test('incoming acceptance requires explicit action and enables only connected user selection', async ({ page }) => {
    await openSharing(page);
    expect(state.calls.some(c => c.path === '/sharing/users/401/applications/')).toBe(false);
    await panel(page).getByRole('button', { name: '同意', exact: true }).click();
    await expect.poll(() => state.incoming[0].status).toBe('accepted');
    expect(state.calls.find(c => c.path === '/sharing/requests/701/respond/')?.body).toEqual({ decision: 'accepted' });
    await member(page, incomingUser.username).click();
    await expect(records(page)).toContainText('用户401专属公司');
  });

  test('incoming rejection and request history remain unprivileged and show each status', async ({ page }) => {
    state.outgoing.push(requestItem(703, ME, user(403), 'accepted'), requestItem(704, ME, user(404), 'rejected'), requestItem(705, ME, user(405), 'revoked'));
    await openSharing(page);
    await panel(page).getByRole('button', { name: '拒绝', exact: true }).click();
    await expect.poll(() => state.incoming[0].status).toBe('rejected');
    expect(state.calls.find(c => c.path === '/sharing/requests/701/respond/')?.body).toEqual({ decision: 'rejected' });
    for (const status of [/待对方同意|待处理/, /已同意/, /已拒绝/, /已解除/]) await expect(panel(page)).toContainText(status);
    await expect(member(page, incomingUser.username)).toHaveCount(0);
    expect(state.calls.some(c => c.path === '/sharing/users/401/applications/')).toBe(false);
  });

  test('selecting user animates panel to top right, narrows it and return restores centered wide panel', async ({ page }) => {
    await openSharing(page);
    const main = await box(page.getByRole('main'));
    const centered = await box(panel(page));
    expect(Math.abs(centered.x + centered.width / 2 - (main.x + main.width / 2))).toBeLessThan(main.width * .18);
    expect(centered.y + centered.height / 2).toBeGreaterThan(main.y + main.height * .25);
    await page.screenshot({ path: '../docs/test-reports/WEB-SHARE-001-centered.png', fullPage: true, animations: 'disabled' });
    await pick(page);
    await expect.poll(async () => (await box(panel(page))).width).toBeLessThan(centered.width * .9);
    const corner = await box(panel(page));
    expect(corner.x).toBeGreaterThan(centered.x);
    expect(corner.y).toBeLessThan(main.y + main.height * .3);
    expect(corner.x + corner.width).toBeLessThanOrEqual(main.x + main.width + 2);
    await page.screenshot({ path: '../docs/test-reports/WEB-SHARE-001-selected.png', fullPage: true, animations: 'disabled' });
    await panel(page).getByRole('button', { name: '返回用户选择', exact: true }).click();
    await expect(records(page)).toBeHidden();
    await expect.poll(async () => (await box(panel(page))).width).toBeGreaterThan(corner.width * 1.1);
  });

  test('record display is read only, exposes stages, links and searches/paginates the selected public API', async ({ page }) => {
    await openSharing(page); await pick(page);
    await expect(records(page)).toContainText('用户201专属公司第1页');
    await expect(records(page)).toContainText('测试工程师');
    for (const label of [/AI.*面试/, /笔试/, /一面|第一轮面试/, /二面|第二轮面试/, /三面|第三轮面试/, /HR.*面试/])
      await expect(records(page)).toContainText(label);
    for (const minutes of [30, 45, 60]) await expect(records(page)).toContainText(new RegExp(`${minutes}\\s*分钟`));
    await expect(records(page).getByRole('link').filter({ hasText: /投递|链接/ }).first()).toHaveAttribute('href', record(A.id).application_url);
    await expect(records(page).getByRole('button', { name: /编辑|删除/ })).toHaveCount(0);
    await expect(records(page)).not.toContainText('个人备注');
    const recordSearch = records(page).getByRole('textbox', { name: /公司|岗位|搜索/ }).first();
    await recordSearch.fill('过滤词');
    await records(page).getByRole('button', { name: /搜索|查询/ }).first().click();
    await expect.poll(() => state.calls.some(c => c.path === '/sharing/users/201/applications/' && c.search.get('search') === '过滤词')).toBe(true);
    await expect(records(page)).toContainText('过滤词匹配公司');
    const size = records(page).getByRole('combobox', { name: /每页/ });
    await size.selectOption('10');
    await expect.poll(() => state.calls.some(c => c.path === '/sharing/users/201/applications/' && c.search.get('page_size') === '10')).toBe(true);
    await expect(size.locator('option')).toHaveText(['10', '20', '50', '100']);
    await records(page).getByRole('button', { name: /下一页/ }).click();
    await expect.poll(() => state.calls.some(c => c.path === '/sharing/users/201/applications/' && c.search.get('page') === '2')).toBe(true);
    expect(state.calls.filter(c => c.path === '/applications/' && c.search.has('user_id'))).toHaveLength(0);
  });

  test('shared records use the canonical status label once and remain read only', async ({ page }) => {
    await openSharing(page); await pick(page);
    await expect(records(page)).toContainText('一面');
    await expect(records(page)).not.toContainText(/进行中|Offer|已撤回/);
    await expect(records(page).getByRole('button', { name: /编辑|删除|修改/ })).toHaveCount(0);
  });

  test('switch clears former records immediately and late previous-user response cannot overwrite', async ({ page }) => {
    await openSharing(page);
    state.delayA = true;
    await member(page, A.username).click();
    await expect.poll(() => state.calls.some(c => c.path === '/sharing/users/201/applications/')).toBe(true);
    await member(page, B.username).click();
    await expect(records(page)).toContainText('用户202专属公司');
    state.releaseA();
    await page.waitForTimeout(350);
    await expect(records(page)).toContainText('用户202专属公司');
    await expect(records(page)).not.toContainText('用户201专属公司');
  });

  test('record failure allows retry, shows loading and empty records', async ({ page }) => {
    await openSharing(page);
    state.recordFailures = 1;
    await member(page, A.username).click();
    await expect(records(page)).toContainText(/失败|重试/);
    await records(page).getByRole('button', { name: /重试/ }).click();
    await expect(records(page)).toContainText('用户201专属公司');
    await page.route('**/api/v1/sharing/users/202/applications/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 400));
      await json(route, 200, pagination([]));
    });
    await member(page, B.username).click();
    await expect(records(page)).not.toContainText('用户201专属公司');
    await expect(records(page)).toContainText(/加载/);
    await expect(records(page)).toContainText(/暂无|没有.*记录|空/);
  });

  test('unilateral revoke requires confirmation then clears current records and restores panel', async ({ page }) => {
    await openSharing(page); await pick(page);
    const connectedRow = panel(page).getByRole('listitem').filter({ hasText: A.username });
    await connectedRow.getByRole('button', { name: '解除共享', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toContainText(/解除/);
    await dialog.getByRole('button', { name: /确认|确定|解除共享/ }).click();
    await expect.poll(() => state.calls.some(c => c.path === '/sharing/connections/601/' && c.method === 'DELETE')).toBe(true);
    await expect(records(page)).toBeHidden();
    await expect(page.getByText('用户201专属公司第1页', { exact: true })).toHaveCount(0);
    await expect(member(page, A.username)).toHaveCount(0);
  });

  test('404 after partner revokes clears stale visible records and explains lost access', async ({ page }) => {
    await openSharing(page); await pick(page);
    await expect(records(page)).toContainText('用户201专属公司第1页');
    state.revoked = true;
    await records(page).getByRole('textbox', { name: /公司|岗位|搜索/ }).first().fill('重新加载');
    await records(page).getByRole('button', { name: /搜索|查询/ }).first().click();
    await expect(page.getByRole('main')).toContainText('共享已失效');
    await expect(page.getByRole('main')).not.toContainText('用户201专属公司第1页');
  });

  test('eight local avatar variants are visible, distinct and stable across refresh', async ({ page }) => {
    await openSharing(page);
    const avatarImages = panel(page).getByRole('img');
    await expect(avatarImages).toHaveCount(15); // self + ten recommended + two pending + two connected
    const signatures = await avatarImages.evaluateAll(images => images.map(el => {
      const img = el as HTMLImageElement;
      return img.tagName === 'IMG' ? img.src : el.innerHTML;
    }));
    expect(new Set(signatures).size).toBe(8);
    expect(signatures.every(s => !/^https?:\/\/(?!127\.0\.0\.1)/.test(s))).toBe(true);
    await page.reload();
    await expect(panel(page)).toBeVisible();
    await expect.poll(() => avatarImages.evaluateAll(images => images.map(el => el.tagName === 'IMG' ? (el as HTMLImageElement).src : el.innerHTML))).toEqual(signatures);
  });

  test('pending and connected search results cannot resend; a conflict refreshes authoritative request state', async ({ page }) => {
    await openSharing(page);
    await searchId(page, String(outgoingUser.id));
    const pendingRow = panel(page).getByRole('listitem').filter({ hasText: outgoingUser.username });
    await expect(pendingRow.getByRole('button', { name: '申请共享', exact: true })).toHaveCount(0);
    await searchId(page, String(A.id));
    const connectedRow = panel(page).getByRole('listitem').filter({ hasText: A.username });
    await expect(connectedRow.getByRole('button', { name: '申请共享', exact: true })).toHaveCount(0);
    const before = state.calls.filter(c => c.path === '/sharing/requests/' && c.method === 'GET').length;
    await page.route('**/api/v1/sharing/requests/', async route => {
      if (route.request().method() !== 'POST') return route.fallback();
      const recipient = user(501, 'outgoing_pending');
      state.outgoing.unshift(requestItem(1501, ME, recipient));
      await json(route, 409, { code: 'SHARING_CONFLICT', message: '申请状态已变化，请刷新' });
    });
    await searchId(page, '501');
    await panel(page).getByRole('listitem').filter({ hasText: '共享用户501' }).getByRole('button', { name: '申请共享', exact: true }).click();
    await expect.poll(() => state.calls.filter(c => c.path === '/sharing/requests/' && c.method === 'GET').length).toBeGreaterThan(before);
    await expect(panel(page)).toContainText(/状态已变化|待对方同意|待处理/);
    await expect(panel(page).getByRole('listitem').filter({ hasText: '共享用户501' }).getByRole('button', { name: '申请共享', exact: true })).toHaveCount(0);
  });

  test('in-flight application submission is disabled and produces exactly one POST', async ({ page }) => {
    await openSharing(page);
    let release: () => void = () => {};
    let attempts = 0;
    await page.route('**/api/v1/sharing/requests/', async route => {
      if (route.request().method() !== 'POST') return route.fallback();
      attempts += 1;
      await new Promise<void>(resolve => { release = resolve; });
      const recipient = user(301, 'outgoing_pending');
      const item = requestItem(1301, ME, recipient);
      state.outgoing.unshift(item);
      state.recommendations = state.recommendations.filter(u => u.id !== recipient.id);
      await json(route, 201, item);
    });
    const submit = panel(page).getByRole('listitem').filter({ hasText: '共享用户301' }).getByRole('button', { name: '申请共享', exact: true });
    await submit.click();
    await expect.poll(() => attempts).toBe(1);
    await expect(submit).toBeDisabled();
    release();
    await expect(panel(page)).toContainText(/待对方同意|待处理/);
    expect(attempts).toBe(1);
  });

  test('late search response cannot replace newer results for the same shared user', async ({ page }) => {
    await openSharing(page); await pick(page);
    let release: () => void = () => {};
    let oldSearchRequested = false;
    await page.route('**/api/v1/sharing/users/201/applications/**', async route => {
      const search = new URL(route.request().url()).searchParams.get('search');
      if (search === '旧搜索') {
        oldSearchRequested = true;
        await new Promise<void>(resolve => { release = resolve; });
      }
      await json(route, 200, pagination([record(201, `${search}匹配公司`)]));
    });
    const searchBox = records(page).getByRole('textbox', { name: /公司|岗位|搜索/ }).first();
    const searchButton = records(page).getByRole('button', { name: /搜索|查询/ }).first();
    await searchBox.fill('旧搜索'); await searchButton.click();
    await expect.poll(() => oldSearchRequested).toBe(true);
    await searchBox.fill('新搜索'); await searchButton.click();
    await expect(records(page)).toContainText('新搜索匹配公司');
    release();
    await page.waitForTimeout(350);
    await expect(records(page)).toContainText('新搜索匹配公司');
    await expect(records(page)).not.toContainText('旧搜索匹配公司');
  });

  test('mobile drawer, user selection and reduced motion layout remain usable without overflow', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await openSharing(page);
    await page.getByRole('button', { name: '打开导航', exact: true }).click();
    await expect(page.getByRole('link', { name: '投递共享', exact: true })).toBeVisible();
    await page.getByRole('link', { name: '投递共享', exact: true }).click();
    await expect(panel(page)).toBeVisible();
    const bounds = await box(panel(page));
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(391);
    await member(page, A.username).click();
    await expect(records(page)).toContainText('用户201专属公司');
    const content = await box(records(page));
    const picker = await box(panel(page));
    expect(content.x + content.width).toBeLessThanOrEqual(391);
    expect(picker.x + picker.width).toBeLessThanOrEqual(391);
    expect(content.y >= picker.y + picker.height - 2 || picker.y >= content.y + content.height - 2).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const animations = await panel(page).evaluate(el => el.getAnimations({ subtree: true }).map(animation => animation.effect?.getTiming().duration ?? 0));
    expect(animations.every(duration => Number(duration) <= 50)).toBe(true);
    await page.getByRole('button', { name: '打开导航', exact: true }).click();
    await page.getByRole('link', { name: '日历', exact: true }).click();
    await expect(page).toHaveURL(/\/calendar/);
  });
});
