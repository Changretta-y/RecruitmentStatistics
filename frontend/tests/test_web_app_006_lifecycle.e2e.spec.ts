import { expect, test } from '@playwright/test';
import { companyHttpFixture, editCompany, positionGroup, interviewGroup, saveButton } from './web_app_006_http_fixture';

test.describe('WEB-APP-006 nested HTTP and reliable interaction', () => {
  test('creates independent positions, unique shared stages and repeated interviews then reloads server result', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await page.locator('a[href="/applications/new"]').last().click();
    await page.getByLabel('公司名称', { exact: true }).fill('新增多岗位公司');
    await positionGroup(page, 1).getByLabel('岗位名称', { exact: true }).fill('后端新增');
    await positionGroup(page, 1).getByLabel('投递链接', { exact: true }).fill('https://jobs.example.invalid/backend');
    await positionGroup(page, 1).getByLabel('备注', { exact: true }).fill('独立后端备注');
    await page.getByRole('button', { name: '添加岗位', exact: true }).click();
    await positionGroup(page, 2).getByLabel('岗位名称', { exact: true }).fill('前端新增');
    await positionGroup(page, 2).getByLabel('投递链接', { exact: true }).fill('https://jobs.example.invalid/frontend');
    await positionGroup(page, 2).getByLabel('备注', { exact: true }).fill('独立前端备注');
    await page.getByLabel('测评时间', { exact: true }).fill('2026-10-05T10:00');
    for (let number = 1; number <= 2; number++) {
      await positionGroup(page, 1).getByRole('button', { name: '添加面试', exact: true }).click();
      await interviewGroup(page, 1, number).getByLabel('面试名称', { exact: true }).fill('技术面');
      await interviewGroup(page, 1, number).getByLabel('面试时间', { exact: true }).fill(`2026-10-0${number + 5}T10:00`);
    }
    await saveButton(page).click();
    await expect(page).not.toHaveURL(/\/applications\/new/);
    const writes = state.calls.filter(c => c.method === 'POST' && c.path === '/api/v1/applications/');
    expect(writes).toHaveLength(1);
    const body = writes[0].body;
    expect(body.positions).toHaveLength(2);
    expect(body.positions[0]).toMatchObject({ position_name: '后端新增', application_url: 'https://jobs.example.invalid/backend', notes: '独立后端备注' });
    expect(body.positions[1]).toMatchObject({ position_name: '前端新增', application_url: 'https://jobs.example.invalid/frontend', notes: '独立前端备注' });
    expect(body.positions[0].interviews.map((i: any) => i.name)).toEqual(['技术面', '技术面']);
    expect(body.positions.every((p: any) => p.id === undefined)).toBe(true);
    expect(body.positions[0].interviews.every((i: any) => i.id === undefined)).toBe(true);
    expect(body.shared_stages.map((s: any) => s.type).sort()).toEqual(['ai_interview', 'assessment', 'written_test']);
    expect(body.shared_stages.find((s: any) => s.type === 'assessment')).toMatchObject({ duration_minutes: 60 });
    expect(body.positions.every((p: any) => !('shared_stages' in p))).toBe(true);
    await page.reload();
    const row = page.getByRole('row').filter({ hasText: '新增多岗位公司' });
    await row.locator('button[aria-expanded]').click();
    await expect(page.getByText('前端新增', { exact: true })).toBeVisible();
    await expect(page.getByText('后端新增', { exact: true })).toBeVisible();
  });

  test('edits only target position/interview, clears shared date and explicitly deletes specified children', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await editCompany(page);
    await positionGroup(page, 1).getByLabel('备注', { exact: true }).fill('只修改后端备注');
    await interviewGroup(page, 1, 1).getByLabel('面试名称', { exact: true }).fill('架构面');
    await interviewGroup(page, 1, 2).getByRole('button', { name: '删除面试2', exact: true }).click();
    await positionGroup(page, 2).getByRole('button', { name: '移除岗位2', exact: true }).click();
    await page.getByLabel('测评时间', { exact: true }).fill('');
    await saveButton(page).click();
    await expect(positionGroup(page, 1)).toBeHidden();
    await expect(page).not.toHaveURL(/\/applications\/901\/edit/);
    const writes = state.calls.filter(c => c.method !== 'GET' && c.path.startsWith('/api/v1/applications/'));
    expect(writes[0].method).toBe('PATCH');
    expect(writes[0].body.positions[0]).toMatchObject({ id: 902, notes: '只修改后端备注', application_url: 'https://jobs.example.invalid/902' });
    expect(writes[0].body.positions[0].interviews[0]).toMatchObject({ id: 9020, name: '架构面', duration_minutes: 90 });
    expect(writes[0].body.shared_stages.find((s: any) => s.type === 'assessment')).toMatchObject({ scheduled_at: null, duration_minutes: null });
    expect(writes.filter(c => c.method === 'DELETE').map(c => c.path).sort()).toEqual(['/api/v1/applications/901/positions/902/interviews/9021/', '/api/v1/applications/901/positions/903/']);
    expect(state.records[0].positions).toHaveLength(1);
    expect(state.records[0].positions[0].interviews).toHaveLength(1);
  });

  test('PATCH success followed by DELETE failure adopts new IDs and retries remaining deletion without duplicate creation', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await editCompany(page);
    await page.getByRole('button', { name: '添加岗位', exact: true }).click();
    await positionGroup(page, 3).getByLabel('岗位名称', { exact: true }).fill('新岗位只创建一次');
    await positionGroup(page, 3).getByLabel('投递链接', { exact: true }).fill('https://jobs.example.invalid/new');
    await positionGroup(page, 1).getByRole('button', { name: '添加面试', exact: true }).click();
    await interviewGroup(page, 1, 3).getByLabel('面试名称', { exact: true }).fill('新增面试只创建一次');
    await positionGroup(page, 2).getByRole('button', { name: '移除岗位2', exact: true }).click();
    state.deleteFailures = 1;
    await saveButton(page).click();
    await expect(page.getByText(/部分更改已保存.*删除未完成/)).toBeVisible();
    await expect(positionGroup(page, 2).getByLabel('岗位名称', { exact: true })).toHaveValue('新岗位只创建一次');
    await expect(interviewGroup(page, 1, 3).getByLabel('面试名称', { exact: true })).toHaveValue('新增面试只创建一次');
    const snapshots = structuredClone(state.records[0]);
    // A subsequent edit makes retry issue PATCH with the server IDs already assigned.
    await positionGroup(page, 2).getByLabel('备注', { exact: true }).fill('失败后仍可编辑');
    await saveButton(page).click();
    await expect(positionGroup(page, 1)).toBeHidden();
    await expect(page).not.toHaveURL(/\/applications\/901\/edit/);
    const patches = state.calls.filter(c => c.method === 'PATCH');
    expect(patches).toHaveLength(2);
    const newPosition = snapshots.positions.find((p: any) => p.position_name === '新岗位只创建一次');
    const newInterview = snapshots.positions.find((p: any) => p.id === 902).interviews.find((i: any) => i.name === '新增面试只创建一次');
    expect(patches[1].body.positions.find((p: any) => p.position_name === '新岗位只创建一次')).toMatchObject({ id: newPosition.id, notes: '失败后仍可编辑', application_url: 'https://jobs.example.invalid/new' });
    expect(patches[1].body.positions.find((p: any) => p.id === 902).interviews.find((i: any) => i.name === '新增面试只创建一次').id).toBe(newInterview.id);
    expect(state.records[0].positions.filter((p: any) => p.position_name === '新岗位只创建一次')).toHaveLength(1);
    expect(state.records[0].positions.find((p: any) => p.id === 902).interviews.filter((i: any) => i.name === '新增面试只创建一次')).toHaveLength(1);
    expect(state.calls.filter(c => c.method === 'DELETE').map(c => c.path)).toEqual(['/api/v1/applications/901/positions/903/', '/api/v1/applications/901/positions/903/']);
  });

  test('field validation preserves both positions and maps the error to the target input before retry', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await editCompany(page);
    await positionGroup(page, 2).getByLabel('岗位名称', { exact: true }).fill('前端改名');
    state.fieldError = { positions: [{}, { position_name: ['目标岗位字段错误'] }] };
    await saveButton(page).click();
    await expect(positionGroup(page, 2)).toContainText('目标岗位字段错误');
    await expect(positionGroup(page, 1).getByLabel('岗位名称', { exact: true })).toHaveValue('后端工程师');
    await expect(positionGroup(page, 2).getByLabel('岗位名称', { exact: true })).toHaveValue('前端改名');
    state.fieldError = null;
    await saveButton(page).click();
    await expect(positionGroup(page, 1)).toBeHidden();
    await expect(page).not.toHaveURL(/\/applications\/901\/edit/);
    expect(state.records[0].positions[1].position_name).toBe('前端改名');
  });

  test('network save failure keeps complete input and save busy disables all input and structural controls', async ({ page }) => {
    const state = await companyHttpFixture(page);
    await editCompany(page);
    await positionGroup(page, 2).getByLabel('备注', { exact: true }).fill('失败不得丢失的前端备注');
    state.holdSave = true;
    state.saveFailures = 1;
    await saveButton(page).click();
    await expect(saveButton(page)).toBeDisabled();
    await expect(page.getByRole('button', { name: '添加岗位', exact: true })).toBeDisabled();
    await expect(positionGroup(page, 1).getByLabel('岗位名称', { exact: true })).toBeDisabled();
    await expect(positionGroup(page, 2).getByLabel('备注', { exact: true })).toBeDisabled();
    await expect(positionGroup(page, 1).getByRole('button', { name: '添加面试', exact: true })).toBeDisabled();
    await expect(page.getByRole('button', { name: /取消|关闭/ })).toBeDisabled();
    state.holdSave = false; state.releaseSave();
    await expect(page.getByText(/保存失败|重试/).first()).toBeVisible();
    await expect(positionGroup(page, 2).getByLabel('备注', { exact: true })).toHaveValue('失败不得丢失的前端备注');
    await saveButton(page).click();
    await expect(positionGroup(page, 1)).toBeHidden();
    await expect(page).not.toHaveURL(/\/applications\/901\/edit/);
    expect(state.calls.filter(c => c.method === 'PATCH')).toHaveLength(2);
  });

  test('unsaved changes are confirmed and the last position can be replaced before removal', async ({ page }) => {
    const state = await companyHttpFixture(page);
    state.records[0].positions = [state.records[0].positions[0]];
    await page.reload();
    const row = page.getByRole('row').filter({ hasText: '多岗位示例科技' });
    await row.getByRole('link', { name: /编辑/ }).or(row.getByRole('button', { name: /编辑/ })).click();
    await expect(positionGroup(page, 1).getByRole('button', { name: '移除岗位1', exact: true })).toBeDisabled();
    await page.getByRole('button', { name: '添加岗位', exact: true }).click();
    await positionGroup(page, 2).getByLabel('岗位名称', { exact: true }).fill('替代岗位');
    await expect(positionGroup(page, 1).getByRole('button', { name: '移除岗位1', exact: true })).toBeEnabled();
    await positionGroup(page, 1).getByRole('button', { name: '移除岗位1', exact: true }).click();
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('button', { name: /取消|关闭/ }).click();
    await expect(positionGroup(page, 1).getByLabel('岗位名称', { exact: true })).toHaveValue('替代岗位');
    expect(state.calls.filter(c => c.method !== 'GET' && c.path.startsWith('/api/v1/applications/'))).toEqual([]);
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: /取消|关闭/ }).click();
    await expect(positionGroup(page, 1)).toBeHidden();
  });

  test('company deletion confirms name and position count, cancellation and retry preserve the row', async ({ page }) => {
    const state = await companyHttpFixture(page);
    const row = page.getByRole('row').filter({ hasText: '多岗位示例科技' });
    await row.getByRole('button', { name: /^删除 / }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toContainText('多岗位示例科技');
    await expect(dialog).toContainText(/2\s*个岗位|岗位.*2/);
    await dialog.getByRole('button', { name: /取消/ }).click();
    expect(state.calls.filter(c => c.method === 'DELETE')).toEqual([]);
    await row.getByRole('button', { name: /^删除 / }).click();
    state.deleteFailures = 1;
    await dialog.getByRole('button', { name: /确认|删除/ }).click();
    await expect(page.getByText(/删除失败|重试/).first()).toBeVisible();
    await expect(row).toBeVisible();
    // The confirmation may stay open; if it closes, invoke the public delete action again.
    if (!(await dialog.isVisible())) await row.getByRole('button', { name: /^删除 / }).click();
    await dialog.getByRole('button', { name: /确认|删除/ }).click();
    await expect(row).toHaveCount(0);
    expect(state.calls.filter(c => c.method === 'DELETE').map(c => c.path)).toEqual(['/api/v1/applications/901/', '/api/v1/applications/901/']);
  });
});
