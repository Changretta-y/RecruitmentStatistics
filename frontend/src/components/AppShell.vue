<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { VAppBar } from "vuetify/components/VAppBar";
import { VBtn } from "vuetify/components/VBtn";
import { VDivider } from "vuetify/components/VDivider";
import { VIcon } from "vuetify/components/VIcon";
import { VList, VListItem } from "vuetify/components/VList";
import { VNavigationDrawer } from "vuetify/components/VNavigationDrawer";
import { VSpacer } from "vuetify/components/VGrid";

import { useAuthStore } from "../stores/auth";

withDefaults(defineProps<{ title?: string }>(), { title: "我的投递进度" });

const drawerOpen = ref(false);
const desktopSidebarExpanded = ref(true);
const { mobile } = useDisplay();
const auth = useAuthStore();
const router = useRouter();
const username = () => {
  const user = auth.user as Record<string, unknown> | null;
  return user?.username ? String(user.username) : "";
};

function updateDrawerState(open: boolean): void {
  if (mobile.value) drawerOpen.value = open;
}

async function logout(): Promise<void> {
  const navigation = router.push({ path: "/login" });
  try { await auth.logout(); }
  finally { await navigation; }
}
</script>

<template>
  <VNavigationDrawer
    v-if="mobile || desktopSidebarExpanded"
    :model-value="mobile ? drawerOpen : true"
    @update:model-value="updateDrawerState"
    :permanent="!mobile"
    :temporary="mobile"
    location="left"
    width="280"
  >
    <div class="drawer-brand pa-6">
      <img class="brand-logo" src="/logo.png" alt="校招进度管理系统 Logo" width="36" height="36" />
      <span class="drawer-title">我的投递进度</span>
    </div>
    <VDivider />
    <VList nav density="comfortable">
      <VListItem prepend-icon="mdi-view-dashboard-outline" title="我的投递进度" to="/applications" @click="drawerOpen = false" />
      <VListItem prepend-icon="mdi-calendar-month-outline" title="日历" to="/calendar" @click="drawerOpen = false" />
      <VListItem prepend-icon="mdi-account-switch-outline" title="投递共享" to="/sharing" @click="drawerOpen = false" />
      <VListItem prepend-icon="mdi-plus-circle-outline" title="新增投递" to="/applications/new" @click="drawerOpen = false" />
    </VList>
  </VNavigationDrawer>

  <VAppBar color="surface" elevation="1" class="app-bar px-2 px-md-6">
    <VBtn v-if="mobile" icon="mdi-menu" variant="text" aria-label="打开导航" @click="drawerOpen = !drawerOpen" />
    <VBtn
      v-else
      :icon="desktopSidebarExpanded ? 'mdi-menu-open' : 'mdi-menu'"
      variant="text"
      :aria-label="desktopSidebarExpanded ? '收起侧边栏' : '展开侧边栏'"
      @click="desktopSidebarExpanded = !desktopSidebarExpanded"
    />
    <div class="app-title text-primary">{{ title }}</div>
    <VSpacer />
    <VBtn variant="text" prepend-icon="mdi-bell-outline" to="/notification-settings">通知设置</VBtn>
    <span v-if="username()" class="user-name mr-2" aria-label="当前用户">
      <VIcon size="18" class="mr-1">mdi-account-circle-outline</VIcon>{{ username() }}
    </span>
    <VBtn variant="text" prepend-icon="mdi-logout-variant" @click="logout">退出</VBtn>
  </VAppBar>

  <slot />
</template>

<style scoped>
.app-bar { position: sticky; top: 0; z-index: 10; }
.drawer-brand { display: flex; align-items: center; gap: 12px; color: #182230; }
.brand-logo { display: block; width: 36px; height: 36px; object-fit: contain; flex: none; }
.drawer-title, .app-title { font-size: 1rem; line-height: 1.5; font-weight: 700; }
.app-title { letter-spacing: .01em; }
@media (max-width: 680px) { .user-name { display: none; } }
</style>
