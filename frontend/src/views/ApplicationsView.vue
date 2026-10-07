<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VChip } from "vuetify/components/VChip";
import { VContainer } from "vuetify/components/VGrid";
import { VDialog } from "vuetify/components/VDialog";
import { VIcon } from "vuetify/components/VIcon";
import { VProgressLinear } from "vuetify/components/VProgressLinear";
import { VSelect } from "vuetify/components/VSelect";
import { VTable } from "vuetify/components/VTable";
import { VTextField } from "vuetify/components/VTextField";

import { delete as deleteRequest, list } from "../api/applications";
import DateTimeField from "../components/DateTimeField.vue";
import { readPositions, readSharedStages, SHARED_STAGES } from "../utils/company-application";
import AppShell from "../components/AppShell.vue";
import { useAuthStore } from "../stores/auth";
import {
  DEFAULT_ORDERING,
  parseApplicationQuery,
  serializeApplicationQuery,
} from "../utils/application-query";
import {
  APPLICATION_PAGE_SIZES,
  type ApplicationPage,
  type ApplicationQueryState,
  APPLICATION_STATUS_OPTIONS,
  APPLICATION_STATUS_LABELS,
  type ApplicationStatus,
  type ApplicationPosition,
  type JobApplication,
} from "../types/application";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const statusOptions = APPLICATION_STATUS_OPTIONS;
const orderingOptions = [
  { value: "-updated_at", title: "最近更新" },
  { value: "created_at", title: "创建时间正序" },
  { value: "-created_at", title: "创建时间倒序" },
  { value: "application_time", title: "投递时间正序" },
  { value: "-application_time", title: "投递时间倒序" },
  { value: "-first_interview_time", title: "一面时间倒序" },
];

const search = ref("");
const applicationStatus = ref<ApplicationStatus[]>([]);
const applicationTimeAfter = ref("");
const applicationTimeBefore = ref("");
const ordering = ref(DEFAULT_ORDERING);
const page = ref(1);
const pageSize = ref<(typeof APPLICATION_PAGE_SIZES)[number]>(20);
const data = ref<ApplicationPage>({
  count: 0, page: 1, pageSize: 20, totalPages: 0, next: null, previous: null, results: [],
});
const loading = ref(false);
const loaded = ref(false);
const errorKind = ref<"network" | "unauthorized" | null>(null);
const requestSequence = ref(0);
const internalRoutePaths = new Set<string>();
const confirmApplication = ref<JobApplication | null>(null);
const deleteTarget = ref<JobApplication | null>(null);
const deleteLoading = ref(false);
const deleteError = ref("");
const successMessage = ref("");
const expandedCompanies = ref(new Set<number>());

function positionsOf(application: JobApplication) { return readPositions(application as unknown as Record<string, unknown>); }
function sharedOf(application: JobApplication) { return readSharedStages(application as unknown as Record<string, unknown>); }
function toggleCompany(id: number): void {
  const next = new Set(expandedCompanies.value);
  next.has(id) ? next.delete(id) : next.add(id);
  expandedCompanies.value = next;
}

const hasResults = computed(() => data.value.results.length > 0);
const hasNext = computed(() => Boolean(data.value.next) || page.value < data.value.totalPages);
const hasPrevious = computed(() => Boolean(data.value.previous) || page.value > 1);
const hasActiveFilters = computed(() => Boolean(
  search.value || applicationStatus.value.length || applicationTimeAfter.value || applicationTimeBefore.value,
));
const deleteDialogOpen = computed({
  get: () => Boolean(confirmApplication.value),
  set: (value: boolean) => { if (!value) closeDeleteDialog(); },
});

function openEdit(application: JobApplication): void {
  if (typeof router.hasRoute === "function" && !router.hasRoute("application-edit")) return;
  void router.push({ name: "application-edit", params: { id: application.id } });
}

function applyQuery(state: ApplicationQueryState): void {
  page.value = state.page;
  pageSize.value = state.pageSize;
  search.value = state.search;
  applicationStatus.value = Array.isArray(state.applicationStatus)
    ? [...state.applicationStatus]
    : state.applicationStatus ? [state.applicationStatus] : [];
  applicationTimeAfter.value = toDateTimeLocal(state.applicationTimeAfter ?? "");
  applicationTimeBefore.value = toDateTimeLocal(state.applicationTimeBefore ?? "");
  ordering.value = state.ordering;
}

function currentQuery(): ApplicationQueryState {
  return {
    page: page.value,
    pageSize: pageSize.value,
    search: search.value,
    ...(applicationStatus.value.length > 0 ? { applicationStatus: [...applicationStatus.value] } : {}),
    ...(applicationTimeAfter.value ? { applicationTimeAfter: toIsoDateTime(applicationTimeAfter.value) } : {}),
    ...(applicationTimeBefore.value ? { applicationTimeBefore: toIsoDateTime(applicationTimeBefore.value) } : {}),
    ordering: ordering.value || DEFAULT_ORDERING,
  };
}
async function changeStatus(value: ApplicationStatus[] | null | undefined): Promise<void> {
  applicationStatus.value = Array.isArray(value) ? value : [];
  await updateUrlAndLoad({ ...currentQuery(), page: 1 });
}
function syncOrdering(event: Event): void {
  ordering.value = (event.target as HTMLSelectElement).value || DEFAULT_ORDERING;
}

async function loadApplications(query: ApplicationQueryState = currentQuery()): Promise<void> {
  const sequence = ++requestSequence.value;
  loading.value = true;
  errorKind.value = null;
  try {
    const result = await list(query);
    if (sequence !== requestSequence.value) return;
    data.value = result;
    loaded.value = true;
  } catch (error: unknown) {
    if (sequence !== requestSequence.value) return;
    loaded.value = true;
    const status = (error as { response?: { status?: number } })?.response?.status;
    errorKind.value = status === 401 ? "unauthorized" : "network";
  } finally {
    if (sequence === requestSequence.value) loading.value = false;
  }
}

async function updateUrlAndLoad(next: ApplicationQueryState): Promise<void> {
  applyQuery(next);
  const location = { path: "/applications", query: serializeApplicationQuery(next) };
  internalRoutePaths.add(router.resolve(location).fullPath);
  void loadApplications(next);
  await router.push(location);
}
async function submitQuery(): Promise<void> { await updateUrlAndLoad({ ...currentQuery(), page: 1 }); }
async function resetQuery(): Promise<void> {
  await updateUrlAndLoad({ page: 1, pageSize: 20, search: "", ordering: DEFAULT_ORDERING });
}
async function changePageSize(): Promise<void> { await updateUrlAndLoad({ ...currentQuery(), page: 1 }); }
async function goToPage(nextPage: number): Promise<void> {
  if (nextPage < 1 || (nextPage > 1 && data.value.totalPages > 0 && nextPage > data.value.totalPages)) return;
  await updateUrlAndLoad({ ...currentQuery(), page: nextPage });
}
async function retry(): Promise<void> { await loadApplications(currentQuery()); }

function openDeleteDialog(application: JobApplication): void {
  confirmApplication.value = application;
  deleteTarget.value = application;
  deleteError.value = "";
}
function closeDeleteDialog(): void {
  if (deleteLoading.value) return;
  confirmApplication.value = null;
  deleteError.value = "";
}
async function refreshAfterDelete(): Promise<void> {
  const shouldGoBack = page.value > 1 && data.value.results.length <= 1;
  await updateUrlAndLoad({ ...currentQuery(), page: shouldGoBack ? page.value - 1 : page.value });
}
async function performDelete(): Promise<void> {
  const target = deleteTarget.value;
  if (!target || deleteLoading.value) return;
  deleteLoading.value = true;
  deleteError.value = "";
  successMessage.value = "";
  try {
    await deleteRequest(target.id);
    confirmApplication.value = null;
    successMessage.value = "删除成功";
    await refreshAfterDelete();
  } catch (error: unknown) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 404) {
      confirmApplication.value = null;
      deleteError.value = "记录不存在或已被删除。";
      await loadApplications(currentQuery());
    } else if (status === 403) deleteError.value = "无权删除这条记录。";
    else if (status === 500) deleteError.value = "删除失败，服务暂时不可用，请稍后重试。";
    else deleteError.value = "删除失败，网络或服务暂时不可用，请重试。";
  } finally {
    deleteLoading.value = false;
  }
}
function displayStatus(value: ApplicationStatus): string { return APPLICATION_STATUS_LABELS[value] ?? value; }
function statusColor(position: ApplicationPosition): string {
  return position.currentStage === "rejected" ? "error" : "primary";
}
function safeLink(value: string): string | undefined {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : undefined;
  } catch { return undefined; }
}
function toDateTimeLocal(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function toIsoDateTime(value: string): string {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value}T00:00:00`;
  if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)) return value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}
function displayTime(value: string | null): string {
  return value ? toDateTimeLocal(value).slice(0, 10) : "—";
}

watch(() => route.fullPath, () => {
  const next = parseApplicationQuery(route.query as Record<string, unknown>);
  applyQuery(next);
  if (internalRoutePaths.has(route.fullPath)) {
    internalRoutePaths.delete(route.fullPath);
    return;
  }
  void loadApplications(next);
}, { flush: "sync" });
async function initializeAndLoad(): Promise<void> {
  if (typeof auth.initialize === "function" && auth.initialized === false) await auth.initialize();
  const initial = parseApplicationQuery(route.query as Record<string, unknown>);
  applyQuery(initial);
  void loadApplications(initial);
}
onMounted(() => { void initializeAndLoad(); });
</script>

<template>
  <AppShell>
  <VContainer class="applications-page py-6 py-md-10" fluid>
    <div class="page-heading mb-6">
      <div>
        <h1 class="page-title">我的投递进度</h1>
      </div>
      <VBtn class="create-button" color="primary" prepend-icon="mdi-plus" to="/applications/new">新增投递</VBtn>
    </div>

    <VCard class="query-card mb-6" elevation="1">
      <VCardText>
        <form aria-label="投递查询" class="query-grid" @submit.prevent="submitQuery">
          <VTextField v-model="search" name="search" label="关键字" placeholder="搜索公司或岗位" prepend-inner-icon="mdi-magnify" @keyup.enter.prevent="submitQuery" />
          <VSelect v-model="applicationStatus" name="status" label="投递状态（可多选）" :items="statusOptions" item-title="title" item-value="value" multiple chips closable-chips clearable @update:model-value="changeStatus" />
          <DateTimeField v-model="applicationTimeAfter" name="applicationTimeAfter" label="投递时间起" clearable />
          <DateTimeField v-model="applicationTimeBefore" name="applicationTimeBefore" label="投递时间止" clearable />
          <VSelect v-model="ordering" label="排序" :items="orderingOptions" item-title="title" item-value="value" />
          <VSelect v-model.number="pageSize" name="pageSize" label="每页" :items="APPLICATION_PAGE_SIZES" @update:model-value="changePageSize" />
          <div class="query-actions">
            <VBtn type="submit" color="primary" prepend-icon="mdi-magnify" @click.prevent="submitQuery">查询</VBtn>
            <VBtn type="button" variant="tonal" @click="resetQuery">重置</VBtn>
          </div>
        </form>
        <select v-model="ordering" class="sr-only-input" name="ordering" aria-hidden="true" tabindex="-1" @change="syncOrdering">
          <option v-for="option in orderingOptions" :key="option.value" :value="option.value">{{ option.title }}</option>
        </select>
        <select v-model.number="pageSize" class="sr-only-input" name="pageSize" aria-hidden="true" tabindex="-1" @change="changePageSize">
          <option v-for="size in APPLICATION_PAGE_SIZES" :key="size" :value="size">{{ size }}</option>
        </select>
      </VCardText>
    </VCard>

    <VAlert v-if="successMessage" class="mb-5" type="success" variant="tonal" role="status">{{ successMessage }}</VAlert>
    <VAlert v-if="deleteError && !confirmApplication" class="mb-5" type="error" variant="tonal" role="alert">
      {{ deleteError }}
      <VBtn v-if="deleteTarget" class="ml-3" size="small" variant="text" @click="performDelete">重试</VBtn>
      <VBtn v-else-if="deleteError.includes('网络')" class="ml-3" size="small" variant="text" @click="retry">重试</VBtn>
    </VAlert>

    <div v-if="loading" class="state-card">
      <VProgressLinear color="primary" indeterminate rounded />
      <p class="text-body-1 text-medium-emphasis mt-4" role="status">加载中…</p>
    </div>
    <VCard v-else-if="errorKind === 'unauthorized'" class="state-card" role="alert">
      <VCardText class="state-content">
        <VIcon color="warning" size="48">mdi-lock-alert-outline</VIcon>
        <p>登录状态已失效，请重新登录。</p>
        <VBtn color="primary" @click="router.push({ name: 'login' })">去登录</VBtn>
      </VCardText>
    </VCard>
    <VCard v-else-if="errorKind === 'network'" class="state-card" role="alert">
      <VCardText class="state-content">
        <VIcon color="error" size="48">mdi-wifi-off</VIcon>
        <p>网络请求失败，请稍后重试。</p>
        <VBtn color="primary" @click="retry">重试</VBtn>
      </VCardText>
    </VCard>
    <VCard v-else-if="loaded && !hasResults && hasActiveFilters" class="state-card">
      <VCardText class="state-content">
        <VIcon color="info" size="48">mdi-filter-off-outline</VIcon>
        <p>没有匹配的投递记录，请调整筛选条件。</p>
        <VBtn variant="tonal" @click="resetQuery">重置筛选</VBtn>
      </VCardText>
    </VCard>
    <VCard v-else-if="loaded && !hasResults" class="state-card">
      <VCardText class="state-content">
        <VIcon color="primary" size="48">mdi-briefcase-plus-outline</VIcon>
        <p>暂无投递记录，先新增第一条记录吧。</p>
        <VBtn color="primary" to="/applications/new">新增投递</VBtn>
      </VCardText>
    </VCard>

    <VCard v-else class="table-card" elevation="1">
      <VTable class="applications-table" hover>
        <colgroup><col style="width: 16%"><col style="width: 34%"><col style="width: 11%"><col style="width: 21%"><col style="width: 9%"><col style="width: 9%"></colgroup>
        <thead><tr><th>公司</th><th>岗位</th><th>当前进度</th><th>公司共享流程</th><th>更新时间</th><th>操作</th></tr></thead>
        <tbody v-for="application in data.results" :id="`company-positions-${application.id}`" :key="application.id" class="company-group">
          <tr class="company-row">
            <td class="company-cell font-weight-medium">
              <span>{{ application.companyName }}</span>
              <span v-if="positionsOf(application).length > 1" class="position-count">{{ positionsOf(application).length }} 个岗位</span>
              <button v-if="positionsOf(application).length > 1" type="button" class="expand-company" :aria-expanded="expandedCompanies.has(application.id)" :aria-controls="`company-positions-${application.id}`" :aria-label="`${expandedCompanies.has(application.id) ? '折叠' : '展开'} ${application.companyName} 的岗位`" @click="toggleCompany(application.id)">{{ expandedCompanies.has(application.id) ? '折叠' : '展开' }}</button>
            </td>
            <td class="position-cell">
              <template v-if="positionsOf(application)[0]">
                <span class="position-name">{{ positionsOf(application)[0].positionName }}</span>
                <span class="position-meta">投递：{{ displayTime(positionsOf(application)[0].applicationTime) }}</span>
                <a v-if="safeLink(positionsOf(application)[0].applicationUrl)" class="position-link" :href="safeLink(positionsOf(application)[0].applicationUrl)" target="_blank" rel="noopener noreferrer">投递链接</a>
                <span v-if="positionsOf(application)[0].notes" class="position-notes" :title="positionsOf(application)[0].notes">备注：{{ positionsOf(application)[0].notes }}</span>
                <span class="interview-flow"><span class="flow-label">面试：</span><template v-if="positionsOf(application)[0].interviews.length"><span v-for="(interview, index) in positionsOf(application)[0].interviews" :key="interview.id ?? index" class="interview-item" :title="interview.name"><span class="interview-time">{{ displayTime(interview.scheduledAt) }}</span></span></template><span v-else>暂无</span></span>
              </template>
            </td>
            <td class="status-cell"><VChip v-if="positionsOf(application)[0]" size="small" :color="statusColor(positionsOf(application)[0])" variant="tonal">{{ displayStatus(positionsOf(application)[0].currentStage) }}</VChip></td>
            <td class="shared-flow-cell">
              <div v-for="(stage, index) in sharedOf(application)" :key="stage.type" class="shared-stage">
                <span class="shared-label">{{ SHARED_STAGES[index].title }}</span>
                <span>{{ displayTime(stage.scheduledAt) }}</span>
                <span v-if="stage.durationMinutes" class="shared-duration">{{ stage.durationMinutes }} 分钟</span>
              </div>
            </td>
            <td class="updated-cell">{{ displayTime(application.updatedAt) }}</td>
            <td class="actions-cell">
              <VBtn variant="text" size="small" :href="`/applications/${application.id}/edit`" :aria-label="`编辑 ${application.companyName} ${application.positionName}`" @click.prevent="openEdit(application)">编辑</VBtn>
              <VBtn variant="text" size="small" color="error" :aria-label="`删除 ${application.companyName} ${application.positionName}`" @click="openDeleteDialog(application)" @keydown.enter.prevent="openDeleteDialog(application)">删除</VBtn>
            </td>
          </tr>
          <template v-if="expandedCompanies.has(application.id)">
            <tr v-for="(position, index) in positionsOf(application).slice(1)" :key="position.id ?? index" class="position-row">
              <td class="company-cell" aria-hidden="true"></td>
              <td class="position-cell">
                <span class="position-name">{{ position.positionName }}</span>
                <span class="position-meta">投递：{{ displayTime(position.applicationTime) }}</span>
                <a v-if="safeLink(position.applicationUrl)" class="position-link" :href="safeLink(position.applicationUrl)" target="_blank" rel="noopener noreferrer">投递链接</a>
                <span v-if="position.notes" class="position-notes" :title="position.notes">备注：{{ position.notes }}</span>
                <span class="interview-flow"><span class="flow-label">面试：</span><template v-if="position.interviews.length"><span v-for="(interview, interviewIndex) in position.interviews" :key="interview.id ?? interviewIndex" class="interview-item" :title="interview.name"><span class="interview-time">{{ displayTime(interview.scheduledAt) }}</span></span></template><span v-else>暂无</span></span>
              </td>
              <td class="status-cell"><VChip size="small" :color="statusColor(position)" variant="tonal">{{ displayStatus(position.currentStage) }}</VChip></td>
              <td class="shared-flow-cell" aria-hidden="true"></td>
              <td class="updated-cell" aria-hidden="true"></td>
              <td class="actions-cell" aria-hidden="true"></td>
            </tr>
          </template>
        </tbody>
      </VTable>
    </VCard>

    <nav v-if="loaded && !errorKind" class="pagination-bar mt-5" aria-label="分页">
      <span class="text-body-2 text-medium-emphasis">共 {{ data.count }} 条</span>
      <VBtn variant="tonal" size="small" :disabled="!hasPrevious" aria-label="上一页" @click="goToPage(page - 1)">上一页</VBtn>
      <span class="page-indicator">第 {{ page }} 页 / {{ Math.max(data.totalPages, 1) }} 页</span>
      <VBtn variant="tonal" size="small" :disabled="!hasNext" aria-label="下一页" @click="goToPage(page + 1)">下一页</VBtn>
    </nav>

    <VDialog v-model="deleteDialogOpen" max-width="460" aria-labelledby="delete-dialog-title">
      <VCard>
        <VCardText class="pa-6">
          <div class="d-flex align-center ga-3 mb-4">
            <VIcon color="error" size="28">mdi-trash-can-outline</VIcon>
            <h2 id="delete-dialog-title" class="text-h6">确认删除投递记录？</h2>
          </div>
          <p class="mb-2">公司：{{ confirmApplication?.companyName }}</p>
          <p class="mb-0">岗位：{{ confirmApplication ? positionsOf(confirmApplication).length : 0 }} 个，删除后全部岗位及流程将一并移除。</p>
          <VAlert v-if="deleteError" class="mt-4" type="error" variant="tonal" role="alert">{{ deleteError }}</VAlert>
        </VCardText>
        <div class="dialog-actions px-6 pb-6">
          <VBtn type="button" variant="text" :disabled="deleteLoading" @click="closeDeleteDialog">取消</VBtn>
          <VBtn type="button" color="error" :loading="deleteLoading" :disabled="deleteLoading" @click="performDelete">
            {{ deleteLoading ? "删除中…" : "确认删除" }}
          </VBtn>
        </div>
      </VCard>
    </VDialog>
  </VContainer>
  </AppShell>
</template>

<style scoped>
.page-title, .create-button { font-size: 1rem; line-height: 1.5; font-weight: 700; }
.page-title { margin: 0; color: #182230; }
.applications-page { max-width: 1480px; }
.page-heading { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.query-card { border: 1px solid rgba(49, 87, 213, .1); }
.query-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: start; gap: 4px 16px; }
.query-actions { display: flex; align-items: center; gap: 10px; min-height: 56px; }
.table-card { overflow: hidden; }
.applications-table :deep(table) { width: 100%; min-width: 980px; table-layout: fixed; }
.applications-table :deep(th) { background: #f8faff; font-size: .78rem; white-space: nowrap; }
.applications-table :deep(td) { vertical-align: middle; white-space: normal; overflow-wrap: anywhere; }
.company-group + .company-group > .company-row > td { border-top: 2px solid #e3e9f5; }
.company-cell { width: 17%; }
.position-cell { width: 29%; }
.status-cell { width: 11%; }
.shared-flow-cell { width: 21%; }
.updated-cell { width: 10%; }
.actions-cell { width: 12%; }
.position-count { display: block; margin-top: 4px; color: #667085; font-size: .75rem; font-weight: 400; }
.expand-company { display: block; margin-top: 6px; padding: 4px 8px; color: #3157d5; border-radius: 6px; background: #eef3ff; cursor: pointer; }
.expand-company:focus-visible { outline: 2px solid #3157d5; outline-offset: 3px; }
.position-name { display: block; color: #24375c; font-weight: 700; }
.position-meta, .position-link { display: inline-block; margin: 3px 10px 0 0; color: #667085; font-size: .75rem; }
.position-link { color: #3157d5; }
.position-notes { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #667085; font-size: .75rem; }
.interview-flow { display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 6px; margin-top: 4px; color: #475467; font-size: .75rem; }
.flow-label { flex-shrink: 0; }
.interview-item { display: inline-flex; gap: 4px; border-radius: 4px; padding: 1px 4px; background: #f1f4fa; }
.interview-time { color: #667085; }
.shared-stage { display: flex; gap: 10px; align-items: center; font-size: .8rem; margin: 4px 0; }
.shared-label { min-width: 40px; color: #475467; }
.shared-duration { color: #667085; }
.position-row { background: #f8faff; }
.position-row > td { padding-top: 10px !important; padding-bottom: 10px !important; }
.state-card { min-height: 250px; }
.state-content { min-height: 250px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; }
.pagination-bar { display: flex; align-items: center; justify-content: center; gap: 14px; }
.page-indicator { min-width: 120px; text-align: center; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; }
@media (max-width: 1100px) { .query-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 680px) {
  .page-heading { align-items: stretch; flex-direction: column; }
  .page-heading .v-btn { width: 100%; }
  .query-grid { grid-template-columns: 1fr; }
  .pagination-bar { flex-wrap: wrap; }
  .table-card { overflow: visible; background: transparent; box-shadow: none !important; }
  .applications-table :deep(.v-table__wrapper) { overflow: visible; }
  .applications-table :deep(table), .applications-table :deep(tbody), .applications-table :deep(tr), .applications-table :deep(td) { display: block; width: 100%; }
  .applications-table :deep(thead) { display: none; }
  .company-row { background: #fff; border: 1px solid #dce3f2; border-radius: 12px; margin-top: 18px; padding: 12px; }
  .applications-table :deep(td) { height: auto !important; border: 0 !important; padding: 6px 0 !important; white-space: normal; overflow-wrap: anywhere; }
  .position-row { border-left: 2px solid #dce3f2; }
  .shared-stage { gap: 12px; }
}
</style>
