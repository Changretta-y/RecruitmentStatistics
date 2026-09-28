<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ avatar: string; username: string }>();
const palette = ["#dbeafe", "#fce7f3", "#dcfce7", "#fef3c7", "#ede9fe", "#cffafe", "#ffedd5", "#e2e8f0"];
const symbols = ["✦", "❀", "◆", "☀", "☾", "✿", "★", "❖"];
const variant = computed(() => Math.max(0, Math.min(7, Number(props.avatar.slice(-2)) - 1)) || 0);
</script>

<template>
  <svg class="sharing-avatar" role="img" :aria-label="`${username} 的头像`" viewBox="0 0 48 48">
    <rect width="48" height="48" rx="16" :fill="palette[variant]" />
    <circle cx="24" cy="24" r="17" fill="white" opacity=".6" />
    <text x="24" y="32" text-anchor="middle" font-size="25" fill="#3157d5">{{ symbols[variant] }}</text>
  </svg>
</template>

<style scoped>
.sharing-avatar { flex: 0 0 40px; width: 40px; height: 40px; }
</style>
