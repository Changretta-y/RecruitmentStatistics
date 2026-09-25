<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VContainer } from "vuetify/components/VGrid";
import { verifyNotificationAddress } from "../api/notification-settings";

const router = useRouter();
const state = ref<"verifying" | "success" | "error">("verifying");
const message = ref("正在验证收件邮箱…");

async function verifyFromLandingUrl(): Promise<void> {
  // Capture once, then remove the one-time secret synchronously before any request is made.
  const currentUrl = new URL(window.location.href);
  const token = currentUrl.searchParams.get("token") ?? "";
  window.history.replaceState(window.history.state, "", `${currentUrl.pathname}${currentUrl.hash}`);

  if (!token) {
    state.value = "error";
    message.value = "验证链接缺少令牌，请重新申请验证邮件。";
    return;
  }

  try {
    await verifyNotificationAddress(token);
    state.value = "success";
    message.value = "收件地址已确认，可以返回通知设置启用每日邮件。";
  } catch (error) {
    state.value = "error";
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 400 || status === 404) message.value = "验证链接无效、已使用或已过期，请重新申请验证邮件。";
    else if (status === 401) message.value = "登录状态已失效，请重新登录后重试验证。";
    else if (status && status >= 500) message.value = "验证服务暂时不可用，请稍后重试。";
    else message.value = "验证请求失败，请检查网络后重试。";
  }
}

onMounted(() => { void verifyFromLandingUrl(); });
</script>

<template>
  <VContainer class="verify-page py-10">
    <VCard class="verify-card mx-auto" elevation="1">
      <VCardText class="pa-6 pa-md-10 text-center">
        <div v-if="state === 'verifying'" role="status">{{ message }}</div>
        <div v-else :role="state === 'error' ? 'alert' : 'status'">
          <h1 class="text-h5 font-weight-bold mb-3">{{ state === "success" ? "验证成功" : "邮箱验证未完成" }}</h1>
          <p>{{ message }}</p>
        </div>
        <VBtn class="mt-4" color="primary" @click="router.push('/notification-settings')">返回通知设置</VBtn>
      </VCardText>
    </VCard>
  </VContainer>
</template>

<style scoped>
.verify-page { max-width: 760px; }
.verify-card { border: 1px solid #e2e8f0; }
</style>
