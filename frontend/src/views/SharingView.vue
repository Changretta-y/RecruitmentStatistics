<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { VDialog } from "vuetify/components/VDialog";
import AppShell from "../components/AppShell.vue";
import SharingAvatar from "../components/SharingAvatar.vue";
import SharingUserRow from "../components/SharingUserRow.vue";
import * as sharing from "../api/sharing";
import { APPLICATION_STATUS_LABELS } from "../types/application";
import type { SharedApplication, SharedApplicationPage, SharingConnection, SharingHistory, SharingRequest, SharingUser } from "../types/sharing";

const me = ref<SharingUser | null>(null);
const recommended = ref<SharingUser[]>([]);
const history = ref<SharingHistory>({ incoming: [], outgoing: [] });
const connected = ref<SharingConnection[]>([]);
const selected = ref<SharingConnection | null>(null);
const loadingPanel = ref(true);
const refreshing = ref(false);
const panelError = ref("");
const notice = ref("");
const searchId = ref("");
const searched = ref<SharingUser | null>(null);
const searching = ref(false);
const searchError = ref("");
const busy = ref(new Set<string>());
const revokeTarget = ref<SharingConnection | null>(null);
const revokeDialog = ref(false);
const revokeError = ref("");
const records = ref<SharedApplicationPage | null>(null);
const loadingRecords = ref(false);
const recordsError = ref("");
const recordSearch = ref("");
const page = ref(1);
const pageSize = ref(20);
let recordsSequence = 0;
let panelSequence = 0;
let searchSequence = 0;
let mounted = true;
const stages = [
  { key: "ai_interview", label: "AI 面试" }, { key: "written_test", label: "笔试" },
  { key: "first_interview", label: "一面" }, { key: "second_interview", label: "二面" },
  { key: "third_interview", label: "三面" }, { key: "hr_interview", label: "HR 面试" },
];
function statusOf(error: unknown): number | undefined { return (error as { response?: { status?: number } })?.response?.status; }
function isBusy(key: string): boolean { return busy.value.has(key); }
function setBusy(key: string, value: boolean): void { const next = new Set(busy.value); value ? next.add(key) : next.delete(key); busy.value = next; }
function historyStatus(item: SharingRequest): string {
  return { pending: item.sender.id === me.value?.id ? "待对方同意" : "待我同意", accepted: "已同意", rejected: "已拒绝", revoked: "已解除" }[item.status];
}
function displayTime(value: unknown): string {
  if (typeof value !== "string" || !value) return "未设置";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
}
function duration(record: SharedApplication, key: string): string {
  const value = record[`${key}_duration_minutes`];
  return typeof value === "number" ? `${value} 分钟` : "—";
}
function safeLink(value: string): string | null {
  try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol) ? url.href : null; } catch { return null; }
}

async function loadPanel(): Promise<void> {
  const sequence = ++panelSequence;
  panelError.value = "";
  try {
    const [current, users, requests, members] = await Promise.all([sharing.sharingMe(), sharing.recommendations(), sharing.requestHistory(), sharing.connections()]);
    if (!mounted || sequence !== panelSequence) return;
    me.value = current; recommended.value = users; history.value = requests; connected.value = members;
    if (selected.value && !members.some(member => member.id === selected.value!.id)) loseAccess();
  } catch { if (sequence === panelSequence && mounted) panelError.value = "共享信息加载失败，请重试。"; }
  finally { if (sequence === panelSequence && mounted) loadingPanel.value = false; }
}
async function refreshRecommendations(): Promise<void> {
  if (refreshing.value) return;
  refreshing.value = true; panelError.value = "";
  try { recommended.value = await sharing.recommendations(); }
  catch { panelError.value = "推荐用户加载失败，请重试。"; }
  finally { refreshing.value = false; }
}
async function findUser(): Promise<void> {
  const sequence = ++searchSequence;
  const normalized = searchId.value.trim();
  searchError.value = ""; searched.value = null; searching.value = false;
  if (!/^[1-9]\d*$/.test(normalized) || !Number.isSafeInteger(Number(normalized))) { searchError.value = "请输入有效的正整数用户 ID。"; return; }
  searching.value = true;
  try { const result = await sharing.searchUser(normalized); if (mounted && sequence === searchSequence) searched.value = result; }
  catch (error) { if (mounted && sequence === searchSequence) searchError.value = statusOf(error) === 404 ? "未找到用户" : "搜索失败，请重试。"; }
  finally { if (sequence === searchSequence) searching.value = false; }
}
async function apply(user: SharingUser): Promise<void> {
  const key = `user:${user.id}`;
  if (isBusy(key) || user.relationship !== "none") return;
  setBusy(key, true); panelError.value = ""; notice.value = "";
  try {
    await sharing.sendRequest(user.id);
    user.relationship = "outgoing_pending";
    if (searched.value?.id === user.id) searched.value.relationship = "outgoing_pending";
    notice.value = "申请已发送，待对方同意。";
    await loadPanel();
  } catch (error) {
    panelError.value = statusOf(error) === 409 ? "申请状态已变化，已刷新，请查看当前状态。" : "申请失败，请重试。";
    if (statusOf(error) === 409) { await loadPanel(); if (searched.value?.id === user.id) await findUser(); panelError.value = "申请状态已变化，请查看当前状态。"; }
  } finally { setBusy(key, false); }
}
async function respond(item: SharingRequest, decision: "accepted" | "rejected"): Promise<void> {
  const key = `request:${item.id}`;
  if (isBusy(key)) return;
  setBusy(key, true); panelError.value = ""; notice.value = "";
  try { await sharing.respondRequest(item.id, decision); notice.value = decision === "accepted" ? "已同意，双方现在可以互相查看。" : "已拒绝申请。"; await loadPanel(); }
  catch (error) { if (statusOf(error) === 409) await loadPanel(); panelError.value = "处理申请失败，请刷新或重试。"; }
  finally { setBusy(key, false); }
}
function clearSelection(): void {
  ++recordsSequence; selected.value = null; records.value = null; loadingRecords.value = false; recordsError.value = ""; recordSearch.value = ""; page.value = 1;
}
function loseAccess(): void { clearSelection(); notice.value = "共享已失效，对方的记录已清除。"; }
async function selectUser(member: SharingConnection): Promise<void> {
  if (member.user.relationship !== "connected") return;
  clearSelection(); selected.value = member; notice.value = "";
  await loadRecords();
}
async function loadRecords(): Promise<void> {
  const target = selected.value;
  if (!target) return;
  const sequence = ++recordsSequence;
  loadingRecords.value = true; recordsError.value = ""; records.value = null;
  try {
    const result = await sharing.sharedApplications(target.user.id, page.value, pageSize.value, recordSearch.value.trim());
    if (mounted && sequence === recordsSequence && selected.value?.id === target.id) records.value = result;
  } catch (error) {
    if (!mounted || sequence !== recordsSequence) return;
    if (statusOf(error) === 404) {
      loseAccess(); connected.value = connected.value.filter(member => member.id !== target.id);
      await loadPanel();
    } else recordsError.value = "记录加载失败，请重试。";
  } finally { if (sequence === recordsSequence) loadingRecords.value = false; }
}
async function queryRecords(): Promise<void> { page.value = 1; await loadRecords(); }
async function movePage(next: number): Promise<void> { if (next < 1) return; page.value = next; await loadRecords(); }
function openRevoke(member: SharingConnection): void { revokeTarget.value = member; revokeError.value = ""; revokeDialog.value = true; }
async function revoke(): Promise<void> {
  const target = revokeTarget.value;
  if (!target || isBusy("revoke")) return;
  setBusy("revoke", true); revokeError.value = "";
  try {
    await sharing.revokeConnection(target.id);
    connected.value = connected.value.filter(member => member.id !== target.id);
    if (selected.value?.id === target.id) clearSelection();
    if (searched.value?.id === target.user.id) searched.value.relationship = "none";
    revokeDialog.value = false; notice.value = "共享已解除，双方无法再查看彼此的记录。";
    await loadPanel();
  } catch (error) {
    if (statusOf(error) === 404) { revokeDialog.value = false; if (selected.value?.id === target.id) loseAccess(); await loadPanel(); }
    else revokeError.value = "解除共享失败，请重试。";
  } finally { setBusy("revoke", false); }
}
onMounted(() => { void loadPanel(); });
onBeforeUnmount(() => { mounted = false; ++recordsSequence; ++panelSequence; ++searchSequence; });
</script>

<template>
  <AppShell title="投递共享">
    <div class="sharing-page">
      <header class="page-header"><div><h1>投递共享</h1><p>在彼此同意后，一起了解求职进度。</p></div><span class="privacy-badge">双向同意 · 随时解除</span></header>
      <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      <div class="sharing-stage" :class="{ selected: selected }">
        <section class="user-panel" aria-label="共享用户面板">
          <div class="panel-heading">
            <div v-if="me" class="self"><SharingAvatar :avatar="me.avatar" :username="me.username" /><div><strong>{{ me.username }}</strong><small>我的 ID：{{ me.id }}</small></div></div>
            <span v-else>发现同行者</span>
            <button v-if="selected" class="text-button" @click="clearSelection">返回用户选择</button>
          </div>
          <p class="consent-note">同意后双方可互相查看，个人备注不共享。任何一方解除共享，无需对方同意。</p>
          <div v-if="loadingPanel" class="state" role="status">正在加载共享信息…</div>
          <div v-if="panelError" class="error" role="alert">{{ panelError }} <button class="text-button" @click="loadPanel">刷新</button></div>
          <form class="id-search" @submit.prevent="findUser"><label for="sharing-user-id">用户 ID</label><div class="input-row"><input id="sharing-user-id" v-model="searchId" type="text" inputmode="numeric" autocomplete="off" placeholder="输入对方的数字 ID" /><button class="primary-button" :disabled="searching" type="submit">搜索用户</button></div></form>
          <p v-if="searchError" class="error" role="alert">{{ searchError }}</p>
          <ul v-if="searched" class="people-list search-result"><SharingUserRow :user="searched" :busy="isBusy(`user:${searched.id}`)" @request="apply" /></ul>
          <div class="panel-sections">
            <section class="panel-section shared-section"><h2>已共享用户</h2><p v-if="!connected.length" class="empty-hint">暂无共享用户，通过申请后会出现在这里。</p><ul class="people-list"><li v-for="member in connected" :key="member.id" class="connection-row"><SharingAvatar :avatar="member.user.avatar" :username="member.user.username" /><div class="person-details"><button class="member-button" :aria-pressed="selected?.id === member.id" @click="selectUser(member)">{{ member.user.username }}</button><small>ID {{ member.user.id }}</small></div><button class="text-button revoke-button" @click="openRevoke(member)">解除共享</button></li></ul></section>
            <section class="panel-section recommendations-section"><div class="section-title"><h2>推荐用户</h2><button class="text-button" :disabled="refreshing" @click="refreshRecommendations">换一批</button></div><p v-if="!recommended.length && !loadingPanel" class="empty-hint">暂无可推荐用户，可通过 ID 搜索。</p><ul class="people-list recommendations"><SharingUserRow v-for="user in recommended" :key="user.id" :user="user" :busy="isBusy(`user:${user.id}`)" @request="apply" /></ul></section>
            <section class="panel-section"><h2>收到的申请</h2><p v-if="!history.incoming.length" class="empty-hint">暂无收到的申请</p><ul class="people-list"><li v-for="item in history.incoming" :key="item.id" class="request-row"><SharingAvatar :avatar="item.sender.avatar" :username="item.sender.username" /><div class="person-details"><strong>{{ item.sender.username }}</strong><small>ID {{ item.sender.id }} · {{ historyStatus(item) }}</small><time :datetime="item.created_at">{{ displayTime(item.created_at) }}</time></div><div v-if="item.status === 'pending'" class="request-actions"><button class="text-button" :disabled="isBusy(`request:${item.id}`)" @click="respond(item, 'accepted')">同意</button><button class="text-button muted" :disabled="isBusy(`request:${item.id}`)" @click="respond(item, 'rejected')">拒绝</button></div></li></ul></section>
            <section class="panel-section"><h2>发出的申请</h2><p v-if="!history.outgoing.length" class="empty-hint">暂无发出的申请</p><ul class="people-list"><li v-for="item in history.outgoing" :key="item.id" class="request-row"><SharingAvatar :avatar="item.recipient.avatar" :username="item.recipient.username" /><div class="person-details"><strong>{{ item.recipient.username }}</strong><small>ID {{ item.recipient.id }} · {{ historyStatus(item) }}</small><time :datetime="item.created_at">{{ displayTime(item.created_at) }}</time></div></li></ul></section>
          </div>
        </section>

        <section v-if="selected" class="records-panel" aria-label="共享投递记录">
          <header class="records-heading"><div><h2>{{ selected.user.username }} 的投递记录</h2><p>ID {{ selected.user.id }} · 只读共享</p></div><span class="readonly-badge">只读</span></header>
          <form class="record-query" @submit.prevent="queryRecords"><div><label for="shared-record-search">搜索公司或岗位</label><input id="shared-record-search" v-model="recordSearch" type="text" placeholder="公司名称 / 岗位名称" /></div><button class="primary-button" type="submit">搜索记录</button><div><label for="shared-page-size">每页</label><select id="shared-page-size" v-model.number="pageSize" @change="queryRecords"><option v-for="size in [10, 20, 50, 100]" :key="size" :value="size">{{ size }}</option></select></div></form>
          <p v-if="loadingRecords" class="state" role="status">正在加载投递记录…</p>
          <div v-else-if="recordsError" class="state error" role="alert">{{ recordsError }}<button class="text-button" @click="loadRecords">重试</button></div>
          <p v-else-if="records && !records.results.length" class="state">{{ recordSearch ? '没有匹配的投递记录。' : '暂无投递记录。' }}</p>
          <div v-else-if="records" class="record-list"><article v-for="record in records.results" :key="record.id" class="record-card"><header><div><h3>{{ record.company_name }}</h3><p>{{ record.position_name }}</p></div><span class="status-chip">{{ APPLICATION_STATUS_LABELS[record.current_stage] }}</span></header><div class="record-meta"><span>投递时间：{{ displayTime(record.application_time) }}</span><a v-if="safeLink(record.application_url)" :href="safeLink(record.application_url)!" target="_blank" rel="noopener noreferrer">投递链接 ↗</a></div><dl class="stage-grid"><div v-for="stage in stages" :key="stage.key"><dt>{{ stage.label }}</dt><dd>{{ displayTime(record[`${stage.key}_time`]) }}</dd><dd>时长：{{ duration(record, stage.key) }}</dd></div></dl><footer>创建：{{ displayTime(record.created_at) }} · 更新：{{ displayTime(record.updated_at) }}</footer></article></div>
          <nav v-if="records && !loadingRecords" class="record-pagination" aria-label="共享记录分页"><span>共 {{ records.count }} 条</span><button class="text-button" :disabled="page <= 1" @click="movePage(page - 1)">上一页</button><span>第 {{ page }} / {{ Math.max(1, records.total_pages) }} 页</span><button class="text-button" :disabled="page >= records.total_pages" @click="movePage(page + 1)">下一页</button></nav>
        </section>
      </div>
    </div>
    <VDialog v-model="revokeDialog" max-width="440" :persistent="isBusy('revoke')" aria-labelledby="revoke-title">
      <section class="revoke-dialog"><h2 id="revoke-title">解除共享？</h2><p>解除与 {{ revokeTarget?.user.username }} 的共享后，双方立即无法查看彼此的投递记录，无需对方同意。</p><p v-if="revokeError" class="error" role="alert">{{ revokeError }}</p><div class="dialog-actions"><button class="text-button" :disabled="isBusy('revoke')" @click="revokeDialog = false">取消</button><button class="primary-button danger" :disabled="isBusy('revoke')" @click="revoke">确认解除</button></div></section>
    </VDialog>
  </AppShell>
</template>

<style scoped>
.sharing-page { padding:28px; max-width:1600px; margin:auto; }
.page-header { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:24px; } h1 { font-size:1.25rem; margin:0 0 6px; color:#182230; } h2 { font-size:.95rem; margin:0; } p { margin:0; } .page-header p { color:#667085; font-size:.87rem; }
.privacy-badge,.readonly-badge { color:#0f766e; background:#e8f6f1; border-radius:30px; padding:8px 12px; font-size:.76rem; white-space:nowrap; }
.sharing-stage { position:relative; min-height:max(620px, calc(100vh - 170px)); }
.user-panel { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:min(760px,100%); max-height:calc(100vh - 170px); overflow:auto; padding:22px; border:1px solid #e1e7f0; border-radius:22px; background:#fff; box-shadow:0 18px 60px #1b2c6012; transition:left .42s ease,top .42s ease,width .42s ease,transform .42s ease; z-index:1; scrollbar-width:thin; }
.selected .user-panel { left:calc(100% - 330px); top:0; transform:translate(0,0); width:330px; max-height:calc(100vh - 170px); padding:18px; }
.panel-heading { display:flex; align-items:center; justify-content:space-between; gap:8px; }.self { display:flex; align-items:center; gap:10px; min-width:0; }.self div { display:grid; gap:3px; min-width:0; }.self strong { font-size:.88rem; overflow-wrap:anywhere; }.self small,small { color:#667085; font-size:.75rem; }
.consent-note { background:#f4f7fc; padding:10px 12px; margin:14px 0; border-radius:10px; color:#536078; font-size:.77rem; line-height:1.6; }
label { display:block; font-size:.77rem; font-weight:600; margin-bottom:6px; color:#475467; }.input-row { display:flex; gap:8px; } input,select { border:1px solid #d0d8e6; border-radius:9px; background:#fff; padding:10px; min-width:0; width:100%; color:#182230; font-size:.85rem; } input:focus,select:focus { outline:2px solid #3157d5; outline-offset:1px; }
.primary-button { background:#3157d5; color:white; border-radius:9px; padding:10px 14px; font-size:.8rem; white-space:nowrap; font-weight:600; }.primary-button:hover { background:#2547bb; } button:disabled { opacity:.5; cursor:default; } button:focus-visible { outline:2px solid #3157d5; outline-offset:3px; } .text-button { color:#3157d5; border-radius:8px; padding:6px; font-size:.78rem; white-space:nowrap; } .text-button:hover { background:#eff4ff; } .muted { color:#667085; }
.panel-sections { display:grid; grid-template-columns:1fr 1fr; gap:18px 24px; margin-top:20px; }.panel-section { min-width:0; border-top:1px solid #eef1f6; padding-top:14px; }.shared-section,.recommendations-section { grid-column:1/-1; }.section-title { display:flex; align-items:center; justify-content:space-between; }.people-list { list-style:none; padding:0; margin:6px 0 0; }.recommendations { display:grid; grid-template-columns:1fr 1fr; gap:0 24px; }.connection-row,.request-row { display:flex; align-items:center; gap:9px; padding:10px 0; min-width:0; }.person-details { display:grid; flex:1; min-width:0; gap:3px; }.person-details strong { font-size:.85rem; overflow-wrap:anywhere; }.member-button { padding:0; text-align:left; color:#3157d5; font-size:.85rem; font-weight:600; overflow-wrap:anywhere; }.member-button[aria-pressed=true] { color:#0f766e; }.revoke-button { color:#b42318; }.request-actions { display:flex; }.person-details time { font-size:.69rem; color:#98a2b3; }.empty-hint { font-size:.77rem; color:#98a2b3; padding:12px 0; }.selected .panel-sections,.selected .recommendations { grid-template-columns:1fr; }.selected .panel-heading { align-items:flex-start; flex-direction:column; }.selected .shared-section,.selected .recommendations-section { grid-column:auto; }
.records-panel { width:calc(100% - 354px); min-width:0; }.records-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:20px; }.records-heading h2 { overflow-wrap:anywhere; font-size:1.05rem; }.records-heading p { color:#667085; font-size:.8rem; margin-top:5px; }.record-query { display:flex; align-items:end; gap:10px; margin-bottom:20px; }.record-query div:first-child { flex:1; min-width:0; }.record-query div:last-child { width:78px; flex-shrink:0; }.record-list { display:grid; gap:16px; }.record-card { padding:20px; background:#fff; border:1px solid #e1e7f0; border-radius:16px; }.record-card header { display:flex; justify-content:space-between; align-items:start; gap:10px; }.record-card h3 { font-size:1rem; overflow-wrap:anywhere; margin:0 0 5px; }.record-card header p { color:#667085; font-size:.82rem; }.status-chip { color:#3157d5; background:#eff4ff; font-size:.72rem; border-radius:20px; padding:5px 9px; white-space:nowrap; }.record-meta { display:flex; flex-wrap:wrap; gap:10px 18px; font-size:.76rem; color:#667085; padding:16px 0; }.record-meta a { color:#3157d5; }.stage-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; border-top:1px solid #eef1f6; margin:0; padding-top:16px; }.stage-grid dt { color:#475467; font-size:.77rem; font-weight:600; margin-bottom:4px; }.stage-grid dd { margin:0; font-size:.73rem; color:#667085; line-height:1.6; overflow-wrap:anywhere; }.record-card footer { border-top:1px solid #eef1f6; margin-top:16px; padding-top:12px; font-size:.7rem; color:#98a2b3; overflow-wrap:anywhere; }.record-pagination { display:flex; justify-content:center; align-items:center; gap:8px; flex-wrap:wrap; margin-top:20px; font-size:.8rem; }.state { padding:40px 12px; text-align:center; color:#667085; }.error { color:#b42318; font-size:.8rem; margin:10px 0; }.notice { background:#e8f6f1; color:#0f766e; border-radius:12px; padding:12px 16px; font-size:.85rem; margin-bottom:16px; }.revoke-dialog { background:#fff; border-radius:18px; padding:26px; }.revoke-dialog h2 { font-size:1.1rem; margin-bottom:16px; }.revoke-dialog p { font-size:.87rem; line-height:1.7; color:#667085; }.dialog-actions { display:flex; justify-content:flex-end; gap:12px; margin-top:24px; }.danger { background:#b42318; }
@media(max-width:1100px) { .sharing-stage { min-height:0; display:flex; flex-direction:column; gap:24px; }.user-panel,.selected .user-panel { position:relative; left:auto; top:auto; transform:none; width:100%; max-height:600px; }.records-panel { width:100%; }.selected .panel-heading { flex-direction:row; }.selected .panel-sections { grid-template-columns:1fr 1fr; }.selected .shared-section,.selected .recommendations-section { grid-column:1/-1; }.selected .recommendations { grid-template-columns:1fr 1fr; } }
@media(max-width:680px) { .sharing-page { padding:20px 14px; }.privacy-badge { display:none; }.user-panel,.selected .user-panel { padding:16px; max-height:520px; }.panel-sections,.selected .panel-sections,.recommendations,.selected .recommendations { grid-template-columns:1fr; }.shared-section,.recommendations-section,.selected .shared-section,.selected .recommendations-section { grid-column:auto; }.page-header { margin-bottom:18px; }.record-query { flex-wrap:wrap; }.record-query div:first-child { flex:1 1 100%; }.record-card { padding:16px; }.stage-grid { gap:12px 8px; }.records-heading h2 { font-size:.95rem; } }
@media(prefers-reduced-motion:reduce) { .user-panel { transition:none; } }
</style>
