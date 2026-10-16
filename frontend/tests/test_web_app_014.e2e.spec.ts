import { expect, test, type Page, type Route } from '@playwright/test';

// WEB-APP-014 black-box UI/HTTP tests. No production imports.
const user = { id: 1400, username: 'web014-user', email: 'web014@example.invalid' };
const date = '2026-10-14T02:00:00Z';
const seedPrompts = [
  { id: 1401, title: '自我介绍', content: '请用 STAR 结构介绍自己', is_preset: true, created_at: date, updated_at: date },
  { id: 1402, title: '项目经历深挖', content: '请追问项目中的技术决策', is_preset: true, created_at: date, updated_at: date },
  { id: 1403, title: '行为面试 STAR', content: '请围绕冲突和结果提问', is_preset: true, created_at: date, updated_at: date },
  { id: 1404, title: '我的自定义提示', content: '自定义内容', is_preset: false, created_at: date, updated_at: date },
];

type Call = { method: string; path: string; search: string; body: any };

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, options: { promptsStatus?: number; clipboardFailure?: boolean } = {}) {
  const calls: Call[] = [];
  let prompts = seedPrompts.map((item) => ({ ...item }));
  if (options.clipboardFailure) {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: { writeText: async () => { throw new Error('clipboard unavailable'); } },
      });
    });
  }
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let body: any = undefined;
    try { body = request.postDataJSON(); } catch { /* GET/DELETE have no JSON body. */ }
    calls.push({ method: request.method(), path: url.pathname, search: url.search, body });
    if (request.method() === 'POST' && url.pathname === '/api/v1/auth/login/') {
      return json(route, 200, { access: 'web014-access', refresh: 'web014-refresh', user });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/auth/me/') return json(route, 200, user);
    if (request.method() === 'GET' && url.pathname === '/api/v1/prompts/') {
      if (options.promptsStatus) return json(route, options.promptsStatus, { code: 'PROMPTS_UNAVAILABLE', message: '提示词加载失败' });
      const search = (url.searchParams.get('search') ?? '').toLocaleLowerCase();
      const results = search ? prompts.filter((item) => `${item.title} ${item.content}`.toLocaleLowerCase().includes(search)) : prompts;
      return json(route, 200, { count: results.length, page: 1, page_size: 20, total_pages: 1, next: null, previous: null, results });
    }
    if (request.method() === 'POST' && url.pathname === '/api/v1/prompts/') {
      const created = { id: 1499, ...body, is_preset: false, created_at: date, updated_at: date };
      prompts = [...prompts, created];
      return json(route, 201, created);
    }
    const match = url.pathname.match(/^\/api\/v1\/prompts\/(\d+)\/$/);
    if (match) {
      const id = Number(match[1]);
      const index = prompts.findIndex((item) => item.id === id);
      if (index < 0) return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
      if (request.method() === 'PATCH') {
        prompts[index] = { ...prompts[index], ...body, updated_at: date };
        return json(route, 200, prompts[index]);
      }
      if (request.method() === 'DELETE') {
        prompts = prompts.filter((item) => item.id !== id);
        return route.fulfill({ status: 204, body: '' });
      }
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(user.username);
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  return { calls };
}

const promptTitle = (page: Page, title: string) => page.getByText(title, { exact: true });
const action = (page: Page, name: RegExp) => page.getByRole('button', { name }).first();


test('prompts route is protected and navigation entry opens the prompt page', async ({ page }) => {
  await page.goto('/prompts');
  await expect(page).toHaveURL(/login/);
  await setup(page);
  const nav = page.locator('a').filter({ hasText: /提示词管理/ }).first();
  await expect(nav).toBeVisible();
  await nav.click();
  await expect(page).toHaveURL(/\/prompts(?:[/?#]|$)/);
  await expect(promptTitle(page, '自我介绍')).toBeVisible();
});

test('search filters current user prompts and shows an explicit empty state', async ({ page }) => {
  const { calls } = await setup(page);
  await page.goto('/prompts');
  const search = page.locator('input[placeholder*="搜索"], input[aria-label*="搜索"], input[name="search"]').first();
  await expect(search).toBeVisible();
  await search.fill('自定义');
  await expect.poll(() => calls.some((call) => call.method === 'GET' && call.path === '/api/v1/prompts/' && call.search.includes('search='))).toBe(true);
  await expect(promptTitle(page, '我的自定义提示')).toBeVisible();
  await search.fill('不存在的词');
  await expect(page.getByText(/没有提示词|暂无提示词|无结果|未找到/)).toBeVisible();
});

test('copy invokes clipboard and reports success without changing the record', async ({ page }) => {
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
  await setup(page);
  await page.goto('/prompts');
  await promptTitle(page, '自我介绍').click();
  await action(page, /复制/).click();
  await expect(page.getByText(/复制成功|已复制/)).toBeVisible();
  await expect.poll(async () => page.evaluate(() => navigator.clipboard.readText())).toBe('请用 STAR 结构介绍自己');
  await expect(promptTitle(page, '自我介绍')).toBeVisible();
});

test('clipboard failure shows an error and leaves the prompt intact', async ({ page }) => {
  await setup(page, { clipboardFailure: true });
  await page.goto('/prompts');
  await promptTitle(page, '自我介绍').click();
  await action(page, /复制/).click();
  await expect(page.getByText(/复制失败|剪贴板|无法复制/)).toBeVisible();
  await expect(promptTitle(page, '自我介绍')).toBeVisible();
});

test('new prompt validates required fields, posts, and refreshes the list', async ({ page }) => {
  const { calls } = await setup(page);
  await page.goto('/prompts');
  await page.getByRole('button', { name: /新增提示词|新建提示词/ }).click();
  await page.getByRole('button', { name: /保存|提交/ }).click();
  await expect(page.getByText(/必填|不能为空/)).toBeVisible();
  await page.getByLabel(/标题/).fill('新增提示词');
  await page.getByLabel(/内容/).fill('新增内容');
  await page.getByRole('button', { name: /保存|提交/ }).click();
  await expect.poll(() => calls.some((call) => call.method === 'POST' && call.path === '/api/v1/prompts/')).toBe(true);
  await expect(promptTitle(page, '新增提示词')).toBeVisible();
});

test('edit reuses the form and sends a PATCH before refreshing', async ({ page }) => {
  const { calls } = await setup(page);
  await page.goto('/prompts');
  await promptTitle(page, '我的自定义提示').click();
  await action(page, /编辑/).click();
  await page.getByLabel(/内容/).fill('编辑后的内容');
  await page.getByRole('button', { name: /保存|提交/ }).click();
  await expect.poll(() => calls.some((call) => call.method === 'PATCH' && call.path === '/api/v1/prompts/1404/')).toBe(true);
  await expect(promptTitle(page, '我的自定义提示')).toBeVisible();
});

test('delete requires confirmation; cancel does not request, confirm removes the item', async ({ page }) => {
  const { calls } = await setup(page);
  await page.goto('/prompts');
  await promptTitle(page, '我的自定义提示').click();
  await action(page, /删除/).click();
  await expect(page.getByText(/确认删除|确定删除/)).toBeVisible();
  await page.getByRole('button', { name: /取消/ }).click();
  expect(calls.some((call) => call.method === 'DELETE')).toBe(false);
  await action(page, /删除/).click();
  await page.getByRole('button', { name: /确认删除|确定/ }).click();
  await expect.poll(() => calls.some((call) => call.method === 'DELETE' && call.path === '/api/v1/prompts/1404/')).toBe(true);
  await expect(promptTitle(page, '我的自定义提示')).toHaveCount(0);
});

test('API error is visible instead of silently rendering an empty list', async ({ page }) => {
  await setup(page, { promptsStatus: 503 });
  await page.goto('/prompts');
  await expect(page.getByText(/加载失败|错误|重试/)).toBeVisible();
});
