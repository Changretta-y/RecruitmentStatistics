import { expect, test, type Page, type Route } from '@playwright/test';

// Public HTTP and rendered UI only; no frontend production imports.
const website = 'https://jobs.example.test/careers?ref=campus';
const records = [
  {
    id: 1301, company_id: 1301, company_name: '有链接公司',
    recruitment_url: website, application_url: website,
    positions: [{ id: 1311, position_name: '后端工程师', application_status: 'applied', notes: '', interviews: [] }],
    shared_stages: [],
  },
  {
    id: 1302, company_id: 1302, company_name: '无链接公司',
    recruitment_url: null, application_url: null,
    positions: [{ id: 1312, position_name: '数据工程师', application_status: 'applied', notes: '', interviews: [] }],
    shared_stages: [],
  },
  {
    id: 1303, company_id: 1303, company_name: '非法链接公司',
    recruitment_url: 'javascript:alert(1)', application_url: 'javascript:alert(1)',
    positions: [{ id: 1313, position_name: '测试工程师', application_status: 'applied', notes: '', interviews: [] }],
    shared_stages: [],
  },
];
const names = ['建议甲公司', '建议乙公司', '建议丙公司', '建议丁公司'];
type SuggestionMode = 'success' | 'error';

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, initialMode: SuggestionMode = 'success') {
  const calls: { method: string; path: string; search: string }[] = [];
  let suggestionMode = initialMode;
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    calls.push({ method: request.method(), path: url.pathname, search: url.search });
    if (request.method() === 'POST' && url.pathname === '/api/v1/auth/login/') {
      return json(route, 200, { access: 'web013-access', refresh: 'web013-refresh', user: { id: 1300, username: 'web013-user', email: 'test@example.invalid' } });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/auth/me/') {
      return json(route, 200, { id: 1300, username: 'web013-user', email: 'test@example.invalid' });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/') {
      const pageSize = Number(url.searchParams.get('page_size') ?? '20');
      const suggestions = pageSize === 100 && !url.searchParams.has('search');
      if (suggestions && suggestionMode === 'error') return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '建议加载失败' });
      const results = suggestions ? names.map((name, index) => ({ id: 1400 + index, company_name: name })) : records;
      return json(route, 200, { results, count: results.length, page: 1, page_size: pageSize, total_pages: 1, next: null, previous: null });
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('web013-user');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: '有链接公司' })).toHaveCount(1);
  return { calls, setSuggestionMode: (mode: SuggestionMode) => { suggestionMode = mode; } };
}

const keyword = (page: Page) => page.locator('input[placeholder*="关键字"], input[aria-label*="关键字"], input[name="search"]').first();

test('company name is the only visible website link and opens a new tab', async ({ page }) => {
  await setup(page);
  const row = page.getByRole('row').filter({ hasText: '有链接公司' });
  const link = row.getByRole('link', { name: '有链接公司', exact: true });
  await expect(link).toHaveAttribute('href', website);
  await expect(link).toHaveAttribute('target', '_blank');
  await expect(row.getByText(website, { exact: true })).toHaveCount(0);
  expect(await row.innerText()).not.toContain(website);
});

test('company without recruitment URL remains text rather than a fabricated link', async ({ page }) => {
  await setup(page);
  const row = page.getByRole('row').filter({ hasText: '无链接公司' });
  await expect(row.getByText('无链接公司', { exact: true })).toBeVisible();
  await expect(row.getByRole('link', { name: '无链接公司', exact: true })).toHaveCount(0);
});

test('non-HTTP recruitment URL never turns the company name into a link', async ({ page }) => {
  await setup(page);
  const row = page.getByRole('row').filter({ hasText: '非法链接公司' });
  await expect(row.getByText('非法链接公司', { exact: true })).toBeVisible();
  await expect(row.getByRole('link', { name: '非法链接公司', exact: true })).toHaveCount(0);
  expect(await row.innerText()).not.toContain('javascript:alert');
});

test('suggestion options remain hit-testable below the query field instead of being clipped by cards', async ({ page }) => {
  await setup(page);
  const input = keyword(page);
  await input.focus();
  const listbox = page.getByRole('listbox');
  await expect(listbox).toBeVisible();
  const options = listbox.getByRole('option');
  await expect(options).toHaveCount(names.length);
  await expect(options.last()).toHaveText('建议丁公司');
  // Test the open popup as the user sees it; scrolling an individual option
  // into view would hide a clipping defect at the card boundary.
  const hitResults = await options.evaluateAll(elements => elements.map(element => {
    const box = element.getBoundingClientRect();
    const point = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return point === element || element.contains(point);
  }));
  expect(hitResults).toEqual(names.map(() => true));
});

test('outside click closes suggestions while clicking the input keeps them open', async ({ page }) => {
  await setup(page);
  const input = keyword(page);
  await input.focus();
  const listbox = page.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await input.click();
  await expect(listbox).toBeVisible();
  await page.locator('body').click({ position: { x: 1100, y: 500 } });
  await expect(listbox).toBeHidden();
});

test('Escape closes suggestions without submitting a search', async ({ page }) => {
  const { calls } = await setup(page);
  const input = keyword(page);
  await input.focus();
  const listbox = page.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await input.press('Escape');
  await expect(listbox).toBeHidden();
  expect(calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/' && new URL(call.search, 'http://fixture').searchParams.has('search'))).toBe(false);
});

test('selecting a suggestion submits one search and closes the popup', async ({ page }) => {
  const { calls } = await setup(page);
  const input = keyword(page);
  await input.focus();
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.getByRole('option', { name: '建议乙公司', exact: true }).click();
  await expect(input).toHaveValue('建议乙公司');
  await expect(page.getByRole('listbox')).toBeHidden();
  await expect.poll(() => calls.filter(call => call.method === 'GET' && call.path === '/api/v1/applications/' && new URL(call.search, 'http://fixture').searchParams.get('search') === '建议乙公司').length).toBe(1);
});

test('retry within the suggestion popup reloads options without dismissing it', async ({ page }) => {
  const { setSuggestionMode } = await setup(page, 'error');
  const input = keyword(page);
  await input.focus();
  const listbox = page.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await expect(listbox).toContainText(/失败|重试/);
  setSuggestionMode('success');
  await listbox.getByRole('button', { name: /重试/ }).click();
  await expect(listbox).toBeVisible();
  await expect(listbox.getByRole('option', { name: '建议甲公司' })).toBeVisible();
});
