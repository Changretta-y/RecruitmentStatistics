export type TokenSet = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

export const TOKEN_STORAGE_KEY = "auth_tokens";
export const TOKEN_LIFETIME_MS = 7 * 24 * 60 * 60 * 1000;

function storage(): Storage | null {
  if (typeof globalThis.localStorage === "undefined") return null;
  return globalThis.localStorage;
}

function isTokenSet(value: unknown): value is TokenSet {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<TokenSet>;
  return (
    typeof candidate.accessToken === "string" &&
    typeof candidate.refreshToken === "string" &&
    typeof candidate.expiresAt === "number" &&
    Number.isFinite(candidate.expiresAt)
  );
}

export function saveTokens(tokens: TokenSet): void {
  storage()?.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
}

export function getTokens(): TokenSet | null {
  const store = storage();
  if (!store) return null;

  const raw = store.getItem(TOKEN_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isTokenSet(parsed) || Date.now() >= parsed.expiresAt) {
      clearTokens();
      return null;
    }
    return parsed;
  } catch {
    clearTokens();
    return null;
  }
}

export function clearTokens(): void {
  storage()?.removeItem(TOKEN_STORAGE_KEY);
}

export const tokenStorage = {
  saveTokens,
  getTokens,
  clearTokens,
};

export default tokenStorage;
