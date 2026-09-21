import { apiClient, publicClient } from "./http";
import { getTokens } from "../utils/token-storage";

export type LoginCredentials = {
  username: string;
  password: string;
};

export type RegisterPayload = {
  username: string;
  email?: string;
  password: string;
  password_confirm: string;
};

export async function login(credentials: LoginCredentials): Promise<unknown> {
  return publicClient.post("/api/v1/auth/login/", credentials);
}

export async function register(payload: RegisterPayload): Promise<unknown> {
  return publicClient.post("/api/v1/auth/register/", payload);
}

export async function getMe(): Promise<unknown> {
  const response = await apiClient.get("/api/v1/auth/me/");
  return response.data;
}

export const me = getMe;
export const fetchMe = getMe;

export async function logout(): Promise<unknown> {
  const tokens = getTokens();
  if (!tokens?.refreshToken) return undefined;
  return apiClient.post("/api/v1/auth/logout/", {
    refresh: tokens.refreshToken,
  });
}

export const postLogout = logout;
