// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import vuetify from "../src/plugins/vuetify";

const authApi = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}));

const authStore = vi.hoisted(() => ({
  user: null as any,
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

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  };
}

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", component: { template: "<div>login</div>" } },
      { path: "/register", component: { template: "<div>register</div>" } },
      { path: "/applications", component: { template: "<div>applications</div>" } },
    ],
  });
}

function fill(wrapper: any, values: Record<string, string>) {
  return Promise.all(
    Object.entries(values).map(([name, value]) => wrapper.get(`input[name="${name}"]`).setValue(value)),
  );
}

function submit(wrapper: any) {
  return wrapper.get("form").trigger("submit.prevent");
}

describe("WEB-AUTH-003 RegisterView", () => {
  beforeEach(() => {
    authApi.register.mockReset();
    authStore.user = null;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: memoryStorage(),
    });
  });

  it("validates required fields and password confirmation before submitting", async () => {
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");
    const wrapper = mount(RegisterView, { global: { plugins: [vuetify, testRouter()] } });

    await submit(wrapper);
    expect(authApi.register).not.toHaveBeenCalled();
    expect(wrapper.text()).toMatch(/用户名|密码/);

    await fill(wrapper, {
      username: "alice",
      email: "alice@example.com",
      password: "StrongPass_123",
      password_confirm: "DifferentPass_123",
    });
    await submit(wrapper);

    expect(authApi.register).not.toHaveBeenCalled();
    expect(wrapper.text()).toMatch(/一致|确认密码/);
  });

  it("disables submit while registering and maps backend field errors", async () => {
    let release!: (value: unknown) => void;
    authApi.register.mockReturnValue(new Promise((resolve) => { release = resolve; }));
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");
    const wrapper = mount(RegisterView, { global: { plugins: [vuetify, testRouter()] } });
    await fill(wrapper, {
      username: "alice",
      email: "alice@example.com",
      password: "StrongPass_123",
      password_confirm: "StrongPass_123",
    });
    const request = submit(wrapper);
    await flushPromises();
    const button = wrapper.get('button[type="submit"]');
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.text()).toMatch(/加载|提交|注册/);
    release({
      response: {
        status: 400,
        data: { code: "VALIDATION_ERROR", details: { username: ["用户名已存在"] } },
      },
    });
    await request;
    await flushPromises();
    expect(wrapper.text()).toContain("用户名已存在");
  });

  it("shows success, does not auto-login, and navigates to login", async () => {
    authApi.register.mockResolvedValue({ status: 201, data: {} });
    const router = testRouter();
    await router.push("/register");
    const { default: RegisterView } = await import("../src/views/RegisterView.vue");
    const wrapper = mount(RegisterView, { global: { plugins: [vuetify, router] } });
    await fill(wrapper, {
      username: "alice",
      email: "alice@example.com",
      password: "StrongPass_123",
      password_confirm: "StrongPass_123",
    });
    await submit(wrapper);
    await flushPromises();

    expect(wrapper.text()).toMatch(/注册成功.*登录|请登录/);
    expect(authStore.user).toBeNull();
    expect(router.currentRoute.value.path).toBe("/login");
  });
});

describe("WEB-AUTH-003 LoginView", () => {
  beforeEach(() => {
    authApi.login.mockReset();
    authStore.login.mockReset();
    authStore.user = null;
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: memoryStorage(),
    });
  });

  it("does not submit incomplete credentials", async () => {
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const wrapper = mount(LoginView, { global: { plugins: [vuetify, testRouter()] } });

    await submit(wrapper);

    expect(authApi.login).not.toHaveBeenCalled();
    expect(authStore.login).not.toHaveBeenCalled();
    expect(wrapper.text()).toMatch(/用户名|密码/);
  });

  it("shows a non-enumerating message for 401 invalid credentials", async () => {
    authApi.login.mockRejectedValue({ response: { status: 401, data: { code: "INVALID_CREDENTIALS" } } });
    authStore.login.mockRejectedValue({ response: { status: 401, data: { code: "INVALID_CREDENTIALS" } } });
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const wrapper = mount(LoginView, { global: { plugins: [vuetify, testRouter()] } });
    await fill(wrapper, { username: "alice", password: "wrong-password" });
    await submit(wrapper);
    await flushPromises();

    expect(wrapper.text()).toMatch(/用户名|密码|凭据|登录失败/);
    expect(wrapper.text()).not.toMatch(/用户不存在|用户名不存在|邮箱不存在/);
  });

  it("retains input and permits retry after network or server failure", async () => {
    authApi.login.mockRejectedValueOnce({ response: { status: 500 } }).mockResolvedValue({
      status: 200,
      data: { access: "access", refresh: "refresh", user: { id: 1, username: "alice" } },
    });
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const wrapper = mount(LoginView, { global: { plugins: [vuetify, testRouter()] } });
    await fill(wrapper, { username: "alice", password: "KeepMe_123" });
    await submit(wrapper);
    await flushPromises();

    expect(wrapper.get('input[name="username"]').element.value).toBe("alice");
    expect(wrapper.get('input[name="password"]').element.value).toBe("KeepMe_123");
    expect(wrapper.text()).toMatch(/重试|网络|失败|稍后/);
    await submit(wrapper);
    await flushPromises();
    expect(authApi.login.mock.calls.length + authStore.login.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("disables submit while logging in and navigates to applications or redirect", async () => {
    let release!: (value: unknown) => void;
    authApi.login.mockReturnValue(new Promise((resolve) => { release = resolve; }));
    authStore.login.mockImplementation(async (payload: unknown) => {
      authStore.user = { id: 1, username: "alice" };
      return payload;
    });
    const router = testRouter();
    await router.push({ path: "/login", query: { redirect: "/applications?tab=active" } });
    const { default: LoginView } = await import("../src/views/LoginView.vue");
    const wrapper = mount(LoginView, { global: { plugins: [vuetify, router] } });
    await fill(wrapper, { username: "alice", password: "StrongPass_123" });
    const request = submit(wrapper);
    await flushPromises();
    expect(wrapper.get('button[type="submit"]').attributes("disabled")).toBeDefined();
    release({
      status: 200,
      data: { access: "access", refresh: "refresh", user: { id: 1, username: "alice" } },
    });
    await request;
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/applications");
    expect(router.currentRoute.value.query.tab).toBe("active");
  });
});
