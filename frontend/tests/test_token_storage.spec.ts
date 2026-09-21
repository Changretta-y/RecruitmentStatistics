import { beforeEach, describe, expect, it, vi } from "vitest";

type TokenSet = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

const httpHarness = vi.hoisted(() => ({
  requestHandlers: [] as Array<(config: any) => any>,
  responseHandlers: [] as Array<{ fulfilled?: (value: any) => any; rejected?: (error: any) => any }>,
  requestOutcomes: [] as Array<{ response?: any; reject?: any }>,
  refreshOutcomes: [] as Array<{ response?: any; reject?: any }>,
  seenRequests: [] as any[],
  refreshCalls: [] as any[],
  instance: null as any,
}));

async function runResponseError(error: any) {
  let current = error;
  for (const handler of httpHarness.responseHandlers) {
    if (!handler.rejected) continue;
    try {
      return await handler.rejected(current);
    } catch (nextError) {
      current = nextError;
    }
  }
  throw current;
}

async function runRequest(config: any) {
  let current = { ...config, headers: { ...(config.headers ?? {}) } };
  for (const handler of httpHarness.requestHandlers) {
    current = (await handler(current)) ?? current;
  }
  httpHarness.seenRequests.push(current);
  const outcome = httpHarness.requestOutcomes.shift() ?? {
    response: { status: 200, data: {} },
  };
  if (outcome.reject) {
    return runResponseError({ ...outcome.reject, config: current });
  }
  let response = outcome.response;
  for (const handler of httpHarness.responseHandlers) {
    if (handler.fulfilled) response = await handler.fulfilled(response);
  }
  return response;
}

const fakeAxios = vi.hoisted(() => {
  return {
    create: vi.fn(),
    post: vi.fn(),
  };
});

vi.mock(
  "axios",
  () => {
    const instance = {
      interceptors: {
        request: {
          use: vi.fn((fulfilled: (config: any) => any) => {
            httpHarness.requestHandlers.push(fulfilled);
          }),
        },
        response: {
          use: vi.fn((fulfilled: (value: any) => any, rejected: (error: any) => any) => {
            httpHarness.responseHandlers.push({ fulfilled, rejected });
          }),
        },
      },
      request: vi.fn(runRequest),
      get: vi.fn((url: string, config: any = {}) => runRequest({ ...config, url, method: "get" })),
      post: vi.fn(async (url: string, data: any, config: any = {}) => {
        httpHarness.refreshCalls.push({ url, data, config });
        const outcome = httpHarness.refreshOutcomes.shift() ?? {
          response: { status: 200, data: {} },
        };
        if (outcome.reject) {
          return runResponseError({ ...outcome.reject, config: { ...config, url, method: "post" } });
        }
        return outcome.response;
      }),
    };
    httpHarness.instance = instance;
    fakeAxios.create.mockReturnValue(instance);
    fakeAxios.post.mockImplementation(instance.post);
    return { default: fakeAxios, create: fakeAxios.create, post: fakeAxios.post };
  },
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

function pickFunction(source: any, names: string[]) {
  for (const name of names) {
    if (typeof source?.[name] === "function") return source[name].bind(source);
  }
  return undefined;
}

async function loadTokenStorage() {
  const module = await import("../src/utils/token-storage");
  const source = module.tokenStorage ?? module.default ?? module;
  const save = pickFunction(module, ["saveTokens", "setTokens", "saveTokenSet"])
    ?? pickFunction(source, ["saveTokens", "setTokens", "saveTokenSet", "save"]);
  const read = pickFunction(module, ["getTokens", "readTokens", "loadTokens"])
    ?? pickFunction(source, ["getTokens", "readTokens", "loadTokens", "get"]);
  const clear = pickFunction(module, ["clearTokens", "removeTokens"])
    ?? pickFunction(source, ["clearTokens", "removeTokens", "clear"]);
  expect(save, "token storage must expose a save operation").toBeTypeOf("function");
  expect(read, "token storage must expose a read operation").toBeTypeOf("function");
  expect(clear, "token storage must expose a clear operation").toBeTypeOf("function");
  return { save: save!, read: read!, clear: clear! };
}

async function loadHttpClient() {
  vi.resetModules();
  httpHarness.requestHandlers.length = 0;
  httpHarness.responseHandlers.length = 0;
  httpHarness.requestOutcomes.length = 0;
  httpHarness.refreshOutcomes.length = 0;
  httpHarness.seenRequests.length = 0;
  httpHarness.refreshCalls.length = 0;
  const module = await import("../src/api/http");
  const client = module.apiClient ?? module.http ?? module.client ?? module.default;
  expect(client, "public auth HTTP client must be exported").toBeDefined();
  return client;
}

function tokenSet(overrides: Partial<TokenSet> = {}): TokenSet {
  return {
    accessToken: "access-old",
    refreshToken: "refresh-old",
    expiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
    ...overrides,
  };
}

function unauthorized() {
  return { response: { status: 401 }, message: "unauthorized" };
}

describe("WEB-AUTH-001 token storage", () => {
  let storage: ReturnType<typeof memoryStorage>;

  beforeEach(() => {
    storage = memoryStorage();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: storage,
    });
    vi.useRealTimers();
  });

  it("saves, reads and clears the access/refresh token set through one module", async () => {
    const api = await loadTokenStorage();
    const tokens = tokenSet();

    await api.save(tokens);

    expect(api.read()).toEqual(tokens);
    expect(storage.setItem).toHaveBeenCalled();
    await api.clear();
    expect(api.read()).toBeNull();
    expect(storage.removeItem.mock.calls.length + storage.clear.mock.calls.length).toBeGreaterThan(0);
  });

  it("treats the seven-day deadline as expired and clears local storage", async () => {
    vi.useFakeTimers();
    const now = new Date("2026-09-20T00:00:00.000Z");
    vi.setSystemTime(now);
    const api = await loadTokenStorage();
    await api.save(tokenSet({ expiresAt: now.getTime() + 7 * 24 * 60 * 60 * 1000 }));

    vi.advanceTimersByTime(7 * 24 * 60 * 60 * 1000 + 1);

    expect(api.read()).toBeNull();
    expect(storage.removeItem.mock.calls.length + storage.clear.mock.calls.length).toBeGreaterThan(0);
  });
});

describe("WEB-AUTH-001 public auth HTTP client", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: memoryStorage(),
    });
  });

  it("injects the current access token as a Bearer header", async () => {
    const storage = await loadTokenStorage();
    await storage.save(tokenSet());
    const client = await loadHttpClient();
    httpHarness.requestOutcomes.push({ response: { status: 200, data: { ok: true } } });

    await client.get("/protected");

    expect(httpHarness.seenRequests[0].headers.Authorization).toBe("Bearer access-old");
  });

  it("refreshes once after 401, stores rotated tokens and retries once", async () => {
    const storage = await loadTokenStorage();
    await storage.save(tokenSet());
    const client = await loadHttpClient();
    httpHarness.requestOutcomes.push(
      { reject: unauthorized() },
      { response: { status: 200, data: { ok: true } } },
    );
    httpHarness.refreshOutcomes.push({
      response: { status: 200, data: { access: "access-new", refresh: "refresh-new" } },
    });

    await expect(client.get("/protected")).resolves.toMatchObject({ status: 200 });

    expect(httpHarness.refreshCalls).toHaveLength(1);
    expect(httpHarness.seenRequests).toHaveLength(2);
    expect(httpHarness.seenRequests[1].headers.Authorization).toBe("Bearer access-new");
    expect((await storage.read()).refreshToken).toBe("refresh-new");
  });

  it("shares one refresh promise across concurrent 401 responses", async () => {
    const storage = await loadTokenStorage();
    await storage.save(tokenSet());
    const client = await loadHttpClient();
    let releaseRefresh!: () => void;
    const refreshGate = new Promise<void>((resolve) => {
      releaseRefresh = resolve;
    });
    httpHarness.requestOutcomes.push(
      { reject: unauthorized() },
      { reject: unauthorized() },
      { response: { status: 200, data: { request: 1 } } },
      { response: { status: 200, data: { request: 2 } } },
    );
    httpHarness.refreshOutcomes.push({
      response: refreshGate.then(() => ({
        status: 200,
        data: { access: "access-rotated", refresh: "refresh-rotated" },
      })),
    } as any);

    const first = client.get("/protected/one");
    const second = client.get("/protected/two");
    await Promise.resolve();
    releaseRefresh();
    await expect(Promise.all([first, second])).resolves.toHaveLength(2);

    expect(httpHarness.refreshCalls).toHaveLength(1);
    expect(httpHarness.seenRequests).toHaveLength(4);
    expect((await storage.read()).accessToken).toBe("access-rotated");
  });

  it("does not recursively refresh a failed refresh request", async () => {
    const storage = await loadTokenStorage();
    await storage.save(tokenSet());
    const client = await loadHttpClient();
    httpHarness.refreshOutcomes.push({ reject: unauthorized() });

    await expect(
      client.post("/api/v1/auth/refresh/", { refresh: "refresh-old" }),
    ).rejects.toBeTruthy();

    expect(httpHarness.refreshCalls).toHaveLength(1);
  });

  it("clears tokens and rejects all queued requests when refresh fails", async () => {
    const storage = await loadTokenStorage();
    await storage.save(tokenSet());
    const client = await loadHttpClient();
    httpHarness.requestOutcomes.push({ reject: unauthorized() }, { reject: unauthorized() });
    httpHarness.refreshOutcomes.push({ reject: unauthorized() });

    const results = await Promise.allSettled([
      client.get("/protected/one"),
      client.get("/protected/two"),
    ]);

    expect(results.every((result) => result.status === "rejected")).toBe(true);
    expect(httpHarness.refreshCalls).toHaveLength(1);
    expect(await storage.read()).toBeNull();
  });
});
