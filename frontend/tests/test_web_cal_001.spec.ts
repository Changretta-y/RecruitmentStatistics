// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RouterView } from "vue-router";
import vuetify from "../src/plugins/vuetify";
import * as routerModuleAtLoad from "../src/router";

const apiHarness = vi.hoisted(() => ({
  requests: [] as Array<{ url: string; method: string; params: Record<string, unknown> }>,
  outcomes: [] as Array<{ data?: unknown; reject?: unknown; deferred?: (release: (value: unknown) => void) => void }>,
}));

const authState = vi.hoisted(() => ({
  user: { id: 1, username: "alice" },
  initialized: true,
  loading: false,
  initialize: vi.fn(async () => undefined),
  logout: vi.fn(async () => undefined),
}));

function defaultEvents() {
  return {
    timezone: "Asia/Shanghai",
    start: "2026-09-28",
    end: "2026-11-02",
    events: [
      {
        application_id: 41,
        company_name: "辰星科技",
        position_name: "后端工程师",
        stage: "written_test",
        start_at: "2026-10-14T09:00:00+08:00",
        end_at: "2026-10-14T09:45:00+08:00",
        duration_minutes: 45,
      },
      {
        application_id: 41,
        company_name: "辰星科技",
        position_name: "后端工程师",
        stage: "first_interview",
        start_at: "2026-10-14T09:15:00+08:00",
        end_at: "2026-10-14T10:15:00+08:00",
        duration_minutes: 60,
      },
      {
        application_id: 52,
        company_name: "远山数据",
        position_name: "数据工程师",
        stage: "hr_interview",
        start_at: "2026-10-14T13:00:00+08:00",
        end_at: "2026-10-14T15:00:00+08:00",
        duration_minutes: 120,
      },
      {
        application_id: 63,
        company_name: "跨日实验室",
        position_name: "平台工程师",
        stage: "third_interview",
        start_at: "2026-10-14T23:30:00+08:00",
        end_at: "2026-10-15T01:30:00+08:00",
        duration_minutes: 120,
      },
      {
        application_id: 64,
        company_name: "午夜结束公司",
        position_name: "客户端工程师",
        stage: "ai_interview",
        start_at: "2026-10-14T23:00:00+08:00",
        end_at: "2026-10-15T00:00:00+08:00",
        duration_minutes: 60,
      },
    ],
  };
}

function sendRequest(config: any) {
  const request = {
    url: String(config.url ?? ""),
    method: String(config.method ?? "get").toLowerCase(),
    params: (config.params ?? {}) as Record<string, unknown>,
  };
  apiHarness.requests.push(request);
  const outcome = apiHarness.outcomes.shift();
  if (outcome?.reject) return Promise.reject(outcome.reject);
  if (outcome?.deferred) {
    return new Promise((resolve) => outcome.deferred?.((value) => resolve(value)));
  }
  const data = outcome && "data" in outcome ? outcome.data : defaultEvents();
  return Promise.resolve({ status: 200, data });
}

const axiosMock = vi.hoisted(() => ({
  create: vi.fn(),
  get: vi.fn(sendRequest),
  request: vi.fn(sendRequest),
}));

vi.mock(
  "axios",
  () => {
    const client = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      get: axiosMock.get,
      request: axiosMock.request,
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    };
    axiosMock.create.mockReturnValue(client);
    return { default: axiosMock, create: axiosMock.create };
  },
  { virtual: true },
);

const routerAtLoad = (routerModuleAtLoad as any).router ?? (routerModuleAtLoad as any).default;
const calendarRouteRegisteredAtLoad = routerAtLoad.getRoutes().some((record: any) => record.path === "/calendar");

vi.mock(
  "../src/stores/auth",
  () => ({ useAuthStore: () => authState }),
  { virtual: true },
);

vi.mock(
  "../src/api/applications",
  () => ({
    list: vi.fn(async () => ({
      count: 0,
      page: 1,
      pageSize: 20,
      totalPages: 1,
      next: null,
      previous: null,
      results: [],
    })),
    listApplications: vi.fn(),
    fetchApplications: vi.fn(),
    default: {},
  }),
  { virtual: true },
);

const octoberEvents = defaultEvents().events;

async function makeRouter() {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-14T04:00:00.000Z"));
  const routerModule = await import("../src/router");
  const router = routerModule.router ?? routerModule.default;
  return router;
}

async function mountCalendar() {
  const router = await makeRouter();
  await router.push("/calendar");
  await router.isReady();
  const wrapper = mount(RouterView, { global: { plugins: [vuetify, router] } });
  await flushPromises();
  return { router, wrapper };
}

function calendarRequests() {
  return apiHarness.requests.filter((request) => request.url.includes("/api/v1/calendar/events/"));
}

function lastCalendarRequest() {
  return calendarRequests().at(-1);
}

function buttonByName(wrapper: any, pattern: RegExp) {
  return wrapper.findAll('button, [role="button"]').find((button: any) =>
    pattern.test(`${button.text()} ${button.attributes("aria-label") ?? ""}`),
  );
}

function eventControl(wrapper: any, company: string) {
  return wrapper.findAll('button, [role="button"], a').find((node: any) =>
    `${node.text()} ${node.attributes("aria-label") ?? ""}`.includes(company),
  );
}

function rangeFrom(request: any) {
  return {
    start: request?.params?.start ?? request?.start,
    end: request?.params?.end ?? request?.end,
  };
}

describe("WEB-CAL-001 weekly and monthly calendar", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useRealTimers();
    apiHarness.requests.splice(0);
    apiHarness.outcomes.splice(0);
    axiosMock.get.mockReset();
    axiosMock.request.mockReset();
    axiosMock.get.mockImplementation(sendRequest);
    axiosMock.request.mockImplementation(sendRequest);
    authState.user = { id: 1, username: "alice" };
    authState.initialized = true;
    authState.loading = false;
    authState.initialize.mockReset();
    authState.logout.mockReset();
  });

  it("registers a protected /calendar route and exposes a navigation entry from applications", async () => {
    const router = await makeRouter();
    const route = router.resolve("/calendar");
    expect(route.matched.length, "/calendar must resolve to an application page").toBeGreaterThan(0);
    expect(route.matched.some((record: any) => record.meta?.requiresAuth === true)).toBe(true);

    await router.push("/applications");
    await router.isReady();
    const { default: ApplicationsView } = await import("../src/views/ApplicationsView.vue");
    const wrapper = mount(ApplicationsView, { global: { plugins: [vuetify, router] } });
    await flushPromises();
    const calendarLink = wrapper.find('a[href="/calendar"]');
    expect(calendarLink.exists(), "the main navigation must link to /calendar").toBe(true);
    expect(calendarLink.text()).toMatch(/日历/);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("defaults to the current month, requests its full Monday-first week range, and labels Beijing time", async () => {
    const { router, wrapper } = await mountCalendar();
    expect(router.currentRoute.value.path).toBe("/calendar");
    expect(wrapper.text()).toMatch(/2026年?\s*10月|2026-10/);
    expect(wrapper.text()).toContain("北京时间");
    expect(wrapper.text()).toContain("Asia/Shanghai");
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-09-28", end: "2026-11-02" });
    expect(lastCalendarRequest()?.method).toBe("get");
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("switches to the current Monday-first week, pages backward and forward, then returns to today", async () => {
    const { wrapper } = await mountCalendar();
    const week = buttonByName(wrapper, /周视图|周/);
    expect(week, "a weekly view control is required").toBeTruthy();
    await week!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-10-12", end: "2026-10-19" });

    const previous = buttonByName(wrapper, /上一周|上一周期|上周|上一个/);
    expect(previous).toBeTruthy();
    await previous!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-10-05", end: "2026-10-12" });

    const next = buttonByName(wrapper, /下一周|下一周期|下周|下一个/);
    expect(next).toBeTruthy();
    await next!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-10-12", end: "2026-10-19" });

    const today = buttonByName(wrapper, /今天/);
    expect(today).toBeTruthy();
    await today!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-10-12", end: "2026-10-19" });
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("pages months by complete Monday-first weeks and can switch back to the week containing the anchor date", async () => {
    const { wrapper } = await mountCalendar();
    const next = buttonByName(wrapper, /下个月|下一月|下一周期|下一个/);
    expect(next).toBeTruthy();
    await next!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-10-26", end: "2026-12-07" });

    const week = buttonByName(wrapper, /周视图|周/);
    expect(week).toBeTruthy();
    await week!.trigger("click");
    await flushPromises();
    expect(rangeFrom(lastCalendarRequest())).toEqual({ start: "2026-11-09", end: "2026-11-16" });
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("shows separate overlapping interview and written-test events with their full times, durations, and edit links", async () => {
    const { wrapper } = await mountCalendar();
    for (const [company, time, type] of [
      ["辰星科技", "09:00", /笔试|written_test/],
      ["辰星科技", "09:15", /一面|面试|first_interview/],
      ["远山数据", "13:00", /HR 面|HR面|hr_interview/],
    ] as Array<[string, string, RegExp]>) {
      const control = eventControl(wrapper, company);
      expect(control, `${company} must be an accessible schedule entry`).toBeTruthy();
      expect(`${control!.text()} ${control!.attributes("aria-label") ?? ""}`).toContain(time);
      expect(`${control!.text()} ${control!.attributes("aria-label") ?? ""}`).toMatch(type);
      expect(control!.element.tagName === "BUTTON" || control!.attributes("role") === "button" || control!.element.tagName === "A").toBe(true);
    }
    expect(wrapper.text()).toContain("45 分钟");
    expect(wrapper.text()).toContain("120 分钟");
    expect(wrapper.text()).toContain("09:45");
    expect(wrapper.text()).toContain("10:15");

    const written = eventControl(wrapper, "辰星科技");
    await written!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toMatch(/阶段.*笔试|笔试/);
    expect(wrapper.text()).toContain("辰星科技");
    expect(wrapper.text()).toContain("后端工程师");
    expect(wrapper.text()).toContain("09:00");
    expect(wrapper.text()).toContain("09:45");
    const editLink = wrapper.find('a[href*="/applications/41"]');
    const editAction = buttonByName(wrapper, /编辑.*投递|编辑投递/);
    expect(editLink.exists() || Boolean(editAction), "event details must open the original application editor").toBe(true);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("draws each day as a top-to-bottom 24-hour axis and keeps event coordinates proportional to that date's time", async () => {
    const { wrapper } = await mountCalendar();
    const labels = wrapper.text();
    expect(labels).toMatch(/00:00/);
    expect(labels).toMatch(/12:00/);
    expect(labels).toMatch(/24:00/);

    const morning = eventControl(wrapper, "辰星科技");
    const afternoon = eventControl(wrapper, "远山数据");
    expect(morning).toBeTruthy();
    expect(afternoon).toBeTruthy();
    const morningStyle = morning!.attributes("style") ?? "";
    const afternoonStyle = afternoon!.attributes("style") ?? "";
    const top = (style: string) => Number(style.match(/(?:^|;)\s*top\s*:\s*([\d.]+)%/i)?.[1]);
    const height = (style: string) => Number(style.match(/(?:^|;)\s*height\s*:\s*([\d.]+)%/i)?.[1]);
    expect(Number.isFinite(top(morningStyle)), "event position must expose a measurable vertical time coordinate").toBe(true);
    expect(Number.isFinite(height(morningStyle)), "event length must expose a measurable vertical duration").toBe(true);
    expect(top(afternoonStyle)).toBeGreaterThan(top(morningStyle));
    expect(top(morningStyle)).toBeCloseTo(9 / 24 * 100, 0);
    expect(height(morningStyle)).toBeCloseTo(45 / (24 * 60) * 100, 0);
    expect(top(afternoonStyle)).toBeCloseTo(13 / 24 * 100, 0);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("renders cross-midnight fragments on both dates, excludes an event ending exactly at midnight from the next day, and keeps overlaps accessible", async () => {
    const { wrapper } = await mountCalendar();
    expect(wrapper.text()).toContain("跨日实验室");
    expect(wrapper.text()).toContain("午夜结束公司");
    const fragment = eventControl(wrapper, "跨日实验室");
    expect(fragment).toBeTruthy();
    await fragment!.trigger("keydown.enter");
    await flushPromises();
    expect(wrapper.text()).toContain("23:30");
    expect(wrapper.text()).toContain("次日");
    expect(wrapper.text()).toContain("01:30");

    const week = buttonByName(wrapper, /周视图|周/);
    expect(week).toBeTruthy();
    await week!.trigger("click");
    await flushPromises();
    const nextDay = wrapper.findAll('[data-date="2026-10-15"]');
    expect(nextDay.length).toBeGreaterThan(0);
    expect(nextDay.map((day) => day.text()).join(" ")).toContain("跨日实验室");
    expect(nextDay.map((day) => day.text()).join(" ")).not.toContain("午夜结束公司");
    expect(octoberEvents.filter((event) => event.start_at.startsWith("2026-10-14T09")).length).toBe(2);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("offers a compact timeline in month cells and keeps every event available when a day is crowded", async () => {
    const many = Array.from({ length: 18 }, (_, index) => ({
      application_id: 100 + index,
      company_name: `安排${index + 1}`,
      position_name: `岗位${index + 1}`,
      stage: index % 2 ? "written_test" : "first_interview",
      start_at: `2026-10-14T${String(8 + (index % 10)).padStart(2, "0")}:00:00+08:00`,
      end_at: `2026-10-14T${String(8 + (index % 10)).padStart(2, "0")}:30:00+08:00`,
      duration_minutes: 30,
    }));
    apiHarness.outcomes.push({ data: { ...defaultEvents(), events: many } });
    const { wrapper } = await mountCalendar();
    const dayCell = wrapper.find('[data-date="2026-10-14"]');
    expect(dayCell.exists()).toBe(true);
    expect(dayCell.text()).toMatch(/00:00/);
    expect(dayCell.text()).toMatch(/24:00/);
    const more = buttonByName(dayCell, /更多|全部安排|18 项|18个/);
    expect(more, "month cells may collapse labels but must retain an all-events entry").toBeTruthy();
    await more!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("安排1");
    expect(wrapper.text()).toContain("安排18");
    expect(wrapper.text()).toMatch(/笔试/);
    expect(wrapper.text()).toMatch(/一面|面试/);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("shows a clear empty state and keeps the view with a retry action after API failure", async () => {
    apiHarness.outcomes.push({ data: { ...defaultEvents(), events: [] } });
    const empty = await mountCalendar();
    expect(empty.wrapper.text()).toMatch(/暂无安排|没有安排|无安排/);

    apiHarness.outcomes.push({ reject: new Error("calendar unavailable") });
    await empty.router.push({ path: "/calendar", query: { refresh: "failed" } });
    await flushPromises();
    expect(empty.wrapper.text()).toMatch(/日历|2026年?\s*10月/);
    expect(empty.wrapper.text()).toMatch(/加载失败|网络|重试|错误/);
    const retry = buttonByName(empty.wrapper, /重试/);
    expect(retry).toBeTruthy();
    await retry!.trigger("click");
    await flushPromises();
    expect(calendarRequests().length).toBeGreaterThan(2);
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("uses only the latest date-range response after a rapid view change", async () => {
    const releases: Array<(value: unknown) => void> = [];
    apiHarness.outcomes.push(
      { deferred: (release) => releases.push(release) },
      { deferred: (release) => releases.push(release) },
    );
    const { wrapper } = await mountCalendar();
    const monthRequest = lastCalendarRequest();
    const week = buttonByName(wrapper, /周视图|周/);
    expect(week).toBeTruthy();
    await week!.trigger("click");
    await flushPromises();
    expect(calendarRequests().length).toBeGreaterThanOrEqual(2);
    const freshEvents = { ...defaultEvents(), events: [{ ...octoberEvents[0], company_name: "新周结果" }] };
    releases[1]?.({ status: 200, data: freshEvents });
    await flushPromises();
    releases[0]?.({ status: 200, data: { ...defaultEvents(), events: [{ ...octoberEvents[0], company_name: "旧月结果" }] } });
    await flushPromises();
    expect(wrapper.text()).toContain("新周结果");
    expect(wrapper.text()).not.toContain("旧月结果");
    expect(rangeFrom(monthRequest)).toEqual({ start: "2026-09-28", end: "2026-11-02" });
  });

  it.skipIf(!calendarRouteRegisteredAtLoad)("routes unauthenticated users through the existing login protection", async () => {
    authState.user = null;
    const router = await makeRouter();
    await router.push("/calendar");
    await router.isReady();
    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/calendar");
  });
});
