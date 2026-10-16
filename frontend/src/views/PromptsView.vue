<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard, VCardActions, VCardText, VCardTitle } from "vuetify/components/VCard";
import { VChip } from "vuetify/components/VChip";
import { VContainer } from "vuetify/components/VGrid";
import { VDialog } from "vuetify/components/VDialog";
import { VForm } from "vuetify/components/VForm";
import { VTextField } from "vuetify/components/VTextField";
import { VTextarea } from "vuetify/components/VTextarea";

import AppShell from "../components/AppShell.vue";
import { createPrompt, deletePrompt, listPrompts, updatePrompt, type Prompt } from "../api/prompts";

const prompts = ref<Prompt[]>([]);
const search = ref("");
const loading = ref(true);
const saving = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const selectedId = ref<number | null>(null);
const dialogOpen = ref(false);
const editing = ref<Prompt | null>(null);
const title = ref("");
const content = ref("");
const validation = ref("");
const deleteTarget = ref<Prompt | null>(null);
const deleteOpen = ref(false);

const empty = computed(() => !loading.value && !errorMessage.value && prompts.value.length === 0);

async function load(): Promise<void> {
  loading.value = true; errorMessage.value = "";
  try { prompts.value = (await listPrompts(search.value)).results; }
  catch { errorMessage.value = "提示词加载失败，请稍后重试。"; }
  finally { loading.value = false; }
}
let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => void load(), 200); });

function openCreate(): void { editing.value = null; title.value = ""; content.value = ""; validation.value = ""; dialogOpen.value = true; }
function openEdit(item: Prompt): void { editing.value = item; title.value = item.title; content.value = item.content; validation.value = ""; dialogOpen.value = true; }
function closeDialog(): void { if (!saving.value) dialogOpen.value = false; }
async function save(): Promise<void> {
  validation.value = ""; successMessage.value = "";
  if (!title.value.trim() || !content.value.trim()) { validation.value = "标题和内容不能为空。"; return; }
  saving.value = true;
  try {
    if (editing.value) await updatePrompt(editing.value.id, { title: title.value.trim(), content: content.value.trim() });
    else await createPrompt({ title: title.value.trim(), content: content.value.trim() });
    dialogOpen.value = false; successMessage.value = "提示词已保存。"; await load();
  } catch { validation.value = "保存失败，请检查网络后重试。"; }
  finally { saving.value = false; }
}
async function copy(item: Prompt): Promise<void> {
  try { await navigator.clipboard.writeText(item.content); successMessage.value = "复制成功。"; }
  catch { successMessage.value = "复制失败，剪贴板不可用。"; }
}
function askDelete(item: Prompt): void { deleteTarget.value = item; deleteOpen.value = true; }
async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value) return;
  try { await deletePrompt(deleteTarget.value.id); deleteOpen.value = false; prompts.value = prompts.value.filter((item) => item.id !== deleteTarget.value?.id); successMessage.value = "提示词已删除。"; }
  catch { errorMessage.value = "删除失败，请稍后重试。"; }
}
onMounted(() => void load());
</script>

<template>
  <AppShell title="提示词管理">
    <VContainer class="prompts-page py-6 py-md-10">
      <header class="d-flex flex-wrap align-center justify-space-between ga-3 mb-6">
        <div><p class="text-overline text-primary mb-1">面试准备</p><h1 class="text-h4 font-weight-bold">提示词管理</h1></div>
        <VBtn color="primary" prepend-icon="mdi-plus" aria-label="新增提示词" @click="openCreate" />
      </header>
      <VAlert v-if="errorMessage" type="error" variant="tonal" class="mb-4" role="alert">{{ errorMessage }}</VAlert>
      <VAlert v-if="successMessage" :type="successMessage.includes('失败') ? 'error' : 'success'" variant="tonal" class="mb-4" role="status">{{ successMessage }}</VAlert>
      <VTextField v-model="search" name="search" aria-label="搜索提示词" placeholder="搜索标题或内容" prepend-inner-icon="mdi-magnify" clearable class="mb-6" />
      <div v-if="loading" role="status">正在加载提示词…</div>
      <VAlert v-else-if="empty" type="info" variant="tonal">暂无提示词或没有匹配结果。</VAlert>
      <div v-else class="prompt-grid">
        <VCard v-for="item in prompts" :key="item.id" class="prompt-card" :class="{ selected: selectedId === item.id }" @click="selectedId = item.id">
          <VCardTitle class="d-flex align-center ga-2"><span>{{ item.title }}</span><VChip v-if="item.is_preset" size="small" color="primary" variant="tonal">预设</VChip></VCardTitle>
          <VCardText class="prompt-content">{{ item.content }}</VCardText>
          <VCardActions v-if="selectedId === item.id" class="pt-0">
            <VBtn size="small" variant="text" prepend-icon="mdi-content-copy" @click.stop="copy(item)">复制</VBtn>
            <VBtn size="small" variant="text" prepend-icon="mdi-pencil" @click.stop="openEdit(item)">编辑</VBtn>
            <VBtn size="small" variant="text" color="error" prepend-icon="mdi-delete" @click.stop="askDelete(item)">删除</VBtn>
          </VCardActions>
        </VCard>
      </div>
    </VContainer>
    <VDialog v-model="dialogOpen" max-width="620">
      <VCard><VCardTitle>{{ editing ? '编辑提示词' : '提示词表单' }}</VCardTitle><VCardText>
        <VForm @submit.prevent="save"><VTextField v-model="title" label="标题" name="title" :disabled="saving" /><VTextarea v-model="content" label="内容" name="content" rows="7" :disabled="saving" />
          <VAlert v-if="validation" type="error" variant="tonal" class="mt-3">{{ validation }}</VAlert>
          <div class="d-flex justify-end ga-2 mt-4"><VBtn variant="text" :disabled="saving" @click="closeDialog">取消</VBtn><VBtn color="primary" type="submit" :loading="saving">保存</VBtn></div>
        </VForm>
      </VCardText></VCard>
    </VDialog>
    <VDialog v-model="deleteOpen" max-width="420"><VCard><VCardTitle>删除提示词</VCardTitle><VCardText>此操作不可恢复。</VCardText><VCardActions><VBtn variant="text" @click="deleteOpen = false">取消</VBtn><VBtn color="error" @click="confirmDelete">确认删除</VBtn></VCardActions></VCard></VDialog>
  </AppShell>
</template>

<style scoped>
.prompt-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.prompt-card { cursor: pointer; transition: box-shadow .15s ease, transform .15s ease; }
.prompt-card:hover, .prompt-card.selected { box-shadow: 0 6px 20px rgba(19, 76, 141, .14); transform: translateY(-1px); }
.prompt-content { min-height: 84px; white-space: pre-wrap; color: rgba(24, 34, 48, .78); }
</style>
