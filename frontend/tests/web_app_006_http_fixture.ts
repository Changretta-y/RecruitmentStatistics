import { expect, type Page, type Route } from '@playwright/test';

export const DATE = '2026-09-29T02:00:00Z';
export const makePosition = (id: number, name: string) => ({
  id, position_name: name, application_status: 'in_progress',
  application_url: `https://jobs.example.invalid/${id}`, application_time: DATE, notes: `${name}备注`,
  interviews: [
    { id: id * 10, name: '技术面', scheduled_at: DATE, duration_minutes: 90 },
    { id: id * 10 + 1, name: '技术面', scheduled_at: '2026-09-30T02:00:00Z', duration_minutes: 40 },
  ],
});
export const makeCompany = () => ({
  ...makePosition(902, '后端工程师'), id: 901, company_name: '多岗位示例科技',
  positions: [makePosition(902, '后端工程师'), makePosition(903, '前端工程师')],
  shared_stages: [
    { type: 'ai_interview', scheduled_at: DATE, duration_minutes: 30 },
    { type: 'assessment', scheduled_at: DATE, duration_minutes: 45 },
    { type: 'written_test', scheduled_at: DATE, duration_minutes: 60 },
  ], current_stage: '技术面', created_at: DATE, updated_at: DATE,
  ai_interview_time: DATE, ai_interview_duration_minutes: 30,
  written_test_time: DATE, written_test_duration_minutes: 60,
});
export const positionGroup = (page: Page, number: number) => page.getByRole('group', { name: `岗位${number}`, exact: true });
export const interviewGroup = (page: Page, position: number, interview: number) => positionGroup(page, position).getByRole('group', { name: `面试${interview}`, exact: true });
export const saveButton = (page: Page) => page.getByRole('button', { name: /^(保存|保存进度|保存修改|创建|创建进度)$/ });

export async function companyHttpFixture(page: Page) {
  const state = {
    records: [makeCompany()] as any[], calls: [] as { method: string; path: string; body: any; query: string }[],
    nextId: 1001, deleteFailures: 0, saveFailures: 0, listFailures: 0, fieldError: null as null | Record<string, unknown>,
    holdSave: false, releaseSave: (() => {}) as () => void,
  };
  async function json(route: Route, status: number, body?: unknown) {
    await route.fulfill({ status, contentType: 'application/json', body: body === undefined ? '' : JSON.stringify(body) });
  }
  function applyNested(previous: any, input: any) {
    const result = { ...previous, ...input, id: previous?.id ?? state.nextId++, created_at: DATE, updated_at: DATE };
    result.positions = [...(previous?.positions ?? [])].map(p => structuredClone(p));
    for (const item of input.positions ?? []) {
      const existing = result.positions.find((p: any) => p.id === item.id);
      const p = { ...(existing ?? {}), ...item, id: existing?.id ?? state.nextId++ };
      p.interviews = [...(existing?.interviews ?? [])].map((i: any) => structuredClone(i));
      for (const interview of item.interviews ?? []) {
        const old = p.interviews.find((i: any) => i.id === interview.id);
        const value = { ...(old ?? {}), ...interview, id: old?.id ?? state.nextId++ };
        if (old) Object.assign(old, value); else p.interviews.push(value);
      }
      if (existing) Object.assign(existing, p); else result.positions.push(p);
    }
    result.shared_stages = [...(previous?.shared_stages ?? [])].map((s: any) => structuredClone(s));
    for (const stage of input.shared_stages ?? []) {
      const old = result.shared_stages.find((s: any) => s.type === stage.type);
      if (old) Object.assign(old, stage); else result.shared_stages.push(structuredClone(stage));
    }
    return result;
  }
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), url = new URL(request.url());
    const path = url.pathname, method = request.method(), body = request.postDataJSON();
    state.calls.push({ path, method, body, query: url.search });
    if (path === '/api/v1/auth/login/') return json(route, 200, { access: 'synthetic-access', refresh: 'synthetic-refresh', user: { id: 899, username: 'web_app_006', email: 'test@example.invalid' } });
    if (path === '/api/v1/auth/me/') return json(route, 200, { id: 899, username: 'web_app_006', email: 'test@example.invalid' });
    if (method === 'GET' && path === '/api/v1/applications/') {
      if (state.listFailures-- > 0) return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '加载失败，请重试' });
      const pageNo = Number(url.searchParams.get('page') ?? 1), size = Number(url.searchParams.get('page_size') ?? 20);
      return json(route, 200, { results: state.records, count: 45, page: pageNo, page_size: size, total_pages: Math.ceil(45 / size), next: null, previous: null });
    }
    const match = path.match(/^\/api\/v1\/applications\/(\d+)\/$/);
    if (match && method === 'GET') return json(route, 200, state.records.find(c => c.id === Number(match[1])));
    if ((method === 'POST' && path === '/api/v1/applications/') || (match && method === 'PATCH')) {
      if (state.holdSave) await new Promise<void>(resolve => { state.releaseSave = resolve; });
      if (state.fieldError) return json(route, 400, { code: 'VALIDATION_ERROR', details: state.fieldError });
      if (state.saveFailures-- > 0) return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '保存失败，请重试' });
      const previous = match ? state.records.find(c => c.id === Number(match[1])) : null;
      const result = applyNested(previous, body);
      if (previous) Object.assign(previous, result); else state.records.push(result);
      return json(route, previous ? 200 : 201, result);
    }
    if (method === 'DELETE') {
      if (state.deleteFailures-- > 0) return json(route, 503, { code: 'SERVICE_UNAVAILABLE', message: '删除失败，请重试' });
      const child = path.match(/^\/api\/v1\/applications\/(\d+)\/positions\/(\d+)\/(?:interviews\/(\d+)\/)?$/);
      if (child) {
        const c = state.records.find(c => c.id === Number(child[1]));
        if (child[3]) {
          const p = c.positions.find((p: any) => p.id === Number(child[2]));
          p.interviews = p.interviews.filter((i: any) => i.id !== Number(child[3]));
        } else c.positions = c.positions.filter((p: any) => p.id !== Number(child[2]));
      } else if (match) state.records = state.records.filter(c => c.id !== Number(match[1]));
      return json(route, 204);
    }
    return json(route, 404, { code: 'NOT_FOUND' });
  });
  await page.goto('/login');
  await page.locator('input[name="username"]').fill('web_app_006');
  await page.locator('input[name="password"]').fill('Synthetic_Secret_123');
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await expect(page.getByRole('row').filter({ hasText: '多岗位示例科技' })).toHaveCount(1);
  return state;
}
export async function editCompany(page: Page) {
  const row = page.getByRole('row').filter({ hasText: '多岗位示例科技' });
  await row.getByRole('link', { name: /编辑/ }).or(row.getByRole('button', { name: /编辑/ })).click();
  await expect(positionGroup(page, 1)).toBeVisible();
  await expect(positionGroup(page, 2)).toBeVisible();
}
