import { beforeEach, describe, expect, it, vi } from "vitest";

const authApi = vi.hoisted(() => ({
  login: vi.fn(),
  me: vi.fn(),
  logout: vi.fn(),
}));

const navigation = vi.hoisted(() => ({
  push: vi.fn(),
}));

vi.mock(
  "../src/api/auth",
  () => ({
    login: authApi.login,
    me: authApi.me,
    getMe: authApi.me,
    fetchMe: authApi.me,
    logout: authApi.logout,
    postLogout: authApi.logout,
  }),
  { virtual: true },
);

vi.mock("../src/router", () => ({
  router: navigation,
  default: navigation,
}));

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

async function createStore() {
  const { createPinia, setActivePinia } = await import("pinia");
  setActivePinia(createPinia());
  const useAuthStore = await loadAuthStore();
  return useAuthStore();
}

function savedTokenSet(overrides: Record<string, unknown> = {}) {
  return {
    accessToken: "access-token",
    refreshToken: "refresh-token",
    expiresAt: Date.now() + 86_400_000,
    ...overrides,
  };
}

const user = { id: 7, username: "alice", email: "alice@example.com" };

describe("REL-001 public auth store behavior", () => {
  beforeEach(() => {
    vi.resetModules();
    authApi.login.mockReset();
    authApi.me.mockReset();
    authApi.logout.mockReset();
    navigation.push.mockReset();
    navigation.push.mockResolvedValue(undefined);
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: memoryStorage(),
    });
  });

  it("completes initialization without calling me when no token exists", async () => {
    const store = await createStore();

    await expect(store.initialize()).resolves.toBeUndefined();

    expect(authApi.me).not.toHaveBeenCalled();
    expect(store.user).toBeNull();
    expect(store.initialized).toBe(true);
    expect(store.loading).toBe(false);
  });

  it("restores the user after a successful getMe request", async () => {
    const storage = await loadTokenStorage();
    await storage.save(savedTokenSet());
    authApi.me.mockResolvedValue(user);
    const store = await createStore();

    await store.initialize();

    expect(authApi.me).toHaveBeenCalledTimes(1);
    expect(store.user).toEqual(user);
    expect(store.initialized).toBe(true);
    expect(store.loading).toBe(false);
  });

  it("clears the session and still completes initialization when getMe fails", async () => {
    const storage = await loadTokenStorage();
    await storage.save(savedTokenSet());
    authApi.me.mockRejectedValue({ response: { status: 401 } });
    const store = await createStore();

    await expect(store.initialize()).resolves.toBeUndefined();

    expect(authApi.me).toHaveBeenCalledTimes(1);
    expect(store.user).toBeNull();
    expect(store.initialized).toBe(true);
    expect(store.loading).toBe(false);
    expect(await storage.read()).toBeNull();
  });

  it("passes login credentials to the API and persists the returned session", async () => {
    const session = {
      access: "access-new",
      refresh: "refresh-new",
      access_expires_in: 1800,
      refresh_expires_in: 604800,
      user,
    };
    authApi.login.mockResolvedValue({ ...session, data: session });
    const store = await createStore();
    const credentials = { username: "alice", password: "StrongPass_123" };

    await store.login(credentials);

    expect(authApi.login).toHaveBeenCalledWith(credentials);
    expect(store.user).toEqual(user);
    const saved = await (await loadTokenStorage()).read();
    expect(saved).toMatchObject({ accessToken: "access-new", refreshToken: "refresh-new" });
    expect(saved?.expiresAt).toBeGreaterThan(Date.now());
  });

  it("clears user and token state after a successful logout", async () => {
    const storage = await loadTokenStorage();
    await storage.save(savedTokenSet());
    authApi.logout.mockResolvedValue({ status: 204 });
    const store = await createStore();
    store.user = user;

    await expect(store.logout()).resolves.toBeUndefined();

    expect(authApi.logout).toHaveBeenCalledTimes(1);
    expect(store.user).toBeNull();
    expect(await storage.read()).toBeNull();
    expect(navigation.push).toHaveBeenCalledWith("/login");
  });

  it("clears user and token state when the logout API fails", async () => {
    const storage = await loadTokenStorage();
    await storage.save(savedTokenSet());
    authApi.logout.mockRejectedValue(new Error("logout unavailable"));
    const store = await createStore();
    store.user = user;

    await expect(store.logout()).resolves.toBeUndefined();

    expect(store.user).toBeNull();
    expect(await storage.read()).toBeNull();
    expect(navigation.push).toHaveBeenCalledWith("/login");
  });

  it("does not reject logout when navigation to login fails", async () => {
    const storage = await loadTokenStorage();
    await storage.save(savedTokenSet());
    authApi.logout.mockResolvedValue({ status: 204 });
    navigation.push.mockRejectedValue(new Error("navigation interrupted"));
    const store = await createStore();
    store.user = user;

    await expect(store.logout()).resolves.toBeUndefined();

    expect(store.user).toBeNull();
    expect(await storage.read()).toBeNull();
    expect(navigation.push).toHaveBeenCalledWith("/login");
  });
});
