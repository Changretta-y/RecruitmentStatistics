import { expect, test, type Page, type Route } from '@playwright/test';

// Public HTTP fixtures and rendered user interactions only; no production imports.
const timestamp = '2026-09-29T02:00:00Z';
const shared = [
  { type: 'ai_interview', scheduled_at: timestamp, duration_minutes: 30 },
  { type: 'assessment', scheduled_at: '2026-09-30T02:00:00Z', duration_minutes: 45 },
  { type: 'written_test', scheduled_at: '2026-10-01T02:00:00Z', duration_minutes: 60 },
];
const position = (id: number, name: string) => ({
  id, position_name: name, application_status: 'assessment',
  application_url: `https://jobs.example.invalid/${id}`, application_time: timestamp,
  notes: `${name}独立备注`,
  interviews: [
    { id: id * 10, name: '技术面', scheduled_at: '2026-10-02T02:00:00Z', duration_minutes: 90 },
    { id: id * 10 + 1, name: '技术面', scheduled_at: '2026-10-03T02:00:00Z', duration_minutes: 40 },
  ],
});
const company = () => ({
  company_name: '多岗位示例科技', positions: [position(902, '后端工程师'), position(903, '前端工程师')],
  shared_stages: structuredClone(shared), current_stage: 'assessment', created_at: timestamp, updated_at: timestamp,
  // APP-009 retains a flat compatibility projection; both shapes describe the same company.
  ...position(902, '后端工程师'), id: 901,
  ai_interview_time: timestamp, ai_interview_duration_minutes: 30,
  written_test_time: '2026-10-01T02:00:00Z', written_test_duration_minutes: 60,
  first_interview_time: null, first_interview_duration_minutes: null,
  second_interview_time: null, second_interview_duration_minutes: null,
  third_interview_time: null, third_interview_duration_minutes: null,
  hr_interview_time: null, hr_interview_duration_minutes: null,
});
async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}
async function fixture(page: Page) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    calls.push({ method: request.method(), path, body: request.postDataJSON() });
    if (path === '/api/v1/auth/login/') return json(route, 200, { access: 'synthetic-access', refresh: 'synthetic-refresh', user: { id: 899, username: 'web_app_006', email: 'test@example.invalid' } });
    if (path === '/api/v1/auth/me/') return json(route, 200, { id: 899, username: 'web_app_006', email: 'test@example.invalid' });
    if (path === '/api/v1/applications/') return json(route, 200, { results: [company()], count: 1, page: 1, page_size: 20, total_pages: 1, next: null, previous: null });
    if (path === '/api/v1/applications/901/') return json(route, 200, company());
    return json(route, 404, { code: 'NOT_FOUND' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('web_app_006');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: '多岗位示例科技' })).toHaveCount(1);
  return calls;
}
async function createPage(page: Page) {
  await page.locator('a[href="/applications/new"]').last().click();
  await expect(page.locator('input[name="companyName"], input[name="company_name"]')).toBeVisible();
  await expect(page.getByRole('button', { name: /保存|提交|创建/ })).toBeVisible();
}

test.describe('WEB-APP-006 core public UI contract', () => {
  test('fixture baseline authenticates, renders nested-company row and opens a valid form', async ({ page }) => {
    const calls = await fixture(page);
    await createPage(page);
    expect(calls.some(call => call.path === '/api/v1/applications/' && call.method === 'GET')).toBe(true);
    await expect(page.locator('form')).toBeVisible();
  });

  test('create form can add a second independently editable position', async ({ page }) => {
    await fixture(page);
    await createPage(page);
    const add = page.getByRole('button', { name: /添加岗位|新增岗位/ });
    await expect(add).toBeVisible();
    await add.click();
    await expect(page.getByLabel(/岗位名称/)).toHaveCount(2);
    await page.getByLabel(/岗位名称/).nth(0).fill('后端工程师');
    await page.getByLabel(/岗位名称/).nth(1).fill('前端工程师');
    await expect(page.getByLabel(/岗位名称/).nth(0)).toHaveValue('后端工程师');
    await expect(page.getByLabel(/岗位名称/).nth(1)).toHaveValue('前端工程师');
  });

  test('create form exposes one shared assessment time independently of position count', async ({ page }) => {
    await fixture(page);
    await createPage(page);
    const assessmentTime = page.getByLabel(/测评/).and(page.locator('input:not([type="number"]):visible'));
    await expect(assessmentTime).toHaveCount(1);
    const add = page.getByRole('button', { name: /添加岗位|新增岗位/ });
    await add.click();
    await expect(assessmentTime).toHaveCount(1);
  });

  test('multi-position company expands by keyboard with aria state and no write request', async ({ page }) => {
    const calls = await fixture(page);
    const row = page.getByRole('row').filter({ hasText: '多岗位示例科技' });
    const expand = row.locator('button[aria-expanded]');
    await expect(expand).toHaveCount(1);
    await expect(expand).toHaveAttribute('aria-expanded', 'false');
    await expand.focus();
    await page.keyboard.press('Enter');
    await expect(expand).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByText('前端工程师', { exact: true })).toBeVisible();
    await expect(page.getByText('测评', { exact: true }).filter({ visible: true }).first()).toBeVisible();
    await expand.focus();
    await page.keyboard.press('Space');
    await expect(expand).toHaveAttribute('aria-expanded', 'false');
    expect(calls.filter(call => call.path.startsWith('/api/v1/applications/') && call.method !== 'GET')).toEqual([]);
  });
});
