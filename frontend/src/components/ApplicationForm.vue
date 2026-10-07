<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard, VCardActions, VCardText, VCardTitle } from "vuetify/components/VCard";
import { VSelect } from "vuetify/components/VSelect";
import { VTextarea } from "vuetify/components/VTextarea";
import { VTextField } from "vuetify/components/VTextField";
import { create, update, deleteInterview, deletePosition } from "../api/applications";
import { APPLICATION_STATUS_OPTIONS, type ApplicationStatus, type JobApplication, type SharedStageType } from "../types/application";
import { applicationValue, readPositions, readSharedStages, SHARED_STAGES } from "../utils/company-application";

type FormMode = "create" | "edit";
interface Props { mode?: FormMode; application?: Partial<JobApplication> | Record<string, unknown> | null; }
const props = withDefaults(defineProps<Props>(), { mode: "create", application: null });
const emit = defineEmits<{
  (event: "close"): void;
  (event: "success" | "saved", payload: { page: number; response: unknown }): void;
  (event: "refresh", payload: { page: number }): void;
}>();
interface ScheduleDraft { scheduledAt: string | null; durationMinutes: string | null; }
interface InterviewDraft extends ScheduleDraft { key: number; id?: number; name: string; }
interface PositionDraft {
  key: number; id?: number; positionName: string; applicationUrl: string;
  applicationStatus: ApplicationStatus; applicationTime: string | null; notes: string; interviews: InterviewDraft[];
}
interface SharedDraft extends ScheduleDraft { type: SharedStageType; }
let keySequence = 0;
const statuses = APPLICATION_STATUS_OPTIONS;
function emptyPosition(): PositionDraft {
  return { key: ++keySequence, positionName: "", applicationUrl: "", applicationStatus: "applied", applicationTime: null, notes: "", interviews: [] };
}
function emptyShared(): SharedDraft[] {
  return SHARED_STAGES.map(stage => ({ type: stage.type, scheduledAt: null, durationMinutes: null }));
}
const form = reactive({ companyName: "", sharedStages: emptyShared(), positions: [emptyPosition()] });
const fieldErrors = reactive<Record<string, string>>({});
const generalError = ref("");
const isSubmitting = ref(false);
const pendingPositions = ref<number[]>([]);
const pendingInterviews = ref<Array<{ positionId: number; id: number }>>([]);
const savedPayload = ref<Record<string, unknown>>({});
const originalPositionIds = new Set<number>();
const originalInterviewIds = new Map<number, Set<number>>();
let allowExit = false;
let lastResponse: unknown;
let submittedPositionIndexes: number[] = [];
let submittedSharedIndexes: number[] = [];
const submittedInterviewIndexes = new Map<number, number[]>();

function timeToInput(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function timeToRequest(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}
function schedulePayload(value: ScheduleDraft) {
  return { scheduledAt: timeToRequest(value.scheduledAt), durationMinutes: value.scheduledAt ? Number(value.durationMinutes) : null };
}
function requestPayload(): Record<string, unknown> {
  return {
    companyName: form.companyName.trim(),
    sharedStages: form.sharedStages.map(stage => ({ type: stage.type, ...schedulePayload(stage) })),
    positions: form.positions.map(position => ({
      ...(position.id !== undefined ? { id: position.id } : {}),
      positionName: position.positionName.trim(), applicationUrl: position.applicationUrl.trim(),
      applicationStatus: position.applicationStatus, applicationTime: timeToRequest(position.applicationTime), notes: position.notes,
      interviews: position.interviews.map(interview => ({
        ...(interview.id !== undefined ? { id: interview.id } : {}), name: interview.name.trim(), ...schedulePayload(interview),
      })),
    })),
  };
}
function snapshot(): void { savedPayload.value = JSON.parse(JSON.stringify(requestPayload())); }

function editPayload(): Record<string, unknown> {
  const current = requestPayload();
  const changed: Record<string, unknown> = {};
  if (current.companyName !== savedPayload.value.companyName) changed.companyName = current.companyName;
  const oldStages = savedPayload.value.sharedStages as Record<string, unknown>[] ?? [];
  submittedSharedIndexes = [];
  const stages = (current.sharedStages as Record<string, unknown>[]).filter((stage, index) => {
    if (JSON.stringify(stage) === JSON.stringify(oldStages.find(old => old.type === stage.type))) return false;
    submittedSharedIndexes.push(index); return true;
  });
  if (stages.length) changed.sharedStages = stages;
  const oldPositions = savedPayload.value.positions as Record<string, unknown>[] ?? [];
  submittedPositionIndexes = []; submittedInterviewIndexes.clear();
  const positions: Record<string, unknown>[] = [];
  (current.positions as Record<string, unknown>[]).forEach((position, positionIndex) => {
    const old = position.id === undefined ? undefined : oldPositions.find(item => item.id === position.id);
    if (!old) {
      positions.push(position); submittedPositionIndexes.push(positionIndex);
      submittedInterviewIndexes.set(positionIndex, (position.interviews as unknown[]).map((_, index) => index));
      return;
    }
    const item: Record<string, unknown> = { id: position.id };
    Object.entries(position).forEach(([key, value]) => {
      if (key !== "id" && key !== "interviews" && JSON.stringify(value) !== JSON.stringify(old[key])) item[key] = value;
    });
    const oldInterviews = old.interviews as Record<string, unknown>[] ?? [];
    const childIndexes: number[] = [];
    const interviews = (position.interviews as Record<string, unknown>[]).filter((interview, childIndex) => {
      const previous = interview.id === undefined ? undefined : oldInterviews.find(value => value.id === interview.id);
      if (previous && JSON.stringify(previous) === JSON.stringify(interview)) return false;
      childIndexes.push(childIndex); return true;
    });
    if (interviews.length) item.interviews = interviews;
    if (Object.keys(item).length > 1) {
      positions.push(item); submittedPositionIndexes.push(positionIndex); submittedInterviewIndexes.set(positionIndex, childIndexes);
    }
  });
  if (positions.length) changed.positions = positions;
  return changed;
}
const hasPendingDeletes = computed(() => pendingPositions.value.length > 0 || pendingInterviews.value.length > 0);
const isDirty = computed(() => JSON.stringify(requestPayload()) !== JSON.stringify(savedPayload.value) || hasPendingDeletes.value);
function clearErrors(): void { Object.keys(fieldErrors).forEach(key => delete fieldErrors[key]); generalError.value = ""; }
function load(): void {
  const source = (props.application ?? {}) as Record<string, unknown>;
  form.companyName = String(applicationValue(source, "companyName") ?? "");
  form.sharedStages = readSharedStages(source).map(stage => ({ type: stage.type, scheduledAt: timeToInput(stage.scheduledAt), durationMinutes: stage.scheduledAt ? String(stage.durationMinutes ?? 60) : null }));
  form.positions = readPositions(source).map(position => ({
    ...position, key: ++keySequence, applicationTime: timeToInput(position.applicationTime),
    interviews: position.interviews.map(interview => ({ ...interview, key: ++keySequence, scheduledAt: timeToInput(interview.scheduledAt), durationMinutes: interview.scheduledAt ? String(interview.durationMinutes ?? 60) : null })),
  }));
  if (form.positions.length === 0) form.positions.push(emptyPosition());
  originalPositionIds.clear(); originalInterviewIds.clear();
  form.positions.forEach(position => {
    if (position.id !== undefined) {
      originalPositionIds.add(position.id);
      originalInterviewIds.set(position.id, new Set(position.interviews.flatMap(interview => interview.id === undefined ? [] : [interview.id])));
    }
  });
  pendingPositions.value = []; pendingInterviews.value = [];
  allowExit = false; lastResponse = undefined; snapshot(); clearErrors();
}
watch(() => [props.mode, props.application], load, { immediate: true });
function addPosition(): void { if (!isSubmitting.value) form.positions.push(emptyPosition()); }
function removePosition(index: number): void {
  if (isSubmitting.value || form.positions.length <= 1) return;
  const [position] = form.positions.splice(index, 1);
  if (position.id !== undefined) {
    pendingPositions.value.push(position.id);
    pendingInterviews.value = pendingInterviews.value.filter(item => item.positionId !== position.id);
  }
}
function addInterview(position: PositionDraft): void {
  if (!isSubmitting.value) position.interviews.push({ key: ++keySequence, name: "", scheduledAt: null, durationMinutes: null });
}
function removeInterview(position: PositionDraft, index: number): void {
  if (isSubmitting.value) return;
  const [interview] = position.interviews.splice(index, 1);
  if (interview.id !== undefined && position.id !== undefined) pendingInterviews.value.push({ positionId: position.id, id: interview.id });
}
function scheduleChanged(value: ScheduleDraft): void {
  if (!value.scheduledAt) value.durationMinutes = null;
  else if (!value.durationMinutes) value.durationMinutes = "60";
}
function error(path: string): string[] { return fieldErrors[path] ? [fieldErrors[path]] : []; }
function validateSchedule(value: ScheduleDraft, prefix: string): void {
  if (value.scheduledAt && Number.isNaN(Date.parse(value.scheduledAt))) fieldErrors[`${prefix}.scheduledAt`] = "请输入有效时间";
  if (!value.scheduledAt) { value.durationMinutes = null; return; }
  if (!value.durationMinutes || !/^\d+$/.test(value.durationMinutes) || Number(value.durationMinutes) < 1 || Number(value.durationMinutes) > 1440) fieldErrors[`${prefix}.durationMinutes`] = "时长必须为 1 到 1440 分钟的整数";
}
function validate(): boolean {
  clearErrors();
  if (!form.companyName.trim()) fieldErrors.companyName = "公司名称不能为空";
  form.sharedStages.forEach((stage, index) => validateSchedule(stage, `sharedStages.${index}`));
  form.positions.forEach((position, index) => {
    const prefix = `positions.${index}`;
    if (!position.positionName.trim()) fieldErrors[`${prefix}.positionName`] = "岗位名称不能为空";
    if (!statuses.some(status => status.value === position.applicationStatus)) fieldErrors[`${prefix}.applicationStatus`] = "请选择有效状态";
    if (position.applicationTime && Number.isNaN(Date.parse(position.applicationTime))) fieldErrors[`${prefix}.applicationTime`] = "请输入有效投递时间";
    if (position.applicationUrl && !/^https?:\/\//i.test(position.applicationUrl.trim())) fieldErrors[`${prefix}.applicationUrl`] = "请输入 http 或 https 投递链接";
    position.interviews.forEach((interview, interviewIndex) => {
      const child = `${prefix}.interviews.${interviewIndex}`;
      if (!interview.name.trim()) fieldErrors[`${child}.name`] = "面试名称不能为空";
      validateSchedule(interview, child);
    });
  });
  return Object.keys(fieldErrors).length === 0;
}
function errorPath(path: string): string {
  if (props.mode !== "edit") return path;
  return path.replace(/^sharedStages\.(\d+)/, (_, index: string) => `sharedStages.${submittedSharedIndexes[Number(index)] ?? index}`)
    .replace(/^positions\.(\d+)(?:\.interviews\.(\d+))?/, (_, positionIndex: string, interviewIndex?: string) => {
      const mapped = submittedPositionIndexes[Number(positionIndex)] ?? Number(positionIndex);
      return `positions.${mapped}` + (interviewIndex === undefined ? "" : `.interviews.${submittedInterviewIndexes.get(mapped)?.[Number(interviewIndex)] ?? interviewIndex}`);
    });
}
function mapErrors(value: unknown, path = ""): void {
  if (Array.isArray(value)) {
    if (value.every(item => typeof item === "string")) fieldErrors[errorPath(path)] = value.join("；");
    else value.forEach((item, index) => mapErrors(item, path ? `${path}.${index}` : String(index)));
  } else if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      const camel = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
      mapErrors(item, path ? `${path}.${camel}` : camel);
    }
  } else if (value !== undefined) fieldErrors[errorPath(path)] = String(value);
}
function adoptIds(response: unknown): void {
  const raw = response as Record<string, unknown>;
  const body = raw && raw.data && typeof raw.data === "object" ? raw.data as Record<string, unknown> : raw;
  if (!body || !Array.isArray(body.positions)) return;
  const positions = readPositions(body);
  const newPositions = positions.filter(position => position.id !== undefined && !originalPositionIds.has(position.id));
  let newIndex = 0;
  form.positions.forEach(position => {
    const saved = position.id === undefined ? newPositions[newIndex++] : positions.find(item => item.id === position.id);
    if (!saved || saved.id === undefined) return;
    position.id = saved.id;
    const known = originalInterviewIds.get(saved.id) ?? new Set<number>();
    const newInterviews = saved.interviews.filter(interview => interview.id !== undefined && !known.has(interview.id));
    let interviewIndex = 0;
    position.interviews.forEach(interview => {
      if (interview.id === undefined) interview.id = newInterviews[interviewIndex++]?.id;
    });
    originalPositionIds.add(saved.id);
    originalInterviewIds.set(saved.id, new Set(saved.interviews.flatMap(interview => interview.id === undefined ? [] : [interview.id])));
  });
}
async function deletePending(companyId: number): Promise<void> {
  while (pendingInterviews.value.length) {
    const item = pendingInterviews.value[0];
    try { await deleteInterview(companyId, item.positionId, item.id); }
    catch (caught) { if ((caught as { response?: { status?: number } }).response?.status !== 404) throw caught; }
    pendingInterviews.value.shift();
  }
  while (pendingPositions.value.length) {
    const id = pendingPositions.value[0];
    try { await deletePosition(companyId, id); }
    catch (caught) { if ((caught as { response?: { status?: number } }).response?.status !== 404) throw caught; }
    pendingPositions.value.shift();
  }
}
async function submit(): Promise<void> {
  if (isSubmitting.value || !validate()) return;
  isSubmitting.value = true;
  let deleting = false;
  try {
    const payload = requestPayload();
    if (props.mode === "edit") {
      const companyId = Number((props.application as Record<string, unknown>)?.id);
      const changes = editPayload();
      if (Object.keys(changes).length) {
        lastResponse = await update(companyId, changes);
        adoptIds(lastResponse); snapshot();
      }
      deleting = true;
      await deletePending(companyId);
    } else lastResponse = await create(payload);
    snapshot(); allowExit = true;
    emit("success", { page: 1, response: lastResponse });
    emit("saved", { page: 1, response: lastResponse }); emit("refresh", { page: 1 }); emit("close");
  } catch (caught: unknown) {
    const details = (caught as { response?: { data?: { details?: unknown } } }).response?.data?.details;
    if (details) mapErrors(details);
    generalError.value = hasPendingDeletes.value && deleting
      ? "部分更改已保存，删除未完成。输入已保留，请点击保存重试剩余删除。"
      : "保存失败，输入已保留，请稍后重试。";
  } finally { isSubmitting.value = false; }
}
function confirmExit(): boolean {
  if (isSubmitting.value) return false;
  return allowExit || !isDirty.value || globalThis.confirm("有未保存的修改，确定关闭吗？");
}
function closeForm(): void { if (confirmExit()) { allowExit = true; emit("close"); } }
function beforeUnload(event: BeforeUnloadEvent): void {
  if (isDirty.value && !allowExit) { event.preventDefault(); event.returnValue = ""; }
}
onMounted(() => window.addEventListener("beforeunload", beforeUnload));
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnload));
defineExpose({ confirmExit, isDirty });
</script>

<template>
  <form class="application-form" novalidate @submit.prevent="submit">
    <VCard class="application-card" elevation="2">
      <VCardTitle class="form-heading">
        <span class="text-h5 font-weight-bold">{{ mode === 'edit' ? '编辑投递记录' : '新增投递记录' }}</span>
        <VBtn type="button" variant="text" aria-label="关闭表单" :disabled="isSubmitting" @click="closeForm">关闭</VBtn>
      </VCardTitle>
      <VCardText class="form-content">
        <VAlert v-if="generalError" class="mb-5" type="error" variant="tonal" role="alert">{{ generalError }}</VAlert>
        <p class="timezone-note">时间按浏览器本地时区填写；日历按北京时间显示。移除记录在保存后生效。</p>
        <VTextField v-model="form.companyName" name="companyName" label="公司名称" required :disabled="isSubmitting" :error-messages="error('companyName')" />
        <fieldset class="flow-group" aria-label="公司共享流程" :disabled="isSubmitting">
          <legend>公司共享流程</legend>
          <p class="group-note">AI 面、测评和笔试各登记一次，所有岗位共用。</p>
          <div class="schedule-grid">
            <div v-for="(stage, index) in form.sharedStages" :key="stage.type" class="schedule-pair">
              <VTextField v-model="stage.scheduledAt" :name="`${SHARED_STAGES[index].field}Time`" :label="`${SHARED_STAGES[index].title}时间`" type="datetime-local" clearable :disabled="isSubmitting" :error-messages="error(`sharedStages.${index}.scheduledAt`)" @update:model-value="scheduleChanged(stage)" />
              <VTextField v-model="stage.durationMinutes" :name="`${SHARED_STAGES[index].field}DurationMinutes`" :label="`${SHARED_STAGES[index].title}时长（分钟）`" type="number" min="1" max="1440" step="1" inputmode="numeric" :disabled="isSubmitting || !stage.scheduledAt" hint="1 到 1440 分钟" :error-messages="error(`sharedStages.${index}.durationMinutes`)" />
            </div>
          </div>
        </fieldset>
        <fieldset v-for="(position, index) in form.positions" :key="position.key" class="flow-group position-group" :aria-label="`岗位${index + 1}`" :disabled="isSubmitting">
          <legend>岗位{{ index + 1 }}</legend>
          <div class="group-actions">
            <VBtn type="button" color="error" variant="text" :aria-label="`移除岗位${index + 1}`" :disabled="isSubmitting || form.positions.length <= 1" @click="removePosition(index)">移除岗位{{ index + 1 }}</VBtn>
          </div>
          <div class="position-grid">
            <VTextField v-model="position.positionName" :name="index === 0 ? 'positionName' : `positionName${index + 1}`" label="岗位名称" required :disabled="isSubmitting" :error-messages="error(`positions.${index}.positionName`)" />
            <VTextField v-model="position.applicationUrl" :name="index === 0 ? 'applicationUrl' : `applicationUrl${index + 1}`" label="投递链接" type="url" placeholder="https://..." :disabled="isSubmitting" :error-messages="error(`positions.${index}.applicationUrl`)" />
            <VSelect v-model="position.applicationStatus" :name="index === 0 ? 'applicationStatus' : `applicationStatus${index + 1}`" label="业务状态" :items="statuses" item-title="title" item-value="value" :disabled="isSubmitting" :error-messages="error(`positions.${index}.applicationStatus`)" />
            <VTextField v-model="position.applicationTime" :name="index === 0 ? 'applicationTime' : `applicationTime${index + 1}`" label="投递时间" type="datetime-local" clearable :disabled="isSubmitting" :error-messages="error(`positions.${index}.applicationTime`)" />
            <VTextarea v-model="position.notes" :name="index === 0 ? 'notes' : `notes${index + 1}`" label="备注" rows="2" auto-grow class="full-width" :disabled="isSubmitting" :error-messages="error(`positions.${index}.notes`)" />
          </div>
          <fieldset v-for="(interview, childIndex) in position.interviews" :key="interview.key" class="interview-group" :aria-label="`面试${childIndex + 1}`">
            <legend>面试{{ childIndex + 1 }}</legend>
            <div class="interview-grid">
              <VTextField v-model="interview.name" label="面试名称" :name="`positions.${index}.interviews.${childIndex}.name`" required :disabled="isSubmitting" :error-messages="error(`positions.${index}.interviews.${childIndex}.name`)" />
              <VTextField v-model="interview.scheduledAt" label="面试时间" :name="`positions.${index}.interviews.${childIndex}.scheduledAt`" type="datetime-local" clearable :disabled="isSubmitting" :error-messages="error(`positions.${index}.interviews.${childIndex}.scheduledAt`)" @update:model-value="scheduleChanged(interview)" />
              <VTextField v-model="interview.durationMinutes" label="面试时长（分钟）" :name="`positions.${index}.interviews.${childIndex}.durationMinutes`" type="number" min="1" max="1440" step="1" inputmode="numeric" :disabled="isSubmitting || !interview.scheduledAt" hint="1 到 1440 分钟" :error-messages="error(`positions.${index}.interviews.${childIndex}.durationMinutes`)" />
              <VBtn type="button" color="error" variant="text" :aria-label="`删除面试${childIndex + 1}`" :disabled="isSubmitting" @click="removeInterview(position, childIndex)">删除面试{{ childIndex + 1 }}</VBtn>
            </div>
          </fieldset>
          <p v-if="position.interviews.length === 0" class="group-note">尚未添加面试环节。</p>
          <VBtn type="button" variant="tonal" prepend-icon="mdi-plus" :disabled="isSubmitting" @click="addInterview(position)">添加面试</VBtn>
        </fieldset>
        <VBtn type="button" variant="tonal" prepend-icon="mdi-plus" :disabled="isSubmitting" @click="addPosition">添加岗位</VBtn>
      </VCardText>
      <VCardActions class="justify-end px-6 pb-6">
        <VBtn type="submit" color="primary" aria-label="保存" :aria-busy="isSubmitting" :loading="isSubmitting" :disabled="isSubmitting">{{ isSubmitting ? '保存中…' : '保存' }}</VBtn>
      </VCardActions>
    </VCard>
  </form>
</template>

<style scoped>
.application-form { width: 100%; }
.application-card { overflow: visible; }
.form-heading { display: flex; align-items: center; justify-content: space-between; padding: 24px; gap: 12px; }
.form-content { padding: 0 24px 24px; }
.timezone-note, .group-note { color: #667085; font-size: .85rem; line-height: 1.6; margin-bottom: 16px; }
.flow-group { border: 1px solid #dce3f2; border-radius: 12px; padding: 18px; margin: 12px 0 24px; min-inline-size: 0; }
.flow-group > legend { font-weight: 700; color: #24375c; padding: 0 8px; }
.group-actions { display: flex; justify-content: flex-end; margin: -8px 0 4px; }
.position-grid, .schedule-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 16px; }
.schedule-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.full-width { grid-column: 1 / -1; }
.interview-group { border: 0; border-top: 1px solid #e4e9f3; margin: 16px 0 12px; padding: 12px 0 0; min-inline-size: 0; }
.interview-group > legend { color: #475467; padding-right: 8px; font-weight: 600; }
.interview-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr) minmax(0, .8fr); gap: 4px 12px; }
.interview-grid > .v-btn { grid-column: 1 / -1; justify-self: end; }
@media (max-width: 700px) {
  .form-heading, .form-content { padding-left: 16px; padding-right: 16px; }
  .form-heading > span { font-size: 1.1rem !important; }
  .flow-group { padding: 12px; }
  .position-grid, .schedule-grid, .interview-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
