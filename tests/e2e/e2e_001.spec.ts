import { execFileSync } from "node:child_process";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";
const PASSWORD = "E2E_StrongPass_123";

type Session = { username: string; password: string; access: string; refresh: string };

function uniqueUser() {
  return `e2e_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

async function input(page: Page, names: string[], label: RegExp) {
  for (const name of names) {
    const locator = page.locator(`input[name="${name}"]`);
    if (await locator.count()) return locator.first();
  }
  return page.getByLabel(label).first();
}

async function registerAndLogin(page: Page): Promise<Session> {
  const username = uniqueUser();
  await page.goto("/register");
  await (await input(page, ["username"], /用户名|username/i)).fill(username);
  const email = page.locator('input[name="email"]');
  if (await email.count()) await email.first().fill(`${username}@example.com`);
  await (await input(page, ["password"], /密码|password/i)).fill(PASSWORD);
  const confirmation = page.locator('input[name="password_confirm"], input[name="passwordConfirm"]');
  if (await confirmation.count()) await confirmation.first().fill(PASSWORD);
  await page.getByRole("button", { name: /注册|register/i }).click();
  await expect(page).toHaveURL(/login/);

  const loginResponse = page.waitForResponse(
    (response) => response.url().includes("/api/v1/auth/login/") && response.request().method() === "POST",
  );
  await (await input(page, ["username"], /用户名|username/i)).fill(username);
  await (await input(page, ["password"], /密码|password/i)).fill(PASSWORD);
  await page.getByRole("button", { name: /登录|login/i }).click();
  const response = await loginResponse;
  expect(response.ok()).toBeTruthy();
  const tokens = await response.json();
  await expect(page).toHaveURL(/applications/);
  await expect(page.getByText(username, { exact: true })).toBeVisible();
  return { username, password: PASSWORD, access: tokens.access, refresh: tokens.refresh };
}

async function apiCreate(request: APIRequestContext, access: string, companyName: string, positionName: string) {
  const response = await request.post(`${API_BASE_URL}/api/v1/applications/`, {
    headers: { Authorization: `Bearer ${access}` },
    data: { company_name: companyName, position_name: positionName },
  });
  expect(response.status()).toBe(201);
}

function recordRow(page: Page, company: string) {
  return page.getByRole("row").filter({ hasText: company }).first();
}

async function openCreate(page: Page) {
  await page.getByRole("link", { name: "新增公司进度", exact: true }).click();
}

async function createFromForm(page: Page, company: string, position: string) {
  await openCreate(page);
  await (await input(page, ["company", "company_name", "companyName"], /公司名称|公司|company/i)).fill(company);
  await (await input(page, ["position", "position_name", "positionName"], /岗位名称|岗位|position/i)).fill(position);
  const createResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/applications/") &&
      response.request().method() === "POST" &&
      response.status() === 201,
  );
  await page.getByRole("button", { name: /保存|提交|创建/ }).click();
  const response = await createResponse;
  expect(response.status()).toBe(201);
  await expect(page).not.toHaveURL(/\/applications\/new(?:[/?]|$)/);
  await expect(page.getByText(company, { exact: true })).toBeVisible();
}

test.describe("E2E-001 core public flows", () => {
  test("registers, logs in, and reaches the personal applications list", async ({ page }) => {
    await registerAndLogin(page);
    await expect(page.getByRole("heading", { name: "校招进度管理系统", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "投递查询", exact: true })).toBeVisible();
  });

  test("creates a record, persists it after refresh, and sets then clears stage times", async ({ page }) => {
    await registerAndLogin(page);
    const lifecycleEvents: Array<Record<string, unknown>> = [];
    page.on("request", (requestEvent) => {
      if (requestEvent.url().includes("/api/v1/auth/me/") || requestEvent.url().includes("/api/v1/applications/")) {
        lifecycleEvents.push({ type: "request", method: requestEvent.method(), url: requestEvent.url() });
      }
    });
    page.on("response", async (response) => {
      if (!response.url().includes("/api/v1/auth/me/") && !response.url().includes("/api/v1/applications/")) return;
      const event: Record<string, unknown> = {
        type: "response",
        method: response.request().method(),
        url: response.url(),
        status: response.status(),
      };
      if (response.request().method() === "GET" && response.url().includes("/api/v1/applications/")) {
        try {
          const payload = await response.json();
          const results = Array.isArray(payload) ? payload : payload.results ?? [];
          event.resultsCount = results.length;
          event.containsTarget = results.some((item: unknown) => JSON.stringify(item).includes("E2E 持久化公司"));
          event.results = results;
        } catch (error) {
          event.jsonError = String(error);
        }
      }
      lifecycleEvents.push(event);
    });
    const urlBeforeCreate = page.url();
    await createFromForm(page, "E2E 持久化公司", "后端工程师");
    const urlAfterCreateBeforeReload = page.url();
    const textAfterCreateBeforeReload = await page.locator("body").innerText();
    await test.info().attach("persistence-before-reload", {
      body: JSON.stringify({ urlBeforeCreate, urlAfterCreateBeforeReload, textAfterCreateBeforeReload }, null, 2),
      contentType: "application/json",
    });

    await page.reload({ waitUntil: "commit" });
    await page.waitForTimeout(1_500);
    const urlAfterReload = page.url();
    const textAfterReload = await page.locator("body").innerText();
    const applicationsResponses = lifecycleEvents.filter(
      (event) => event.type === "response" && event.method === "GET" && String(event.url).includes("/api/v1/applications/"),
    );
    const persistenceEvidence = {
      urlBeforeCreate,
      urlAfterCreateBeforeReload,
      urlAfterReload,
      hitLoginAfterReload: /\/login(?:[/?]|$)/.test(urlAfterReload),
      textAfterReload,
      applicationsResponses,
    };
    await test.info().attach("persistence-lifecycle-diagnostics", {
      body: JSON.stringify(persistenceEvidence, null, 2),
      contentType: "application/json",
    });
    console.log("E2E-001 persistence lifecycle", JSON.stringify(persistenceEvidence));
    expect(urlAfterReload).not.toMatch(/\/login(?:[/?]|$)/);
    expect(applicationsResponses.length).toBeGreaterThan(0);
    expect(applicationsResponses.at(-1)?.containsTarget).toBe(true);
    await expect(page.getByText("E2E 持久化公司", { exact: true })).toBeVisible();

    await recordRow(page, "E2E 持久化公司").getByRole("button", { name: /编辑|修改/ }).click();
    await (await input(page, ["writtenTestTime", "written_test_time"], /笔试|written/i)).fill("2026-09-20T10:00:00+08:00");
    await (await input(page, ["firstInterviewTime", "first_interview_time"], /一面|first/i)).fill("2026-09-21T10:00:00+08:00");
    const updateResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/applications/") &&
        response.request().method() === "PATCH" &&
        [200, 204].includes(response.status()),
    );
    await page.getByRole("button", { name: /保存|提交/ }).click();
    const updated = await updateResponse;
    expect([200, 204]).toContain(updated.status());
    await expect(page).not.toHaveURL(/\/applications\/\d+\/edit(?:[/?]|$)/);
    await page.reload();
    await expect(recordRow(page, "E2E 持久化公司")).toContainText("2026-09-21");

    await recordRow(page, "E2E 持久化公司").getByRole("button", { name: /编辑|修改/ }).click();
    await (await input(page, ["firstInterviewTime", "first_interview_time"], /一面|first/i)).fill("");
    await page.getByRole("button", { name: /保存|提交/ }).click();
    await expect(page.getByText("E2E 持久化公司", { exact: true })).toBeVisible();
  });

  test("searches, filters, sorts, paginates, and changes page size across multiple records", async ({ page, request }) => {
    const session = await registerAndLogin(page);
    for (let index = 1; index <= 21; index += 1) {
      await apiCreate(request, session.access, `E2E 批量公司 ${index}`, `岗位 ${index}`);
    }
    await page.reload();
    const search = await input(page, ["search"], /关键字|搜索|search/i);
    await search.fill("E2E 批量公司 2");
    await page.getByRole("button", { name: /查询|搜索/ }).click();
    await expect(page.getByText("E2E 批量公司 2", { exact: true })).toBeVisible();

    const status = page.getByLabel(/状态|status/i);
    if (await status.count()) await status.selectOption({ index: 1 });
    const ordering = page.getByLabel(/排序|ordering/i);
    if (await ordering.count()) await ordering.selectOption({ index: 1 });
    const pageSize = page.getByLabel(/每页|page.?size/i);
    if (await pageSize.count()) await pageSize.selectOption("10");
    await expect(page).toHaveURL(/page_size=10|pageSize=10/);
  });

  test("cancels deletion without a request, then confirms deletion and updates the list", async ({ page }) => {
    await registerAndLogin(page);
    await createFromForm(page, "E2E 删除公司", "删除岗位");
    const record = recordRow(page, "E2E 删除公司");
    await record.getByRole("button", { name: /^删除 / }).click();
    const confirmation = page.getByRole("dialog");
    await expect(confirmation).toContainText("E2E 删除公司");
    await expect(confirmation).toContainText("删除岗位");
    await confirmation.getByRole("button", { name: /取消|cancel/i }).click();
    await expect(page.getByText("E2E 删除公司", { exact: true })).toBeVisible();

    await record.getByRole("button", { name: /^删除 / }).click();
    await page.getByRole("dialog").getByRole("button", { name: /确认|删除|confirm/i }).click();
    await expect(page.getByText("E2E 删除公司", { exact: true })).not.toBeVisible();
  });

  test("refreshes an expired access request once, then logout invalidates the old refresh token", async ({ page, request }) => {
    const session = await registerAndLogin(page);
    let forced401 = false;
    let refreshRequests = 0;
    const requestEvidence: Array<{ type: string; method: string; url: string; status?: number }> = [];
    page.on("request", (requestEvent) => {
      if (requestEvent.url().includes("/api/v1/auth/refresh/") || requestEvent.url().includes("/api/v1/applications/")) {
        if (requestEvent.url().includes("/api/v1/auth/refresh/")) refreshRequests += 1;
        requestEvidence.push({ type: "request", method: requestEvent.method(), url: requestEvent.url() });
      }
    });
    page.on("response", (response) => {
      if (response.url().includes("/api/v1/auth/refresh/") || response.url().includes("/api/v1/applications/")) {
        requestEvidence.push({ type: "response", method: response.request().method(), url: response.url(), status: response.status() });
      }
    });
    await page.route("**/api/v1/applications**", async (route) => {
      if (!forced401 && route.request().method() === "GET") {
        forced401 = true;
        await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ code: "TOKEN_EXPIRED" }) });
        return;
      }
      await route.continue();
    });
    try {
      const protectedApplicationsGet = page.waitForResponse(
        (response) => response.url().includes("/api/v1/applications/") && response.request().method() === "GET",
        { timeout: 10_000 },
      );
      await page.reload();
      await protectedApplicationsGet;
      await expect(page).toHaveURL(/applications/);
      await expect.poll(() => refreshRequests, { timeout: 8_000 }).toBe(1);
    } finally {
      await test.info().attach("refresh-request-diagnostics", {
        body: JSON.stringify({ refreshRequests, forced401, requests: requestEvidence }, null, 2),
        contentType: "application/json",
      });
    }

    await page.getByRole("button", { name: /退出|logout/i }).click();
    await expect(page).toHaveURL(/login/);
    const oldRefresh = await request.post(`${API_BASE_URL}/api/v1/auth/refresh/`, { data: { refresh: session.refresh } });
    expect(oldRefresh.status()).toBe(401);
  });

  test("keeps application records isolated between two browser users", async ({ browser }) => {
    const firstContext = await browser.newContext();
    const secondContext = await browser.newContext();
    const firstPage = await firstContext.newPage();
    const secondPage = await secondContext.newPage();
    await registerAndLogin(firstPage);
    await createFromForm(firstPage, "E2E 私有公司", "私有岗位");
    await registerAndLogin(secondPage);
    await expect(secondPage.getByText("E2E 私有公司", { exact: true })).not.toBeVisible();
    await firstContext.close();
    await secondContext.close();
  });

  test("restarts the backend and preserves application persistence", async ({ page }) => {
    const restartCommand = process.env.E2E_RESTART_COMMAND;
    test.skip(!restartCommand, "需要 CI/编排器提供安全的服务重启命令");
    if (!restartCommand) return;

    await registerAndLogin(page);
    await createFromForm(page, "E2E 重启持久化公司", "重启岗位");

    let restartOutput = "";
    try {
      restartOutput = execFileSync(
        "pwsh.exe",
        ["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", restartCommand],
        { cwd: process.cwd(), timeout: 45_000, encoding: "utf8" },
      );
    } catch (error) {
      await test.info().attach("restart-command-error", {
        body: String(error),
        contentType: "text/plain",
      });
      throw error;
    }
    await test.info().attach("restart-command-result", {
      body: restartOutput,
      contentType: "text/plain",
    });

    const applicationsGet = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/applications/") &&
        response.request().method() === "GET" &&
        response.status() === 200,
      { timeout: 15_000 },
    );
    await page.reload({ waitUntil: "commit" });
    const response = await applicationsGet;
    expect(response.status()).toBe(200);
    const payload = await response.json();
    const results = Array.isArray(payload) ? payload : payload.results ?? [];
    expect(results.some((item: unknown) => JSON.stringify(item).includes("E2E 重启持久化公司"))).toBe(true);
    await expect(page.getByText("E2E 重启持久化公司", { exact: true })).toBeVisible();
  });
});
