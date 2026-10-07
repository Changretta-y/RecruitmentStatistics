import { expect, test, type Page, type Route } from '@playwright/test';

// APP-011 black-box UI/HTTP fixture; no production imports.
const date = '2026-10-07T02:00:00Z';
const statusLabels = ['投递', '测评', '笔试', '一面', '二面', '其他轮次', 'HR面', '拒绝'];

const company = () => ({
  id: 1101,
  company_name: 'APP-011最新状态公司',
  positions: [
    {
      id: 1102,
      position_name: '后端工程师',
      application_status: 'applied',
      current_stage: 'second_interview',
      application_time: date,
      notes: '岗位私有备注',
      interviews: [{ id: 1103, name: '二面', scheduled_at: date, duration_minutes: 60 }],
    },
  ],
  shared_stages: [
    { type: 'assessment', scheduled_at: date, duration_minutes: 45 },
    { type: 'written_test', scheduled_at: null, duration_minutes: null },
    { type: 'ai_interview', scheduled_at: null, duration_minutes: null },
  ],
  current_stage: 'second_interview',
  created_at: date,
  updated_at: date,
});

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  const calls: { method: string; path: string; search: string; body: any }[] = [];
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const body = request.postDataJSON();
    calls.push({ method: request.method(), path: url.pathname, search: url.search, body });
    if (url.pathname === '/api/v1/auth/login/') {
      return json(route, 200, { access: 'app011-access', refresh: 'app011-refresh', user: { id: 110, username: 'app011-ui', email: 'test@example.invalid' } });
    }
    if (url.pathname === '/api/v1/auth/me/') {
      return json(route, 200, { id: 110, username: 'app011-ui', email: 'test@example.invalid' });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/') {
      return json(route, 200, { results: [company()], count: 1, page: 1, page_size: 20, total_pages: 1, next: null, previous: null });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/1101/') return json(route, 200, company());
    if (request.method() === 'POST' && url.pathname === '/api/v1/applications/') {
      return json(route, 201, { ...company(), positions: body?.positions ?? company().positions });
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('app011-ui');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: 'APP-011最新状态公司' })).toHaveCount(1);
  return calls;
}

test.describe('APP-011 latest-flow public UI contract', () => {
  test('form exposes exactly the canonical eight options in order', async ({ page }) => {
    const calls = await setup(page);
    await page.goto('/applications/new');
    const role = page.getByRole('group', { name: '岗位1', exact: true });
    const status = role.getByRole('combobox');
    await expect(status).toHaveCount(1);
    await status.click();
    await expect(page.getByRole('option')).toHaveCount(statusLabels.length);
    expect(await page.getByRole('option').allTextContents()).toEqual(statusLabels);
    await expect(page.getByText(/已投递|进行中|Offer|已拒绝|已撤回/)).toHaveCount(0);
    await page.getByRole('option', { name: '二面', exact: true }).click();
    await page.getByLabel('公司名称', { exact: true }).fill('APP-011新建公司');
    await role.getByLabel('岗位名称', { exact: true }).fill('平台工程师');
    await page.getByRole('button', { name: /创建|保存/ }).last().click();
    await expect.poll(() => calls.some(call => call.method === 'POST' && call.path === '/api/v1/applications/')).toBe(true);
    const saved = calls.find(call => call.method === 'POST' && call.path === '/api/v1/applications/')!;
    expect(saved.body.positions[0].application_status).toBe('second_interview');
  });

  test('main list renders the public current_stage rather than the saved fallback status', async ({ page }) => {
    await setup(page);
    const row = page.getByText('后端工程师', { exact: true }).locator('xpath=ancestor::tr[1]');
    await expect(row.getByText('二面', { exact: true })).toHaveCount(1);
    await expect(row).not.toContainText('投递状态');
    await expect(row).not.toContainText('进行中');
  });

  test('status filter remains canonical and does not send the retired stage parameter', async ({ page }) => {
    const calls = await setup(page);
    const filter = page.getByRole('combobox').first();
    await filter.click();
    await page.getByRole('option', { name: '二面', exact: true }).click();
    await expect.poll(() => calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('application_status=second_interview'))).toBe(true);
    const request = calls.find(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('application_status=second_interview'))!;
    expect(request.search).not.toContain('stage=');
  });
});
