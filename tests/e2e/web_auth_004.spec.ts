import { expect, test, type Page } from "@playwright/test";

type SurfaceMetrics = {
  width: number;
  left: number;
  right: number;
  maxWidth: string;
  documentWidth: number;
  viewportWidth: number;
};

async function authenticationSurfaceMetrics(page: Page): Promise<SurfaceMetrics> {
  return page.locator("form").evaluate((form) => {
    let candidate = form.parentElement;

    while (candidate && candidate !== document.body) {
      const maxWidth = getComputedStyle(candidate).maxWidth;
      if (maxWidth && maxWidth !== "none") {
        const rect = candidate.getBoundingClientRect();
        return {
          width: rect.width,
          left: rect.left,
          right: window.innerWidth - rect.right,
          maxWidth,
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: document.documentElement.clientWidth,
        };
      }
      candidate = candidate.parentElement;
    }

    throw new Error("认证表单没有可测量的公开容器宽度契约");
  });
}

test.describe("WEB-AUTH-004 real browser authentication layout", () => {
  for (const path of ["/login", "/register"]) {
    test(`${path} renders a 560px authentication card at a 1280px viewport`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(path);

      const metrics = await authenticationSurfaceMetrics(page);
      expect(metrics.width).toBeGreaterThanOrEqual(558);
      expect(metrics.width).toBeLessThanOrEqual(562);
      expect(metrics.maxWidth).toBe("560px");
    });

    test(`${path} has 16px side gaps and no horizontal overflow at a 375px viewport`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(path);

      const metrics = await authenticationSurfaceMetrics(page);
      expect(metrics.left).toBeGreaterThanOrEqual(16);
      expect(metrics.right).toBeGreaterThanOrEqual(16);
      expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.viewportWidth);
    });
  }

  test("return-to-login is keyboard focusable, navigates directly, and does not register", async ({ page }) => {
    let registerRequests = 0;
    page.on("request", (request) => {
      if (request.method() === "POST" && request.url().includes("/api/v1/auth/register/")) {
        registerRequests += 1;
      }
    });

    await page.goto("/register");
    const entry = page.getByRole("link", { name: "返回登录", exact: true });
    await expect(entry).toBeVisible();
    await entry.focus();
    await expect(entry).toBeFocused();
    await entry.press("Enter");

    await expect(page).toHaveURL(/\/login(?:[/?#]|$)/);
    expect(registerRequests).toBe(0);
  });
});
