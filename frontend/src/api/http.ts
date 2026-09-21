import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import {
  clearTokens,
  getTokens,
  saveTokens,
  TOKEN_LIFETIME_MS,
  type TokenSet,
} from "../utils/token-storage";

const REFRESH_PATH = "/api/v1/auth/refresh/";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").trim();

const axiosDefaults = API_BASE_URL ? { baseURL: API_BASE_URL } : undefined;

type RetriableRequestConfig = InternalAxiosRequestConfig & {
  _authRetry?: boolean;
};

export const publicClient: AxiosInstance = axios.create(axiosDefaults);
export const authClient: AxiosInstance = axios.create(axiosDefaults);

let refreshPromise: Promise<TokenSet> | null = null;

function navigateToLogin(): void {
  if (typeof window === "undefined") return;
  try {
    window.location.assign("/login");
  } catch {
    // Navigation can be unavailable in non-browser test environments.
  }
}

function setBearer(config: InternalAxiosRequestConfig, accessToken: string): void {
  config.headers.Authorization = "Bearer " + accessToken;
}

function isRefreshRequest(config?: AxiosRequestConfig): boolean {
  const url = String(config?.url ?? "").split("?", 1)[0];
  return url === REFRESH_PATH || url.endsWith(REFRESH_PATH);
}

async function refreshAccessToken(): Promise<TokenSet> {
  const current = getTokens();
  if (!current?.refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await authClient.post(REFRESH_PATH, {
    refresh: current.refreshToken,
  });
  const accessToken = response.data?.access;
  const refreshToken = response.data?.refresh;
  if (typeof accessToken !== "string" || typeof refreshToken !== "string") {
    throw new Error("Refresh response did not contain rotated tokens");
  }

  const nextTokens: TokenSet = {
    accessToken,
    refreshToken,
    expiresAt: Date.now() + TOKEN_LIFETIME_MS,
  };
  saveTokens(nextTokens);
  return nextTokens;
}

function getRefreshPromise(): Promise<TokenSet> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken();
  }
  return refreshPromise;
}

function clearAuthentication(error: unknown): never {
  clearTokens();
  navigateToLogin();
  throw error;
}

authClient.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.accessToken) {
    setBearer(config, tokens.accessToken);
  }
  return config;
});

authClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableRequestConfig | undefined;
    const status = Number(error.response?.status ?? (error as AxiosError & { status?: number }).status);
    if (
      status !== 401 ||
      !config ||
      isRefreshRequest(config) ||
      config._authRetry
    ) {
      return Promise.reject(error);
    }

    const tokens = getTokens();
    if (!tokens?.refreshToken) {
      return clearAuthentication(error);
    }

    const pendingRefresh = getRefreshPromise();
    try {
      const rotated = await pendingRefresh;
      config._authRetry = true;
      setBearer(config, rotated.accessToken);
      return authClient.request(config);
    } catch (refreshError) {
      clearTokens();
      navigateToLogin();
      return Promise.reject(refreshError);
    } finally {
      if (refreshPromise === pendingRefresh) {
        refreshPromise = null;
      }
    }
  },
);

export const apiClient = authClient;
export const http = authClient;
export const client = authClient;

export default authClient;
