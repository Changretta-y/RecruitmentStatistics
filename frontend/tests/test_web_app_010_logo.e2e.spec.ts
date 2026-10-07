import { expect, test, type Page, type Route } from '@playwright/test';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';

const NEW_LOGO_SHA256 = 'a09c7876116515619ac4a2ed0293ade91077627a446329458ced6b9515d79e88';
const OLD_LOGO_SHA256 = '9c0420fd9643705bd36a1c9e8e5c4d80b5fe100ea5b22492bb1301abba610403';
const sha256 = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const user = { id: 1010, username: 'logo_replace_test', email: 'logo-replace@example.invalid' };

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function login(page: Page) {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/login/') && route.request().method() === 'POST') {
      return json(route, 200, { access: 'new-logo-access', refresh: 'new-logo-refresh', user });
    }
    if (path.endsWith('/auth/me/') && route.request().method() === 'GET') return json(route, 200, user);
    if (path.endsWith('/applications/') && route.request().method() === 'GET') {
      return json(route, 200, { count: 0, page: 1, page_size: 20, total_pages: 1, results: [] });
    }
    if (path.endsWith('/calendar/events/') && route.request().method() === 'GET') {
      return json(route, 200, { timezone: 'Asia/Shanghai', start: '2026-09-28', end: '2026-11-02', events: [] });
    }
    return json(route, 404, { code: 'NOT_FOUND' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(user.username);
  await page.locator('input[name="password"]').fill('Synthetic_Logo_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
}

test.describe('WEB-APP-010 supplied logo replacement', () => {
  test('existing login and navigation remain available', async ({ page }) => {
    await login(page);
    await expect(page.getByText('我的投递进度', { exact: true }).filter({ visible: true }).first()).toBeVisible();
    await page.locator('a[href="/calendar"]').first().click();
    await expect(page).toHaveURL(/\/calendar(?:[/?#]|$)/);
    await page.locator('a[href="/applications"]').first().click();
    await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  });

  test('favicon keeps /logo.png and serves the new unmodified supplied bytes', async ({ page }) => {
    await page.goto('/login');
    const favicon = page.locator('link[rel~="icon"]').first();
    await expect(favicon).toHaveAttribute('href', '/logo.png');
    const response = await page.request.get('/logo.png');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toMatch(/^image\/png/);
    const hash = sha256(await response.body());
    expect(hash, 'favicon must replace the old image, not retain it').not.toBe(OLD_LOGO_SHA256);
    expect(hash, 'favicon bytes match the new user attachment').toBe(NEW_LOGO_SHA256);
    expect(await page.evaluate(async () => {
      const image = new Image();
      image.src = '/logo.png';
      try { await image.decode(); return image.naturalWidth > 0 && image.naturalHeight > 0; }
      catch { return false; }
    })).toBe(true);
  });

  test('sidebar brand keeps accessible /logo.png image with the new bytes', async ({ page }) => {
    await login(page);
    const brand = page.getByText('我的投递进度', { exact: true }).filter({ visible: true }).first();
    const brandBox = await brand.boundingBox();
    const image = page.locator('img[src="/logo.png"]').first();
    await expect(image).toBeVisible();
    const imageBox = await image.boundingBox();
    expect(brandBox).not.toBeNull();
    expect(imageBox).not.toBeNull();
    expect(imageBox!.x).toBeLessThan(brandBox!.x);
    expect(Math.abs(imageBox!.y + imageBox!.height / 2 - (brandBox!.y + brandBox!.height / 2))).toBeLessThan(28);
    expect(((await image.getAttribute('alt')) ?? '').trim()).not.toBe('');
    const response = await page.request.get('/logo.png');
    expect(response.status()).toBe(200);
    const hash = sha256(await response.body());
    expect(hash, 'brand image must replace the old image, not retain it').not.toBe(OLD_LOGO_SHA256);
    expect(hash, 'brand image bytes match the new user attachment').toBe(NEW_LOGO_SHA256);
    await page.waitForTimeout(450);
    await page.screenshot({ path: resolve(process.cwd(), '../docs/test-reports/WEB-APP-010-brand.png'), fullPage: false });
  });
});
