// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import vuetify from "../src/plugins/vuetify";

const applicationApi = vi.hoisted(() => ({
  list: vi.fn(),
  listApplications: vi.fn(),
  fetchApplications: vi.fn(),
  delete: vi.fn(),
  deleteApplication: vi.fn(),
  removeApplication: vi.fn(),
  destroyApplication: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  user: { id: 1, username: "alice" },
}));

vi.mock(
  "../src/api/applications",
  () => ({
    list: applicationApi.list,
    listApplications: applicationApi.listApplications,
    fetchApplications: applicationApi.fetchApplications,
    delete: applicationApi.delete,
    deleteApplication: applicationApi.deleteApplication,
    removeApplication: applicationApi.removeApplication,
    destroyApplication: applicationApi.destroyApplication,
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

const firstApplication = {
  id: 41,
  companyName: "删除示例科技",
  positionName: "后端工程师",
  applicationStatus: "in_progress",
  currentStage: "first_interview",
  applicationTime: "2026-09-10T02:00:00Z",
  aiInterviewTime: null,
  writtenTestTime: null,
  firstInterviewTime: null,
  secondInterviewTime: null,
  thirdInterviewTime: null,
  hrInterviewTime: null,
  notes: "不应出现在错误提示中",
  createdAt: "2026-09-01T02:00:00Z",
  updatedAt: "2026-09-11T02:00:00Z",
};

const secondApplication = {
  ...firstApplication,
  id: 42,
  companyName: "另一家公司",
  positionName: "前端工程师",
};

function page(results = [firstApplication, secondApplication], extra: Record<string, unknown> = {}) {
  return {
    count: results.length,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    next: null,
    previous: null,
    results,
    ...extra,
  };
}

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

async function mountApplications(query: Record<string, string> = {}) {
  const router = routerFor(query);
  await router.push({ path: "/applications", query });
  await router.isReady();
  const { default: ApplicationsView } = await import("../src/views/ApplicationsView.vue");
  const wrapper = mount(ApplicationsView, { global: { plugins: [vuetify, router] } });
  await flushPromises();
  return { wrapper, router };
}

function listCalls() {
  return [
    ...applicationApi.list.mock.calls,
    ...applicationApi.listApplications.mock.calls,
    ...applicationApi.fetchApplications.mock.calls,
  ];
}

function deleteCalls() {
  return [
    ...applicationApi.delete.mock.calls,
    ...applicationApi.deleteApplication.mock.calls,
    ...applicationApi.removeApplication.mock.calls,
    ...applicationApi.destroyApplication.mock.calls,
  ];
}

function buttonByText(wrapper: any, pattern: RegExp) {
  return wrapper.findAll("button").find((button: any) => pattern.test(button.text()));
}

function rowFor(wrapper: any, company: string) {
  return wrapper.findAll("tr").find((row: any) => row.text().includes(company));
}

function deleteButtonFor(wrapper: any, company: string) {
  const row = rowFor(wrapper, company);
  if (row) {
    return row.findAll("button").find((button: any) => /删除/.test(`${button.text()} ${button.attributes("aria-label") ?? ""}`));
  }
  return wrapper.findAll("button").find((button: any) => /删除/.test(`${button.text()} ${button.attributes("aria-label") ?? ""}`));
}

function dialog(wrapper: any) {
  const labelled = wrapper.find('[role="dialog"]');
  return labelled.exists() ? labelled : wrapper;
}

async function openDeleteDialog(wrapper: any, company = firstApplication.companyName) {
  const deleteButton = deleteButtonFor(wrapper, company);
  expect(deleteButton, "a public delete action is required").toBeTruthy();
  await deleteButton.trigger("click");
  await flushPromises();
  return dialog(wrapper);
}

async function confirmDelete(wrapper: any) {
  const activeDialog = dialog(wrapper);
  const confirm = buttonByText(activeDialog, /确认删除|确认|删除/);
  expect(confirm, "a public confirm action is required").toBeTruthy();
  await confirm.trigger("click");
  await flushPromises();
}

describe("WEB-APP-004 delete and empty/error interactions", () => {
  beforeEach(() => {
    Object.values(applicationApi).forEach((mock) => mock.mockReset());
    applicationApi.list.mockResolvedValue(page());
    applicationApi.listApplications.mockResolvedValue(page());
    applicationApi.fetchApplications.mockResolvedValue(page());
    applicationApi.delete.mockResolvedValue({ status: 204 });
    applicationApi.deleteApplication.mockResolvedValue({ status: 204 });
    applicationApi.removeApplication.mockResolvedValue({ status: 204 });
    applicationApi.destroyApplication.mockResolvedValue({ status: 204 });
  });

  it("opens a keyboard-operable confirmation showing company and position, and cancel sends no request", async () => {
    const { wrapper } = await mountApplications();
    const deleteButton = deleteButtonFor(wrapper, firstApplication.companyName);
    expect(deleteButton).toBeTruthy();
    expect(deleteButton.element.tagName).toBe("BUTTON");
    await deleteButton.trigger("keydown.enter");
    await flushPromises();
    const activeDialog = dialog(wrapper);
    expect(activeDialog.text()).toContain(firstApplication.companyName);
    expect(activeDialog.text()).toContain(firstApplication.positionName);

    const cancel = buttonByText(activeDialog, /取消|关闭/);
    expect(cancel).toBeTruthy();
    await cancel.trigger("click");
    expect(deleteCalls()).toHaveLength(0);
  });

  it("confirms DELETE with the record id, refreshes the current page, and shows success", async () => {
    const { wrapper } = await mountApplications();
    await openDeleteDialog(wrapper);
    await confirmDelete(wrapper);

    expect(JSON.stringify(deleteCalls())).toContain("41");
    expect(listCalls().length).toBeGreaterThan(1);
    expect(wrapper.text()).toMatch(/删除成功|已删除|成功/);
  });

  it("moves from the last item on page 2 back to page 1 after deletion", async () => {
    applicationApi.list.mockReset();
    applicationApi.listApplications.mockReset();
    applicationApi.fetchApplications.mockReset();
    applicationApi.list.mockResolvedValueOnce(page([firstApplication], { page: 2, totalPages: 2, count: 21 }));
    applicationApi.list.mockResolvedValueOnce(page([], { page: 1, totalPages: 1, count: 20 }));
    const { wrapper } = await mountApplications({ page: "2" });
    await openDeleteDialog(wrapper);
    await confirmDelete(wrapper);

    const requests = listCalls();
    expect(requests.length).toBeGreaterThan(1);
    expect(JSON.stringify(requests[requests.length - 1])).toContain('"page":1');
  });

  it.each([
    [404, /不存在|已删除|找不到/],
    [403, /无权|权限|禁止/],
    [500, /服务|失败|稍后|错误/],
  ])("shows a safe understandable message for DELETE %s", async (status, expected) => {
    const sensitive = "Token=secret-password stack-trace-at-private-file";
    applicationApi.delete.mockRejectedValue({
      response: { status, data: { detail: sensitive, traceback: sensitive } },
    });
    const { wrapper } = await mountApplications();
    await openDeleteDialog(wrapper);
    await confirmDelete(wrapper);

    expect(wrapper.text()).toMatch(expected);
    expect(wrapper.text()).not.toContain("secret-password");
    expect(wrapper.text()).not.toContain("stack-trace-at-private-file");
    expect(wrapper.text()).not.toContain("Token=");
  });

  it("keeps the query and offers retry after a network delete failure", async () => {
    applicationApi.delete.mockRejectedValueOnce(new Error("network failure with Token=secret"));
    applicationApi.delete.mockResolvedValueOnce({ status: 204 });
    const { wrapper } = await mountApplications({ search: "保留筛选", page: "2" });
    await openDeleteDialog(wrapper);
    await confirmDelete(wrapper);

    expect(wrapper.text()).toMatch(/网络|重试|失败/);
    expect(wrapper.text()).not.toContain("Token=secret");
    const retry = buttonByText(wrapper, /重试/);
    expect(retry).toBeTruthy();
    await retry.trigger("click");
    await flushPromises();
    expect(deleteCalls().length).toBeGreaterThan(1);
    expect(JSON.stringify(listCalls())).toContain("保留筛选");
  });

  it("shows an add entry for empty data and a reset-filter action for no results", async () => {
    applicationApi.list.mockResolvedValue(page([]));
    const empty = await mountApplications();
    expect(empty.wrapper.text()).toMatch(/新增|第一条/);
    expect(empty.wrapper.find('a[href="/applications/new"]').exists()).toBe(true);

    applicationApi.list.mockResolvedValue(page([]));
    const filtered = await mountApplications({ search: "无结果" });
    expect(filtered.wrapper.text()).toMatch(/无结果|调整.*筛选|没有.*匹配/);
    const reset = filtered.wrapper.find('.state-card button');
    expect(reset).toBeTruthy();
    await reset.trigger("click");
    await filtered.router.isReady();
    await flushPromises();
    expect(filtered.router.currentRoute.value.query.search).toBeUndefined();
  });
});
