import { expect, test, type Page, type Route } from '@playwright/test';

// APP-010 public UI/HTTP checks only: no production imports.
const date = '2026-10-07T02:00:00Z';
const statusLabels = ['投递', '测评', '笔试', '一面', '二面', '其他轮次', 'HR面', '拒绝'];

const position = (id: number, name: string, status: string) => ({
  id,
  position_name: name,
  application_status: status,
  application_time: date,
  notes: `${name}私有备注`,
  interviews: [],
});

const company = () => ({
  id: 1001,
  company_name: 'APP-010公开状态公司',
  positions: [
    position(1002, '后端工程师', 'assessment'),
    position(1003, '数据工程师', 'hr_interview'),
  ],
  shared_stages: [
    { type: 'ai_interview', scheduled_at: date, duration_minutes: 30 },
    { type: 'assessment', scheduled_at: date, duration_minutes: 45 },
    { type: 'written_test', scheduled_at: null, duration_minutes: null },
  ],
  current_stage: 'assessment',
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
    if (url.pathname === '/api/v1/auth/login/') return json(route, 200, { access: 'app010-access', refresh: 'app010-refresh', user: { id: 100, username: 'app010-ui', email: 'test@example.invalid' } });
    if (url.pathname === '/api/v1/auth/me/') return json(route, 200, { id: 100, username: 'app010-ui', email: 'test@example.invalid' });
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/') {
      return json(route, 200, { results: [company()], count: 1, page: 1, page_size: 20, total_pages: 1, next: null, previous: null });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/1001/') return json(route, 200, company());
    if (request.method() === 'POST' && url.pathname === '/api/v1/applications/') {
      return json(route, 201, { ...company(), positions: body?.positions ?? company().positions });
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('app010-ui');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: 'APP-010公开状态公司' })).toHaveCount(1);
  return calls;
}

test.describe('APP-010 public status UI contract', () => {
  test('new-position form exposes exactly one business-status selector in canonical order', async ({ page }) => {
    const calls = await setup(page);
    await page.goto('/applications/new');
    const role = page.getByRole('group', { name: '岗位1', exact: true });
    await expect(role).toBeVisible();
    const status = role.getByRole('combobox');
    await expect(status).toHaveCount(1);
    await status.click();
    const options = page.getByRole('option');
    await expect(options).toHaveCount(statusLabels.length);
    expect(await options.allTextContents()).toEqual(statusLabels);
    await page.getByRole('option', { name: '二面', exact: true }).click();
    await page.getByLabel('公司名称', { exact: true }).fill('APP-010新建公司');
    await role.getByLabel('岗位名称', { exact: true }).fill('平台工程师');
    await page.getByRole('button', { name: /创建|保存/ }).last().click();
    await expect.poll(() => calls.some(call => call.method === 'POST' && call.path === '/api/v1/applications/')).toBe(true);
    const saved = calls.find(call => call.method === 'POST' && call.path === '/api/v1/applications/')!;
    expect(saved.body.positions[0].application_status).toBe('second_interview');
    await expect(role.getByText(/当前阶段|面试状态/)).toHaveCount(0);
  });

  test('list renders one canonical status per position and does not render a second current-stage label', async ({ page }) => {
    await setup(page);
    const row = page.getByRole('row').filter({ hasText: 'APP-010公开状态公司' });
    const firstPositionRow = page.getByText('后端工程师', { exact: true }).locator('xpath=ancestor::tr[1]');
    await expect(firstPositionRow.getByRole('cell').nth(2).getByText('测评', { exact: true })).toHaveCount(1);
    await expect(row).not.toContainText(/当前阶段|进行中|Offer|已撤回/);
    const expand = row.locator('button[aria-expanded]');
    await expect(expand).toHaveCount(1);
    await expand.click();
    await expect(page.getByText('数据工程师', { exact: true })).toBeVisible();
    await expect(page.getByText('HR面', { exact: true })).toHaveCount(1);
  });

  test('status filter sends application_status and never sends stage', async ({ page }) => {
    const calls = await setup(page);
    const filter = page.getByRole('combobox').first();
    await expect(filter).toHaveCount(1);
    await filter.click();
    await page.getByRole('option', { name: 'HR面', exact: true }).click();
    await expect.poll(() => calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('application_status=hr_interview'))).toBe(true);
    const request = calls.find(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('application_status=hr_interview'))!;
    expect(request.search).not.toContain('stage=');
  });
});
