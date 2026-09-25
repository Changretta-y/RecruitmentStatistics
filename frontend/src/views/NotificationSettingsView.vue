<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VAppBar } from "vuetify/components/VAppBar";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VCheckbox } from "vuetify/components/VCheckbox";
import { VContainer } from "vuetify/components/VGrid";
import { VIcon } from "vuetify/components/VIcon";
import { VSpacer } from "vuetify/components/VGrid";
import { VTextField } from "vuetify/components/VTextField";

import {
  getNotificationSettings,
  requestNotificationVerification,
  saveNotificationSettings,
  type DeliveryStatus,
  type NotificationSettings,
} from "../api/notification-settings";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const settings = ref<NotificationSettings | null>(null);
const recipientEmail = ref("");
const dailyTime = ref("");
const enabled = ref(false);
const loading = ref(true);
const saving = ref(false);
const sendingVerification = ref(false);
const pageError = ref("");
const successMessage = ref("");
const emailError = ref("");
const timeError = ref("");
const verificationMessage = ref("");

const canEnable = computed(() => Boolean(recipientEmail.value.trim())
  && /^([01]\d|2[0-3]):[0-5]\d$/.test(dailyTime.value)
  && Boolean(settings.value?.verified)
  && recipientEmail.value.trim() === settings.value?.recipient_email);
const toggleDisabled = computed(() => !enabled.value && !canEnable.value);
const username = computed(() => {
  const user = auth.user as Record<string, unknown> | null;
  return user?.username ? String(user.username) : "";
});

function statusText(status: DeliveryStatus): string {
  const labels: Record<DeliveryStatus, string> = {
    pending: "等待发送", sending: "正在发送", accepted: "邮件服务已接受", failed_retryable: "发送失败，将重试",
    failed: "发送失败", unknown: "发送结果待核实",
  };
  return labels[status] ?? "状态未知";
}

function assignSettings(value: NotificationSettings): void {
  settings.value = value;
  recipientEmail.value = value.recipient_email ?? "";
  dailyTime.value = value.daily_time ?? "";
  enabled.value = Boolean(value.enabled);
}

async function loadSettings(): Promise<void> {
  loading.value = true;
  pageError.value = "";
  try {
    assignSettings(await getNotificationSettings());
  } catch (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    pageError.value = status === 401 ? "登录状态已失效，请重新登录。" : "通知设置加载失败，请检查网络后重试。";
  } finally {
    loading.value = false;
  }
}

function fieldErrors(error: unknown): void {
  const response = (error as { response?: { status?: number; data?: { details?: Record<string, unknown> } } })?.response;
  const status = response?.status;
  const details = response?.data?.details ?? {};
  const message = (value: unknown): string => Array.isArray(value) ? value.join(" ") : typeof value === "string" ? value : "";
  emailError.value = message(details.recipient_email);
  timeError.value = message(details.daily_time);
  if (status === 400) {
    if (!emailError.value && !timeError.value) pageError.value = "请检查收件邮箱、每日时间和启用条件。";
  } else if (status === 429) pageError.value = "验证邮件请求过于频繁，请稍后再试。";
  else if (status === 401) pageError.value = "登录状态已失效，请重新登录。";
  else if (status && status >= 500) pageError.value = "服务暂时不可用，请稍后重试。";
  else pageError.value = "保存失败，请检查网络后重试。";
}

async function save(): Promise<void> {
  if (saving.value || loading.value) return;
  saving.value = true;
  pageError.value = "";
  successMessage.value = "";
  emailError.value = "";
  timeError.value = "";
  verificationMessage.value = "";
  const previousEmail = settings.value?.recipient_email ?? "";
  try {
    const updated = await saveNotificationSettings({
      recipient_email: recipientEmail.value.trim(),
      daily_time: dailyTime.value,
      enabled: enabled.value,
    });
    assignSettings(updated);
    successMessage.value = previousEmail && previousEmail !== updated.recipient_email
      ? "设置已保存。旧地址已立即停用，请验证新地址后再启用通知。"
      : "设置已保存。";
  } catch (error) {
    fieldErrors(error);
    // Refresh server state after an uncertain request, while retaining the user's editable draft.
    try { settings.value = await getNotificationSettings(); } catch { /* Keep the last known server state. */ }
  } finally {
    saving.value = false;
  }
}

async function sendVerification(): Promise<void> {
  if (sendingVerification.value || saving.value) return;
  sendingVerification.value = true;
  pageError.value = "";
  verificationMessage.value = "";
  emailError.value = "";
  timeError.value = "";
  try {
    if (settings.value && recipientEmail.value.trim() !== settings.value.recipient_email) {
      try {
        // Verification is bound to the saved pending address; persist a changed address first.
        assignSettings(await saveNotificationSettings({
          recipient_email: recipientEmail.value.trim(),
          daily_time: dailyTime.value,
          enabled: false,
        }));
      } catch (error) {
        fieldErrors(error);
        return;
      }
    }
    await requestNotificationVerification();
    verificationMessage.value = "验证邮件已发送，请检查收件箱。";
  } catch (error) {
    const status = (error as { response?: { status?: number; data?: { details?: Record<string, unknown> } } })?.response?.status;
    if (status === 429) verificationMessage.value = "请求过于频繁，请稍后再试。";
    else if (status === 400) verificationMessage.value = "请先保存有效的收件邮箱，再申请验证邮件。";
    else if (status === 401) verificationMessage.value = "登录状态已失效，请重新登录。";
    else verificationMessage.value = status && status >= 500
      ? "验证邮件暂时无法发送，请稍后重试。"
      : "验证邮件请求失败，请检查网络后重试。";
  } finally {
    sendingVerification.value = false;
  }
}

function logout(): void {
  void auth.logout().finally(() => router.push("/login"));
}

onMounted(() => { void loadSettings(); });
</script>

<template>
  <VAppBar color="surface" elevation="1" class="px-3 px-md-6">
    <VBtn icon="mdi-arrow-left" variant="text" aria-label="返回投递列表" @click="router.push('/applications')" />
    <VIcon color="primary" class="mr-2">mdi-bell-outline</VIcon>
    <span class="text-primary font-weight-bold">通知设置</span>
    <VSpacer />
    <span v-if="username" class="mr-3">{{ username }}</span>
    <VBtn variant="text" prepend-icon="mdi-logout-variant" @click="logout">退出</VBtn>
  </VAppBar>

  <VContainer class="notification-page py-6 py-md-10">
    <header class="mb-6">
      <p class="text-overline text-primary mb-1">每日安排邮件</p>
      <h1 class="text-h4 font-weight-bold mb-2">通知设置</h1>
      <p class="text-medium-emphasis">配置收件地址和每日发送时间。邮件由平台服务端发送。</p>
    </header>

    <VAlert v-if="pageError" type="error" variant="tonal" class="mb-4" role="alert">{{ pageError }}</VAlert>
    <VAlert v-if="successMessage" type="success" variant="tonal" class="mb-4" role="status">{{ successMessage }}</VAlert>

    <VCard class="notification-card" :loading="loading" elevation="1">
      <VCardText class="pa-5 pa-md-8">
        <div v-if="loading" role="status">正在加载通知设置…</div>
        <form v-else aria-label="通知设置" class="settings-form" @submit.prevent="save">
          <VTextField
            v-model="recipientEmail"
            name="recipient_email"
            label="收件邮箱"
            type="email"
            autocomplete="email"
            :error-messages="emailError"
            :hide-details="!emailError"
            :disabled="saving"
          />
          <VTextField
            v-model="dailyTime"
            name="daily_time"
            label="每日推送时间（北京时间）"
            type="time"
            :error-messages="timeError"
            :hide-details="!timeError"
            :disabled="saving"
          />
          <p class="timezone-note">北京时间（Asia/Shanghai）</p>

          <VAlert v-if="settings?.verified" type="success" variant="tonal" density="compact" class="mb-4" role="status">
            收件邮箱已验证：{{ settings.recipient_email }}
          </VAlert>
          <VAlert v-else type="warning" variant="tonal" density="compact" class="mb-4" role="status">
            收件邮箱待验证。修改邮箱会立即停用旧地址，并关闭每日推送。
          </VAlert>

          <VCheckbox
            v-model="enabled"
            name="enabled"
            label="启用每日安排邮件"
            color="primary"
            :disabled="toggleDisabled || saving"
            hide-details
            class="mb-4"
          />

          <div v-if="settings?.last_delivery" class="delivery-status mb-5" aria-label="最近一次发送状态">
            最近发送：{{ settings.last_delivery.date }} · {{ statusText(settings.last_delivery.status) }}
          </div>
          <div v-else class="delivery-status mb-5">尚无发送记录</div>

          <VAlert v-if="verificationMessage" :type="verificationMessage.includes('已发送') ? 'success' : 'warning'" variant="tonal" class="mb-4" role="status">
            {{ verificationMessage }}
          </VAlert>

          <div class="form-actions">
            <VBtn type="submit" color="primary" :loading="saving" :disabled="loading || saving">保存</VBtn>
            <VBtn
              v-if="!settings?.verified || recipientEmail.trim() !== settings?.recipient_email"
              type="button"
              variant="tonal"
              :loading="sendingVerification"
              :disabled="sendingVerification || saving || !recipientEmail.trim()"
              @click="sendVerification"
            >发送验证邮件</VBtn>
          </div>
        </form>
      </VCardText>
    </VCard>
  </VContainer>
</template>

<style scoped>
.notification-page { max-width: 860px; }
.notification-card { border: 1px solid #e2e8f0; }
.settings-form { max-width: 620px; }
.timezone-note { margin: -12px 0 20px; color: #526174; font-size: .92rem; }
.delivery-status { color: #526174; font-size: .92rem; }
.form-actions { display: flex; flex-wrap: wrap; gap: 12px; }
</style>
