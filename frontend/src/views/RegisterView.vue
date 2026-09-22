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

import { register } from "../api/auth";

const router = useRouter();
const form = reactive({
  username: "",
  email: "",
  password: "",
  password_confirm: "",
});
const errors = ref<Record<string, string[]>>({});
const formError = ref("");
const successMessage = ref("");
const loading = ref(false);

function firstError(field: string): string {
  return errors.value[field]?.[0] ?? "";
}

function validate(): boolean {
  const nextErrors: Record<string, string[]> = {};
  if (form.username.trim().length < 3 || form.username.trim().length > 30) {
    nextErrors.username = ["用户名长度应为 3-30 个字符。"];
  }
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    nextErrors.email = ["请输入有效邮箱。"];
  }
  if (form.password.length < 8) nextErrors.password = ["密码至少需要 8 个字符。"];
  if (form.password !== form.password_confirm) {
    nextErrors.password_confirm = ["两次输入的密码不一致。"];
  }
  errors.value = nextErrors;
  return Object.keys(nextErrors).length === 0;
}

function mapRegistrationError(error: any): void {
  const response = error?.response?.data;
  const details = response?.details;
  if (details && typeof details === "object") {
    errors.value = details;
    return;
  }

  if (response?.code === "WEAK_PASSWORD") {
    errors.value = {
      password: ["密码过于简单，请使用至少 8 个字符且不易被猜到的密码。"],
    };
    return;
  }

  if (response?.code === "PASSWORDS_DO_NOT_MATCH") {
    errors.value = {
      password_confirm: ["两次输入的密码不一致。"],
    };
    return;
  }

  if (response?.code === "USERNAME_ALREADY_EXISTS") {
    errors.value = {
      username: ["用户名已存在，请换一个用户名。"],
    };
    return;
  }

  formError.value = "注册失败，请稍后重试。";
}

async function submit(): Promise<void> {
  successMessage.value = "";
  formError.value = "";
  if (!validate()) return;

  loading.value = true;
  try {
    const response: any = await register({
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
      password_confirm: form.password_confirm,
    });
    if (response?.response?.status >= 400) throw response;
    successMessage.value = "注册成功，请登录";
    await router.push("/login");
  } catch (error: any) {
    mapRegistrationError(error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <VContainer class="auth-page py-10 py-md-16" style="padding-left: 16px; padding-right: 16px">
    <VCard class="auth-card mx-auto" width="100%" max-width="560" elevation="2">
      <VCardTitle class="auth-title text-h4">注册</VCardTitle>
      <VCardText>
        <VAlert v-if="successMessage" class="mb-4" type="success" variant="tonal" role="status">
          {{ successMessage }}
        </VAlert>
        <VAlert v-if="formError" class="mb-5" type="error" variant="tonal" role="alert">
          {{ formError }}
        </VAlert>
        <form aria-label="注册表单" @submit.prevent="submit">
          <VTextField
            id="register-username"
            v-model="form.username"
            name="username"
            label="用户名"
            autocomplete="username"
            :error-messages="firstError('username') ? [firstError('username')] : []"
          />

          <VTextField
            id="register-email"
            v-model="form.email"
            name="email"
            type="email"
            label="邮箱（可选）"
            autocomplete="email"
            :error-messages="firstError('email') ? [firstError('email')] : []"
          />

          <VTextField
            id="register-password"
            v-model="form.password"
            name="password"
            type="password"
            label="密码"
            autocomplete="new-password"
            :error-messages="firstError('password') ? [firstError('password')] : []"
          />

          <VTextField
            id="register-password-confirm"
            v-model="form.password_confirm"
            name="password_confirm"
            type="password"
            label="确认密码"
            autocomplete="new-password"
            :error-messages="firstError('password_confirm') ? [firstError('password_confirm')] : []"
          />

          <VBtn class="mt-3" type="submit" color="primary" block :loading="loading" :disabled="loading">
            {{ loading ? "提交中…" : "注册" }}
          </VBtn>
        </form>
      </VCardText>
      <VCardActions class="justify-center pb-5">
        <RouterLink to="/login" class="text-primary font-weight-medium">返回登录</RouterLink>
      </VCardActions>
    </VCard>
  </VContainer>
</template>

<style scoped>
.auth-page { min-height: calc(100vh - 64px); display: flex; align-items: center; }
.auth-title { justify-content: center; padding-top: 32px; font-weight: 800; }
</style>

