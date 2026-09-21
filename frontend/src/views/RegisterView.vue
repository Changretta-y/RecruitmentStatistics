<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { VAlert } from "vuetify/components/VAlert";
import { VBtn } from "vuetify/components/VBtn";
import { VCard } from "vuetify/components/VCard";
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
    const details = error?.response?.data?.details;
    if (details && typeof details === "object") errors.value = details;
    else formError.value = "注册失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <VContainer class="auth-page py-10 py-md-16">
    <VCard class="auth-card mx-auto" max-width="480" elevation="2">
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
          <p v-if="firstError('username')" class="field-error" role="alert">{{ firstError("username") }}</p>

          <VTextField
            id="register-email"
            v-model="form.email"
            name="email"
            type="email"
            label="邮箱（可选）"
            autocomplete="email"
            :error-messages="firstError('email') ? [firstError('email')] : []"
          />
          <p v-if="firstError('email')" class="field-error" role="alert">{{ firstError("email") }}</p>

          <VTextField
            id="register-password"
            v-model="form.password"
            name="password"
            type="password"
            label="密码"
            autocomplete="new-password"
            :error-messages="firstError('password') ? [firstError('password')] : []"
          />
          <p v-if="firstError('password')" class="field-error" role="alert">{{ firstError("password") }}</p>

          <VTextField
            id="register-password-confirm"
            v-model="form.password_confirm"
            name="password_confirm"
            type="password"
            label="确认密码"
            autocomplete="new-password"
            :error-messages="firstError('password_confirm') ? [firstError('password_confirm')] : []"
          />
          <p v-if="firstError('password_confirm')" class="field-error" role="alert">
            {{ firstError("password_confirm") }}
          </p>

          <VBtn class="mt-3" type="submit" color="primary" block :loading="loading" :disabled="loading">
            {{ loading ? "提交中…" : "注册" }}
          </VBtn>
        </form>
      </VCardText>
    </VCard>
  </VContainer>
</template>

<style scoped>
.auth-page { min-height: calc(100vh - 64px); display: flex; align-items: center; }
.auth-title { justify-content: center; padding-top: 32px; font-weight: 800; }
.field-error { margin: -14px 0 14px; color: #b42318; font-size: .875rem; }
</style>

