import { expect, test, type Page, type Route } from "@playwright/test";

const USER = { id: 981, username: "calendar_navigation_user", email: "nav@example.com" };

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockAuthenticatedApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/login/") && request.method() === "POST") {
      return json(route, 200, { access: "nav-test-access", refresh: "nav-test-refresh" });
    }
    if (path.endsWith("/auth/me/") && request.method() === "GET") return json(route, 200, USER);
    if (path.endsWith("/auth/refresh/") && request.method() === "POST") {
      return json(route, 401, { code: "TOKEN_EXPIRED" });
    }
    if (path.endsWith("/applications/") && request.method() === "GET") {
      return json(route, 200, { count: 0, page: 1, page_size: 20, results: [] });
    }
    if (path.endsWith("/calendar/events/") && request.method() === "GET") {
      return json(route, 200, { timezone: "Asia/Shanghai", start: "2026-09-28", end: "2026-11-02", events: [] });
    }
    return json(route, 404, { code: "NOT_FOUND" });
  });
}

async function signIn(page: Page) {
  await page.goto("/login");
  await page.locator('input[name="username"]').fill(USER.username);
  await page.locator('input[name="password"]').fill("Navigation_test_123");
  await page.getByRole("button", { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
}

async function expectSharedNavigation(page: Page) {
  const applications = page.locator('a[href="/applications"]').filter({ hasText: /投递/ }).first();
  const calendar = page.getByRole("link", { name: "日历", exact: true });
  await expect(applications).toBeVisible();
  await expect(applications).toHaveAttribute("href", "/applications");
  await expect(applications).toContainText("投递");
  await expect(calendar).toBeVisible();
  await expect(calendar).toHaveAttribute("href", "/calendar");
  return applications;
}

async function openNavigationIfCollapsed(page: Page) {
  const openButton = page.getByRole("button", { name: "打开导航", exact: true });
  if (await openButton.isVisible().catch(() => false)) await openButton.click();
}

test.describe("WEB-NAV-001 authenticated calendar navigation", () => {
  test.beforeEach(async ({ page }) => mockAuthenticatedApi(page));

  test("retains the shared navigation when entering the calendar from applications and returns to the application list", async ({ page }) => {
    await signIn(page);
    await openNavigationIfCollapsed(page);
    await expectSharedNavigation(page);

    await page.getByRole("link", { name: "日历", exact: true }).click();
    await expect(page).toHaveURL(/\/calendar(?:[/?#]|$)/);
    const applications = await expectSharedNavigation(page);
    await expect(page.getByText(/周视图|月视图|日历/).first()).toBeVisible();

    await applications.click();
    await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
    await expect(page.getByRole("heading", { name: /投递进度/ })).toBeVisible();
  });

  test("shows the same navigation and calendar content after directly opening the calendar route", async ({ page }) => {
    await signIn(page);
    await openNavigationIfCollapsed(page);
    await page.goto("/calendar");

    await expect(page).toHaveURL(/\/calendar(?:[/?#]|$)/);
    await expectSharedNavigation(page);
    await expect(page.getByText(/周视图|月视图|日历/).first()).toBeVisible();
  });
});
