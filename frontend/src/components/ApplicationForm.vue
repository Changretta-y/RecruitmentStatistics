<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardActions } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VCardTitle } from "vuetify/components/VCard";
import { VSelect } from "vuetify/components/VSelect";
import { VTextarea } from "vuetify/components/VTextarea";
import { VTextField } from "vuetify/components/VTextField";

import { create, update } from "../api/applications";
import DateTimeField from "./DateTimeField.vue";
import type { JobApplication, ApplicationStatus } from "../types/application";

type FormMode = "create" | "edit";
type EditableField =
  | "companyName"
  | "positionName"
  | "applicationStatus"
  | "applicationTime"
  | "aiInterviewTime"
  | "writtenTestTime"
  | "firstInterviewTime"
  | "secondInterviewTime"
  | "thirdInterviewTime"
  | "hrInterviewTime";

interface Props {
  mode?: FormMode;
  application?: Partial<JobApplication> | Record<string, unknown> | null;
}

const props = withDefaults(defineProps<Props>(), { mode: "create", application: null });
const emit = defineEmits<{
  (event: "close"): void;
  (event: "success", payload: { page: number; response: unknown }): void;
  (event: "saved", payload: { page: number; response: unknown }): void;
  (event: "refresh", payload: { page: number }): void;
}>();

const statuses: Array<{ value: ApplicationStatus; title: string }> = [
  { value: "applied", title: "已投递" },
  { value: "in_progress", title: "进行中" },
  { value: "offer", title: "Offer" },
  { value: "rejected", title: "已拒绝" },
  { value: "withdrawn", title: "已撤回" },
];
const stageFields: EditableField[] = [
  "aiInterviewTime", "writtenTestTime", "firstInterviewTime",
  "secondInterviewTime", "thirdInterviewTime", "hrInterviewTime",
];
const stageLabels: Record<string, string> = {
  aiInterviewTime: "AI 面时间",
  writtenTestTime: "笔试时间",
  firstInterviewTime: "一面时间",
  secondInterviewTime: "二面时间",
  thirdInterviewTime: "三面时间",
  hrInterviewTime: "HR 面时间",
};
const editableFields: EditableField[] = [
  "companyName", "positionName", "applicationStatus", "applicationTime", ...stageFields,
];
const timeFields: EditableField[] = ["applicationTime", ...stageFields];

type FormState = Record<EditableField, string | null> & {
  companyName: string;
  positionName: string;
  applicationStatus: ApplicationStatus | string;
  notes: string;
};

function emptyForm(): FormState {
  return {
    companyName: "", positionName: "", applicationStatus: "applied",
    applicationTime: null, aiInterviewTime: null, writtenTestTime: null,
    firstInterviewTime: null, secondInterviewTime: null, thirdInterviewTime: null,
    hrInterviewTime: null, notes: "",
  };
}

const form = reactive<FormState>(emptyForm());
const initialRequest = ref<Record<string, unknown>>({});
const fieldErrors = reactive<Record<string, string>>({});
const generalError = ref("");
const isSubmitting = ref(false);

function sourceValue(source: Props["application"], field: EditableField | "notes"): unknown {
  if (!source) return undefined;
  const record = source as Record<string, unknown>;
  const snake = field.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
  return record[field] ?? record[snake];
}

function isTimeField(field: EditableField | "notes"): boolean {
  return timeFields.includes(field as EditableField);
}

function timeToInput(value: unknown): string | null {
  if (value === undefined || value === null || value === "") return null;
  const raw = String(value);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw)) return raw;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formFromApplication(source: Props["application"]): FormState {
  const next = emptyForm();
  for (const field of [...editableFields, "notes" as const]) {
    const value = sourceValue(source, field);
    if (value !== undefined && value !== null) {
      next[field] = (isTimeField(field) ? timeToInput(value) : String(value)) as never;
    }
  }
  return next;
}

function assignForm(next: FormState): void {
  for (const field of [...editableFields, "notes" as const]) form[field] = next[field] as never;
}

function clearErrors(): void {
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key]);
  generalError.value = "";
}

function timeToRequest(value: string | null): string | null {
  if (!value) return null;
  if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)) return value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

function fieldToRequest(field: EditableField | "notes", value: string | null): unknown {
  if (field === "companyName" || field === "positionName" || field === "notes") return value ?? "";
  if (field === "applicationStatus") return value;
  return timeToRequest(value);
}

function requestPayload(source: FormState): Record<string, unknown> {
  return [...editableFields, "notes" as const].reduce<Record<string, unknown>>((payload, field) => {
    payload[field] = fieldToRequest(field, source[field]);
    return payload;
  }, {});
}

function isValidTime(value: string | null): boolean {
  return !value || (value.includes("T") && !Number.isNaN(Date.parse(value)));
}

function validate(): boolean {
  clearErrors();
  const hasTimeValue = ["applicationTime", ...stageFields].some((field) => Boolean(form[field]));
  if (!form.companyName?.trim() && !hasTimeValue) fieldErrors.companyName = "公司名称不能为空";
  if (!form.positionName?.trim() && !hasTimeValue) fieldErrors.positionName = "岗位名称不能为空";
  if (!statuses.some((status) => status.value === form.applicationStatus)) {
    fieldErrors.applicationStatus = "请选择有效状态";
  }
  for (const field of ["applicationTime", ...stageFields] as EditableField[]) {
    if (!isValidTime(form[field])) fieldErrors[field] = "请输入有效的 ISO 时间";
  }
  return Object.keys(fieldErrors).length === 0;
}

const isDirty = computed(() => JSON.stringify(requestPayload(form)) !== JSON.stringify(initialRequest.value));

function loadFromProps(): void {
  assignForm(formFromApplication(props.application));
  initialRequest.value = requestPayload(form);
  clearErrors();
}

watch(() => [props.mode, props.application], loadFromProps, { immediate: true });

function closeForm(): void {
  if (isDirty.value && !globalThis.confirm("有未保存的修改，确定关闭吗？")) return;
  emit("close");
}

function mapBackendErrors(error: unknown): void {
  const details = (error as { response?: { data?: { details?: Record<string, unknown> } } }).response?.data?.details;
  if (!details) {
    generalError.value = "保存失败，请稍后重试";
    return;
  }
  for (const [key, value] of Object.entries(details)) {
    const camel = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
    fieldErrors[camel] = Array.isArray(value) ? value.join("；") : String(value);
  }
}

async function submit(): Promise<void> {
  if (isSubmitting.value || !validate()) return;
  isSubmitting.value = true;
  clearErrors();
  try {
    const allValues = requestPayload(form);
    const payload = props.mode === "edit"
      ? Object.fromEntries(
          [...editableFields, "notes" as const]
            .filter((field) => allValues[field] !== initialRequest.value[field])
            .map((field) => [field, allValues[field]]),
        )
      : allValues;
    const response = props.mode === "edit"
      ? await update((props.application as Record<string, unknown>)?.id as number, payload)
      : await create(payload);
    assignForm(emptyForm());
    initialRequest.value = requestPayload(form);
    emit("success", { page: 1, response });
    emit("saved", { page: 1, response });
    emit("refresh", { page: 1 });
    emit("close");
  } catch (error: unknown) {
    mapBackendErrors(error);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <form class="application-form" @submit.prevent="submit">
    <VCard class="application-card" elevation="2">
      <VCardTitle class="d-flex align-center justify-space-between pa-6">
        <span class="text-h5 font-weight-bold">{{ mode === "edit" ? "编辑投递记录" : "新增投递记录" }}</span>
        <VBtn type="button" variant="text" aria-label="关闭表单" @click="closeForm">关闭</VBtn>
      </VCardTitle>

      <VCardText class="px-6 pb-2">
        <VAlert v-if="generalError" class="mb-5" type="error" variant="tonal" role="alert">
          {{ generalError }}
        </VAlert>

        <div class="form-grid">
          <VTextField
            v-model="form.companyName"
            name="companyName"
            label="公司名称"
            required
            :error-messages="fieldErrors.companyName ? [fieldErrors.companyName] : []"
          />
          <VTextField
            v-model="form.positionName"
            name="positionName"
            label="岗位名称"
            required
            :error-messages="fieldErrors.positionName ? [fieldErrors.positionName] : []"
          />
          <VSelect
            v-model="form.applicationStatus"
            name="applicationStatus"
            label="投递状态"
            :items="statuses"
            item-title="title"
            item-value="value"
            :error-messages="fieldErrors.applicationStatus ? [fieldErrors.applicationStatus] : []"
          />
          <DateTimeField
            v-model="form.applicationTime"
            name="applicationTime"
            label="投递时间"
            clearable
            :error-messages="fieldErrors.applicationTime ? [fieldErrors.applicationTime] : []"
          />
          <DateTimeField
            v-for="field in stageFields"
            :key="field"
            v-model="form[field]"
            :name="field"
            :label="stageLabels[field]"
            clearable
            :error-messages="fieldErrors[field] ? [fieldErrors[field]] : []"
          />
          <VTextarea
            v-model="form.notes"
            name="notes"
            label="备注"
            rows="4"
            auto-grow
            :error-messages="fieldErrors.notes ? [fieldErrors.notes] : []"
          />
        </div>
      </VCardText>

      <VCardActions class="justify-end px-6 pb-6">
        <VBtn type="submit" color="primary" :loading="isSubmitting" :disabled="isSubmitting">
          {{ isSubmitting ? "保存中…" : "保存" }}
        </VBtn>
      </VCardActions>
    </VCard>
  </form>
</template>

<style scoped>
.application-form { width: 100%; }
.application-card { overflow: visible; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 18px; }
.form-grid > :last-child { grid-column: 1 / -1; }
@media (max-width: 700px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-grid > :last-child { grid-column: auto; }
}
</style>

