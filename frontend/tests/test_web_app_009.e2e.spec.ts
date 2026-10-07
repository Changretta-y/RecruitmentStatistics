import { expect, test, type Page, type Route } from '@playwright/test';
import { createHash } from 'node:crypto';

const USER = { id: 909, username: 'web_app_009', email: 'logo@example.invalid' };
const PROVIDED_LOGO_SHA256 = '9c0420fd9643705bd36a1c9e8e5c4d80b5fe100ea5b22492bb1301abba610403';
const sha256 = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function syntheticLogin(page: Page) {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/login/') && route.request().method() === 'POST') {
      return json(route, 200, { access: 'logo-test-access', refresh: 'logo-test-refresh', user: USER });
    }
    if (path.endsWith('/auth/me/') && route.request().method() === 'GET') return json(route, 200, USER);
    if (path.endsWith('/applications/') && route.request().method() === 'GET') {
      return json(route, 200, { count: 0, page: 1, page_size: 20, total_pages: 1, results: [] });
    }
    return json(route, 404, { code: 'NOT_FOUND' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(USER.username);
  await page.locator('input[name="password"]').fill('Logo_test_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
}

test.describe('WEB-APP-009 public project logo', () => {
  test('authenticated shell and project title remain available', async ({ page }) => {
    await syntheticLogin(page);
    await expect(page.getByText('我的投递进度', { exact: true }).filter({ visible: true }).first()).toBeVisible();
  });

  test('document favicon links to a same-origin browser-decodable image', async ({ page }) => {
    await page.goto('/login');
    const icon = page.locator('link[rel~="icon"]').first();
    await expect(icon).toHaveAttribute('href', /\S/);
    const iconUrl = new URL((await icon.getAttribute('href'))!, page.url());
    expect(iconUrl.origin).toBe(new URL(page.url()).origin);
    const response = await page.request.get(iconUrl.toString());
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toMatch(/^image\//);
    expect(sha256(await response.body()), 'favicon uses the user-provided image bytes').toBe(PROVIDED_LOGO_SHA256);
    const decoded = await page.evaluate(async src => {
      const image = new Image();
      image.src = src;
      try { await image.decode(); return image.naturalWidth > 0 && image.naturalHeight > 0; }
      catch { return false; }
    }, iconUrl.toString());
    expect(decoded, 'favicon resource is a real browser-decodable image').toBe(true);
  });

  test('sidebar brand uses an accessible image as its leading logo', async ({ page }) => {
    await syntheticLogin(page);
    const brand = page.getByText('我的投递进度', { exact: true }).filter({ visible: true }).first();
    const brandBox = await brand.boundingBox();
    expect(brandBox).not.toBeNull();
    const images = page.getByRole('img');
    let logo: { alt: string; src: string } | null = null;
    for (let index = 0; index < await images.count(); index++) {
      const image = images.nth(index);
      const box = await image.boundingBox();
      if (!box || !brandBox) continue;
      const horizontallyLeading = box.x < brandBox.x && box.x < 280;
      const aligned = Math.abs(box.y + box.height / 2 - (brandBox.y + brandBox.height / 2)) < 28;
      if (horizontallyLeading && aligned) {
        logo = { alt: (await image.getAttribute('alt')) ?? '', src: (await image.getAttribute('src')) ?? '' };
        break;
      }
    }
    expect(logo, 'sidebar brand has a visible image before its name').not.toBeNull();
    expect(logo!.alt.trim(), 'logo exposes a meaningful accessible name').not.toBe('');
    const logoUrl = new URL(logo!.src, page.url());
    const response = await page.request.get(logoUrl.toString());
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toMatch(/^image\//);
    expect(sha256(await response.body()), 'sidebar uses the user-provided image bytes').toBe(PROVIDED_LOGO_SHA256);
  });
});
