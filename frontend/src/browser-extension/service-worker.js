import {
  buildCreatePayload,
  buildPatchPayload,
  createAuthClient,
  createSelectionController,
  findApplicationMatch,
} from "./core.js";

const DEFAULT_API_ORIGIN = "http://115.190.240.84:5173";
const ALLOWED_API_ORIGINS = new Set([
  DEFAULT_API_ORIGIN,
  "http://127.0.0.1:5173",
  "http://localhost:5173",
]);

const storage = {
  async get(key) {
    const result = await chrome.storage.local.get(key);
    return result[key];
  },
  async set(key, value) {
    await chrome.storage.local.set({ [key]: value });
  },
  async remove(key) {
    await chrome.storage.local.remove(key);
  },
};

function cleanOrigin(value) {
  const origin = String(value || DEFAULT_API_ORIGIN).replace(/\/+$/, "");
  if (!ALLOWED_API_ORIGINS.has(origin)) {
    throw new Error("该 API 地址不在插件允许的服务器列表中。");
  }
  return origin;
}

async function apiOrigin() {
  return cleanOrigin((await storage.get("apiOrigin")) || DEFAULT_API_ORIGIN);
}

async function authClient() {
  return createAuthClient({ apiOrigin: await apiOrigin(), fetch, storage });
}

async function responseBody(response) {
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const details = body?.details ? JSON.stringify(body.details) : body?.code;
    const error = new Error(details || `平台请求失败（HTTP ${response.status}）`);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

function confirmedFields(value) {
  return {
    company_name: value.company_name,
    position_name: value.position_name,
    application_url: value.application_url,
    application_status: value.application_status,
    application_time: value.application_time,
  };
}

async function matchApplications(client, confirmed) {
  return findApplicationMatch({
    ...confirmed,
    async fetchPage(page, pageSize) {
      const response = await client.request(
        `/api/v1/applications/?page=${page}&page_size=${pageSize}`,
      );
      return responseBody(response);
    },
  });
}

function previewFrom(plan, confirmed) {
  if (plan.kind === "create") {
    return {
      operation: "create",
      payload: buildCreatePayload(confirmed),
      changes: buildCreatePayload(confirmed),
    };
  }
  if (plan.kind === "ambiguous") {
    return {
      operation: "ambiguous",
      matchedBy: plan.matchedBy,
      candidates: plan.candidates,
    };
  }
  return {
    operation: "update",
    matchedBy: plan.matchedBy,
    record: plan.record,
    changes: patchPayloadForTarget(plan.record, confirmed),
  };
}

function patchPayloadForTarget(target, confirmed) {
  const changes = buildPatchPayload(target, confirmed);
  if (!target.position_index) return changes;

  const { application_url, company_name, ...positionChanges } = changes;
  if (application_url !== undefined) {
    throw new Error("平台暂不支持单独修改该岗位链接，请在主站确认后再保存。");
  }
  return Object.keys(positionChanges).length
    ? { positions: [{ id: target.id, ...positionChanges }] }
    : {};
}

async function prepareSave(rawConfirmed) {
  const confirmed = confirmedFields(rawConfirmed);
  const client = await authClient();
  const plan = await matchApplications(client, confirmed);
  return previewFrom(plan, confirmed);
}

async function confirmSave(message) {
  const confirmed = confirmedFields(message.confirmed);
  const client = await authClient();
  const plan = await matchApplications(client, confirmed);
  let operation = plan.kind;
  let target = plan.kind === "update" ? plan.record : null;

  if (plan.kind === "ambiguous") {
    if (message.forceCreate === true) operation = "create";
    else {
      target = plan.candidates.find(
        (candidate) => Number(candidate.id) === Number(message.selectedTargetId),
      );
      if (!target) throw new Error("存在多条匹配投递，请先选择更新目标或明确新建。");
      operation = "update";
    }
  }

  if (operation === "create") {
    const payload = buildCreatePayload(confirmed);
    const response = await client.request("/api/v1/applications/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return { operation, record: await responseBody(response) };
  }

  const payload = patchPayloadForTarget(target, confirmed);
  if (Object.keys(payload).length === 0) {
    return { operation, record: target, unchanged: true };
  }
  const response = await client.request(`/api/v1/applications/${target.company_id || target.id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (response.status === 404) {
    return { stale: true, preview: await prepareSave(confirmed) };
  }
  return { operation, record: await responseBody(response) };
}

async function handleMessage(message, sender) {
  switch (message?.type) {
    case "GET_STATE": {
      const auth = await storage.get("auth");
      return {
        apiOrigin: await apiOrigin(),
        user: auth?.user ?? null,
        authenticated: Boolean(auth?.access && auth?.refresh),
      };
    }
    case "LOGIN": {
      const origin = cleanOrigin(message.apiOrigin);
      await storage.set("apiOrigin", origin);
      const client = createAuthClient({ apiOrigin: origin, fetch, storage });
      const result = await client.login({
        username: String(message.username || ""),
        password: String(message.password || ""),
      });
      return { user: result.user };
    }
    case "VERIFY_USER": {
      const client = await authClient();
      const response = await client.request("/api/v1/auth/me/");
      const user = await responseBody(response);
      const auth = await storage.get("auth");
      if (auth?.access && auth?.refresh) {
        await storage.set("auth", { ...auth, user });
      }
      return { user };
    }
    case "LOGOUT": {
      const auth = await storage.get("auth");
      try {
        if (auth?.access && auth?.refresh) {
          const client = await authClient();
          const response = await client.request("/api/v1/auth/logout/", {
            method: "POST",
            body: JSON.stringify({ refresh: auth.refresh }),
          });
          await responseBody(response);
        }
      } catch {
        // Local logout is mandatory even when the server is unavailable.
      } finally {
        await storage.remove("auth");
      }
      return { loggedOut: true };
    }
    case "PREPARE_SAVE":
      return prepareSave(message.confirmed);
    case "CONFIRM_SAVE":
      return confirmSave(message);
    case "SELECTION_ACCEPTED": {
      const tabId = sender?.tab?.id;
      const currentUrl = sender?.tab?.url || message.url;
      if (!Number.isInteger(tabId) || !["company", "position"].includes(message.field)) {
        throw new Error("页面点选上下文无效。");
      }
      const context = { tabId, url: currentUrl };
      const controller = createSelectionController({ storage });
      await controller.begin(message.field, context);
      const accepted = await controller.acceptVisibleText(context, message.text);
      return { accepted };
    }
    default:
      throw new Error("未知的插件请求。");
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) =>
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : "插件操作失败。",
      }),
    );
  return true;
});
