import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000';
const PASSWORD = 'Share_E2E_StrongPass_123';
const panel = (page: Page) => page.getByRole('region', { name: '共享用户面板', exact: true });
const records = (page: Page) => page.getByRole('region', { name: '共享投递记录', exact: true });
const headers = (access: string) => ({ Authorization: `Bearer ${access}` });

async function account(request: APIRequestContext, suffix: string) {
  const username = `share_${Date.now()}_${suffix}_${Math.random().toString(16).slice(2, 6)}`;
  const registered = await request.post(`${API}/api/v1/auth/register/`, { data: {
    username, email: `${username}@example.com`, password: PASSWORD, password_confirm: PASSWORD,
  } });
  expect(registered.status()).toBe(201);
  const response = await request.post(`${API}/api/v1/auth/login/`, { data: { username, password: PASSWORD } });
  expect(response.status()).toBe(200);
  const { access } = await response.json();
  const me = await request.get(`${API}/api/v1/sharing/me/`, { headers: headers(access) });
  expect(me.status()).toBe(200);
  return { ...(await me.json()), access, username };
}

async function signIn(page: Page, username: string) {
  await page.goto('/login');
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: /登录|login/i }).click();
  await expect(page).toHaveURL(/\/applications(?:[/?#]|$)/);
  await page.goto('/sharing');
  await expect(panel(page)).toBeVisible();
}

test('WEB-SHARE-001 real two-user consent, reciprocal read-only records and unilateral immediate revocation', async ({ browser, request }) => {
  const a = await account(request, 'a');
  const b = await account(request, 'b');
  const created = [];
  for (const [owner, company] of [[a, '互看甲专属公司'], [b, '互看乙专属公司']] as const) {
    const response = await request.post(`${API}/api/v1/applications/`, {
      headers: headers(owner.access), data: {
        company_name: company, position_name: '共享验证岗位',
        application_url: 'https://jobs.example.com/shared-e2e',
        notes: `${owner.username}不应共享的秘密备注`,
      },
    });
    expect(response.status()).toBe(201);
    created.push(await response.json());
  }
  for (const [viewer, target] of [[a, b], [b, a]] as const) {
    const denied = await request.get(`${API}/api/v1/sharing/users/${target.id}/applications/`, { headers: headers(viewer.access) });
    expect(denied.status()).toBe(404);
  }
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();
  try {
    await signIn(pageA, a.username);
    await signIn(pageB, b.username);
    await panel(pageA).getByLabel('用户 ID', { exact: true }).fill(String(b.id));
    await panel(pageA).getByRole('button', { name: '搜索用户', exact: true }).click();
    const searched = panel(pageA).getByRole('listitem').filter({ hasText: b.username });
    await searched.getByRole('button', { name: '申请互看', exact: true }).last().click();
    await expect(panel(pageA)).toContainText(/待对方同意|待处理/);
    const stillDenied = await request.get(`${API}/api/v1/sharing/users/${b.id}/applications/`, { headers: headers(a.access) });
    expect(stillDenied.status()).toBe(404);
    await pageB.reload();
    await panel(pageB).getByRole('button', { name: '同意', exact: true }).click();
    await expect(panel(pageB).getByRole('button', { name: a.username, exact: true })).toBeVisible();
    await pageA.reload();
    await panel(pageA).getByRole('button', { name: b.username, exact: true }).click();
    await panel(pageB).getByRole('button', { name: a.username, exact: true }).click();
    await expect(records(pageA)).toContainText('互看乙专属公司');
    await expect(records(pageB)).toContainText('互看甲专属公司');
    for (const page of [pageA, pageB]) {
      await expect(page.getByRole('link', { name: '日历', exact: true })).toBeVisible();
      await expect(records(page).getByRole('button', { name: /编辑|删除/ })).toHaveCount(0);
      await expect(records(page)).not.toContainText('不应共享的秘密备注');
    }
    const forbiddenPatch = await request.patch(`${API}/api/v1/applications/${created[1].id}/`, {
      headers: headers(a.access), data: { company_name: '不可修改' },
    });
    expect(forbiddenPatch.status()).toBe(404);
    await panel(pageA).getByRole('listitem').filter({ hasText: b.username }).getByRole('button', { name: '解除共享', exact: true }).click();
    await pageA.getByRole('dialog').getByRole('button', { name: /确认|确定|解除共享/ }).click();
    await expect(records(pageA)).toBeHidden();
    for (const [viewer, target] of [[a, b], [b, a]] as const) {
      const denied = await request.get(`${API}/api/v1/sharing/users/${target.id}/applications/`, { headers: headers(viewer.access) });
      expect(denied.status()).toBe(404);
    }
    await records(pageB).getByRole('textbox', { name: /公司|岗位|搜索/ }).first().fill('重新读取');
    await records(pageB).getByRole('button', { name: /搜索|查询/ }).first().click();
    await expect(pageB.getByRole('main')).toContainText('共享已失效');
    await expect(pageB.getByRole('main')).not.toContainText('互看甲专属公司');
    const reapply = await request.post(`${API}/api/v1/sharing/requests/`, { headers: headers(a.access), data: { recipient_id: b.id } });
    expect(reapply.status()).toBe(201);
  } finally {
    await contextA.close();
    await contextB.close();
  }
});
