import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";

import { useAuthStore } from "../stores/auth";
import { getTokens } from "../utils/token-storage";
import ApplicationsView from "../views/ApplicationsView.vue";
import ApplicationFormView from "../views/ApplicationFormView.vue";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/applications",
  },
  {
    path: "/login",
    name: "login",
    component: LoginView,
  },
  {
    path: "/register",
    name: "register",
    component: RegisterView,
  },
  {
    path: "/applications",
    name: "applications",
    component: ApplicationsView,
    meta: { requiresAuth: true },
  },
  {
    path: "/applications/new",
    name: "application-new",
    component: ApplicationFormView,
    meta: { requiresAuth: true },
  },
  {
    path: "/applications/:id/edit",
    name: "application-edit",
    component: ApplicationFormView,
    meta: { requiresAuth: true },
  },
];

const history =
  typeof window === "undefined" ? createMemoryHistory() : createWebHistory();

export const router = createRouter({
  history,
  routes,
});

router.beforeEach(async (to) => {
  let store: ReturnType<typeof useAuthStore> | null = null;
  try {
    store = useAuthStore();
  } catch {
    // Tests may use the router without installing Pinia.
  }

  if (store && !store.initialized) {
    await store.initialize();
  }

  const authenticated = store
    ? store.user !== null
    : getTokens() !== null;

  if (to.meta.requiresAuth && !authenticated) {
    return {
      name: "login",
      query: { redirect: to.fullPath },
    };
  }

  if (
    authenticated &&
    (to.name === "login" || to.name === "register")
  ) {
    return { name: "applications" };
  }

  return true;
});

export default router;
