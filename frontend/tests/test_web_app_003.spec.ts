// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import vuetify from '../src/plugins/vuetify';
import { publicButton, publicControl, publicGroup } from './web_app_006_dom';
vi.setConfig({ testTimeout: 15000 });

const api = vi.hoisted(() => ({ create: vi.fn(), createApplication: vi.fn(), update: vi.fn(), updateApplication: vi.fn(), patchApplication: vi.fn(), deletePosition: vi.fn(), deleteInterview: vi.fn() }));
vi.mock('../src/api/applications', () => ({ ...api, default: api }), { virtual: true });
const originalCompany = () => ({
  id: 17, companyName: '原公司', currentStage: 'first_interview', createdAt: '2026-09-01T02:00:00Z', updatedAt: '2026-09-04T02:00:00Z',
  sharedStages: [
    { type: 'ai_interview', scheduledAt: null, durationMinutes: null },
    { type: 'assessment', scheduledAt: null, durationMinutes: null },
    { type: 'written_test', scheduledAt: '2026-09-03T02:00:00Z', durationMinutes: 80 },
  ],
  positions: [{ id: 18, positionName: '原岗位', applicationStatus: 'first_interview', applicationUrl: 'https://jobs.example.invalid/original', applicationTime: '2026-09-01T02:00:00Z', notes: '原备注', interviews: [{ id: 19, name: '一面', scheduledAt: '2026-09-04T02:00:00Z', durationMinutes: 60 }] }],
});
async function form(props: Record<string, unknown> = {}) {
  const { default: Form } = await import('../src/components/ApplicationForm.vue');
  return mount(Form, { props: { mode: 'create', application: null, ...props }, global: { plugins: [vuetify] } });
}
const calls = () => Object.values(api).flatMap(mock => mock.mock.calls);
const body = () => calls().at(-1)?.find((v: any) => v && typeof v === 'object');
async function submit(wrapper: any) { await wrapper.get('form').trigger('submit.prevent'); await flushPromises(); }
async function required(wrapper: any) {
  await publicControl(wrapper, '公司名称').setValue('示例公司');
  await publicControl(publicGroup(wrapper, '岗位1'), '岗位名称').setValue('工程师');
}
describe('WEB-APP-003 form behavior under APP-009 nested contract', () => {
  beforeEach(() => {
    vi.resetModules();
    Object.values(api).forEach(mock => mock.mockReset().mockResolvedValue(originalCompany()));
    vi.stubGlobal('confirm', vi.fn(() => true));
  });
  it('renders company/role fields, three shared empty stages and dynamically adds an empty interview', async () => {
    const wrapper = await form();
    expect(publicControl(wrapper, '公司名称').exists()).toBe(true);
    const role = publicGroup(wrapper, '岗位1');
    for (const label of ['岗位名称', '投递链接', '业务状态', '投递时间', '备注']) expect(publicControl(role, label).exists()).toBe(true);
    for (const label of ['AI 面时间', '测评时间', '笔试时间']) expect(publicControl(wrapper, label).element.value).toBe('');
    await publicButton(role, '添加面试').trigger('click');
    const interview = publicGroup(role, '面试1');
    expect(publicControl(interview, '面试名称').element.value).toBe('');
    expect(publicControl(interview, '面试时间').element.value).toBe('');
  });
  it('prefills a nested copy and does not mutate original company, role or interview while editing', async () => {
    const original = originalCompany(), before = structuredClone(original);
    const wrapper = await form({ mode: 'edit', application: original });
    expect(publicControl(wrapper, '公司名称').element.value).toBe('原公司');
    const role = publicGroup(wrapper, '岗位1');
    expect(publicControl(role, '投递链接').element.value).toBe(before.positions[0].applicationUrl);
    await publicControl(wrapper, '公司名称').setValue('修改后的公司');
    await publicControl(role, '备注').setValue('修改后的备注');
    await publicControl(publicGroup(role, '面试1'), '面试名称').setValue('修改后的面试');
    expect(original).toEqual(before);
  });
  it('submits dates for shared phases and four dynamic interviews, preserving null for a cleared date', async () => {
    const wrapper = await form(); await required(wrapper);
    for (const [index, label] of ['AI 面时间', '测评时间', '笔试时间'].entries()) await publicControl(wrapper, label).setValue(`2026-09-${10 + index}T09:00`);
    const role = publicGroup(wrapper, '岗位1');
    for (const [index, name] of ['一面', '二面', '三面', 'HR 面'].entries()) {
      await publicButton(role, '添加面试').trigger('click');
      const interview = publicGroup(role, `面试${index + 1}`);
      await publicControl(interview, '面试名称').setValue(name);
      await publicControl(interview, '面试时间').setValue(`2026-09-${13 + index}T09:00`);
    }
    await publicControl(publicGroup(role, '面试2'), '面试时间').setValue('');
    await submit(wrapper);
    expect(calls()).toHaveLength(1);
    for (const [index, type] of ['ai_interview', 'assessment', 'written_test'].entries()) expect(new Date(body().sharedStages.find((s: any) => s.type === type).scheduledAt).getTime()).toBe(new Date(`2026-09-${10 + index}T09:00`).getTime());
    expect(new Date(body().positions[0].interviews[0].scheduledAt).getTime()).toBe(new Date('2026-09-13T09:00').getTime());
    expect(body().positions[0].interviews[1]).toMatchObject({ scheduledAt: null, durationMinutes: null });
    expect(body().positions[0].interviews[2].name).toBe('三面');
    expect(body().positions[0].interviews[3].name).toBe('HR 面');
  });
  it('rejects missing company/role and invalid status; native date control excludes malformed text', async () => {
    const wrapper = await form(); await submit(wrapper);
    expect(calls()).toHaveLength(0); expect(wrapper.text()).toMatch(/公司|岗位|必填/);
    await required(wrapper);
    const role = publicGroup(wrapper, '岗位1');
    const status = publicControl(role, '业务状态');
    await status.setValue('not-a-status');
    const time = publicControl(role, '投递时间');
    expect(time.attributes('type')).toBe('datetime-local');
    await time.setValue('not-an-iso-time');
    expect(time.element.value).toBe('');
    expect(status.element.value).not.toBe('not-a-status');
    await submit(wrapper);
    expect(calls()).toHaveLength(1);
    expect(body().positions[0].applicationStatus).not.toBe('not-a-status');
  });
  it('disables duplicate submit and inputs while request pending and shows loading', async () => {
    let release!: (v: unknown) => void;
    const deferred = new Promise(resolve => { release = resolve; });
    Object.values(api).forEach(mock => mock.mockReturnValue(deferred));
    const wrapper = await form(); await required(wrapper);
    await wrapper.get('form').trigger('submit.prevent'); await flushPromises();
    await wrapper.get('form').trigger('submit.prevent');
    expect(calls()).toHaveLength(1);
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined();
    expect(publicControl(wrapper, '公司名称').attributes('disabled')).toBeDefined();
    expect(publicButton(wrapper, '添加岗位').attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toMatch(/加载|提交|保存/);
    release(originalCompany()); await flushPromises();
  });
  it('creates once and emits success/close with page-one refresh', async () => {
    const wrapper = await form(); await required(wrapper); await submit(wrapper);
    expect(calls()).toHaveLength(1);
    expect(Object.keys(wrapper.emitted())).toEqual(expect.arrayContaining([expect.stringMatching(/close|success|saved|refresh/i)]));
    expect(JSON.stringify(Object.values(wrapper.emitted()).flat())).toMatch(/1|page/);
  });
  it('PATCH preserves target selectors, clears one interview date and omits unchanged role fields', async () => {
    const original = originalCompany(), before = structuredClone(original);
    const wrapper = await form({ mode: 'edit', application: original });
    await publicControl(wrapper, '公司名称').setValue('新公司');
    await publicControl(publicGroup(publicGroup(wrapper, '岗位1'), '面试1'), '面试时间').setValue('');
    await submit(wrapper);
    expect(calls()).toHaveLength(1); expect(body().companyName).toBe('新公司');
    expect(body().positions[0]).toMatchObject({ id: 18 });
    expect(body().positions[0].interviews[0]).toMatchObject({ id: 19, scheduledAt: null, durationMinutes: null });
    expect(body().positions[0].positionName).toBeUndefined();
    expect(original).toEqual(before);
  });
  it('retains company/role/link input and maps server field errors after failed submission', async () => {
    Object.values(api).forEach(mock => mock.mockRejectedValue({ response: { status: 400, data: { code: 'VALIDATION_ERROR', details: { company_name: ['公司已存在'] } } } }));
    const wrapper = await form(); await required(wrapper);
    await publicControl(publicGroup(wrapper, '岗位1'), '投递链接').setValue('https://jobs.example.invalid/preserved');
    await submit(wrapper);
    expect(publicControl(wrapper, '公司名称').element.value).toBe('示例公司');
    expect(publicControl(publicGroup(wrapper, '岗位1'), '岗位名称').element.value).toBe('工程师');
    expect(publicControl(publicGroup(wrapper, '岗位1'), '投递链接').element.value).toBe('https://jobs.example.invalid/preserved');
    expect(wrapper.text()).toContain('公司已存在');
  });
  it('asks before closing a dirty form and cancellation preserves it', async () => {
    const confirm = vi.fn(() => false); vi.stubGlobal('confirm', confirm);
    const wrapper = await form(); await publicControl(wrapper, '公司名称').setValue('未保存公司');
    const close = wrapper.findAll('button').find((b: any) => /关闭|取消/.test(b.text()) || /关闭/.test(b.attributes('aria-label') ?? ''));
    expect(close).toBeTruthy(); await close.trigger('click');
    expect(confirm).toHaveBeenCalled(); expect(wrapper.emitted('close')).toBeUndefined();
  });
});
