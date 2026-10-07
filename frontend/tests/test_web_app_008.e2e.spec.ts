import { expect, test, type Page, type Route } from '@playwright/test';

// WEB-APP-008 public HTTP/UI fixture only; no production imports.
const date = '2026-10-08T02:00:00Z';
const historicalCompanies = [
  { id: 801, company_name: '本人历史甲公司' },
  { id: 802, company_name: '本人历史乙公司' },
  { id: 803, company_name: '本人历史甲公司 ' },
  { id: 804, company_name: '本人历史丙公司' },
];
const pageRecords = [
  { id: 901, company_name: '进行中公司', positions: [{ id: 902, position_name: '后端', application_status: 'applied', current_stage: 'assessment' }] },
  { id: 903, company_name: '拒绝公司', positions: [{ id: 904, position_name: '后端', application_status: 'rejected', current_stage: 'rejected' }] },
];
const publicCompany = '公共目录公司';
type SuggestionMode = 'success' | 'empty' | 'unauthorized' | 'error';

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

function response(results: unknown[], page: number, pageSize: number, totalPages: number, next: string | null = null, previous: string | null = null, count = totalPages === 0 ? 0 : 45) {
  return { results, count, page, page_size: pageSize, total_pages: totalPages, next, previous };
}

async function setup(page: Page, initialSuggestionMode: SuggestionMode = 'success') {
  const calls: { method: string; path: string; search: string; body: any }[] = [];
  let suggestionMode = initialSuggestionMode;
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const body = request.postDataJSON();
    calls.push({ method: request.method(), path: url.pathname, search: url.search, body });
    if (url.pathname === '/api/v1/auth/login/') return json(route, 200, { access: 'web008-access', refresh: 'web008-refresh', user: { id: 808, username: 'web008-ui', email: 'test@example.invalid' } });
    if (url.pathname === '/api/v1/auth/me/') return json(route, 200, { id: 808, username: 'web008-ui', email: 'test@example.invalid' });
    if (request.method() === 'GET' && url.pathname === '/api/v1/applications/') {
      const pageNo = Number(url.searchParams.get('page') ?? '1');
      const pageSize = Number(url.searchParams.get('page_size') ?? '20');
      const isSuggestion = pageSize === 100 && !url.searchParams.has('search') && !url.searchParams.has('application_status') && !url.searchParams.has('ordering') && !url.searchParams.has('application_time_after') && !url.searchParams.has('application_time_before');
      if (isSuggestion) {
        if (suggestionMode === 'empty') return json(route, 200, response([], pageNo, pageSize, 0, null, null, 0));
        if (suggestionMode === 'unauthorized') return json(route, 401, { code: 'NOT_AUTHENTICATED', message: '未认证' });
        if (suggestionMode === 'error') return json(route, 500, { code: 'SERVER_ERROR', message: '建议加载失败' });
        const results = pageNo === 1 ? historicalCompanies.slice(0, 2) : historicalCompanies.slice(2);
        return json(route, 200, response(results, pageNo, pageSize, 2));
      }
      if (url.searchParams.get('search') === '无数据') {
        return json(route, 200, response([], pageNo, pageSize, 0, null, null, 0));
      }
      const normalizedPage = pageNo === 999 ? 3 : pageNo;
      return json(route, 200, response(pageRecords, normalizedPage, pageSize, 3,
        normalizedPage < 3 ? `/api/v1/applications/?page=${normalizedPage + 1}&page_size=${pageSize}` : null,
        normalizedPage > 1 ? `/api/v1/applications/?page=${normalizedPage - 1}&page_size=${pageSize}` : null));
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('web008-ui');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  return { calls, setSuggestionMode: (mode: SuggestionMode) => { suggestionMode = mode; } };
}

const keyword = (page: Page) => page.locator('input[placeholder*="关键字"], input[aria-label*="关键字"], input[name="search"]').first();

test.describe('WEB-APP-008 public suggestions and pagination', () => {
  test('focus loads own deduplicated company suggestions and selecting one searches with preserved query state', async ({ page }) => {
    const { calls } = await setup(page);
    await page.goto('/applications?page=3&pageSize=50&applicationStatus=assessment&application_time_after=2026-10-01&ordering=-updated_at');
    const input = keyword(page);
    await expect(input).toBeVisible();
    await input.focus();
    await expect(page.getByRole('listbox')).toBeVisible();
    await expect(page.getByRole('listbox')).toContainText('本人历史甲公司');
    await expect(page.getByRole('listbox')).toContainText('本人历史乙公司');
    await expect(page.getByRole('listbox')).toContainText('本人历史丙公司');
    await expect(page.getByRole('listbox').getByText('本人历史甲公司', { exact: true })).toHaveCount(1);
    await page.getByRole('option', { name: '本人历史乙公司', exact: true }).click();
    await expect(input).toHaveValue('本人历史乙公司');
    await expect(page).toHaveURL(/search=%E6%9C%AC%E4%BA%BA%E5%8E%86%E5%8F%B2%E4%B9%99%E5%85%AC%E5%8F%B8/);
    await expect(page).toHaveURL(/page=1/);
    await expect(page).toHaveURL(/pageSize=50/);
    await expect(page).toHaveURL(/applicationStatus=assessment/);
    await expect.poll(() => calls.filter(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('search=')).length).toBe(1);
    const searchCall = calls.find(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('search='))!;
    expect(searchCall.search).toContain('page=1');
    expect(searchCall.search).toContain('page_size=50');
    expect(searchCall.search).toContain('application_status=assessment');
    expect(searchCall.search).toContain('ordering=-updated_at');
  });

  test('page selector and numeric jump preserve page size and filters, while invalid input sends no request', async ({ page }) => {
    const { calls } = await setup(page);
    await page.goto('/applications?page=1&pageSize=50&search=保持条件&applicationStatus=assessment&ordering=-updated_at');
    const pageSelect = page.getByRole('combobox', { name: /页码/ });
    await expect(pageSelect).toBeVisible();
    await expect(pageSelect.locator('option')).toHaveText(['1', '2', '3']);
    await pageSelect.selectOption('2');
    await expect.poll(() => calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('page=2'))).toBe(true);
    const secondPage = calls.find(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('page=2'))!;
    expect(secondPage.search).toContain('page_size=50');
    expect(secondPage.search).toContain('search=%E4%BF%9D%E6%8C%81%E6%9D%A1%E4%BB%B6');
    expect(secondPage.search).toContain('application_status=assessment');
    const pageInput = page.getByRole('spinbutton', { name: /页码/ });
    await expect(pageInput).toBeVisible();
    await pageInput.fill('0');
    const beforeInvalid = calls.filter(call => call.method === 'GET' && call.path === '/api/v1/applications/').length;
    await pageInput.press('Enter');
    await expect(page.getByText(/页码.*(合法|有效)|请输入.*页码/)).toBeVisible();
    await expect.poll(() => calls.filter(call => call.method === 'GET' && call.path === '/api/v1/applications/').length).toBe(beforeInvalid);
  });

  test('isolates empty, unauthorized, and failed suggestions and normalizes pagination boundaries', async ({ page, browser }) => {
    for (const scenario of [
      { mode: 'empty' as const, state: /暂无|没有.*公司|空/ },
      { mode: 'unauthorized' as const, state: /没有匹配|暂无|认证|登录/ },
      { mode: 'error' as const, state: /失败|重试|网络/ },
    ]) {
      const suggestionContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5189' });
      const suggestionPage = await suggestionContext.newPage();
      const { calls } = await setup(suggestionPage, scenario.mode);
      const input = keyword(suggestionPage);
      await expect(input).toBeVisible();
      await input.focus();
      await expect.poll(() => calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/' && call.search.includes('page_size=100'))).toBe(true);
      await expect(suggestionPage.getByRole('listbox')).toBeVisible();
      await expect(suggestionPage.getByRole('listbox')).toContainText(scenario.state);
      await expect(suggestionPage.getByText(publicCompany, { exact: true })).toHaveCount(0);
      await suggestionContext.close();
    }

    const { calls } = await setup(page);
    const sharedQuery = 'pageSize=50&search=边界状态&applicationStatus=assessment&applicationTimeAfter=2026-10-01T00:00:00%2B08:00&applicationTimeBefore=2026-10-31T23:59:59%2B08:00&ordering=-updated_at';
    const previous = page.getByRole('button', { name: /上一页|previous/i });
    const next = page.getByRole('button', { name: /下一页|next/i });
    const pageSelect = page.getByRole('combobox', { name: /页码/ });

    await page.goto(`/applications?page=1&${sharedQuery}`);
    await expect(previous).toBeDisabled();
    await expect(pageSelect.locator('option')).toHaveText(['1', '2', '3']);
    await pageSelect.selectOption('3');
    await expect(page).toHaveURL(/page=3/);
    await expect(next).toBeDisabled();
    const lastPageCall = calls.find(call => call.method === 'GET' && call.path === '/api/v1/applications/' && new URL(call.search, 'http://fixture').searchParams.get('page') === '3')!;
    const lastPageParams = new URL(lastPageCall.search, 'http://fixture').searchParams;
    expect(lastPageParams.get('page_size')).toBe('50');
    expect(lastPageParams.get('search')).toBe('边界状态');
    expect(lastPageParams.get('application_status')).toBe('assessment');
    expect(lastPageParams.get('application_time_after')).toBe('2026-10-01T00:00:00+08:00');
    expect(lastPageParams.get('application_time_before')).toBe('2026-10-31T23:59:59+08:00');
    expect(lastPageParams.get('ordering')).toBe('-updated_at');

    await page.goto(`/applications?page=999&${sharedQuery}`);
    await expect(page).toHaveURL(/page=3/);
    const normalizedLastUrl = new URL(page.url());
    expect(normalizedLastUrl.searchParams.get('pageSize') ?? normalizedLastUrl.searchParams.get('page_size')).toBe('50');
    expect(normalizedLastUrl.searchParams.get('search')).toBe('边界状态');
    expect(normalizedLastUrl.searchParams.get('applicationStatus') ?? normalizedLastUrl.searchParams.get('application_status')).toBe('assessment');
    expect(normalizedLastUrl.searchParams.get('applicationTimeAfter') ?? normalizedLastUrl.searchParams.get('application_time_after')).toBe('2026-10-01T00:00:00+08:00');
    expect(normalizedLastUrl.searchParams.get('applicationTimeBefore') ?? normalizedLastUrl.searchParams.get('application_time_before')).toBe('2026-10-31T23:59:59+08:00');
    expect(normalizedLastUrl.searchParams.get('ordering')).toBe('-updated_at');

    await page.goto(`/applications?page=999&${sharedQuery.replace('边界状态', '无数据')}`);
    await expect(page).toHaveURL(/page=1/);
    await expect(page.getByText(publicCompany, { exact: true })).toHaveCount(0);
    await expect(previous).toBeDisabled();
    await expect(next).toBeDisabled();
    await expect(pageSelect).toBeDisabled();
    await expect(page.getByRole('spinbutton', { name: /页码/ })).toBeDisabled();
    const emptyUrl = new URL(page.url());
    expect(emptyUrl.searchParams.get('pageSize') ?? emptyUrl.searchParams.get('page_size')).toBe('50');
    expect(emptyUrl.searchParams.get('search')).toBe('无数据');
    expect(emptyUrl.searchParams.get('applicationStatus') ?? emptyUrl.searchParams.get('application_status')).toBe('assessment');
    expect(emptyUrl.searchParams.get('applicationTimeAfter') ?? emptyUrl.searchParams.get('application_time_after')).toBe('2026-10-01T00:00:00+08:00');
    expect(emptyUrl.searchParams.get('applicationTimeBefore') ?? emptyUrl.searchParams.get('application_time_before')).toBe('2026-10-31T23:59:59+08:00');
    expect(emptyUrl.searchParams.get('ordering')).toBe('-updated_at');
  });
});
