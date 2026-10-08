import { expect, test, type Page, type Route } from '@playwright/test';

// APP-012 public DOM/HTTP contract.  No frontend production modules are imported.
const user = { id: 1200, username: 'app012-ui', email: 'app012@example.invalid' };
const recruitmentUrl = 'https://jobs.example.test';

const company = () => ({
  id: 1201,
  company_id: 1201,
  company_name: '全局示例科技',
  recruitment_url: recruitmentUrl,
  company: { id: 1201, company_name: '全局示例科技', recruitment_url: recruitmentUrl },
  positions: [
    { id: 1202, position_name: '后端工程师', application_status: 'applied', current_stage: 'applied', application_time: null, notes: '岗位一备注', interviews: [] },
    { id: 1203, position_name: '数据工程师', application_status: 'second_interview', current_stage: 'second_interview', application_time: null, notes: '岗位二备注', interviews: [] },
  ],
  shared_stages: [],
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

    if (url.pathname === '/api/v1/auth/login/' && request.method() === 'POST') {
      return json(route, 200, { access: 'app012-access', refresh: 'app012-refresh', user });
    }
    if (url.pathname === '/api/v1/auth/me/' && request.method() === 'GET') return json(route, 200, user);
    if (url.pathname === '/api/v1/companies/' && request.method() === 'GET') {
      return json(route, 200, {
        count: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
        results: [{ id: 1201, company_name: '全局示例科技', recruitment_url: recruitmentUrl }],
      });
    }
    if (url.pathname === '/api/v1/companies/' && request.method() === 'POST') {
      return json(route, 201, { id: 1201, company_name: body?.company_name, recruitment_url: body?.recruitment_url });
    }
    if (url.pathname === '/api/v1/companies/1201/' && request.method() === 'PATCH') {
      return json(route, 200, { id: 1201, company_name: '全局示例科技', recruitment_url: body?.recruitment_url ?? recruitmentUrl });
    }
    if (url.pathname === '/api/v1/applications/' && request.method() === 'GET') {
      return json(route, 200, { results: [company()], count: 1, page: 1, page_size: 20, total_pages: 1, next: null, previous: null });
    }
    if (url.pathname === '/api/v1/applications/' && request.method() === 'POST') {
      return json(route, 201, { ...company(), positions: body?.positions ?? company().positions });
    }
    if (url.pathname === '/api/v1/applications/1201/' && request.method() === 'GET') return json(route, 200, company());
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });

  await page.goto('/login');
  await page.locator('input[name="username"]').fill(user.username);
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: '全局示例科技' })).toHaveCount(1);
  return calls;
}

test.describe('APP-012 global company public UI contract', () => {
  test('new form uses a global company selector/create entry and sends company_id only', async ({ page }) => {
    const calls = await setup(page);
    await page.goto('/applications/new');

    const companySelector = page.getByRole('combobox', { name: /公司/ });
    await expect(companySelector).toHaveCount(1);
    await expect(page.getByRole('button', { name: /创建公司|新增公司/ })).toHaveCount(1);
    await companySelector.click();
    await expect(page.getByRole('option', { name: '全局示例科技', exact: true })).toBeVisible();
    await page.getByRole('option', { name: '全局示例科技', exact: true }).click();

    const positionNames = page.getByLabel(/岗位名称/);
    await expect(positionNames).toHaveCount(1);
    await positionNames.first().fill('后端工程师');
    await page.getByRole('button', { name: /添加岗位|新增岗位/ }).click();
    await expect(positionNames).toHaveCount(2);
    await positionNames.nth(1).fill('数据工程师');

    const websiteInputs = page.getByLabel(/招聘网站/);
    await expect(websiteInputs).toHaveCount(1);
    await expect(page.getByText(recruitmentUrl, { exact: true })).toHaveCount(1);
    await page.getByRole('button', { name: /创建|保存/ }).last().click();

    await expect.poll(() => calls.some(call => call.method === 'POST' && call.path === '/api/v1/applications/')).toBe(true);
    const saved = calls.find(call => call.method === 'POST' && call.path === '/api/v1/applications/')!;
    expect(saved.body.company_id).toBe(1201);
    expect(saved.body.company_name).toBeUndefined();
    expect(saved.body.recruitment_url).toBeUndefined();
    expect(saved.body.positions).toHaveLength(2);
    expect(saved.body.positions.every((position: any) => position.application_url === undefined)).toBe(true);
    expect(saved.body.positions.every((position: any) => position.recruitment_url === undefined)).toBe(true);
  });

  test('company name is the sole website link, expansion reveals only current-user positions, and each position has an edit entry', async ({ page }) => {
    await setup(page);
    const row = page.getByRole('row').filter({ hasText: '全局示例科技' });
    const companyLink = row.getByRole('link', { name: '全局示例科技', exact: true });
    await expect(companyLink).toHaveAttribute('href', recruitmentUrl);
    await expect(companyLink).toHaveAttribute('target', '_blank');
    await expect(row.getByText(recruitmentUrl, { exact: true })).toHaveCount(0);
    const expand = row.locator('button[aria-expanded]');
    await expect(expand).toHaveCount(1);
    await expand.click();
    await expect(page.getByText('后端工程师', { exact: true })).toBeVisible();
    await expect(page.getByText('数据工程师', { exact: true })).toBeVisible();
    await expect(page.getByText(recruitmentUrl, { exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /编辑/ })).toHaveCount(2);
  });

  test('company metadata edit is explicitly shared and does not become a position field', async ({ page }) => {
    const calls = await setup(page);
    const row = page.getByRole('row').filter({ hasText: '全局示例科技' });
    await row.getByRole('button', { name: /编辑公司|修改网站|共享信息/ }).click();
    await expect(page.getByText(/共享信息|影响所有用户/)).toBeVisible();
    const website = page.getByLabel(/招聘网站/);
    await expect(website).toHaveCount(1);
    await website.fill('https://jobs.updated.example.test');
    await page.getByRole('button', { name: /保存/ }).click();
    await expect.poll(() => calls.some(call => call.method === 'PATCH' && call.path === '/api/v1/companies/1201/')).toBe(true);
    expect(calls.find(call => call.method === 'PATCH' && call.path === '/api/v1/companies/1201/')!.body).toEqual({
      recruitment_url: 'https://jobs.updated.example.test',
    });
  });
});
