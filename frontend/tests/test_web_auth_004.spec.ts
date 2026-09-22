// @vitest-environment jsdom

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import vuetify from "../src/plugins/vuetify";

const authApi = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}));

const authStore = vi.hoisted(() => ({
  user: null as unknown,
  login: vi.fn(),
}));

vi.mock(
  "../src/api/auth",
  () => ({
    login: authApi.login,
    register: authApi.register,
  }),
  { virtual: true },
);

vi.mock(
  "../src/stores/auth",
  () => ({
    useAuthStore: () => authStore,
  }),
  { virtual: true },
);

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div>home</div>" } },
      { path: "/login", component: { template: "<div>login</div>" } },
      { path: "/register", component: { template: "<div>register</div>" } },
      { path: "/applications", component: { template: "<div>applications</div>" } },
    ],
  });
}

function authSurface(wrapper: VueWrapper) {
  const form = wrapper.get("form").element as HTMLElement;
  let candidate = form.parentElement;

  while (candidate && candidate !== wrapper.element.parentElement) {
    const declaredWidth = candidate.style.width;
    const declaredMaxWidth = candidate.style.maxWidth;
    if (declaredWidth || declaredMaxWidth) return candidate;
    candidate = candidate.parentElement;
  }

  throw new Error("认证表单没有暴露可观察的容器宽度契约");
}

function widthContract(surface: HTMLElement) {
  return [surface.style.width, surface.style.maxWidth].filter(Boolean);
}

describe("WEB-AUTH-004 authentication layout", () => {
  beforeEach(() => {
    authApi.login.mockReset();
    authApi.register.mockReset();
    authStore.login.mockReset();
    authStore.user = null;
  });

  it("uses the same 560px desktop authentication width on login and register", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");
    const login = mount(LoginView, { global: { plugins: [vuetify, testRouter()] } });
    const register = mount(RegisterView, { global: { plugins: [vuetify, testRouter()] } });

    const loginWidths = widthContract(authSurface(login));
    const registerWidths = widthContract(authSurface(register));

    expect(loginWidths).toContain("560px");
    expect(registerWidths).toContain("560px");
    expect(registerWidths).toEqual(loginWidths);
  });

  it("keeps both authentication surfaces shrinkable within a 375px viewport with 16px side gaps", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");

    for (const View of [LoginView, RegisterView]) {
      const wrapper = mount(View, { global: { plugins: [vuetify, testRouter()] } });
      const surface = authSurface(wrapper);
      const rootStyle = getComputedStyle(wrapper.element);
      const leftPadding = Number.parseFloat(rootStyle.paddingLeft || "0");
      const rightPadding = Number.parseFloat(rootStyle.paddingRight || "0");

      expect(surface.style.maxWidth).toBe("560px");
      expect(surface.style.width).not.toMatch(/^\d+(?:\.\d+)?px$/);
      expect(leftPadding).toBeGreaterThanOrEqual(16);
      expect(rightPadding).toBeGreaterThanOrEqual(16);
    }
  });
});

describe("WEB-AUTH-004 register return-to-login entry", () => {
  beforeEach(() => {
    authApi.register.mockReset();
    authStore.user = null;
  });

  it("is visible, keyboard focusable, routes to /login, and does not submit registration", async () => {
    const router = testRouter();
    await router.push("/register");
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");
    const wrapper = mount(RegisterView, {
      attachTo: document.body,
      global: { plugins: [vuetify, router] },
    });
    await wrapper.get('input[name="username"]').setValue("alice");
    await wrapper.get('input[name="email"]').setValue("alice@example.com");
    await wrapper.get('input[name="password"]').setValue("StrongPass_123");
    await wrapper.get('input[name="password_confirm"]').setValue("StrongPass_123");

    const entry = wrapper
      .findAll("a, button")
      .find((candidate) => candidate.text().trim() === "返回登录");

    expect(entry, "注册页应显示可访问名称为“返回登录”的链接或按钮").toBeDefined();
    const element = entry!.element as HTMLElement;
    expect(element.hidden).toBe(false);
    expect(element.getAttribute("aria-hidden")).not.toBe("true");
    if (element.tagName === "BUTTON") expect(element.getAttribute("type")).toBe("button");
    element.focus();
    expect(document.activeElement).toBe(element);

    await entry!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/login");
    expect(authApi.register).not.toHaveBeenCalled();

    wrapper.unmount();
  });
});
