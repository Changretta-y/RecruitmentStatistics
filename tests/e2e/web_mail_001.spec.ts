import { expect, test, type Page, type Route } from "@playwright/test";

const API = "**/api/v1/";
const MOCK_USER = { id: 801, username: "mail_ui_user", email: "login@example.com" };
const INITIAL_SETTINGS = {
  recipient_email: "schedule@example.com",
  daily_time: "08:15",
  enabled: true,
  verified: true,
  timezone: "Asia/Shanghai",
  last_delivery: { date: "2026-09-24", status: "unknown" },
};

type Settings = typeof INITIAL_SETTINGS;

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installApiMocks(page: Page, options: {
  settings?: Settings;
  patchStatus?: number;
  patchError?: unknown;
  verificationStatus?: number;
  verifyStatus?: number;
  failSettingsNetwork?: boolean;
  failPatchNetwork?: boolean;
  patchDelayMs?: number;
} = {}) {
  let settings = structuredClone(options.settings ?? INITIAL_SETTINGS);
  const calls: Array<{ method: string; path: string; body?: any }> = [];

  await page.route(`${API}**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    let body: any;
    try { body = request.postDataJSON(); } catch { body = undefined; }
    calls.push({ method, path, body });

    if (path.endsWith("/auth/login/") && method === "POST") {
      return json(route, 200, { access: "mock-access", refresh: "mock-refresh" });
    }
    if (path.endsWith("/auth/me/") && method === "GET") return json(route, 200, MOCK_USER);
    if (path.endsWith("/applications/") && method === "GET") return json(route, 200, { count: 0, results: [] });
    if (path.endsWith("/notification-settings/") && method === "GET") {
      if (options.failSettingsNetwork) return route.abort("failed");
      return json(route, 200, settings);
    }
    if (path.endsWith("/notification-settings/") && method === "PATCH") {
      if (options.failPatchNetwork) return route.abort("failed");
      if (options.patchDelayMs) await new Promise((resolve) => setTimeout(resolve, options.patchDelayMs));
      if (options.patchStatus && options.patchStatus !== 200) {
        return json(route, options.patchStatus, options.patchError ?? { code: "VALIDATION_ERROR", details: {} });
      }
      settings = { ...settings, ...body };
      if (Object.hasOwn(body ?? {}, "recipient_email") && body.recipient_email !== options.settings?.recipient_email && body.recipient_email !== INITIAL_SETTINGS.recipient_email) {
        settings.verified = false;
        settings.enabled = false;
      }
      return json(route, 200, settings);
    }
    if (path.endsWith("/notification-settings/verification/") && method === "POST") {
      return json(route, options.verificationStatus ?? 202, options.verificationStatus === 429 ? { code: "RATE_LIMITED" } : { detail: "验证邮件已发送" });
    }
    if (path.endsWith("/notification-settings/verify/") && method === "POST") {
      return json(route, options.verifyStatus ?? 200, options.verifyStatus === 200 ? { ...settings, verified: true } : { code: "INVALID_TOKEN" });
    }
    if (path.endsWith("/auth/refresh/") && method === "POST") return json(route, 401, { code: "TOKEN_EXPIRED" });
    return json(route, 404, { code: "NOT_FOUND" });
  });
  return { calls, get settings() { return settings; } };
}

async function login(page: Page) {
  await page.goto("/login");
  const username = page.locator('input[name="username"]');
  const password = page.locator('input[name="password"]');
  await username.fill(MOCK_USER.username);
  await password.fill("Test_password_123");
  await page.getByRole("button", { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/applications/);
}

async function enterSettings(page: Page) {
  const settingsLink = page.locator('a[href*="notification-settings"]').first();
  const accountMenu = page.getByRole("button", { name: /账号|用户|个人中心/i }).first();
  if (!(await settingsLink.isVisible().catch(() => false)) && await accountMenu.count()) {
    await accountMenu.click();
  }
  await expect(settingsLink).toBeVisible();
  await settingsLink.click();
  await expect(page).toHaveURL(/notification-settings/);
}

async function field(page: Page, label: RegExp) {
  return page.getByLabel(label).first();
}

test.describe("WEB-MAIL-001 notification settings page", () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(4_000);
  });

  test("navigation shows the signed-in user's settings, Beijing timezone, and unknown delivery status", async ({ page }) => {
    const api = await installApiMocks(page, {
      settings: { ...INITIAL_SETTINGS, last_delivery: { date: "2026-09-24", status: "unknown" } },
    });
    await login(page);
    await enterSettings(page);

    await expect(await field(page, /收件邮箱|接收邮箱/i)).toHaveValue("schedule@example.com");
    await expect(await field(page, /每日.*时间|推送时间/i)).toHaveValue("08:15");
    await expect(page.getByText(/北京时间（Asia\/Shanghai）/)).toBeVisible();
    await expect(page.getByText("发送结果待核实")).toBeVisible();
    await expect(page.getByRole("checkbox", { name: /启用|每日邮件/ }).first()).toBeChecked();
    expect(api.calls.some((call) => call.path.endsWith("/notification-settings/") && call.method === "GET")).toBe(true);
  });

  test("saves only recipient and HH:mm time, marks a changed address unverified and disabled, then requests verification", async ({ page }) => {
    const api = await installApiMocks(page);
    await login(page);
    await enterSettings(page);

    await (await field(page, /收件邮箱|接收邮箱/i)).fill("new-address@example.com");
    await (await field(page, /每日.*时间|推送时间/i)).fill("19:45");
    await page.getByRole("button", { name: /保存/ }).click();
    await expect(page.getByText(/待验证|尚未验证/)).toBeVisible();
    await expect(page.getByText(/旧地址.*停用|原邮箱.*停用/)).toBeVisible();
    const toggle = page.getByRole("checkbox", { name: /启用|每日邮件/ }).first();
    await expect(toggle).toBeDisabled();

    await page.getByRole("button", { name: /发送验证邮件|发送验证/ }).click();
    await expect(page.getByText(/验证邮件已发送|已发送验证邮件/)).toBeVisible();
    expect(api.calls.some((call) => call.method === "PATCH" && call.body?.recipient_email === "new-address@example.com" && call.body?.daily_time === "19:45")).toBe(true);
    expect(api.calls.some((call) => call.path.endsWith("/notification-settings/verification/") && call.method === "POST")).toBe(true);
    await page.reload();
    await expect(await field(page, /收件邮箱|接收邮箱/i)).toHaveValue("new-address@example.com");
    await expect(await field(page, /每日.*时间|推送时间/i)).toHaveValue("19:45");
  });

  test("turns off an already verified notification and persists the disabled state", async ({ page }) => {
    const api = await installApiMocks(page);
    await login(page);
    await enterSettings(page);

    const toggle = page.getByRole("checkbox", { name: /启用|每日邮件/ }).first();
    await expect(toggle).toBeChecked();
    await toggle.uncheck();
    await page.getByRole("button", { name: /保存/ }).click();
    await expect(toggle).not.toBeChecked();
    expect(api.calls.some((call) => call.method === "PATCH" && call.body?.enabled === false)).toBe(true);
    await page.reload();
    await expect(page.getByRole("checkbox", { name: /启用|每日邮件/ }).first()).not.toBeChecked();
  });

  test("does not expose platform SMTP credentials or permit enabling incomplete or unverified settings", async ({ page }) => {
    await installApiMocks(page, { settings: { ...INITIAL_SETTINGS, recipient_email: "", daily_time: "", enabled: false, verified: false } });
    await login(page);
    await enterSettings(page);

    await expect(page.getByRole("textbox")).toHaveCount(2);
    await expect(page.getByLabel(/SMTP|发信账号|发信密码/i)).toHaveCount(0);
    await expect(page.getByText(/SMTP_HOST|EMAIL_HOST|smtp.*password/i)).toHaveCount(0);
    await expect(page.getByRole("checkbox", { name: /启用|每日邮件/ }).first()).toBeDisabled();
  });

  test("verifies a landing token after removing it from the address bar", async ({ page }) => {
    const api = await installApiMocks(page);
    let urlAtVerifyRequest = "";
    const thirdPartyRequestsWithTokenInUrl: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).origin !== "http://127.0.0.1:5173" && page.url().includes("single-use-secret-token")) {
        thirdPartyRequestsWithTokenInUrl.push(request.url());
      }
    });
    page.route("**/api/v1/notification-settings/verify/", async (route) => {
      urlAtVerifyRequest = page.url();
      const requestBody = route.request().postDataJSON();
      api.calls.push({ method: "POST", path: "/api/v1/notification-settings/verify/", body: requestBody });
      await json(route, 200, { ...INITIAL_SETTINGS, verified: true, enabled: false });
    });
    await login(page);
    await page.goto("/notification-settings/verify?token=single-use-secret-token");

    await expect(page).toHaveURL(/\/notification-settings\/verify$/);
    await expect(page.getByText(/邮箱已验证|验证成功/)).toBeVisible();
    expect(urlAtVerifyRequest).not.toContain("single-use-secret-token");
    expect(thirdPartyRequestsWithTokenInUrl).toEqual([]);
    expect(api.calls.filter((call) => call.path.endsWith("/notification-settings/verify/")).at(-1)?.body).toEqual({ token: "single-use-secret-token" });
  });

  test("prevents duplicate settings submissions while a save is in flight", async ({ page }) => {
    const api = await installApiMocks(page, { patchDelayMs: 700 });
    await login(page);
    await enterSettings(page);
    const save = page.getByRole("button", { name: /保存/ });
    await save.click();
    await expect(save).toBeDisabled();
    await expect.poll(() => api.calls.filter((call) => call.method === "PATCH").length).toBe(1);
  });

  test("maps 400, 429, 401, server, and network failures while retaining editable form values", async ({ page }) => {
    const api = await installApiMocks(page, {
      patchStatus: 400,
      patchError: { code: "VALIDATION_ERROR", details: { daily_time: ["请输入有效的 HH:mm 时间"] } },
    });
    await login(page);
    await enterSettings(page);

    const email = await field(page, /收件邮箱|接收邮箱/i);
    const time = await field(page, /每日.*时间|推送时间/i);
    await email.fill("keep-this@example.com");
    await time.fill("12:34");
    await page.getByRole("button", { name: /保存/ }).click();
    await expect(page.getByText(/HH:mm|有效时间/)).toBeVisible();
    await expect(email).toHaveValue("keep-this@example.com");
    await expect(time).toHaveValue("12:34");

    await page.unrouteAll({ behavior: "wait" });
    await installApiMocks(page, { verificationStatus: 429 });
    await page.getByRole("button", { name: /发送验证邮件|发送验证/ }).click();
    await expect(page.getByText(/稍后再试|频繁|限流/)).toBeVisible();
    await expect(email).toHaveValue("keep-this@example.com");

    await page.unrouteAll({ behavior: "wait" });
    await installApiMocks(page, { patchStatus: 503, patchError: { code: "SERVICE_UNAVAILABLE" } });
    await page.getByRole("button", { name: /保存/ }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(email).toHaveValue("keep-this@example.com");
    await expect(time).toHaveValue("12:34");

    await page.unrouteAll({ behavior: "wait" });
    await installApiMocks(page, { failPatchNetwork: true });
    await page.getByRole("button", { name: /保存/ }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(email).toHaveValue("keep-this@example.com");
    await expect(time).toHaveValue("12:34");

    await page.unrouteAll({ behavior: "wait" });
    await installApiMocks(page);
    await page.route("**/api/v1/notification-settings/", async (route) => json(route, 401, { code: "UNAUTHENTICATED" }));
    await page.reload();
    await expect(page).toHaveURL(/login/);
    expect(api.calls.length).toBeGreaterThan(0);
  });

  test("removes query tokens after unsuccessful verification as well", async ({ page }) => {
    await installApiMocks(page, { verifyStatus: 400 });
    await login(page);
    await page.goto("/notification-settings/verify?token=expired-token");

    await expect(page).toHaveURL(/\/notification-settings\/verify$/);
    await expect(page.getByText(/无效|过期|验证失败/)).toBeVisible();
    expect(page.url()).not.toContain("expired-token");
  });
});
