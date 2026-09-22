<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
import { VCardActions } from "vuetify/components/VCard";
import { VCardText } from "vuetify/components/VCard";
import { VCardTitle } from "vuetify/components/VCard";
import { VContainer } from "vuetify/components/VGrid";
import { VTextField } from "vuetify/components/VTextField";

import { login as requestLogin } from "../api/auth";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const form = reactive({ username: "", password: "" });
const errors = ref<Record<string, string[]>>({});
const formError = ref("");
const loading = ref(false);

function firstError(field: string): string {
  return errors.value[field]?.[0] ?? "";
}

function validate(): boolean {
  const nextErrors: Record<string, string[]> = {};
  if (!form.username.trim()) nextErrors.username = ["请输入用户名。"];
  if (!form.password) nextErrors.password = ["请输入密码。"];
  errors.value = nextErrors;
  return Object.keys(nextErrors).length === 0;
}

function errorMessage(error: any): string {
  if (error?.response?.status === 401) return "用户名或密码错误，请重试。";
  return "登录失败，请稍后重试。";
}

async function submit(): Promise<void> {
  formError.value = "";
  if (!validate()) return;

  loading.value = true;
  try {
    const response: any = await requestLogin({
      username: form.username.trim(),
      password: form.password,
    });
    await authStore.login(response?.data ?? response);
    const redirect = router.currentRoute.value.query.redirect;
    const target = typeof redirect === "string" && redirect.startsWith("/")
      ? redirect
      : "/applications";
    await router.push(target);
  } catch (error: any) {
    const details = error?.response?.data?.details;
    if (details && typeof details === "object") errors.value = details;
    else formError.value = errorMessage(error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <VContainer class="auth-page py-10 py-md-16" style="padding-left: 16px; padding-right: 16px">
    <VCard class="auth-card mx-auto" width="100%" max-width="560" elevation="2">
      <VCardTitle class="auth-title text-h4">登录</VCardTitle>
      <VCardText>
        <VAlert v-if="formError" class="mb-5" type="error" variant="tonal" role="alert">
          {{ formError }}
        </VAlert>
        <form aria-label="登录表单" @submit.prevent="submit">
          <VTextField
            id="login-username"
            v-model="form.username"
            name="username"
            label="用户名"
            autocomplete="username"
            :error-messages="firstError('username') ? [firstError('username')] : []"
          />

          <VTextField
            id="login-password"
            v-model="form.password"
            name="password"
            label="密码"
            type="password"
            autocomplete="current-password"
            :error-messages="firstError('password') ? [firstError('password')] : []"
          />

          <VBtn
            class="mt-3"
            type="submit"
            color="primary"
            block
            :loading="loading"
            :disabled="loading"
          >
            {{ loading ? "登录中…" : "登录" }}
          </VBtn>
        </form>
      </VCardText>
      <VCardActions class="justify-center pb-5">
        <span class="text-medium-emphasis">还没有账号？</span>
        <RouterLink to="/register" class="text-primary font-weight-medium">注册</RouterLink>
      </VCardActions>
    </VCard>
  </VContainer>
</template>

<style scoped>
.auth-page { min-height: calc(100vh - 64px); display: flex; align-items: center; }
.auth-title { justify-content: center; padding-top: 32px; font-weight: 800; }
</style>

