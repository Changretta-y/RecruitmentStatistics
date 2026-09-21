<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VContainer } from "vuetify/components/VGrid";
import { VProgressCircular } from "vuetify/components/VProgressCircular";

import { getApplication } from "../api/applications";
import ApplicationForm from "../components/ApplicationForm.vue";
import type { JobApplication } from "../types/application";

const route = useRoute();
const router = useRouter();
const application = ref<JobApplication | null>(null);
const loading = ref(false);
const loadError = ref("");
const isEdit = computed(() => route.name === "application-edit");

async function loadApplication(): Promise<void> {
  if (!isEdit.value) return;
  const id = String(route.params.id ?? "");
  if (!id) {
    loadError.value = "投递记录不存在。";
    return;
  }
  loading.value = true;
  loadError.value = "";
  try {
    application.value = await getApplication(id);
  } catch {
    loadError.value = "投递记录不存在或暂时无法加载。";
  } finally {
    loading.value = false;
  }
}

function backToApplications(): void {
  void router.push({ name: "applications" });
}

onMounted(() => {
  void loadApplication();
});
</script>

<template>
  <VContainer class="application-form-page py-8 py-md-12">
    <div v-if="loading" class="state-panel" role="status">
      <VProgressCircular color="primary" indeterminate size="42" />
      <span>加载中…</span>
    </div>
    <VCard v-else-if="loadError" class="state-card mx-auto" max-width="760" elevation="2">
      <VCardText class="state-panel" role="alert">
        <VAlert type="error" variant="tonal" class="mb-5">{{ loadError }}</VAlert>
        <VBtn type="button" color="primary" @click="backToApplications">返回投递列表</VBtn>
      </VCardText>
    </VCard>
    <ApplicationForm
      v-else-if="!isEdit || application"
      :mode="isEdit ? 'edit' : 'create'"
      :application="application"
      @close="backToApplications"
    />
  </VContainer>
</template>

<style scoped>
.application-form-page { max-width: 860px; }
.state-panel { min-height: 220px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; text-align: center; }
.state-card { width: 100%; }
</style>

