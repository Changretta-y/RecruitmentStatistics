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

const stages = [
  { time: "aiInterviewTime", duration: "aiInterviewDurationMinutes", apiTime: "ai_interview_time", apiDuration: "ai_interview_duration_minutes" },
  { time: "writtenTestTime", duration: "writtenTestDurationMinutes", apiTime: "written_test_time", apiDuration: "written_test_duration_minutes" },
  { time: "firstInterviewTime", duration: "firstInterviewDurationMinutes", apiTime: "first_interview_time", apiDuration: "first_interview_duration_minutes" },
  { time: "secondInterviewTime", duration: "secondInterviewDurationMinutes", apiTime: "second_interview_time", apiDuration: "second_interview_duration_minutes" },
  { time: "thirdInterviewTime", duration: "thirdInterviewDurationMinutes", apiTime: "third_interview_time", apiDuration: "third_interview_duration_minutes" },
  { time: "hrInterviewTime", duration: "hrInterviewDurationMinutes", apiTime: "hr_interview_time", apiDuration: "hr_interview_duration_minutes" },
];

function control(wrapper: any, ...names: string[]) {
  return wrapper.find(names.map((name) => `[name="${name}"]`).join(","));
}

function durationControl(wrapper: any, stage: (typeof stages)[number]) {
  const snakeName = stage.apiDuration;
  return control(wrapper, stage.duration, snakeName);
}

function calls() {
  return [
    ...applicationApi.create.mock.calls,
    ...applicationApi.createApplication.mock.calls,
    ...applicationApi.update.mock.calls,
    ...applicationApi.updateApplication.mock.calls,
    ...applicationApi.patchApplication.mock.calls,
  ];
}

function lastBody() {
  const call = calls()[calls().length - 1] ?? [];
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

async function fillRequiredFields(wrapper: any) {
  await control(wrapper, "companyName", "company_name").setValue("时长测试公司");
  await control(wrapper, "positionName", "position_name").setValue("软件工程师");
}

describe("WEB-APP-005 application stage durations", () => {
  beforeEach(() => {
    vi.resetModules();
    Object.values(applicationApi).forEach((mock) => mock.mockReset());
    applicationApi.create.mockResolvedValue({ status: 201, data: {} });
    applicationApi.createApplication.mockResolvedValue({ status: 201, data: {} });
    applicationApi.update.mockResolvedValue({ status: 200, data: {} });
    applicationApi.updateApplication.mockResolvedValue({ status: 200, data: {} });
    applicationApi.patchApplication.mockResolvedValue({ status: 200, data: {} });
  });

  it("exposes an independent duration input for every stage and defaults a newly timed stage to 60 minutes", async () => {
    const wrapper = await mountForm();
    let missingDurationInput = false;

    for (const stage of stages) {
      const time = control(wrapper, stage.time, stage.apiTime);
      const duration = durationControl(wrapper, stage);
      expect(time.exists(), `${stage.time} input`).toBe(true);
      expect.soft(duration.exists(), `${stage.duration} input`).toBe(true);
      if (!duration.exists()) {
        missingDurationInput = true;
        continue;
      }
      expect(duration.element.value === "" || duration.element.value === null).toBe(true);
      expect(duration.attributes("disabled")).toBeDefined();

      await time.setValue("2026-10-08T09:30");
      expect(duration.element.value).toBe("60");
      expect(duration.attributes("disabled")).toBeUndefined();
    }
    if (missingDurationInput) return;
  });

  it("submits all six independently entered durations and keeps the default duration in the create payload", async () => {
    const wrapper = await mountForm();
    await fillRequiredFields(wrapper);

    for (let index = 0; index < stages.length; index += 1) {
      const stage = stages[index];
      await control(wrapper, stage.time).setValue(`2026-10-${String(8 + index).padStart(2, "0")}T09:30`);
      const duration = durationControl(wrapper, stage);
      expect(duration.exists(), `${stage.duration} input is required`).toBe(true);
      if (!duration.exists()) return;
      if (index !== 0) await duration.setValue(String(35 + index * 10));
    }
    await submit(wrapper);

    const body = lastBody();
    expect(calls()).toHaveLength(1);
    expect(body[stages[0].apiDuration] ?? body[stages[0].duration]).toBe(60);
    for (let index = 1; index < stages.length; index += 1) {
      expect(body[stages[index].apiDuration] ?? body[stages[index].duration]).toBe(35 + index * 10);
    }
  });

  it("prefills each saved custom duration and preserves it when its start time changes", async () => {
    const application = {
      id: 27,
      companyName: "已有公司",
      positionName: "已有岗位",
      applicationStatus: "in_progress",
      aiInterviewTime: "2026-10-08T01:30:00Z",
      aiInterviewDurationMinutes: 25,
      writtenTestTime: "2026-10-09T01:30:00Z",
      writtenTestDurationMinutes: 75,
      firstInterviewTime: "2026-10-10T01:30:00Z",
      firstInterviewDurationMinutes: 40,
      secondInterviewTime: "2026-10-11T01:30:00Z",
      secondInterviewDurationMinutes: 90,
      thirdInterviewTime: "2026-10-12T01:30:00Z",
      thirdInterviewDurationMinutes: 50,
      hrInterviewTime: "2026-10-13T01:30:00Z",
      hrInterviewDurationMinutes: 120,
      notes: "",
    };
    const wrapper = await mountForm({ mode: "edit", application });

    for (const [index, stage] of stages.entries()) {
      const duration = durationControl(wrapper, stage);
      expect(duration.exists(), `${stage.duration} input is required`).toBe(true);
      if (!duration.exists()) return;
      expect(duration.element.value).toBe(String([25, 75, 40, 90, 50, 120][index]));
    }
    await control(wrapper, stages[2].time).setValue("2026-10-20T11:00");
    await submit(wrapper);

    const body = lastBody();
    expect(body[stages[2].apiDuration] ?? body[stages[2].duration]).toBe(40);
  });

  it("clears a stage duration with its start time and submits null for both fields", async () => {
    const application = {
      id: 28,
      companyName: "清空测试公司",
      positionName: "软件工程师",
      applicationStatus: "in_progress",
      writtenTestTime: "2026-10-09T01:30:00Z",
      writtenTestDurationMinutes: 80,
    };
    const wrapper = await mountForm({ mode: "edit", application });
    const duration = durationControl(wrapper, stages[1]);
    expect(duration.exists(), `${stages[1].duration} input is required`).toBe(true);
    if (!duration.exists()) return;
    await control(wrapper, stages[1].time).setValue("");

    expect(duration.element.value === "" || duration.element.value === null).toBe(true);
    expect(duration.attributes("disabled")).toBeDefined();
    await submit(wrapper);

    const body = lastBody();
    expect(body[stages[1].apiTime] ?? body[stages[1].time]).toBeNull();
    expect(body[stages[1].apiDuration] ?? body[stages[1].duration]).toBeNull();
  });

  it.each(["0", "-1", "1441", "1.5", "abc"])("rejects invalid duration %s before submitting and identifies the field", async (value) => {
    const wrapper = await mountForm();
    await fillRequiredFields(wrapper);
    await control(wrapper, stages[4].time).setValue("2026-10-12T09:30");
    const duration = durationControl(wrapper, stages[4]);
    expect(duration.exists(), `${stages[4].duration} input is required`).toBe(true);
    if (!duration.exists()) return;
    await duration.setValue(value);
    await submit(wrapper);

    expect(calls()).toHaveLength(0);
    expect(wrapper.text()).toMatch(/时长|分钟|有效|范围/);
    expect(duration.element.value).toBe(value);
  });

  it("maps a server duration field error to that field and retains values after server or network failure", async () => {
    applicationApi.create.mockRejectedValueOnce({
      response: { status: 400, data: { code: "VALIDATION_ERROR", details: { hr_interview_duration_minutes: ["时长必须为 1 到 1440 分钟"] } } },
    });
    const wrapper = await mountForm();
    await fillRequiredFields(wrapper);
    await control(wrapper, stages[5].time).setValue("2026-10-13T09:30");
    const duration = durationControl(wrapper, stages[5]);
    expect(duration.exists(), `${stages[5].duration} input is required`).toBe(true);
    if (!duration.exists()) return;
    await duration.setValue("105");
    await submit(wrapper);

    expect(duration.element.value).toBe("105");
    expect(wrapper.text()).toContain("时长必须为 1 到 1440 分钟");
    expect(calls()).toHaveLength(1);

    applicationApi.create.mockRejectedValueOnce(new Error("network unavailable"));
    await submit(wrapper);
    expect(duration.element.value).toBe("105");
    expect(calls()).toHaveLength(2);
  });
});
