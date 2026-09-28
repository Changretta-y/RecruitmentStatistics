import { expect, test, type Page, type Route } from "@playwright/test";

const USER = { id: 982, username: "application_navigation_user", email: "nav002@example.com" };

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function mockAuthenticatedApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/auth/login/") && request.method() === "POST") {
      return json(route, 200, { access: "nav002-test-access", refresh: "nav002-test-refresh" });
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
  const applications = page.getByRole("link", { name: /我的投递进度|投递/ }).first();
  await expect(applications).toBeVisible();
  await expect(applications).toHaveAttribute("href", "/applications");
  await expect(page.getByRole("link", { name: "日历", exact: true })).toBeVisible();
  return applications;
}

test.describe("WEB-NAV-002 sidebar controls and create application layout", () => {
  test.beforeEach(async ({ page }) => mockAuthenticatedApi(page));

  test("allows a desktop user to collapse and restore the sidebar while keeping page content available", async ({ page }) => {
    await signIn(page);
    await expect(page.getByRole("heading", { name: /投递进度/ })).toBeVisible();
    await expectSharedNavigation(page);

    const collapseButton = page.getByRole("button", { name: "收起侧边栏", exact: true });
    await expect(collapseButton).toBeVisible();
    await collapseButton.click();
    await expect(page.getByRole("link", { name: "日历", exact: true })).toBeHidden();
    await expect(page.getByRole("heading", { name: /投递进度/ })).toBeVisible();

    await page.getByRole("button", { name: "展开侧边栏", exact: true }).click();
    await expectSharedNavigation(page);
    await expect(page.getByRole("heading", { name: /投递进度/ })).toBeVisible();
  });

  test("directly opening the create route shows shared navigation and the application form", async ({ page }) => {
    await signIn(page);
    await page.goto("/applications/new");

    await expect(page).toHaveURL(/\/applications\/new(?:[/?#]|$)/);
    await expect(page.getByText("新增投递记录", { exact: true })).toBeVisible();
    await expect(page.getByRole("textbox").first()).toBeVisible();
    const applications = await expectSharedNavigation(page);
    await applications.click();
    await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  });

  test("entering the create route from the application list preserves navigation and allows returning", async ({ page }) => {
    await signIn(page);
    await expectSharedNavigation(page);
    await page.getByRole("main").getByRole("link", { name: /新增投递/ }).first().click();

    await expect(page).toHaveURL(/\/applications\/new(?:[/?#]|$)/);
    await expect(page.getByText("新增投递记录", { exact: true })).toBeVisible();
    await expect(page.getByRole("textbox").first()).toBeVisible();
    const applications = await expectSharedNavigation(page);
    await applications.click();
    await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
    await expect(page.getByRole("heading", { name: /投递进度/ })).toBeVisible();
  });

  test("keeps the narrow-screen navigation drawer available", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await signIn(page);

    const openNavigation = page.getByRole("button", { name: "打开导航", exact: true });
    await expect(openNavigation).toBeVisible();
    await openNavigation.click();
    await expectSharedNavigation(page);

    await page.getByRole("link", { name: "日历", exact: true }).click();
    await expect(page).toHaveURL(/\/calendar(?:[/?#]|$)/);
    await expect(page.getByText(/周视图|月视图|日历/).first()).toBeVisible();
  });
});
