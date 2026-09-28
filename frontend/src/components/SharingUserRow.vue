<script setup lang="ts">
import type { SharingUser } from "../types/sharing";
import SharingAvatar from "./SharingAvatar.vue";

defineProps<{ user: SharingUser; busy?: boolean }>();
defineEmits<{ request: [user: SharingUser] }>();
</script>

<template>
  <li class="user-row">
    <SharingAvatar :avatar="user.avatar" :username="user.username" />
    <div class="user-details"><strong>{{ user.username }}</strong><small>ID {{ user.id }}</small></div>
    <button v-if="user.relationship === 'none'" class="sharing-action" :disabled="busy" @click="$emit('request', user)">申请互看</button>
    <small v-else class="relationship">{{ user.relationship === 'connected' ? '已共享' : user.relationship === 'incoming_pending' ? '待我同意' : '待对方同意' }}</small>
  </li>
</template>

<style scoped>
.user-row { display:flex; align-items:center; gap:10px; min-width:0; padding:10px 0; }
.user-details { flex:1; min-width:0; display:grid; gap:3px; }
strong { font-size:.86rem; overflow-wrap:anywhere; } small { color:#667085; font-size:.76rem; }
.relationship { max-width:75px; }
.sharing-action { color:#3157d5; font-weight:600; font-size:.8rem; padding:8px; border-radius:8px; white-space:nowrap; }
.sharing-action:hover { background:#eff4ff; }.sharing-action:disabled { opacity:.5; }
</style>
