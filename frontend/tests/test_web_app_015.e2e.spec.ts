import { expect, test, type Page, type Route } from '@playwright/test';

// WEB-APP-015 black-box UI/HTTP tests. No production imports.
const user = { id: 1500, username: 'web015-user', email: 'web015@example.invalid' };
const date = '2026-10-15T02:00:00Z';
const longContent = '长提示词内容-' + 'A'.repeat(220);
const records = [
  { id: 1501, title: '短提示词', content: '短内容', is_preset: false, created_at: date, updated_at: date },
  { id: 1502, title: '长提示词', content: longContent, is_preset: true, created_at: date, updated_at: date },
];

type ClipboardMode = 'normal' | 'missing-fallback' | 'reject-fallback' | 'double-failure';
type Call = { method: string; path: string; search: string; body: any };

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, mode: ClipboardMode = 'normal') {
  const calls: Call[] = [];
  if (mode !== 'normal') {
    await page.addInitScript((clipboardMode) => {
      if (clipboardMode === 'missing-fallback') {
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
        (document as any).execCommand = (command: string) => command === 'copy';
      } else if (clipboardMode === 'reject-fallback') {
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('denied'); } } });
        (document as any).execCommand = (command: string) => command === 'copy';
      } else {
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('denied'); } } });
        (document as any).execCommand = () => false;
      }
    }, mode);
  }
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let body: any = undefined;
    try { body = request.postDataJSON(); } catch { /* GET/DELETE have no body. */ }
    calls.push({ method: request.method(), path: url.pathname, search: url.search, body });
    if (request.method() === 'POST' && url.pathname === '/api/v1/auth/login/') {
      return json(route, 200, { access: 'web015-access', refresh: 'web015-refresh', user });
    }
    if (request.method() === 'GET' && url.pathname === '/api/v1/auth/me/') return json(route, 200, user);
    if (request.method() === 'GET' && url.pathname === '/api/v1/prompts/') {
      const search = (url.searchParams.get('search') ?? '').toLocaleLowerCase();
      const results = search ? records.filter((item) => `${item.title} ${item.content}`.toLocaleLowerCase().includes(search)) : records;
      return json(route, 200, { count: results.length, page: 1, page_size: 20, total_pages: 1, next: null, previous: null, results });
    }
    return json(route, 404, { code: 'NOT_FOUND', message: '未找到' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(user.username);
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await page.goto('/prompts');
  await expect(page.getByText('长提示词', { exact: true })).toBeVisible();
  return { calls };
}

const copyButton = (page: Page) => page.getByRole('button', { name: /复制/ }).first();


test('missing Clipboard API falls back to page copy and reports success', async ({ page }) => {
  await setup(page, 'missing-fallback');
  await page.getByText('短提示词', { exact: true }).click();
  await copyButton(page).click();
  await expect(page.getByText(/复制成功|已复制/)).toBeVisible();
});

test('rejected Clipboard API falls back to page copy and reports success', async ({ page }) => {
  await setup(page, 'reject-fallback');
  await page.getByText('短提示词', { exact: true }).click();
  await copyButton(page).click();
  await expect(page.getByText(/复制成功|已复制/)).toBeVisible();
});

test('when modern API and fallback both fail, failure is visible and record remains', async ({ page }) => {
  await setup(page, 'double-failure');
  await page.getByText('短提示词', { exact: true }).click();
  await copyButton(page).click();
  await expect(page.getByText(/复制失败|剪贴板|无法复制/)).toBeVisible();
  await expect(page.getByText('短提示词', { exact: true })).toBeVisible();
  await expect(page.getByText('短内容', { exact: true })).toBeVisible();
  await expect(page.getByText(/复制成功|已复制/)).toHaveCount(0);
});

test('long prompt cards show a bounded ellipsis preview without full content', async ({ page }) => {
  await setup(page);
  const bodyText = await page.locator('body').innerText();
  expect(bodyText).not.toContain(longContent);
  expect(bodyText).toContain('…');
  const previewLines = bodyText.split('\n').filter((line) => line.includes('AAAA'));
  expect(previewLines.length).toBeGreaterThan(0);
  expect(Math.max(...previewLines.map((line) => line.length))).toBeLessThanOrEqual(160);
});

test('clicking a prompt opens full details and closing returns to the bounded list', async ({ page }) => {
  await setup(page);
  await page.getByText('长提示词', { exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('长提示词');
  await expect(page.getByRole('dialog')).toContainText(longContent);
  await page.getByRole('dialog').getByRole('button', { name: /关闭|返回/ }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  expect(await page.locator('body').innerText()).not.toContain(longContent);
});
