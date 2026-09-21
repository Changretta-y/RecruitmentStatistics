// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import vuetify from "../src/plugins/vuetify";

const applicationApi = vi.hoisted(() => ({
  create: vi.fn(),
  createApplication: vi.fn(),
  update: vi.fn(),
  updateApplication: vi.fn(),
  patchApplication: vi.fn(),
}));

vi.mock(
  "../src/api/applications",
  () => ({
    create: applicationApi.create,
    createApplication: applicationApi.createApplication,
    update: applicationApi.update,
    updateApplication: applicationApi.updateApplication,
    patchApplication: applicationApi.patchApplication,
    default: applicationApi,
  }),
  { virtual: true },
);

const existingApplication = {
  id: 17,
  companyName: "原公司",
  positionName: "原岗位",
  applicationStatus: "in_progress",
  currentStage: "first_interview",
  applicationTime: "2026-09-01T02:00:00Z",
  aiInterviewTime: null,
  writtenTestTime: "2026-09-03T02:00:00Z",
  firstInterviewTime: "2026-09-04T02:00:00Z",
  secondInterviewTime: null,
  thirdInterviewTime: null,
  hrInterviewTime: null,
  notes: "原备注",
  createdAt: "2026-09-01T02:00:00Z",
  updatedAt: "2026-09-04T02:00:00Z",
};

const stageNames = [
  "aiInterviewTime",
  "writtenTestTime",
  "firstInterviewTime",
  "secondInterviewTime",
  "thirdInterviewTime",
  "hrInterviewTime",
];

function field(wrapper: any, ...names: string[]) {
  return wrapper.find(names.map((name) => `[name="${name}"]`).join(","));
}

function buttonByText(wrapper: any, pattern: RegExp) {
  return wrapper.findAll("button").find((button: any) => pattern.test(button.text()));
}

function requestCalls() {
  return [
    ...applicationApi.create.mock.calls,
    ...applicationApi.createApplication.mock.calls,
    ...applicationApi.update.mock.calls,
    ...applicationApi.updateApplication.mock.calls,
    ...applicationApi.patchApplication.mock.calls,
  ];
}

function lastBody() {
  const call = requestCalls()[requestCalls().length - 1] ?? [];
  return call.find((value: unknown) => value && typeof value === "object" && !Array.isArray(value)) as Record<string, unknown>;
}

async function mountForm(props: Record<string, unknown> = {}) {
  const { default: ApplicationForm } = await import("../src/components/ApplicationForm.vue");
  return mount(ApplicationForm, {
    props: { mode: "create", application: null, ...props },
    global: { plugins: [vuetify] },
  });
}

async function submit(wrapper: any) {
  await wrapper.get("form").trigger("submit.prevent");
  await flushPromises();
}

describe("WEB-APP-003 ApplicationForm", () => {
  beforeEach(() => {
    vi.resetModules();
    Object.values(applicationApi).forEach((mock) => mock.mockReset());
    applicationApi.create.mockResolvedValue({ status: 201, data: {} });
    applicationApi.createApplication.mockResolvedValue({ status: 201, data: {} });
    applicationApi.update.mockResolvedValue({ status: 200, data: {} });
    applicationApi.updateApplication.mockResolvedValue({ status: 200, data: {} });
    applicationApi.patchApplication.mockResolvedValue({ status: 200, data: {} });
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("renders create defaults and all fields, with six stage times initially null/empty", async () => {
    const wrapper = await mountForm();

    expect(field(wrapper, "companyName", "company_name").exists()).toBe(true);
    expect(field(wrapper, "positionName", "position_name").exists()).toBe(true);
    expect(field(wrapper, "applicationStatus", "application_status").exists()).toBe(true);
    expect(field(wrapper, "applicationTime", "application_time").exists()).toBe(true);
    expect(field(wrapper, "notes").exists()).toBe(true);
    for (const name of stageNames) {
      const control = field(wrapper, name, name.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`));
      expect(control.exists(), `${name} field should be public`).toBe(true);
      expect(control.element.value === "" || control.element.value === null).toBe(true);
    }
  });

  it("prefills edit fields from a copy and never mutates the original row while editing", async () => {
    const original = structuredClone(existingApplication);
    const wrapper = await mountForm({ mode: "edit", application: original });
    const company = field(wrapper, "companyName", "company_name");
    expect(company.element.value).toBe("原公司");
    await company.setValue("修改后的公司");
    expect(original.companyName).toBe("原公司");
    expect(company.element.value).toBe("修改后的公司");
  });

  it("submits ISO values for all six stages and preserves null when a stage is cleared", async () => {
    const wrapper = await mountForm();
    const isoValues = [
      "2026-09-10T01:00:00Z",
      "2026-09-11T01:00:00Z",
      "2026-09-12T01:00:00Z",
      "2026-09-13T01:00:00Z",
      "2026-09-14T01:00:00Z",
      "2026-09-15T01:00:00Z",
    ];
    for (let index = 0; index < stageNames.length; index += 1) {
      const control = field(wrapper, stageNames[index]);
      await control.setValue(isoValues[index]);
    }
    await field(wrapper, "secondInterviewTime").setValue("");
    await submit(wrapper);

    const body = lastBody();
    expect(body.ai_interview_time ?? body.aiInterviewTime).toBe(isoValues[0]);
    expect(body.written_test_time ?? body.writtenTestTime).toBe(isoValues[1]);
    expect(body.first_interview_time ?? body.firstInterviewTime).toBe(isoValues[2]);
    expect(body.second_interview_time ?? body.secondInterviewTime).toBeNull();
    expect(body.third_interview_time ?? body.thirdInterviewTime).toBe(isoValues[4]);
    expect(body.hr_interview_time ?? body.hrInterviewTime).toBe(isoValues[5]);
  });

  it("rejects missing company/position and invalid status or time before calling the API", async () => {
    const wrapper = await mountForm();
    await submit(wrapper);
    expect(requestCalls()).toHaveLength(0);
    expect(wrapper.text()).toMatch(/公司|岗位|必填/);

    await field(wrapper, "companyName", "company_name").setValue("示例公司");
    await field(wrapper, "positionName", "position_name").setValue("工程师");
    const status = field(wrapper, "applicationStatus", "application_status");
    if (status.exists()) await status.setValue("not-a-status");
    await field(wrapper, "applicationTime", "application_time").setValue("not-an-iso-time");
    await submit(wrapper);
    expect(requestCalls()).toHaveLength(0);
    expect(wrapper.text()).toMatch(/状态|时间|格式|有效/);
  });

  it("disables duplicate submit and exposes loading while a request is pending", async () => {
    let release!: (value: unknown) => void;
    applicationApi.create.mockReturnValue(new Promise((resolve) => { release = resolve; }));
    const wrapper = await mountForm();
    await field(wrapper, "companyName", "company_name").setValue("示例公司");
    await field(wrapper, "positionName", "position_name").setValue("工程师");
    const first = wrapper.get("form").trigger("submit.prevent");
    await flushPromises();
    await wrapper.get("form").trigger("submit.prevent");
    expect(requestCalls()).toHaveLength(1);
    expect(wrapper.get('button[type="submit"]').attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toMatch(/加载|提交|保存/);
    release({ status: 201, data: {} });
    await first;
    await flushPromises();
  });

  it("creates with POST semantics and after success emits close/success and refresh-to-page-one", async () => {
    const wrapper = await mountForm();
    await field(wrapper, "companyName", "company_name").setValue("示例公司");
    await field(wrapper, "positionName", "position_name").setValue("工程师");
    await submit(wrapper);

    expect(requestCalls()).toHaveLength(1);
    expect(Object.keys(wrapper.emitted())).toEqual(expect.arrayContaining([expect.stringMatching(/close|success|saved|refresh/i)]));
    const eventValues = Object.values(wrapper.emitted()).flat();
    expect(JSON.stringify(eventValues)).toMatch(/1|page/);
  });

  it("edits by PATCHing only changed fields, including null for a cleared stage", async () => {
    const original = structuredClone(existingApplication);
    const wrapper = await mountForm({ mode: "edit", application: original });
    await field(wrapper, "companyName", "company_name").setValue("新公司");
    await field(wrapper, "firstInterviewTime", "first_interview_time").setValue("");
    await submit(wrapper);

    const calls = requestCalls();
    expect(calls).toHaveLength(1);
    const body = lastBody();
    expect(JSON.stringify(body)).toContain("新公司");
    expect(body.first_interview_time ?? body.firstInterviewTime).toBeNull();
    expect(body.position_name ?? body.positionName).toBeUndefined();
    expect(original.companyName).toBe("原公司");
    expect(original.firstInterviewTime).toBe("2026-09-04T02:00:00Z");
  });

  it("keeps entered values and maps backend field errors when submission fails", async () => {
    applicationApi.create.mockRejectedValue({
      response: { status: 400, data: { code: "VALIDATION_ERROR", details: { company_name: ["公司已存在"] } } },
    });
    const wrapper = await mountForm();
    await field(wrapper, "companyName", "company_name").setValue("保留公司");
    await field(wrapper, "positionName", "position_name").setValue("保留岗位");
    await submit(wrapper);

    expect(field(wrapper, "companyName", "company_name").element.value).toBe("保留公司");
    expect(field(wrapper, "positionName", "position_name").element.value).toBe("保留岗位");
    expect(wrapper.text()).toContain("公司已存在");
  });

  it("asks for confirmation before closing a dirty form", async () => {
    const confirmMock = vi.fn(() => false);
    vi.stubGlobal("confirm", confirmMock);
    const wrapper = await mountForm();
    await field(wrapper, "companyName", "company_name").setValue("未保存公司");
    const close = wrapper.find('button[aria-label*="关闭"]');
    const closeButton = close.exists() ? close : buttonByText(wrapper, /关闭|取消/);
    expect(closeButton).toBeTruthy();
    await closeButton.trigger("click");
    expect(confirmMock).toHaveBeenCalled();
    expect(wrapper.emitted("close")).toBeUndefined();
  });
});
