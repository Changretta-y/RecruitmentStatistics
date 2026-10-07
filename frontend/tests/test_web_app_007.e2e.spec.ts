import { expect, test, type Page } from '@playwright/test';
import { resolve } from 'node:path';
import { companyHttpFixture } from './web_app_006_http_fixture';

const companyName = '多岗位示例科技';
const firstPosition = '后端工程师';
const secondPosition = '前端工程师';
const companyRow = (page: Page) => page.getByRole('row').filter({ hasText: companyName });
const positionRow = (page: Page, name: string) => page.getByText(name, { exact: true }).filter({ visible: true }).first().locator('xpath=ancestor::tr[1]');
const screenshot = (name: string) => resolve(process.cwd(), '../docs/test-reports', `WEB-APP-007-desktop-${name}.png`);

test.describe('WEB-APP-007 desktop position rows', () => {
  test('baseline reads one company with two nested positions from public HTTP', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await expect(companyRow(page)).toHaveCount(1);
    expect(state.records[0].positions.map((position: { position_name: string }) => position.position_name)).toEqual([firstPosition, secondPosition]);
    expect(state.calls.some(call => call.method === 'GET' && call.path === '/api/v1/applications/')).toBe(true);
  });

  test('single-position company shows its horizontal position row by default', async ({ page }) => {
    const state = await companyHttpFixture(page);
    state.records[0].positions = state.records[0].positions.slice(0, 1);
    await page.reload();
    await expect(companyRow(page)).toHaveCount(1);
    const row = positionRow(page, firstPosition);
    await expect(row).toHaveCount(1);
    await expect(row).toBeVisible();
    const box = await row.boundingBox();
    expect(box?.width, 'desktop position occupies a horizontal table row').toBeGreaterThan(700);
    expect(box?.height, 'desktop position is a compact row rather than a vertical card').toBeLessThan(160);
  });

  test('multi-position company defaults to its first row only', async ({ page }) => {
    await companyHttpFixture(page);
    const first = positionRow(page, firstPosition);
    const second = positionRow(page, secondPosition);
    await expect(first).toHaveCount(1);
    await expect(first).toBeVisible();
    await expect(second).toHaveCount(0);
    await page.waitForTimeout(450);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: screenshot('default'), fullPage: true });
  });

  test('keyboard expansion shows every position in a distinct compact horizontal row and folds again', async ({ page }) => {
    await companyHttpFixture(page);
    const first = positionRow(page, firstPosition);
    const second = positionRow(page, secondPosition);
    const expand = companyRow(page).locator('button[aria-expanded]');
    await expect(expand).toHaveAttribute('aria-expanded', 'false');
    const controlledId = await expand.getAttribute('aria-controls');
    expect(controlledId, 'expand button names its controlled content').toBeTruthy();
    await expand.focus();
    await page.keyboard.press('Enter');
    await expect(expand).toHaveAttribute('aria-expanded', 'true');
    await expect(second).toHaveCount(1);
    await expect(second).toBeVisible();
    await expect(first).not.toContainText(secondPosition);
    const firstBox = await first.boundingBox();
    const secondBox = await second.boundingBox();
    expect(firstBox?.height).toBeLessThan(160);
    expect(secondBox?.height).toBeLessThan(160);
    expect(secondBox!.y).toBeGreaterThan(firstBox!.y);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: screenshot('expanded'), fullPage: true });
    await expand.focus();
    await page.keyboard.press('Space');
    await expect(expand).toHaveAttribute('aria-expanded', 'false');
    await expect(second).toHaveCount(0);
    await expect(first).toBeVisible();
  });

  test('company-level shared stages occur once and toggling only changes local visibility', async ({ page }) => {
    const state = await companyHttpFixture(page);
    const originalUrl = page.url();
    const expand = companyRow(page).locator('button[aria-expanded]');
    const initialCalls = state.calls.length;
    const sharedStageLabels = page.getByText('测评', { exact: true }).filter({ visible: true });
    const initialVisibleCount = await sharedStageLabels.count();
    expect(initialVisibleCount).toBeGreaterThan(0);
    await expand.click();
    await expect(sharedStageLabels).toHaveCount(initialVisibleCount + 1);
    await expand.click();
    await expect(sharedStageLabels).toHaveCount(initialVisibleCount);
    expect(page.url()).toBe(originalUrl);
    expect(state.records[0].shared_stages).toHaveLength(3);
    expect(state.calls.slice(initialCalls).filter(call => ['POST', 'PATCH', 'DELETE'].includes(call.method))).toEqual([]);
    await expect(page.getByText('第 1 页 / 3 页')).toBeVisible();
  });
});
