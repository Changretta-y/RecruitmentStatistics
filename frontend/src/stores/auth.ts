import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { router } from "../router";

import {
  getMe,
  login as requestLogin,
  logout as requestLogout,
  type LoginCredentials,
} from "../api/auth";
import {
  clearTokens,
  getTokens,
  saveTokens,
  TOKEN_LIFETIME_MS,
} from "../utils/token-storage";

export type AuthUser = Record<string, unknown>;
type LoginSession = {
  access: string;
  refresh: string;
  user: AuthUser;
};

let initializePromise: Promise<void> | null = null;

async function navigateToLogin(): Promise<void> {
  try {
    await router.push("/login");
  } catch {
    if (typeof window === "undefined") return;
    try {
      window.location.assign("/login");
    } catch {
      // Navigation is unavailable in non-browser test environments.
    }
  }
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<AuthUser | null>(null);
  const initialized = ref(false);
  const loading = ref(false);

  async function initialize(): Promise<void> {
    if (initialized.value) return;
    if (initializePromise) return initializePromise;

    initializePromise = (async () => {
      loading.value = true;
      try {
        if (!getTokens()) {
          user.value = null;
          return;
        }
        user.value = (await getMe()) as AuthUser;
      } catch {
        user.value = null;
        clearTokens();
      } finally {
        initialized.value = true;
        loading.value = false;
      }
    })();

    try {
      await initializePromise;
    } finally {
      initializePromise = null;
    }
  }

  async function logout(): Promise<void> {
    try {
      await requestLogout();
    } catch {
      // Local authentication state is cleared even when the API fails.
    } finally {
      user.value = null;
      clearTokens();
      await navigateToLogin();
    }
  }

  async function login(
    credentialsOrSession: LoginCredentials | LoginSession,
  ): Promise<AuthUser> {
    const response =
      "access" in credentialsOrSession
        ? { data: credentialsOrSession }
        : (await requestLogin(credentialsOrSession)) as {
            data: LoginSession;
          };
    const data = response.data as LoginSession;
    saveTokens({
      accessToken: data.access,
      refreshToken: data.refresh,
      expiresAt: Date.now() + TOKEN_LIFETIME_MS,
    });
    user.value = data.user;
    initialized.value = true;
    return data.user;
  }

  return {
    user,
    initialized,
    loading,
    isAuthenticated: computed(() => user.value !== null),
    initialize,
    fetchMe: initialize,
    login,
    logout,
  };
});

export default useAuthStore;
