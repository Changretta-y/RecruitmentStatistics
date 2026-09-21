// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import vuetify from "../src/plugins/vuetify";

const applicationApi = vi.hoisted(() => ({
  list: vi.fn(),
  listApplications: vi.fn(),
  fetchApplications: vi.fn(),
  getApplications: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  user: { id: 1, username: "alice" } as { id: number; username: string } | null,
  logout: vi.fn(),
}));

vi.mock(
  "../src/api/applications",
  () => ({
    list: applicationApi.list,
    listApplications: applicationApi.listApplications,
    fetchApplications: applicationApi.fetchApplications,
    getApplications: applicationApi.getApplications,
    default: applicationApi,
  }),
  { virtual: true },
);

vi.mock(
  "../src/stores/auth",
  () => ({
    useAuthStore: () => authState,
  }),
  { virtual: true },
);

const applications = [
  {
    id: 1,
    companyName: "示例科技",
    positionName: "后端工程师",
    applicationStatus: "in_progress",
    currentStage: "first_interview",
    applicationTime: "2026-09-10T02:00:00Z",
    aiInterviewTime: null,
    writtenTestTime: "2026-09-11T02:00:00Z",
    firstInterviewTime: "2026-09-12T02:00:00Z",
    secondInterviewTime: null,
    thirdInterviewTime: null,
    hrInterviewTime: null,
    notes: "技术岗",
    createdAt: "2026-09-01T02:00:00Z",
    updatedAt: "2026-09-13T02:00:00Z",
  },
];

const page = (results = applications, extra: Record<string, unknown> = {}) => ({
  count: results.length,
  page: 1,
  pageSize: 20,
  totalPages: 1,
  next: null,
  previous: null,
  results,
  ...extra,
});

function routerFor(query: Record<string, string> = {}) {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/applications", component: { template: "<div />" } },
      { path: "/applications/new", component: { template: "<div />" } },
      { path: "/login", name: "login", component: { template: "<div />" } },
    ],
  });
}

async function mountView(query: Record<string, string> = {}) {
  const router = routerFor(query);
  await router.push({ path: "/applications", query });
  await router.isReady();
  const { default: ApplicationsView } = await import("../src/views/ApplicationsView.vue");
  const wrapper = mount(ApplicationsView, { global: { plugins: [vuetify, router] } });
  await flushPromises();
  return { wrapper, router };
}

function searchInput(wrapper: any) {
  return wrapper.find('input[name="search"], input[placeholder*="关键字"], input[placeholder*="搜索"]');
}

function selectInput(wrapper: any, names: string[]) {
  return wrapper.find(names.map((name) => `select[name="${name}"]`).join(","));
}

function requestArguments() {
  const calls = [
    ...applicationApi.list.mock.calls,
    ...applicationApi.listApplications.mock.calls,
    ...applicationApi.fetchApplications.mock.calls,
    ...applicationApi.getApplications.mock.calls,
  ];
  return calls.flatMap((call) => call).filter((value) => value && typeof value === "object");
}

function latestRequest() {
  const args = requestArguments();
  return args[args.length - 1] as Record<string, unknown>;
}

function buttonByText(wrapper: any, pattern: RegExp) {
  return wrapper.findAll("button").find((button: any) => pattern.test(button.text()));
}

describe("WEB-APP-002 ApplicationsView", () => {
  beforeEach(() => {
    Object.values(applicationApi).forEach((mock) => mock.mockReset());
    authState.user = { id: 1, username: "alice" };
    authState.logout.mockReset();
    applicationApi.list.mockResolvedValue(page());
    applicationApi.listApplications.mockResolvedValue(page());
    applicationApi.fetchApplications.mockResolvedValue(page());
    applicationApi.getApplications.mockResolvedValue(page());
  });

  it("requests the current query and renders company, position, status, six stages, and updated time", async () => {
    const { wrapper } = await mountView({ page: "1", page_size: "20", ordering: "-updated_at" });

    expect(JSON.stringify(requestArguments())).toContain("-updated_at");
    expect(wrapper.text()).toContain("示例科技");
    expect(wrapper.text()).toContain("后端工程师");
    expect(wrapper.text()).toMatch(/in_progress|进行中/);
    expect(wrapper.text()).toMatch(/first_interview|一面/);
    expect(wrapper.text()).toContain("2026-09-13");
    expect(wrapper.text()).toContain("2026-09-11");
    expect(wrapper.text()).toContain("2026-09-12");
  });

  it("sends search, status/stage/time filters and ordering, then resets page on query changes", async () => {
    const { wrapper } = await mountView({ page: "3", page_size: "50" });

    const search = searchInput(wrapper);
    expect(search.exists()).toBe(true);
    await search.setValue("示例");
    await search.trigger("keyup.enter");

    const status = selectInput(wrapper, ["status", "applicationStatus", "application_status"]);
    const stage = selectInput(wrapper, ["stage", "currentStage", "current_stage"]);
    if (status.exists()) { await status.setValue("in_progress"); await status.trigger("change"); }
    if (stage.exists()) { await stage.setValue("first_interview"); await stage.trigger("change"); }
    const after = wrapper.find('input[name="applicationTimeAfter"], input[name="application_time_after"]');
    const before = wrapper.find('input[name="applicationTimeBefore"], input[name="application_time_before"]');
    if (after.exists()) await after.setValue("2026-09-01T00:00:00+08:00");
    if (before.exists()) await before.setValue("2026-09-30T23:59:59+08:00");
    const ordering = wrapper.find('select[name="ordering"], input[name="ordering"]');
    if (ordering.exists()) { await ordering.setValue("-first_interview_time"); await ordering.trigger("change"); }
    const submitButton = wrapper.find('button[type="submit"]');
    const searchButton = submitButton.exists() ? submitButton : buttonByText(wrapper, /查询/);
    if (searchButton) await searchButton.trigger("click");
    await flushPromises();


    const request = latestRequest();
    expect(JSON.stringify(request)).toContain("示例");
    expect(JSON.stringify(request)).toContain("in_progress");
    expect(JSON.stringify(request)).toContain("first_interview");
    expect(JSON.stringify(request)).toContain("2026-09-01");
    expect(JSON.stringify(request)).toContain("-first_interview_time");
    expect(JSON.stringify(request)).toContain("page");
    expect(JSON.stringify(request)).toContain("1");
  });

  it("changes page size with a page reset and keeps filters when moving to the next page", async () => {
    const { wrapper } = await mountView({ page: "2", page_size: "20", search: "示例", ordering: "-updated_at" });
    const pageSize = selectInput(wrapper, ["pageSize", "page_size"]);
    expect(pageSize.exists()).toBe(true);
    await pageSize.setValue("50");
    await flushPromises();
    expect(JSON.stringify(latestRequest())).toContain("50");
    expect(JSON.stringify(latestRequest())).toContain("示例");
    expect(JSON.stringify(latestRequest())).toContain('"page":1');

    const labelledNext = wrapper.find('button[aria-label*="下一"]');
    const next = labelledNext.exists() ? labelledNext : buttonByText(wrapper, /下一页|下一/);
    expect(next).toBeTruthy();
    await next.trigger("click");
    await flushPromises();
    expect(JSON.stringify(latestRequest())).toContain("示例");
    expect(JSON.stringify(latestRequest())).toContain("-updated_at");
  });

  it("restores query state from URL and on browser back/forward navigation", async () => {
    const { wrapper, router } = await mountView({
      page: "2",
      page_size: "50",
      search: "示例",
      application_status: "in_progress",
      stage: "first_interview",
      ordering: "-first_interview_time",
    });
    expect(searchInput(wrapper).element.value).toBe("示例");
    expect(JSON.stringify(requestArguments())).toContain("first_interview");

    await router.push({ path: "/applications", query: { page: "1", page_size: "10", search: "新查询" } });
    await flushPromises();
    expect(searchInput(wrapper).element.value).toBe("新查询");
    await router.back();
    await router.isReady();
    await flushPromises();
    expect(searchInput(wrapper).element.value).toBe("示例");
    expect(router.currentRoute.value.query.page_size).toBe("50");
  });

  it("provides current user, logout, and create-application entry points", async () => {
    const { wrapper, router } = await mountView();
    expect(wrapper.text()).toContain("alice");
    const createLink = wrapper.find('a[href="/applications/new"]');
    const create = createLink.exists() ? createLink : buttonByText(wrapper, /新增公司进度/);
    expect(create).toBeTruthy();
    const logout = buttonByText(wrapper, /退出/);
    expect(logout).toBeTruthy();
    await logout.trigger("click");
    await router.isReady();
    await flushPromises();
    expect(authState.logout).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("distinguishes initial empty, filtered no-result, network error, and 401 states without dropping query", async () => {
    applicationApi.list.mockResolvedValueOnce(page([]));
    let mounted = await mountView();
    expect(mounted.wrapper.text()).toMatch(/暂无|第一条|新增/);

    applicationApi.list.mockResolvedValueOnce(page([]));
    await mounted.router.push({ path: "/applications", query: { search: "不存在" } });
    await flushPromises();
    expect(mounted.wrapper.text()).toMatch(/无结果|没有.*匹配|调整.*筛选/);
    expect(searchInput(mounted.wrapper).element.value).toBe("不存在");

    applicationApi.list.mockRejectedValueOnce(new Error("network"));
    await mounted.router.push({ path: "/applications", query: { search: "网络保留" } });
    await flushPromises();
    expect(mounted.wrapper.text()).toMatch(/网络|重试|失败/);
    expect(searchInput(mounted.wrapper).element.value).toBe("网络保留");

    applicationApi.list.mockRejectedValueOnce({ response: { status: 401 } });
    await mounted.router.push({ path: "/applications", query: { search: "认证保留" } });
    await flushPromises();
    expect(mounted.wrapper.text()).toMatch(/登录|认证|会话/);
    expect(searchInput(mounted.wrapper).element.value).toBe("认证保留");
  });

  it("accepts only the latest response when searches overlap", async () => {
    const pending = new Map<string, (value: unknown) => void>();
    applicationApi.list.mockImplementation((query: { search?: string }) => {
      const key = query.search ?? "";
      if (!key) return Promise.resolve(page());
      return new Promise((resolve) => pending.set(key, resolve));
    });
    const { wrapper } = await mountView();
    const search = searchInput(wrapper);

    await search.setValue("旧查询");
    await search.trigger("keyup.enter");
    await search.setValue("新查询");
    await search.trigger("keyup.enter");
    pending.get("新查询")?.(page([{ ...applications[0], companyName: "新结果" }]));
    await flushPromises();
    pending.get("旧查询")?.(page([{ ...applications[0], companyName: "旧结果" }]));
    await flushPromises();

    expect(wrapper.text()).toContain("新结果");
    expect(wrapper.text()).not.toContain("旧结果");
  });
});
