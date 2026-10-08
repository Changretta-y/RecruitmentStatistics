const MANAGED_FIELDS = [
  "company_name",
  "position_name",
  "application_url",
  "application_status",
  "application_time",
];

const TRACKING_PARAMETERS = new Set(["fbclid", "gclid"]);

export function collapseWhitespace(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function decodeEntities(value) {
  const entities = {
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    nbsp: " ",
    quot: '"',
  };
  return String(value ?? "")
    .replace(/&#(\d+);/g, (_match, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) =>
      String.fromCodePoint(Number.parseInt(code, 16)),
    )
    .replace(/&([a-z]+);/gi, (match, name) => entities[name.toLowerCase()] ?? match);
}

function visibleText(value) {
  return collapseWhitespace(
    decodeEntities(
      String(value ?? "")
        .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
        .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " "),
    ),
  );
}

export function normalizeApplicationUrl(value) {
  const raw = collapseWhitespace(value);
  if (!raw) return "";

  try {
    const url = new URL(raw);
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      const normalizedKey = key.toLowerCase();
      if (normalizedKey.startsWith("utm_") || TRACKING_PARAMETERS.has(normalizedKey)) {
        url.searchParams.delete(key);
      }
    }
    return url.toString();
  } catch {
    return raw.split("#", 1)[0];
  }
}

function candidate(value, source, confidence) {
  const normalized = collapseWhitespace(value);
  return normalized ? { value: normalized, source, confidence } : null;
}

function jobPostingFrom(value) {
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = jobPostingFrom(item);
      if (found) return found;
    }
    return null;
  }
  if (!value || typeof value !== "object") return null;

  const types = Array.isArray(value["@type"]) ? value["@type"] : [value["@type"]];
  if (types.some((type) => String(type).toLowerCase() === "jobposting")) return value;

  for (const child of Object.values(value)) {
    const found = jobPostingFrom(child);
    if (found) return found;
  }
  return null;
}

function jsonLdCandidates(html) {
  const scripts = String(html).matchAll(
    /<script\b[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi,
  );
  for (const match of scripts) {
    try {
      const posting = jobPostingFrom(JSON.parse(decodeEntities(match[1]).trim()));
      if (!posting) continue;
      const organization = posting.hiringOrganization;
      const company =
        typeof organization === "string" ? organization : organization?.name;
      return {
        company: candidate(company, "json-ld", "high"),
        position: candidate(posting.title, "json-ld", "high"),
      };
    } catch {
      // A malformed JSON-LD block is ignored and lower-priority sources are tried.
    }
  }
  return { company: null, position: null };
}

function attributesOf(tag) {
  const attributes = {};
  for (const match of tag.matchAll(/([:@\w-]+)\s*=\s*(["'])([\s\S]*?)\2/g)) {
    attributes[match[1].toLowerCase()] = decodeEntities(match[3]);
  }
  return attributes;
}

function metadataCandidates(html) {
  const values = new Map();
  for (const match of String(html).matchAll(/<meta\b[^>]*>/gi)) {
    const attributes = attributesOf(match[0]);
    const key = collapseWhitespace(attributes.property || attributes.name).toLowerCase();
    const content = collapseWhitespace(attributes.content);
    if (key && content && !values.has(key)) values.set(key, content);
  }

  const first = (keys) => keys.map((key) => values.get(key)).find(Boolean);
  return {
    company: candidate(
      first(["job:company", "company", "og:site_name", "application-name"]),
      "meta",
      "medium",
    ),
    position: candidate(
      first(["job:title", "position", "og:title", "twitter:title"]),
      "meta",
      "medium",
    ),
  };
}

function firstVisibleMatch(html, patterns) {
  for (const pattern of patterns) {
    const match = pattern.exec(html);
    const value = visibleText(match?.[1]);
    if (value) return value;
  }
  return "";
}

function domCandidates(html) {
  const source = String(html);
  const company = firstVisibleMatch(source, [
    /<dt\b[^>]*>\s*(?:公司|企业|单位|Company)\s*<\/dt>\s*<dd\b[^>]*>([\s\S]*?)<\/dd>/i,
    /<[^>]+itemprop\s*=\s*["']hiringOrganization["'][^>]*>([\s\S]*?)<\/[^>]+>/i,
    /<[^>]+(?:class|data-testid)\s*=\s*["'][^"']*company[^"']*["'][^>]*>([\s\S]*?)<\/[^>]+>/i,
  ]);
  const position = firstVisibleMatch(source, [
    /<[^>]+itemprop\s*=\s*["']title["'][^>]*>([\s\S]*?)<\/[^>]+>/i,
    /<h1\b[^>]*>([\s\S]*?)<\/h1>/i,
    /<[^>]+(?:class|data-testid)\s*=\s*["'][^"']*(?:job[-_ ]?title|position)[^"']*["'][^>]*>([\s\S]*?)<\/[^>]+>/i,
  ]);
  return {
    company: candidate(company, "dom", "low"),
    position: candidate(position, "dom", "low"),
  };
}

export function extractJobDetails({ html, activeTabUrl }) {
  const jsonLd = jsonLdCandidates(html);
  const meta = metadataCandidates(html);
  const dom = domCandidates(html);
  const company = jsonLd.company || meta.company || dom.company;
  const position = jsonLd.position || meta.position || dom.position;
  const warnings = [];

  if (!company) warnings.push("未识别到公司，请手工填写或从页面点选公司。");
  else if (company.confidence === "low") warnings.push("公司识别置信度低，请确认。");
  if (!position) warnings.push("未识别到岗位，请手工填写或从页面点选岗位。");
  else if (position.confidence === "low") warnings.push("岗位识别置信度低，请确认。");

  return {
    company,
    position,
    url: normalizeApplicationUrl(activeTabUrl),
    needsConfirmation:
      !company || !position || company.confidence === "low" || position.confidence === "low",
    warnings,
  };
}

function sameContext(left, right) {
  return Boolean(
    left &&
      right &&
      left.tabId === right.tabId &&
      String(left.url) === String(right.url),
  );
}

function draftKey(context) {
  return `selection-draft:${context.tabId}:${encodeURIComponent(String(context.url))}`;
}

export function createSelectionController({ storage }) {
  let active = null;
  return {
    async begin(field, context) {
      active = { field, context: { ...context } };
    },
    async acceptVisibleText(context, text) {
      if (!active || !sameContext(active.context, context)) return false;
      const normalized = collapseWhitespace(text);
      if (!normalized) return false;
      const key = draftKey(context);
      const existing = await storage.get(key);
      const draft = existing && typeof existing === "object" ? { ...existing } : {};
      draft[active.field] = normalized;
      await storage.set(key, draft);
      active = null;
      return true;
    },
    async handleKey(key) {
      if (key === "Escape" || key === "Esc") active = null;
    },
    isSelecting() {
      return active !== null;
    },
    async getDraft(context) {
      const value = await storage.get(draftKey(context));
      return value && typeof value === "object" ? value : null;
    },
  };
}

function validAuth(value) {
  return Boolean(
    value &&
      typeof value === "object" &&
      typeof value.access === "string" &&
      typeof value.refresh === "string",
  );
}

function errorFromResponse(response, fallback) {
  return response
    .clone()
    .json()
    .catch(() => ({}))
    .then((body) => {
      const code = typeof body?.code === "string" ? body.code : fallback;
      return new Error(`${fallback}: ${code}`);
    });
}

export function createAuthClient({ apiOrigin, fetch: fetchImpl, storage }) {
  const origin = String(apiOrigin).replace(/\/+$/, "");
  let user = null;
  let refreshPromise = null;

  async function loadAuth() {
    const value = await storage.get("auth");
    if (!validAuth(value)) return null;
    user = value.user ?? null;
    return value;
  }

  async function clearAuth() {
    user = null;
    await storage.remove("auth");
  }

  async function persist(body, previousUser = null) {
    const now = Date.now();
    const auth = {
      access: body.access,
      refresh: body.refresh,
      accessExpiresAt: now + Number(body.access_expires_in || 1800) * 1000,
      refreshExpiresAt: now + Number(body.refresh_expires_in || 604800) * 1000,
      user: body.user ?? previousUser,
    };
    user = auth.user ?? null;
    await storage.set("auth", auth);
    return auth;
  }

  async function refreshSession(refreshToken, previousUser) {
    if (!refreshPromise) {
      refreshPromise = (async () => {
        const response = await fetchImpl(`${origin}/api/v1/auth/refresh/`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ refresh: refreshToken }),
        });
        if (!response.ok) {
          await clearAuth();
          throw new Error("登录认证已失效，refresh token 无法刷新。");
        }
        const body = await response.json();
        if (typeof body.access !== "string" || typeof body.refresh !== "string") {
          await clearAuth();
          throw new Error("登录认证刷新响应无效。");
        }
        return persist(body, previousUser);
      })().finally(() => {
        refreshPromise = null;
      });
    }
    return refreshPromise;
  }

  async function authorizedFetch(path, init, access) {
    const headers = new Headers(init?.headers);
    headers.set("authorization", `Bearer ${access}`);
    if (init?.body && !headers.has("content-type")) {
      headers.set("content-type", "application/json");
    }
    return fetchImpl(`${origin}${path}`, { ...init, headers });
  }

  return {
    async login(credentials) {
      const response = await fetchImpl(`${origin}/api/v1/auth/login/`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password,
        }),
      });
      if (!response.ok) throw await errorFromResponse(response, "登录失败");
      const body = await response.json();
      if (typeof body.access !== "string" || typeof body.refresh !== "string") {
        throw new Error("登录响应缺少 token。");
      }
      await persist(body, body.user ?? null);
      return body;
    },
    async request(path, init = {}) {
      const auth = await loadAuth();
      if (!auth) throw new Error("未登录或认证 token 已失效。");

      const first = await authorizedFetch(path, init, auth.access);
      if (first.status !== 401) return first;

      const latest = await loadAuth();
      let rotated;
      if (latest && latest.access !== auth.access) rotated = latest;
      else {
        try {
          rotated = await refreshSession(auth.refresh, auth.user);
        } catch (error) {
          await clearAuth();
          throw error;
        }
      }

      const retried = await authorizedFetch(path, init, rotated.access);
      if (retried.status === 401) {
        await clearAuth();
        throw new Error("登录认证重试失败，请重新登录。");
      }
      return retried;
    },
    currentUser() {
      return user;
    },
  };
}

function normalizedName(value) {
  return collapseWhitespace(value).toLocaleLowerCase();
}

export async function findApplicationMatch({
  company_name,
  position_name,
  fetchPage,
}) {
  const company = normalizedName(company_name);
  const position = normalizedName(position_name);
  if (!company || !position) {
    throw new Error("请填写公司名称和岗位名称后再匹配投递。");
  }

  const records = [];
  let pageNumber = 1;
  while (true) {
    const page = await fetchPage(pageNumber, 100);
    records.push(...(Array.isArray(page?.results) ? page.results : []));
    if (!page?.next) break;
    pageNumber += 1;
    if (pageNumber > 10_000) throw new Error("投递分页数量异常，已停止匹配。");
  }

  const nameMatches = records.flatMap((record) => {
    if (normalizedName(record.company_name) !== company) return [];
    const positions = Array.isArray(record.positions) && record.positions.length
      ? record.positions
      : [record];
    return positions.flatMap((candidate, index) => {
      if (normalizedName(candidate.position_name) !== position) return [];
      const nested = candidate !== record;
      return [{
        ...record,
        ...candidate,
        id: nested ? candidate.id : record.id,
        company_id: record.id,
        position_index: index,
        position_name: candidate.position_name,
        application_url: candidate.application_url || record.application_url || "",
        application_status: candidate.application_status || record.application_status,
        application_time: candidate.application_time ?? record.application_time ?? null,
      }];
    });
  });
  if (nameMatches.length === 1) {
    return {
      kind: "update",
      record: nameMatches[0],
      matchedBy: "company-position",
    };
  }
  if (nameMatches.length > 1) {
    return {
      kind: "ambiguous",
      candidates: nameMatches,
      matchedBy: "company-position",
    };
  }
  return { kind: "create" };
}

function managedValue(field, value) {
  if (field === "company_name" || field === "position_name") return collapseWhitespace(value);
  if (field === "application_url") return normalizeApplicationUrl(value);
  return value;
}

export function buildCreatePayload(input) {
  const payload = {};
  for (const field of MANAGED_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(input, field)) {
      payload[field] = managedValue(field, input[field]);
    }
  }
  if (!Object.prototype.hasOwnProperty.call(payload, "application_status")) {
    payload.application_status = "applied";
  }
  return payload;
}

export function buildPatchPayload(existing, confirmed) {
  const payload = {};
  for (const field of MANAGED_FIELDS) {
    if (!Object.prototype.hasOwnProperty.call(confirmed, field)) continue;
    const next = managedValue(field, confirmed[field]);
    const previous = managedValue(field, existing[field]);
    if (next !== previous) payload[field] = next;
  }
  return payload;
}

export function createSubmissionGate(write) {
  let pending = null;
  return {
    preview() {
      return { operation: "pending" };
    },
    confirm() {
      if (pending) return pending;
      try {
        pending = Promise.resolve(write()).finally(() => {
          pending = null;
        });
      } catch (error) {
        pending = null;
        return Promise.reject(error);
      }
      return pending;
    },
    isSubmitting() {
      return pending !== null;
    },
  };
}
