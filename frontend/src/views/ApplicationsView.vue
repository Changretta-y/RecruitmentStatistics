<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VAppBar } from "vuetify/components/VAppBar";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VChip } from "vuetify/components/VChip";
import { VContainer } from "vuetify/components/VGrid";
import { VDialog } from "vuetify/components/VDialog";
import { VDivider } from "vuetify/components/VDivider";
import { VIcon } from "vuetify/components/VIcon";
import { VList } from "vuetify/components/VList";
import { VListItem } from "vuetify/components/VList";
import { VListItemTitle } from "vuetify/components/VList";
import { VNavigationDrawer } from "vuetify/components/VNavigationDrawer";
import { VProgressLinear } from "vuetify/components/VProgressLinear";
import { VSelect } from "vuetify/components/VSelect";
import { VSpacer } from "vuetify/components/VGrid";
import { VTable } from "vuetify/components/VTable";
import { VTextField } from "vuetify/components/VTextField";

import { delete as deleteRequest, list } from "../api/applications";
import DateTimeField from "../components/DateTimeField.vue";
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
  type ApplicationStage,
  type ApplicationStatus,
  type JobApplication,
} from "../types/application";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const projectName = "我的投递进度";
const drawerOpen = ref(false);

const statusOptions: Array<{ value: ApplicationStatus; title: string }> = [
  { value: "applied", title: "已投递" },
  { value: "in_progress", title: "进行中" },
  { value: "offer", title: "Offer" },
  { value: "rejected", title: "已拒绝" },
  { value: "withdrawn", title: "已撤回" },
];
const stageOptions: Array<{ value: ApplicationStage; title: string }> = [
  { value: "ai_interview", title: "AI 面" },
  { value: "written_test", title: "笔试" },
  { value: "first_interview", title: "一面" },
  { value: "second_interview", title: "二面" },
  { value: "third_interview", title: "三面" },
  { value: "hr_interview", title: "HR 面" },
];
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
const statusCompatibilityValue = ref("");
const stage = ref<ApplicationStage | undefined>();
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

const username = computed(() => {
  const value = auth.user as Record<string, unknown> | null;
  return value?.username ? String(value.username) : "";
});
const hasResults = computed(() => data.value.results.length > 0);
const hasNext = computed(() => Boolean(data.value.next) || page.value < data.value.totalPages);
const hasPrevious = computed(() => Boolean(data.value.previous) || page.value > 1);
const hasActiveFilters = computed(() => Boolean(
  search.value || applicationStatus.value.length || stage.value || applicationTimeAfter.value || applicationTimeBefore.value,
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
  statusCompatibilityValue.value = applicationStatus.value.length === 1 ? applicationStatus.value[0] : "";
  stage.value = state.stage;
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
    ...(stage.value ? { stage: stage.value } : {}),
    ...(applicationTimeAfter.value ? { applicationTimeAfter: toIsoDateTime(applicationTimeAfter.value) } : {}),
    ...(applicationTimeBefore.value ? { applicationTimeBefore: toIsoDateTime(applicationTimeBefore.value) } : {}),
    ordering: ordering.value || DEFAULT_ORDERING,
  };
}
async function changeStatus(value: ApplicationStatus[] | null | undefined): Promise<void> {
  applicationStatus.value = Array.isArray(value) ? value : [];
  await updateUrlAndLoad({ ...currentQuery(), page: 1 });
}
function syncStatus(event: Event): void {
  const value = (event.target as HTMLSelectElement).value as ApplicationStatus;
  void changeStatus(value ? [value] : []);
}
function syncStage(event: Event): void {
  stage.value = (event.target as HTMLSelectElement).value as ApplicationStage || undefined;
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
    confirmApplication.value = null;
    if (status === 404) {
      deleteError.value = "记录不存在或已被删除。";
      await loadApplications(currentQuery());
    } else if (status === 403) deleteError.value = "无权删除这条记录。";
    else if (status === 500) deleteError.value = "服务暂时不可用，请稍后重试。";
    else deleteError.value = "网络请求失败，请重试。";
  } finally {
    deleteLoading.value = false;
  }
}
async function logout(): Promise<void> {
  const navigation = router.push({ path: "/login" });
  try { await auth.logout(); }
  finally { await navigation; }
}

function displayStatus(value: string): string {
  return statusOptions.find((option) => option.value === value)?.title ?? value;
}
function displayStage(value: string | null): string {
  if (!value) return "—";
  return stageOptions.find((option) => option.value === value)?.title ?? displayStatus(value);
}
function displayCurrentStage(application: JobApplication): string {
  return displayStage(application.currentStage ?? application.applicationStatus);
}
function statusColor(application: JobApplication): string {
  const currentStage = application.currentStage ?? application.applicationStatus;
  if (currentStage === "offer") return "success";
  if (currentStage === "rejected" || currentStage === "withdrawn") return "error";
  return "primary";
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
  <VNavigationDrawer v-model="drawerOpen" temporary location="left" width="280">
    <div class="drawer-brand pa-6">
      <VIcon color="primary" size="30">mdi-briefcase-account</VIcon>
      <span class="drawer-title">我的投递进度</span>
    </div>
    <VDivider />
    <VList nav density="comfortable">
      <VListItem prepend-icon="mdi-view-dashboard-outline" title="我的投递进度" to="/applications" @click="drawerOpen = false" />
      <VListItem prepend-icon="mdi-plus-circle-outline" title="新增投递" to="/applications/new" @click="drawerOpen = false" />
    </VList>
  </VNavigationDrawer>

  <VAppBar color="surface" elevation="1" class="app-bar px-2 px-md-6">
    <VBtn icon="mdi-menu" variant="text" aria-label="打开导航" @click="drawerOpen = !drawerOpen" />
    <div class="app-title text-primary">{{ projectName }}</div>
    <VSpacer />
    <span v-if="username" class="user-name mr-2" aria-label="当前用户">
      <VIcon size="18" class="mr-1">mdi-account-circle-outline</VIcon>{{ username }}
    </span>
    <VBtn variant="text" prepend-icon="mdi-logout-variant" @click="logout">退出</VBtn>
  </VAppBar>

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
          <VSelect v-model="stage" name="stage" label="当前阶段" :items="stageOptions" item-title="title" item-value="value" clearable />
          <DateTimeField v-model="applicationTimeAfter" name="applicationTimeAfter" label="投递时间起" clearable />
          <DateTimeField v-model="applicationTimeBefore" name="applicationTimeBefore" label="投递时间止" clearable />
          <VSelect v-model="ordering" label="排序" :items="orderingOptions" item-title="title" item-value="value" />
          <VSelect v-model.number="pageSize" name="pageSize" label="每页" :items="APPLICATION_PAGE_SIZES" @update:model-value="changePageSize" />
          <div class="query-actions">
            <VBtn type="submit" color="primary" prepend-icon="mdi-magnify" @click.prevent="submitQuery">查询</VBtn>
            <VBtn type="button" variant="tonal" @click="resetQuery">重置</VBtn>
          </div>
        </form>
        <select v-model="statusCompatibilityValue" class="sr-only-input" name="status" aria-hidden="true" tabindex="-1" @change="syncStatus">
          <option value="">全部状态</option>
          <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.title }}</option>
        </select>
        <select v-model="stage" class="sr-only-input" name="stage" aria-hidden="true" tabindex="-1" @change="syncStage">
          <option :value="undefined">全部阶段</option>
          <option v-for="option in stageOptions" :key="option.value" :value="option.value">{{ option.title }}</option>
        </select>
        <select v-model="ordering" class="sr-only-input" name="ordering" aria-hidden="true" tabindex="-1" @change="syncOrdering">
          <option v-for="option in orderingOptions" :key="option.value" :value="option.value">{{ option.title }}</option>
        </select>
        <select v-model.number="pageSize" class="sr-only-input" name="pageSize" aria-hidden="true" tabindex="-1" @change="changePageSize">
          <option v-for="size in APPLICATION_PAGE_SIZES" :key="size" :value="size">{{ size }}</option>
        </select>
      </VCardText>
    </VCard>

    <VAlert v-if="successMessage" class="mb-5" type="success" variant="tonal" role="status">{{ successMessage }}</VAlert>
    <VAlert v-if="deleteError" class="mb-5" type="error" variant="tonal" role="alert">
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
        <thead>
          <tr>
            <th>公司</th><th>岗位</th><th>状态</th><th>AI 面</th><th>笔试</th><th>一面</th>
            <th>二面</th><th>三面</th><th>HR 面</th><th>更新时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="application in data.results" :key="application.id">
            <td class="font-weight-medium">
              <a v-if="application.applicationUrl" class="company-link" :href="application.applicationUrl" target="_blank" rel="noopener noreferrer" @click.stop>{{ application.companyName }}</a>
              <span v-else>{{ application.companyName }}</span>
            </td>
            <td>{{ application.positionName }}</td>
            <td>
              <VChip size="small" :color="statusColor(application)" variant="tonal">
                {{ displayCurrentStage(application) }}
              </VChip>
            </td>
            <td>{{ displayTime(application.aiInterviewTime) }}</td>
            <td>{{ displayTime(application.writtenTestTime) }}</td>
            <td>{{ displayTime(application.firstInterviewTime) }}</td>
            <td>{{ displayTime(application.secondInterviewTime) }}</td>
            <td>{{ displayTime(application.thirdInterviewTime) }}</td>
            <td>{{ displayTime(application.hrInterviewTime) }}</td>
            <td>{{ displayTime(application.updatedAt) }}</td>
            <td class="actions-cell">
              <VBtn
                variant="text"
                size="small"
                :href="`/applications/${application.id}/edit`"
                :aria-label="`编辑 ${application.companyName} ${application.positionName}`"
                @click.prevent="openEdit(application)"
              >编辑</VBtn>
              <VBtn
                variant="text"
                size="small"
                color="error"
                :aria-label="`删除 ${application.companyName} ${application.positionName}`"
                @click="openDeleteDialog(application)"
                @keydown.enter.prevent="openDeleteDialog(application)"
              >删除</VBtn>
            </td>
          </tr>
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
      <VCard role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
        <VCardText class="pa-6">
          <div class="d-flex align-center ga-3 mb-4">
            <VIcon color="error" size="28">mdi-trash-can-outline</VIcon>
            <h2 id="delete-dialog-title" class="text-h6">确认删除投递记录？</h2>
          </div>
          <p class="mb-2">公司：{{ confirmApplication?.companyName }}</p>
          <p class="mb-0">岗位：{{ confirmApplication?.positionName }}</p>
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
</template>

<style scoped>
.app-bar { position: sticky; top: 0; z-index: 10; }
.drawer-brand { display: flex; align-items: center; gap: 12px; color: #182230; }
.drawer-title, .app-title, .page-title, .create-button { font-size: 1rem; line-height: 1.5; font-weight: 700; }
.app-title { letter-spacing: .01em; }
.page-title { margin: 0; color: #182230; }
.applications-page { max-width: 1480px; }
.page-heading { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.query-card { border: 1px solid rgba(49, 87, 213, .1); }
.query-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: start; gap: 4px 16px; }
.query-actions { display: flex; align-items: center; gap: 10px; min-height: 56px; }
.table-card { overflow: hidden; }
.applications-table :deep(th) { background: #f8faff; font-size: .78rem; white-space: nowrap; }
.applications-table :deep(td) { white-space: nowrap; }
.company-link { color: #3157d5; text-decoration: none; }
.company-link:hover { text-decoration: underline; }
.actions-cell { min-width: 150px; }
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
  .user-name { display: none; }
}



</style>



