import { beforeEach, describe, expect, it, vi } from "vitest";

const authApi = vi.hoisted(() => ({
  me: vi.fn(),
  logout: vi.fn(),
}));

vi.mock(
  "../src/api/auth",
  () => ({
    me: authApi.me,
    getMe: authApi.me,
    fetchMe: authApi.me,
    logout: authApi.logout,
    postLogout: authApi.logout,
  }),
  { virtual: true },
);

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: vi.fn((key: string) => values.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => values.set(key, value)),
    removeItem: vi.fn((key: string) => values.delete(key)),
    clear: vi.fn(() => values.clear()),
  };
}

async function loadTokenStorage() {
  const module = await import("../src/utils/token-storage");
  const source = module.tokenStorage ?? module.default ?? module;
  const save = module.saveTokens ?? source.saveTokens ?? source.save;
  const read = module.getTokens ?? source.getTokens ?? source.get;
  const clear = module.clearTokens ?? source.clearTokens ?? source.clear;
  expect(save).toBeTypeOf("function");
  expect(read).toBeTypeOf("function");
  expect(clear).toBeTypeOf("function");
  return { save, read, clear };
}

async function loadAuthStore() {
  const module = await import("../src/stores/auth");
  const useAuthStore = module.useAuthStore ?? module.default;
  expect(useAuthStore).toBeTypeOf("function");
  return useAuthStore;
}

describe("WEB-AUTH-002 auth store", () => {
  beforeEach(() => {
    vi.resetModules();
    authApi.me.mockReset();
    authApi.logout.mockReset();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: memoryStorage(),
    });
  });

  it("exposes user, initialized and loading state and restores user from me", async () => {
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    const storage = await loadTokenStorage();
    await storage.save({
      accessToken: "access",
      refreshToken: "refresh",
      expiresAt: Date.now() + 86_400_000,
    });
    authApi.me.mockResolvedValue({ id: 1, username: "alice", email: "alice@example.com" });

    const useAuthStore = await loadAuthStore();
    const store = useAuthStore();
    expect(store.user).toBeNull();
    expect(store.initialized).toBe(false);
    await store.initialize();

    expect(store.user).toEqual({ id: 1, username: "alice", email: "alice@example.com" });
    expect(store.initialized).toBe(true);
    expect(store.loading).toBe(false);
    expect(authApi.me).toHaveBeenCalledTimes(1);
  });

  it("clears expired or refresh-failed login state during initialization", async () => {
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    const storage = await loadTokenStorage();
    await storage.save({ accessToken: "expired", refreshToken: "refresh", expiresAt: Date.now() - 1 });
    authApi.me.mockRejectedValue(new Error("refresh failed"));

    const store = (await loadAuthStore())();
    await store.initialize();

    expect(store.user).toBeNull();
    expect(store.initialized).toBe(true);
    expect(await storage.read()).toBeNull();
  });

  it("deduplicates concurrent initialization and performs one me request", async () => {
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    const storage = await loadTokenStorage();
    await storage.save({ accessToken: "access", refreshToken: "refresh", expiresAt: Date.now() + 86_400_000 });
    let resolveMe!: (user: object) => void;
    authApi.me.mockReturnValue(new Promise((resolve) => { resolveMe = resolve; }));

    const store = (await loadAuthStore())();
    const first = store.initialize();
    const second = store.initialize();
    resolveMe({ id: 1, username: "alice", email: "alice@example.com" });
    await Promise.all([first, second]);

    expect(authApi.me).toHaveBeenCalledTimes(1);
    expect(store.initialized).toBe(true);
    expect(store.loading).toBe(false);
  });

  it.each([
    ["success", () => Promise.resolve({ status: 204 })],
    ["http failure", () => Promise.reject(new Error("logout failed"))],
    ["network failure", () => Promise.reject(new TypeError("network unavailable"))],
  ])("logout always clears user and tokens on %s", async (_label, outcome) => {
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    const storage = await loadTokenStorage();
    await storage.save({ accessToken: "access", refreshToken: "refresh", expiresAt: Date.now() + 86_400_000 });
    authApi.logout.mockImplementation(outcome);

    const store = (await loadAuthStore())();
    store.user = { id: 1, username: "alice", email: "alice@example.com" };
    await expect(store.logout()).resolves.toBeUndefined();

    expect(store.user).toBeNull();
    expect(await storage.read()).toBeNull();
  });
});

describe("WEB-AUTH-002 route guards", () => {
  it("redirects unauthenticated protected navigation with encoded original URL", async () => {
    const routerModule = await import("../src/router");
    const router = routerModule.router ?? routerModule.default;
    await router.push({ path: "/applications", query: { tab: "active" } });

    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/applications?tab=active");
  });

  it.each(["/login", "/register"])(
    "redirects authenticated navigation from %s to applications",
    async (path) => {
      const { createPinia, setActivePinia } = await import("pinia");
      setActivePinia(createPinia());
      const storage = await loadTokenStorage();
      await storage.save({
        accessToken: "access",
        refreshToken: "refresh",
        expiresAt: Date.now() + 86_400_000,
      });
      const store = (await loadAuthStore())();
      store.user = { id: 1, username: "alice", email: "alice@example.com" };
      const routerModule = await import("../src/router");
      const router = routerModule.router ?? routerModule.default;
      await router.push(path);

      expect(router.currentRoute.value.path).toBe("/applications");
    },
  );
});
