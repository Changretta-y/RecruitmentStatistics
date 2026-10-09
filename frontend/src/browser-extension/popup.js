import {
  createSelectionController,
  createSubmissionGate,
  extractJobDetails,
  normalizeApplicationUrl,
} from "./core.js";

const $ = (selector) => document.querySelector(selector);

const elements = {
  message: $("#global-message"),
  loginView: $("#login-view"),
  captureView: $("#capture-view"),
  entryView: $("#entry-view"),
  recordsView: $("#records-view"),
  newApplicationView: $("#new-application-view"),
  openRecords: $("#open-records"),
  openApplication: $("#open-application"),
  loginForm: $("#login-form"),
  loginButton: $("#login-button"),
  apiOrigin: $("#api-origin"),
  username: $("#username"),
  password: $("#password"),
  currentUser: $("#current-user"),
  logoutButton: $("#logout-button"),
  submittedCount: $("#submitted-count"),
  submittedSearch: $("#submitted-search"),
  submittedRefresh: $("#submitted-refresh"),
  submittedState: $("#submitted-state"),
  submittedRetry: $("#submitted-retry"),
  submittedList: $("#submitted-list"),
  recaptureButton: $("#recapture-button"),
  pageState: $("#page-state"),
  form: $("#application-form"),
  company: $("#company-name"),
  companySource: $("#company-source"),
  position: $("#position-name"),
  positionSource: $("#position-source"),
  url: $("#application-url"),
  status: $("#application-status"),
  applicationTime: $("#application-time"),
  warnings: $("#warnings"),
  previewButton: $("#preview-button"),
  previewPanel: $("#preview-panel"),
  previewSummary: $("#preview-summary"),
  previewDetails: $("#preview-details"),
  candidateField: $("#candidate-field"),
  candidateSelect: $("#candidate-select"),
  confirmButton: $("#confirm-button"),
};

const chromeStorage = {
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

let activeTab = null;
let currentUser = null;
let currentPreview = null;
let saveGate = null;
let statusTouched = false;
let timeTouched = false;
let submittedCompanies = [];
let submittedRequestSequence = 0;
let submittedLoading = false;
let submittedError = null;
let applicationInitialized = false;
let navigationSequence = 0;

function showMessage(text, kind = "info") {
  elements.message.textContent = text;
  elements.message.className = `message ${kind}`;
  elements.message.hidden = !text;
}

function renderSubmittedCompanies() {
  const query = elements.submittedSearch.value.trim().toLocaleLowerCase();
  const matching = submittedCompanies.filter((company) =>
    company.companyName.toLocaleLowerCase().includes(query)
    || company.positions.some((position) => position.toLocaleLowerCase().includes(query)));
  elements.submittedCount.textContent = `共 ${matching.length} 家公司`;
  elements.submittedList.replaceChildren();
  for (const company of matching) {
    const item = document.createElement("li");
    item.className = "submitted-company";
    const name = document.createElement("strong");
    name.textContent = company.companyName;
    item.append(name);
    const positions = document.createElement("ul");
    positions.className = "submitted-positions";
    for (const positionName of company.positions) {
      const position = document.createElement("li");
      position.textContent = positionName;
      positions.append(position);
    }
    item.append(positions);
    elements.submittedList.append(item);
  }
  elements.submittedState.textContent = submittedError
    || (submittedLoading ? "正在加载已投递公司…"
      : matching.length ? ""
        : query && submittedCompanies.length ? "没有匹配结果" : "暂无已投递公司");
  elements.submittedRetry.hidden = !submittedError || /重新登录/.test(submittedError);
  elements.submittedRefresh.disabled = submittedLoading;
}

function clearSubmittedCompanies() {
  submittedRequestSequence += 1;
  submittedCompanies = [];
  submittedLoading = false;
  submittedError = null;
  elements.submittedSearch.value = "";
  renderSubmittedCompanies();
}

function showFeature(feature = "home") {
  navigationSequence += 1;
  elements.entryView.hidden = feature !== "home";
  elements.recordsView.hidden = feature !== "records";
  elements.newApplicationView.hidden = feature !== "application";
}

async function loadSubmittedCompanies() {
  if (!currentUser) return;
  const sequence = ++submittedRequestSequence;
  submittedLoading = true;
  submittedError = null;
  renderSubmittedCompanies();
  try {
    const companies = await send({ type: "LIST_SUBMITTED_COMPANIES" });
    if (sequence !== submittedRequestSequence) return;
    submittedCompanies = Array.isArray(companies) ? companies : [];
  } catch (error) {
    if (sequence !== submittedRequestSequence) return;
    if (/登录|认证|token|401/i.test(error.message || "")) {
      submittedCompanies = [];
      submittedError = "登录已过期，请重新登录。";
    } else {
      submittedError = "网络加载失败，请重试。";
    }
  } finally {
    if (sequence === submittedRequestSequence) {
      submittedLoading = false;
      renderSubmittedCompanies();
    }
  }
}

async function send(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (!response?.ok) throw new Error(response?.error || "插件后台没有返回有效结果。");
  return response.data;
}

function localDateTimeValue(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function apiDateTime(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error("投递时间格式不正确。");
  return date.toISOString();
}

function sourceLabel(candidate) {
  if (!candidate) return "未识别";
  const source = {
    "json-ld": "结构化数据",
    meta: "页面元数据",
    dom: "页面文本",
    manual: "手工填写",
  }[candidate.source];
  const confidence = { high: "高", medium: "中", low: "低" }[candidate.confidence];
  return `${source || candidate.source} · ${confidence || candidate.confidence}`;
}

function resetPreview() {
  currentPreview = null;
  saveGate = null;
  elements.previewPanel.hidden = true;
}

function displayWarnings(warnings) {
  elements.warnings.replaceChildren();
  for (const warning of warnings || []) {
    const paragraph = document.createElement("p");
    paragraph.textContent = warning;
    elements.warnings.append(paragraph);
  }
  elements.warnings.hidden = elements.warnings.childElementCount === 0;
}

function isSupportedPage(url) {
  return /^https?:\/\//i.test(String(url || ""));
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !Number.isInteger(tab.id)) throw new Error("无法获取当前活动标签页。");
  return tab;
}

async function collectPage() {
  resetPreview();
  elements.pageState.textContent = "正在读取当前页面…";
  activeTab = await getActiveTab();
  const activeUrl = String(activeTab.url || "");
  elements.url.value = isSupportedPage(activeUrl)
    ? normalizeApplicationUrl(activeUrl)
    : "";

  let result = {
    company: null,
    position: null,
    warnings: [],
    needsConfirmation: true,
  };
  if (!isSupportedPage(activeUrl)) {
    result.warnings = ["当前页面受浏览器限制，无法自动读取，请手工填写公司和岗位。"];
    elements.pageState.textContent = "当前页面仅支持手工录入";
  } else {
    try {
      const [execution] = await chrome.scripting.executeScript({
        target: { tabId: activeTab.id },
        func: () => ({ html: document.documentElement?.outerHTML || "" }),
      });
      result = extractJobDetails({
        html: execution?.result?.html || "",
        activeTabUrl: activeUrl,
      });
      elements.pageState.textContent = result.needsConfirmation
        ? "已生成候选，请检查后再保存"
        : "已从结构化数据识别，请确认后保存";
    } catch {
      result.warnings = ["页面拒绝脚本注入，无法自动读取；你仍可手工填写。"];
      elements.pageState.textContent = "自动读取受限，请手工录入";
    }
  }

  elements.company.value = result.company?.value || "";
  elements.position.value = result.position?.value || "";
  elements.companySource.textContent = sourceLabel(result.company);
  elements.positionSource.textContent = sourceLabel(result.position);
  elements.url.value = result.url || elements.url.value;
  displayWarnings(result.warnings);

  if (isSupportedPage(activeUrl)) {
    const controller = createSelectionController({ storage: chromeStorage });
    const draft = await controller.getDraft({ tabId: activeTab.id, url: activeUrl });
    if (draft?.company) {
      elements.company.value = draft.company;
      elements.companySource.textContent = "页面点选 · 已回填";
    }
    if (draft?.position) {
      elements.position.value = draft.position;
      elements.positionSource.textContent = "页面点选 · 已回填";
    }
  }
}

function activatePagePicker(field) {
  const markerId = "__recruitment_capture_picker__";
  const previous = window[markerId];
  if (typeof previous === "function") previous();

  const banner = document.createElement("div");
  banner.textContent = `请点击页面中的${field === "company" ? "公司名称" : "岗位名称"}，按 Esc 取消`;
  Object.assign(banner.style, {
    position: "fixed",
    top: "14px",
    left: "50%",
    transform: "translateX(-50%)",
    zIndex: "2147483647",
    padding: "10px 16px",
    borderRadius: "10px",
    color: "white",
    background: "#4059c7",
    boxShadow: "0 8px 28px rgba(0,0,0,.24)",
    font: "600 14px system-ui, sans-serif",
  });
  document.documentElement.append(banner);

  let highlighted = null;
  let previousOutline = "";
  const restore = () => {
    if (highlighted) highlighted.style.outline = previousOutline;
    highlighted = null;
  };
  const cleanup = () => {
    restore();
    banner.remove();
    document.removeEventListener("mouseover", onOver, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("keydown", onKey, true);
    delete window[markerId];
  };
  const onOver = (event) => {
    if (!(event.target instanceof HTMLElement) || event.target === banner) return;
    restore();
    highlighted = event.target;
    previousOutline = highlighted.style.outline;
    highlighted.style.outline = "3px solid #526ee8";
  };
  const onClick = (event) => {
    if (!(event.target instanceof HTMLElement) || event.target === banner) return;
    const text = (event.target.innerText || event.target.textContent || "").replace(/\s+/g, " ").trim();
    if (!text) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    chrome.runtime.sendMessage(
      { type: "SELECTION_ACCEPTED", field, text, url: location.href },
      () => cleanup(),
    );
  };
  const onKey = (event) => {
    if (event.key === "Escape") cleanup();
  };
  document.addEventListener("mouseover", onOver, true);
  document.addEventListener("click", onClick, true);
  document.addEventListener("keydown", onKey, true);
  window[markerId] = cleanup;
}

async function startSelection(field) {
  activeTab = activeTab || (await getActiveTab());
  if (!isSupportedPage(activeTab.url)) {
    showMessage("当前页面不允许点选，请直接手工输入。", "error");
    return;
  }
  await chrome.scripting.executeScript({
    target: { tabId: activeTab.id },
    func: activatePagePicker,
    args: [field],
  });
  showMessage("点选模式已启动。请回到页面点击文字，然后重新打开插件。", "info");
  window.close();
}

function confirmedValues() {
  const company = elements.company.value.replace(/\s+/g, " ").trim();
  const position = elements.position.value.replace(/\s+/g, " ").trim();
  if (!company) throw new Error("请填写公司名称。");
  if (!position) throw new Error("请填写岗位名称。");
  return {
    company_name: company,
    position_name: position,
    application_url: normalizeApplicationUrl(elements.url.value),
    application_status: elements.status.value,
    application_time: apiDateTime(elements.applicationTime.value),
  };
}

function addPreviewDetail(label, value) {
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value ?? "—";
  elements.previewDetails.append(term, description);
}

function renderPreview(preview, confirmed) {
  currentPreview = preview;
  elements.previewPanel.hidden = false;
  elements.previewDetails.replaceChildren();
  elements.candidateSelect.replaceChildren();
  elements.candidateField.hidden = preview.operation !== "ambiguous";

  const operationLabel = {
    create: "新增投递",
    update: "更新已有投递",
    ambiguous: "需要选择匹配记录",
  }[preview.operation];
  elements.previewSummary.textContent = operationLabel;
  addPreviewDetail("当前账号", currentUser?.username || "—");
  addPreviewDetail("公司", confirmed.company_name);
  addPreviewDetail("岗位", confirmed.position_name);
  addPreviewDetail("状态", elements.status.selectedOptions[0]?.textContent || confirmed.application_status);
  addPreviewDetail("投递时间", confirmed.application_time || "已清空");
  addPreviewDetail("链接", confirmed.application_url || "未填写");

  if (preview.operation === "update") {
    addPreviewDetail("匹配方式", preview.matchedBy === "url" ? "投递链接" : "公司 + 岗位");
    addPreviewDetail("目标记录", `#${preview.record.id} ${preview.record.company_name} / ${preview.record.position_name}`);
    addPreviewDetail("变化字段", Object.keys(preview.changes || {}).join("、") || "无变化");
  }

  if (preview.operation === "ambiguous") {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "请选择…";
    elements.candidateSelect.append(placeholder);
    for (const record of preview.candidates || []) {
      const option = document.createElement("option");
      option.value = String(record.id);
      option.textContent = `更新 #${record.id} · ${record.company_name} / ${record.position_name}`;
      elements.candidateSelect.append(option);
    }
    const createOption = document.createElement("option");
    createOption.value = "__create__";
    createOption.textContent = "不更新以上记录，明确新建";
    elements.candidateSelect.append(createOption);
    elements.confirmButton.disabled = true;
  } else {
    elements.confirmButton.disabled = false;
  }

  saveGate = createSubmissionGate(async () => {
    const selection = elements.candidateSelect.value;
    return send({
      type: "CONFIRM_SAVE",
      confirmed: confirmedValues(),
      selectedTargetId: /^\d+$/.test(selection) ? Number(selection) : null,
      forceCreate: selection === "__create__",
    });
  });
  elements.previewPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function preparePreview({ applyExistingDefaults = true } = {}) {
  const confirmed = confirmedValues();
  elements.previewButton.disabled = true;
  elements.previewButton.textContent = "正在查询已有投递…";
  try {
    let preview = await send({ type: "PREPARE_SAVE", confirmed });
    if (preview.operation === "update" && applyExistingDefaults) {
      let changed = false;
      if (!statusTouched && preview.record.application_status) {
        elements.status.value = preview.record.application_status;
        changed = true;
      }
      if (!timeTouched) {
        elements.applicationTime.value = preview.record.application_time
          ? localDateTimeValue(preview.record.application_time)
          : "";
        changed = true;
      }
      if (changed) {
        preview = await send({ type: "PREPARE_SAVE", confirmed: confirmedValues() });
      }
    }
    renderPreview(preview, confirmedValues());
    showMessage("预览已生成。确认目标和变化后再写入。", "info");
  } finally {
    elements.previewButton.disabled = false;
    elements.previewButton.textContent = "生成保存预览";
  }
}

async function confirmPreview() {
  if (!saveGate || !currentPreview) return;
  if (currentPreview.operation === "ambiguous" && !elements.candidateSelect.value) {
    showMessage("请先选择要更新的记录，或明确选择新建。", "error");
    return;
  }
  elements.confirmButton.disabled = true;
  elements.confirmButton.textContent = "正在写入…";
  try {
    const result = await saveGate.confirm();
    if (result.stale) {
      renderPreview(result.preview, confirmedValues());
      showMessage("原更新目标已不存在，已重新生成预览，请再次确认。", "error");
      return;
    }
    const verb = result.unchanged ? "无需修改" : result.operation === "create" ? "新增成功" : "更新成功";
    showMessage(`${verb}：${result.record.company_name} / ${result.record.position_name}`, "success");
    resetPreview();
  } catch (error) {
    resetPreview();
    showMessage(`${error.message} 请重新生成预览后再试。`, "error");
  } finally {
    elements.confirmButton.disabled = false;
    elements.confirmButton.textContent = "确认写入";
  }
}

async function showAuthenticated(state) {
  currentUser = state.user;
  clearSubmittedCompanies();
  applicationInitialized = false;
  elements.form.reset();
  resetPreview();
  elements.loginView.hidden = true;
  elements.captureView.hidden = false;
  showFeature();
  elements.currentUser.textContent = currentUser?.username || "已登录用户";
  statusTouched = false;
  timeTouched = false;
  elements.status.value = "applied";
  elements.applicationTime.value = localDateTimeValue();
}

async function initialize() {
  try {
    const state = await send({ type: "GET_STATE" });
    elements.apiOrigin.value = state.apiOrigin;
    if (state.authenticated) {
      try {
        const verified = await send({ type: "VERIFY_USER" });
        state.user = verified.user;
      } catch (error) {
        const latest = await send({ type: "GET_STATE" });
        if (!latest.authenticated) {
          elements.loginView.hidden = false;
          elements.captureView.hidden = true;
          showMessage("登录状态已失效，请重新登录。", "error");
          return;
        }
        showMessage(`暂时无法校验账号：${error.message}`, "error");
      }
      await showAuthenticated(state);
    } else {
      elements.loginView.hidden = false;
      elements.captureView.hidden = true;
    }
  } catch (error) {
    elements.loginView.hidden = false;
    showMessage(error.message, "error");
  }
}

elements.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.loginButton.disabled = true;
  elements.loginButton.textContent = "正在登录…";
  showMessage("");
  try {
    const result = await send({
      type: "LOGIN",
      apiOrigin: elements.apiOrigin.value,
      username: elements.username.value.trim(),
      password: elements.password.value,
    });
    elements.password.value = "";
    await showAuthenticated({ user: result.user });
  } catch (error) {
    showMessage(error.message || "登录失败，请检查账号和密码。", "error");
  } finally {
    elements.loginButton.disabled = false;
    elements.loginButton.textContent = "登录并继续";
  }
});

elements.logoutButton.addEventListener("click", async () => {
  await send({ type: "LOGOUT" }).catch(() => undefined);
  currentUser = null;
  clearSubmittedCompanies();
  applicationInitialized = false;
  elements.form.reset();
  showFeature();
  elements.captureView.hidden = true;
  elements.loginView.hidden = false;
  resetPreview();
  showMessage("已退出，插件本地登录态已清除。", "success");
});

elements.openRecords.addEventListener("click", () => {
  showFeature("records");
  void loadSubmittedCompanies();
});
elements.openApplication.addEventListener("click", async () => {
  const activeUser = currentUser;
  const request = ++navigationSequence;
  if (!applicationInitialized) {
    try {
      await collectPage();
    } catch (error) {
      showMessage(error.message, "error");
    }
    if (activeUser !== currentUser) return;
    applicationInitialized = true;
  }
  if (request !== navigationSequence) return;
  showFeature("application");
});
for (const button of document.querySelectorAll("[data-back-home]")) {
  button.addEventListener("click", () => showFeature());
}

elements.submittedSearch.addEventListener("input", renderSubmittedCompanies);
elements.submittedRefresh.addEventListener("click", () => { void loadSubmittedCompanies(); });
elements.submittedRetry.addEventListener("click", () => { void loadSubmittedCompanies(); });

elements.recaptureButton.addEventListener("click", () => {
  statusTouched = false;
  timeTouched = false;
  elements.status.value = "applied";
  elements.applicationTime.value = localDateTimeValue();
  collectPage().catch((error) => showMessage(error.message, "error"));
});

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  preparePreview().catch((error) => showMessage(error.message, "error"));
});

elements.confirmButton.addEventListener("click", () => {
  confirmPreview().catch((error) => showMessage(error.message, "error"));
});

elements.candidateSelect.addEventListener("change", () => {
  elements.confirmButton.disabled = !elements.candidateSelect.value;
});

elements.status.addEventListener("change", () => {
  statusTouched = true;
  resetPreview();
});
elements.applicationTime.addEventListener("change", () => {
  timeTouched = true;
  resetPreview();
});
for (const input of [elements.company, elements.position, elements.url]) {
  input.addEventListener("input", resetPreview);
}

for (const button of document.querySelectorAll("[data-select-field]")) {
  button.addEventListener("click", () => {
    startSelection(button.dataset.selectField).catch((error) => showMessage(error.message, "error"));
  });
}

initialize();
