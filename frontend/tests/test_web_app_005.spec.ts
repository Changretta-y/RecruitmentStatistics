// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import vuetify from '../src/plugins/vuetify';
import { publicButton, publicControl, publicGroup } from './web_app_006_dom';
vi.setConfig({ testTimeout: 15000 });

const api = vi.hoisted(() => ({ create: vi.fn(), createApplication: vi.fn(), update: vi.fn(), updateApplication: vi.fn(), patchApplication: vi.fn(), deletePosition: vi.fn(), deleteInterview: vi.fn() }));
vi.mock('../src/api/applications', () => ({ ...api, default: api }), { virtual: true });
const shared = [
  { time: 'AI 面时间', duration: 'AI 面时长（分钟）', type: 'ai_interview' },
  { time: '测评时间', duration: '测评时长（分钟）', type: 'assessment' },
  { time: '笔试时间', duration: '笔试时长（分钟）', type: 'written_test' },
];
const interviewNames = ['一面', '二面', '三面', 'HR 面'];
const application = () => ({
  id: 27, companyName: '已有公司', currentStage: '一面',
  sharedStages: shared.map((stage, index) => ({ type: stage.type, scheduledAt: `2026-10-${String(index + 8).padStart(2, '0')}T01:30:00Z`, durationMinutes: [25, 75, 45][index] })),
  positions: [{ id: 28, positionName: '已有岗位', applicationStatus: 'in_progress', applicationUrl: 'https://jobs.example.invalid/existing', applicationTime: null, notes: '', interviews: interviewNames.map((name, index) => ({ id: 30 + index, name, scheduledAt: `2026-10-${String(index + 11).padStart(2, '0')}T01:30:00Z`, durationMinutes: [40, 90, 50, 120][index] })) }],
});
async function form(props: Record<string, unknown> = {}) {
  const { default: Form } = await import('../src/components/ApplicationForm.vue');
  return mount(Form, { props: { mode: 'create', application: null, ...props }, global: { plugins: [vuetify] } });
}
const calls = () => Object.values(api).flatMap(mock => mock.mock.calls);
const body = () => calls().at(-1)?.find((v: any) => v && typeof v === 'object');
async function submit(wrapper: any) { await wrapper.get('form').trigger('submit.prevent'); await flushPromises(); }
async function required(wrapper: any) {
  await publicControl(wrapper, '公司名称').setValue('时长测试公司');
  await publicControl(publicGroup(wrapper, '岗位1'), '岗位名称').setValue('软件工程师');
}
async function addInterviews(wrapper: any) {
  const role = publicGroup(wrapper, '岗位1');
  for (const [index, name] of interviewNames.entries()) {
    await publicButton(role, '添加面试').trigger('click');
    await publicControl(publicGroup(role, `面试${index + 1}`), '面试名称').setValue(name);
  }
}
describe('WEB-APP-005 durations for shared stages and dynamic interviews', () => {
  beforeEach(() => {
    vi.resetModules();
    Object.values(api).forEach(mock => mock.mockReset().mockResolvedValue(application()));
  });
  it('shows independent disabled duration controls and defaults each newly timed stage/interview to 60', async () => {
    const wrapper = await form();
    for (const stage of shared) {
      const time = publicControl(wrapper, stage.time), duration = publicControl(wrapper, stage.duration);
      expect(duration.element.value).toBe(''); expect(duration.attributes('disabled')).toBeDefined();
      await time.setValue('2026-10-08T09:30');
      expect(duration.element.value).toBe('60'); expect(duration.attributes('disabled')).toBeUndefined();
    }
    await addInterviews(wrapper);
    for (let index = 1; index <= 4; index++) {
      const interview = publicGroup(publicGroup(wrapper, '岗位1'), `面试${index}`);
      const time = publicControl(interview, '面试时间'), duration = publicControl(interview, '面试时长（分钟）');
      expect(duration.element.value).toBe(''); expect(duration.attributes('disabled')).toBeDefined();
      await time.setValue(`2026-10-${String(index + 8).padStart(2, '0')}T09:30`);
      expect(duration.element.value).toBe('60'); expect(duration.attributes('disabled')).toBeUndefined();
    }
  });
  it('submits all shared/position durations independently, including default 60', async () => {
    const wrapper = await form(); await required(wrapper);
    for (const [index, stage] of shared.entries()) {
      await publicControl(wrapper, stage.time).setValue(`2026-10-${String(index + 8).padStart(2, '0')}T09:30`);
      if (index > 0) await publicControl(wrapper, stage.duration).setValue(String(35 + index * 10));
    }
    for (const [index, stage] of shared.entries()) {
      expect(publicControl(wrapper, stage.time).element.value, `${stage.time} remains entered after editing other shared stages`).toBe(`2026-10-${String(index + 8).padStart(2, '0')}T09:30`);
      expect(publicControl(wrapper, stage.duration).element.value, `${stage.duration} remains entered`).toBe(String(index === 0 ? 60 : 35 + index * 10));
    }
    await addInterviews(wrapper);
    for (let index = 1; index <= 4; index++) {
      const interview = publicGroup(publicGroup(wrapper, '岗位1'), `面试${index}`);
      await publicControl(interview, '面试时间').setValue(`2026-10-${index + 10}T09:30`);
      await publicControl(interview, '面试时长（分钟）').setValue(String(index * 20));
    }
    await submit(wrapper);
    expect(calls()).toHaveLength(1);
    expect(body().sharedStages.map((s: any) => s.durationMinutes)).toEqual([60, 45, 55]);
    expect(body().positions[0].interviews.map((i: any) => i.durationMinutes)).toEqual([20, 40, 60, 80]);
  });
  it('prefills every saved custom duration and preserves it when a time changes', async () => {
    const wrapper = await form({ mode: 'edit', application: application() });
    for (const [index, stage] of shared.entries()) expect(publicControl(wrapper, stage.duration).element.value).toBe(String([25, 75, 45][index]));
    for (let index = 1; index <= 4; index++) expect(publicControl(publicGroup(publicGroup(wrapper, '岗位1'), `面试${index}`), '面试时长（分钟）').element.value).toBe(String([40, 90, 50, 120][index - 1]));
    await publicControl(publicGroup(publicGroup(wrapper, '岗位1'), '面试1'), '面试时间').setValue('2026-10-20T11:00');
    await submit(wrapper);
    expect(body().positions[0].interviews[0]).toMatchObject({ id: 30, durationMinutes: 40 });
    expect(body().positions[0].applicationUrl).toBeUndefined();
  });
  it('clears a shared duration with its date and PATCHes null for both', async () => {
    const wrapper = await form({ mode: 'edit', application: application() });
    await publicControl(wrapper, '笔试时间').setValue('');
    const duration = publicControl(wrapper, '笔试时长（分钟）');
    expect(duration.element.value).toBe(''); expect(duration.attributes('disabled')).toBeDefined();
    await submit(wrapper);
    expect(body().sharedStages.find((s: any) => s.type === 'written_test')).toMatchObject({ scheduledAt: null, durationMinutes: null });
  });
  it.each(['0', '-1', '1441', '1.5', 'abc'])('rejects invalid interview duration %s and retains field input', async (value) => {
    const wrapper = await form(); await required(wrapper); await addInterviews(wrapper);
    const interview = publicGroup(publicGroup(wrapper, '岗位1'), '面试3');
    await publicControl(interview, '面试时间').setValue('2026-10-12T09:30');
    const duration = publicControl(interview, '面试时长（分钟）');
    await duration.setValue(value); await submit(wrapper);
    expect(calls()).toHaveLength(0);
    expect(wrapper.text()).toMatch(/时长|分钟|有效|范围/);
    expect(duration.element.value).toBe(value === 'abc' ? '' : value);
  });
  it('maps server duration field error and preserves input after later network failure', async () => {
    const wrapper = await form(); await required(wrapper); await addInterviews(wrapper);
    const interview = publicGroup(publicGroup(wrapper, '岗位1'), '面试4');
    await publicControl(interview, '面试时间').setValue('2026-10-13T09:30');
    const duration = publicControl(interview, '面试时长（分钟）');
    await duration.setValue('105');
    Object.values(api).forEach(mock => mock.mockRejectedValueOnce({ response: { status: 400, data: { code: 'VALIDATION_ERROR', details: { positions: [{ interviews: [{}, {}, {}, { duration_minutes: ['时长必须为 1 到 1440 分钟'] }] }] } } } }));
    await submit(wrapper);
    expect(duration.element.value).toBe('105'); expect(wrapper.text()).toContain('时长必须为 1 到 1440 分钟'); expect(calls()).toHaveLength(1);
    Object.values(api).forEach(mock => mock.mockRejectedValueOnce(new Error('network unavailable')));
    await submit(wrapper);
    expect(duration.element.value).toBe('105'); expect(calls()).toHaveLength(2);
  });
});
