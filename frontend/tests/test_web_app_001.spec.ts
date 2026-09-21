import { beforeEach, describe, expect, it, vi } from "vitest";

const transport = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock(
  "../src/api/http",
  () => ({
    authClient: transport,
    http: transport,
    apiClient: transport,
    default: transport,
  }),
  { virtual: true },
);

function pick(source: any, names: string[]) {
  const object = source.default ?? source;
  for (const name of names) {
    if (typeof source[name] === "function") return source[name].bind(source);
    if (typeof object[name] === "function") return object[name].bind(object);
  }
  return undefined;
}

async function loadApplicationsApi() {
  const module = await import("../src/api/applications");
  const list = pick(module, ["listApplications", "fetchApplications", "getApplications", "list"]);
  const update = pick(module, ["updateApplication", "patchApplication", "editApplication", "update"]);
  expect(list, "applications API must expose a list method").toBeTypeOf("function");
  expect(update, "applications API must expose a PATCH method").toBeTypeOf("function");
  return { list: list!, update: update! };
}

async function loadQueryApi() {
  const loaders = [
    () => import("../src/utils/application-query"),
    () => import("../src/stores/application-query"),
    () => import("../src/utils/query-state"),
  ];
  for (const load of loaders) {
    try {
      const module = await load();
      const parse = pick(module, ["parseApplicationQuery", "parseQuery", "fromUrlQuery", "parse"]);
      const serialize = pick(module, ["serializeApplicationQuery", "serializeQuery", "toUrlQuery", "serialize"]);
      if (parse && serialize) return { parse, serialize };
    } catch {
      // Try the next public utility location from the project contract.
    }
  }
  throw new Error("No public application query parse/serialize module was found");
}

const snakeApplication = {
  id: 7,
  user: 3,
  company_name: "示例科技",
  position_name: "后端工程师",
  application_status: "in_progress",
  current_stage: "first_interview",
  application_time: "2026-09-20T02:00:00Z",
  ai_interview_time: null,
  written_test_time: null,
  first_interview_time: "2026-09-21T02:00:00Z",
  second_interview_time: null,
  third_interview_time: null,
  hr_interview_time: null,
  notes: "备注",
  created_at: "2026-09-19T02:00:00Z",
  updated_at: "2026-09-20T02:00:00Z",
};

const pageResponse = {
  count: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
  next: null,
  previous: null,
  results: [snakeApplication],
};

describe("WEB-APP-001 application API contract", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("maps snake_case application and pagination responses to camelCase without losing null/ISO values", async () => {
    transport.get.mockResolvedValue({ data: pageResponse });
    const api = await loadApplicationsApi();

    const result = await api.list({ page: 1, pageSize: 20, search: "", ordering: "-updated_at" });
    const application = result.results[0];

    expect(application.companyName).toBe("示例科技");
    expect(application.positionName).toBe("后端工程师");
    expect(application.applicationStatus).toBe("in_progress");
    expect(application.currentStage).toBe("first_interview");
    expect(application.applicationTime).toBe("2026-09-20T02:00:00Z");
    expect(application.aiInterviewTime).toBeNull();
    expect(application.firstInterviewTime).toBe("2026-09-21T02:00:00Z");
    expect(application.createdAt).toBe("2026-09-19T02:00:00Z");
    expect(result.pageSize).toBe(20);
    expect(result.results).toHaveLength(1);
  });

  it("serializes query fields to backend names, omits empty filters and preserves ordering minus", async () => {
    transport.get.mockResolvedValue({ data: pageResponse });
    const api = await loadApplicationsApi();

    await api.list({
      page: 2,
      pageSize: 50,
      search: "腾讯",
      applicationStatus: "in_progress",
      stage: "first_interview",
      applicationTimeAfter: "2026-01-01T00:00:00+08:00",
      applicationTimeBefore: "2026-12-31T23:59:59+08:00",
      ordering: "-first_interview_time",
    });

    const requestText = JSON.stringify(transport.get.mock.calls[0]);
    expect(requestText).toContain("page_size");
    expect(requestText).toContain("application_status");
    expect(requestText).toContain("application_time_after");
    expect(requestText).toContain("application_time_before");
    expect(requestText).toContain("-first_interview_time");
    expect(requestText).toContain("腾讯");

    transport.get.mockClear();
    await api.list({ page: 1, pageSize: 20, search: "", ordering: "-updated_at" });
    expect(JSON.stringify(transport.get.mock.calls[0])).not.toContain('"search":""');
  });

  it("passes PATCH null and camelCase fields as snake_case without dropping null", async () => {
    transport.patch.mockResolvedValue({ data: snakeApplication });
    const api = await loadApplicationsApi();

    await api.update(7, { firstInterviewTime: null, applicationTime: "2026-09-20T02:00:00Z" });

    const body = transport.patch.mock.calls[0].find(
      (value: unknown) => value && typeof value === "object" && !Array.isArray(value),
    );
    expect(body.first_interview_time).toBeNull();
    expect(body.application_time).toBe("2026-09-20T02:00:00Z");
    expect(body.firstInterviewTime).toBeUndefined();
  });

  it("keeps unified API error code and field details observable", async () => {
    const error = Object.assign(new Error("validation"), {
      response: { status: 400, data: { code: "VALIDATION_ERROR", details: { notes: ["too long"] } } },
    });
    transport.get.mockRejectedValue(error);
    const api = await loadApplicationsApi();

    await expect(api.list({ page: 1, pageSize: 20, search: "", ordering: "-updated_at" })).rejects.toMatchObject({
      response: { data: { code: "VALIDATION_ERROR", details: { notes: ["too long"] } } },
    });
  });
});

describe("WEB-APP-001 application query state", () => {
  it("uses page 1/pageSize 20 defaults and round-trips supported filters", async () => {
    const query = await loadQueryApi();
    const defaults = query.parse({});
    expect(defaults.page).toBe(1);
    expect(defaults.pageSize).toBe(20);
    expect(defaults.search).toBe("");

    const state = {
      ...defaults,
      page: 2,
      pageSize: 50,
      search: "腾讯",
      applicationStatus: "in_progress",
      stage: "first_interview",
      applicationTimeAfter: "2026-01-01T00:00:00+08:00",
      applicationTimeBefore: "2026-12-31T23:59:59+08:00",
      ordering: "-first_interview_time",
    };
    const urlQuery = query.serialize(state);
    const restored = query.parse(urlQuery);
    expect(restored).toEqual(state);
    expect(urlQuery.ordering).toBe("-first_interview_time");
  });

  it.each([0, 1, 15, 101, "abc", "50.5"])(
    "falls back invalid pageSize %s to 20 without throwing",
    async (pageSize) => {
      const query = await loadQueryApi();
      expect(query.parse({ page: "nope", pageSize })).toMatchObject({ page: 1, pageSize: 20 });
    },
  );

  it("does not serialize empty filters and keeps a leading minus in ordering", async () => {
    const query = await loadQueryApi();
    const urlQuery = query.serialize({
      page: 1,
      pageSize: 20,
      search: "",
      applicationStatus: undefined,
      stage: undefined,
      applicationTimeAfter: undefined,
      applicationTimeBefore: undefined,
      ordering: "-updated_at",
    });

    expect(urlQuery).toEqual({ page: "1", pageSize: "20", ordering: "-updated_at" });
  });
});
