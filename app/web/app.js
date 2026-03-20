const API_PREFIX = "/api/v1";
const DEFAULT_MODEL_ID = "default";
const NONE_MODEL_ID = "none";
const ADD_MODEL_OPTION = "__add_model__";
const DEFAULT_EMBEDDING_ID = "default";
const ADD_EMBEDDING_OPTION = "__add_embedding_model__";
const STORAGE_KEYS = {
  teamId: "caibao.teamId",
  teamName: "caibao.teamName",
  userId: "caibao.userId",
  displayName: "caibao.displayName",
  conversationId: "caibao.conversationId",
  selectedModelPrefix: "caibao.selectedModel",
  selectedEmbeddingPrefix: "caibao.selectedEmbedding",
};

const state = {
  teamId: "",
  teamName: "",
  userId: "",
  displayName: "",
  conversationId: "",
  selectedModel: DEFAULT_MODEL_ID,
  selectedEmbedding: DEFAULT_EMBEDDING_ID,
  modelConfigs: [],
  embeddingConfigs: [],
  conversations: [],
  history: [],
  documents: [],
  sending: false,
  importing: false,
};

const els = {};
let toastTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  hydrateState();
  initModelOptions();
  initEmbeddingOptions();
  bindEvents();
  updateIdentityCard();

  if (state.teamId && state.userId) {
    loadAllData().catch((error) => showToast(error.message, true));
  } else {
    openAuthModal();
  }
});

function bindElements() {
  els.historyList = document.getElementById("historyList");
  els.documentList = document.getElementById("documentList");
  els.profileBtn = document.getElementById("profileBtn");
  els.profileName = document.getElementById("profileName");
  els.profileTeam = document.getElementById("profileTeam");
  els.avatarText = document.getElementById("avatarText");
  els.modelSelect = document.getElementById("modelSelect");
  els.embeddingSelect = document.getElementById("embeddingSelect");
  els.docSelect = document.getElementById("docSelect");
  els.refreshAllBtn = document.getElementById("refreshAllBtn");
  els.heroTitle = document.getElementById("heroTitle");
  els.scenarioCards = document.getElementById("scenarioCards");
  els.messageList = document.getElementById("messageList");
  els.newSessionBtn = document.getElementById("newSessionBtn");
  els.toggleImportBtn = document.getElementById("toggleImportBtn");
  els.importPanel = document.getElementById("importPanel");
  els.messageInput = document.getElementById("messageInput");
  els.sendBtn = document.getElementById("sendBtn");

  els.fileInput = document.getElementById("fileInput");
  els.sourceName = document.getElementById("sourceName");
  els.contentType = document.getElementById("contentType");
  els.fileContent = document.getElementById("fileContent");
  els.autoChunk = document.getElementById("autoChunk");
  els.autoIndex = document.getElementById("autoIndex");
  els.maxChars = document.getElementById("maxChars");
  els.overlap = document.getElementById("overlap");
  els.importBtn = document.getElementById("importBtn");

  els.authModal = document.getElementById("authModal");
  els.accountIdInput = document.getElementById("accountIdInput");
  els.accountNameInput = document.getElementById("accountNameInput");
  els.cancelAuthBtn = document.getElementById("cancelAuthBtn");
  els.saveAuthBtn = document.getElementById("saveAuthBtn");

  els.toast = document.getElementById("toast");
}

function bindEvents() {
  els.profileBtn.addEventListener("click", openAuthModal);
  els.cancelAuthBtn.addEventListener("click", () => {
    if (!state.teamId || !state.userId) {
      showToast("请先登录账号后再开始聊天", true);
      return;
    }
    closeAuthModal();
  });
  els.saveAuthBtn.addEventListener("click", handleSaveAuth);

  els.refreshAllBtn.addEventListener("click", () => {
    loadAllData().catch((error) => showToast(error.message, true));
  });

  els.newSessionBtn.addEventListener("click", () => {
    createAndSwitchConversation().catch((error) => showToast(error.message, true));
  });

  els.toggleImportBtn.addEventListener("click", () => {
    els.importPanel.classList.toggle("hidden");
  });

  els.fileInput.addEventListener("change", handleFileInputChange);
  els.importBtn.addEventListener("click", handleImportDocument);

  els.modelSelect.addEventListener("change", () => {
    handleModelChange().catch((error) => showToast(error.message, true));
  });
  els.embeddingSelect.addEventListener("change", () => {
    handleEmbeddingChange().catch((error) => showToast(error.message, true));
  });
  els.docSelect.addEventListener("change", () => {
    if (els.docSelect.value) {
      showToast(`已切换到文档：${els.docSelect.options[els.docSelect.selectedIndex].text}`);
    }
  });

  els.sendBtn.addEventListener("click", handleSend);
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  });
  els.messageInput.addEventListener("input", autoGrowTextarea);

  const sceneButtons = document.querySelectorAll(".scenario-card");
  for (const button of sceneButtons) {
    button.addEventListener("click", () => {
      const scene = button.dataset.scene || "";
      applyScenarioCard(scene);
    });
  }
}

function hydrateState() {
  state.teamId = localStorage.getItem(STORAGE_KEYS.teamId) || "";
  state.teamName = localStorage.getItem(STORAGE_KEYS.teamName) || "";
  state.userId = localStorage.getItem(STORAGE_KEYS.userId) || "";
  state.displayName = localStorage.getItem(STORAGE_KEYS.displayName) || "";
  state.conversationId = localStorage.getItem(STORAGE_KEYS.conversationId) || "";
  state.selectedModel = loadSelectedModelFromStorage();
  state.selectedEmbedding = loadSelectedEmbeddingFromStorage();
}

function persistIdentity() {
  localStorage.setItem(STORAGE_KEYS.teamId, state.teamId);
  localStorage.setItem(STORAGE_KEYS.teamName, state.teamName);
  localStorage.setItem(STORAGE_KEYS.userId, state.userId);
  localStorage.setItem(STORAGE_KEYS.displayName, state.displayName);
}

function persistConversation() {
  localStorage.setItem(STORAGE_KEYS.conversationId, state.conversationId || "");
}

function selectedModelStorageKey() {
  if (state.teamId && state.userId) {
    return `${STORAGE_KEYS.selectedModelPrefix}:${state.teamId}:${state.userId}`;
  }
  return STORAGE_KEYS.selectedModelPrefix;
}

function loadSelectedModelFromStorage() {
  return localStorage.getItem(selectedModelStorageKey()) || DEFAULT_MODEL_ID;
}

function persistSelectedModel() {
  localStorage.setItem(selectedModelStorageKey(), state.selectedModel || DEFAULT_MODEL_ID);
}

function selectedEmbeddingStorageKey() {
  if (state.teamId && state.userId) {
    return `${STORAGE_KEYS.selectedEmbeddingPrefix}:${state.teamId}:${state.userId}`;
  }
  return STORAGE_KEYS.selectedEmbeddingPrefix;
}

function loadSelectedEmbeddingFromStorage() {
  return localStorage.getItem(selectedEmbeddingStorageKey()) || DEFAULT_EMBEDDING_ID;
}

function persistSelectedEmbedding() {
  localStorage.setItem(
    selectedEmbeddingStorageKey(),
    state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
  );
}

function updateIdentityCard() {
  const name = state.displayName || state.teamName || "未登录";
  const accountId = state.teamId || state.userId;
  const team = accountId ? `account: ${accountId}` : "点击登录或切换账号";
  els.profileName.textContent = name;
  els.profileTeam.textContent = team;
  els.avatarText.textContent = name.slice(0, 1) || "未";

  if (els.accountIdInput) {
    els.accountIdInput.value = accountId || "";
  }
  if (els.accountNameInput) {
    els.accountNameInput.value = name === "未登录" ? "" : name;
  }
}

function initModelOptions() {
  const configuredModels = state.modelConfigs.map((item) => item.model_name);
  const allModels = dedupeStrings([DEFAULT_MODEL_ID, NONE_MODEL_ID, ...configuredModels]);
  els.modelSelect.innerHTML = "";

  for (const model of allModels) {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = formatModelOptionLabel(model);
    els.modelSelect.appendChild(option);
  }

  const addOption = document.createElement("option");
  addOption.value = ADD_MODEL_OPTION;
  addOption.textContent = "新增模型...";
  els.modelSelect.appendChild(addOption);

  state.selectedModel = allModels.includes(state.selectedModel) ? state.selectedModel : DEFAULT_MODEL_ID;
  els.modelSelect.value = state.selectedModel;
  persistSelectedModel();
}

function initEmbeddingOptions() {
  const configuredModels = state.embeddingConfigs.map((item) => item.model_name);
  const allModels = dedupeStrings([DEFAULT_EMBEDDING_ID, ...configuredModels]);
  els.embeddingSelect.innerHTML = "";

  for (const model of allModels) {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = formatEmbeddingOptionLabel(model);
    els.embeddingSelect.appendChild(option);
  }

  const addOption = document.createElement("option");
  addOption.value = ADD_EMBEDDING_OPTION;
  addOption.textContent = "新增向量模型...";
  els.embeddingSelect.appendChild(addOption);

  state.selectedEmbedding = allModels.includes(state.selectedEmbedding)
    ? state.selectedEmbedding
    : DEFAULT_EMBEDDING_ID;
  els.embeddingSelect.value = state.selectedEmbedding;
  persistSelectedEmbedding();
}

function formatModelOptionLabel(model) {
  if (model === DEFAULT_MODEL_ID) {
    return "default (.env)";
  }
  if (model === NONE_MODEL_ID) {
    return "none (mock)";
  }
  return model;
}

function formatEmbeddingOptionLabel(model) {
  if (model === DEFAULT_EMBEDDING_ID) {
    return "default (mock hashing)";
  }
  return model;
}

async function handleModelChange() {
  const selected = els.modelSelect.value;
  if (selected !== ADD_MODEL_OPTION) {
    state.selectedModel = selected;
    persistSelectedModel();
    if (selected === DEFAULT_MODEL_ID) {
      showToast("当前使用 default（读取 .env 大模型配置）");
    } else if (selected === NONE_MODEL_ID) {
      showToast("当前使用 none（强制 mock 回复）");
    } else {
      showToast(`模型已切换为 ${state.selectedModel}`);
    }
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账号", true);
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const modelName = window.prompt("输入模型名称（例如 gpt-4.1-mini）");
  if (!modelName) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const normalizedModelName = modelName.trim();
  if (
    !normalizedModelName ||
    normalizedModelName.toLowerCase() === DEFAULT_MODEL_ID ||
    normalizedModelName.toLowerCase() === NONE_MODEL_ID
  ) {
    els.modelSelect.value = state.selectedModel;
    showToast("模型名称无效", true);
    return;
  }

  const baseUrl = window.prompt(
    "输入 API Base URL（例如 https://api.openai.com/v1）",
    "https://api.openai.com/v1",
  );
  if (!baseUrl || !baseUrl.trim()) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const apiKey = window.prompt("输入 API Key");
  if (!apiKey || !apiKey.trim()) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  await apiRequest("/llm/models", {
    method: "POST",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      model_name: normalizedModelName,
      base_url: baseUrl.trim(),
      api_key: apiKey.trim(),
    },
  });

  state.selectedModel = normalizedModelName;
  persistSelectedModel();
  await loadModelConfigs();
  showToast(`已添加并切换到模型 ${state.selectedModel}`);
}

async function handleEmbeddingChange() {
  const selected = els.embeddingSelect.value;
  if (selected !== ADD_EMBEDDING_OPTION) {
    state.selectedEmbedding = selected;
    persistSelectedEmbedding();
    if (selected === DEFAULT_EMBEDDING_ID) {
      showToast("当前使用 default 向量模型（mock hashing）");
    } else {
      showToast(`向量模型已切换为 ${state.selectedEmbedding}`);
    }
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账号", true);
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }

  const modelName = window.prompt("输入向量模型名称（例如 text-embedding-3-small）");
  if (!modelName) {
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }

  const normalizedModelName = modelName.trim();
  if (
    !normalizedModelName ||
    normalizedModelName.toLowerCase() === DEFAULT_EMBEDDING_ID ||
    normalizedModelName.toLowerCase() === NONE_MODEL_ID
  ) {
    els.embeddingSelect.value = state.selectedEmbedding;
    showToast("向量模型名称无效", true);
    return;
  }

  const providerInput = window.prompt(
    "输入 embedding provider（openai / volcengine / mock）",
    "openai",
  );
  if (!providerInput || !providerInput.trim()) {
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }
  const provider = providerInput.trim().toLowerCase();

  let baseUrl = null;
  let apiKey = null;
  if (provider !== "mock") {
    const baseUrlInput = window.prompt(
      "输入 Embedding API Base URL（例如 https://api.openai.com/v1）",
      "https://api.openai.com/v1",
    );
    if (!baseUrlInput || !baseUrlInput.trim()) {
      els.embeddingSelect.value = state.selectedEmbedding;
      return;
    }

    const apiKeyInput = window.prompt("输入 Embedding API Key");
    if (!apiKeyInput || !apiKeyInput.trim()) {
      els.embeddingSelect.value = state.selectedEmbedding;
      return;
    }
    baseUrl = baseUrlInput.trim();
    apiKey = apiKeyInput.trim();
  }

  await apiRequest("/embedding/models", {
    method: "POST",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      model_name: normalizedModelName,
      provider,
      base_url: baseUrl,
      api_key: apiKey,
    },
  });

  state.selectedEmbedding = normalizedModelName;
  persistSelectedEmbedding();
  await loadEmbeddingConfigs();
  showToast(`已添加并切换到向量模型 ${state.selectedEmbedding}`);
}

async function handleSaveAuth() {
  const rawAccountId = els.accountIdInput.value.trim();
  const accountId = rawAccountId.replace(/\s+/g, "_").slice(0, 64);
  const accountName = els.accountNameInput.value.trim() || accountId;
  const teamId = accountId;
  const userId = accountId;
  const teamName = accountName || accountId;
  const displayName = accountName || accountId;

  if (!accountId) {
    showToast("account_id 不能为空", true);
    return;
  }

  setButtonLoading(els.saveAuthBtn, true, "保存中...");

  try {
    await createOrReuseTeam(teamId, teamName);
    await createOrReuseUser(userId, teamId, displayName);

    state.teamId = teamId;
    state.teamName = teamName;
    state.userId = userId;
    state.displayName = displayName;
    state.conversationId = "";
    persistIdentity();
    persistConversation();

    updateIdentityCard();
    closeAuthModal();
    clearConversation();
    await loadAllData();
    showToast(`已登录账号：${displayName}`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setButtonLoading(els.saveAuthBtn, false, "保存并登录");
  }
}

async function createOrReuseTeam(teamId, teamName) {
  try {
    await apiRequest("/teams", {
      method: "POST",
      body: {
        team_id: teamId,
        name: teamName,
        description: "Created from CaiBao web UI",
      },
    });
  } catch (error) {
    if (!String(error.message).includes("already exists")) {
      throw error;
    }
  }
}

async function createOrReuseUser(userId, teamId, displayName) {
  try {
    await apiRequest("/users", {
      method: "POST",
      body: {
        user_id: userId,
        team_id: teamId,
        display_name: displayName,
        role: "member",
      },
    });
    return;
  } catch (error) {
    if (!String(error.message).includes("already exists")) {
      throw error;
    }
  }

  const existing = await apiRequest(`/users/${encodeURIComponent(userId)}`);
  if (existing.team_id !== teamId) {
    throw new Error(`账号 ${userId} 已绑定其他团队 ${existing.team_id}，请更换 account_id。`);
  }
}

async function loadModelConfigs() {
  if (!state.teamId || !state.userId) {
    state.modelConfigs = [];
    state.selectedModel = DEFAULT_MODEL_ID;
    initModelOptions();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
  });
  const response = await apiRequest(`/llm/models?${query.toString()}`);
  state.modelConfigs = Array.isArray(response.items) ? response.items : [];
  state.selectedModel = loadSelectedModelFromStorage();
  initModelOptions();
}

async function loadEmbeddingConfigs() {
  if (!state.teamId || !state.userId) {
    state.embeddingConfigs = [];
    state.selectedEmbedding = DEFAULT_EMBEDDING_ID;
    initEmbeddingOptions();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
  });
  const response = await apiRequest(`/embedding/models?${query.toString()}`);
  state.embeddingConfigs = Array.isArray(response.items) ? response.items : [];
  state.selectedEmbedding = loadSelectedEmbeddingFromStorage();
  initEmbeddingOptions();
}

async function loadAllData() {
  if (!state.teamId || !state.userId) {
    return;
  }

  await Promise.all([loadModelConfigs(), loadEmbeddingConfigs()]);
  await loadConversations();
  await ensureActiveConversation();
  await Promise.all([loadHistory(), loadDocuments()]);
}

async function loadConversations() {
  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
    limit: "100",
  });
  const response = await apiRequest(`/conversations?${query.toString()}`);
  state.conversations = Array.isArray(response) ? response : [];
  renderConversationList();
}

async function ensureActiveConversation() {
  if (!state.conversations.length) {
    const created = await createConversation("新会话");
    state.conversations = [created];
  }

  const exists = state.conversations.some((item) => item.conversation_id === state.conversationId);
  if (!exists) {
    state.conversationId = state.conversations[0].conversation_id;
    persistConversation();
  }

  renderConversationList();
}

function renderConversationList() {
  els.historyList.innerHTML = "";

  if (!state.conversations.length) {
    appendEmpty(els.historyList, "暂无会话");
    return;
  }

  for (const item of state.conversations) {
    const li = document.createElement("li");
    li.classList.toggle("active", item.conversation_id === state.conversationId);

    const title = truncate(item.title || "新会话", 24);
    const createdAt = formatTime(item.created_at);
    const pinActionText = item.is_pinned ? "取消顶置" : "顶置聊天";

    li.innerHTML = `
      <div class="history-row">
        <div class="history-title-wrap">
          <div class="history-title">${escapeHtml(title)}</div>
          ${item.is_pinned ? '<span class="history-pin-tag">置顶</span>' : ""}
        </div>
        <div class="history-actions">
          <details class="history-menu">
            <summary class="history-more" title="会话操作">...</summary>
            <div class="history-menu-panel">
              <button class="history-action-btn" type="button" data-action="rename" data-id="${escapeHtml(item.conversation_id)}">重命名</button>
              <button class="history-action-btn" type="button" data-action="pin" data-id="${escapeHtml(item.conversation_id)}">${pinActionText}</button>
              <button class="history-action-btn danger" type="button" data-action="delete" data-id="${escapeHtml(item.conversation_id)}">删除</button>
            </div>
          </details>
        </div>
      </div>
      <div class="history-meta">${escapeHtml(createdAt)}</div>
    `;

    li.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target && target.closest(".history-menu")) {
        return;
      }
      switchConversation(item.conversation_id).catch((error) => showToast(error.message, true));
    });

    const actionButtons = li.querySelectorAll(".history-action-btn");
    for (const button of actionButtons) {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const menu = event.currentTarget?.closest(".history-menu");
        if (menu) {
          menu.removeAttribute("open");
        }
        const action = event.currentTarget?.dataset?.action;
        if (action === "rename") {
          renameConversation(item).catch((error) => showToast(error.message, true));
          return;
        }
        if (action === "pin") {
          pinConversation(item.conversation_id, !item.is_pinned).catch((error) => showToast(error.message, true));
          return;
        }
        if (action === "delete") {
          deleteConversation(item.conversation_id).catch((error) => showToast(error.message, true));
        }
      });
    }

    els.historyList.appendChild(li);
  }
}

async function switchConversation(conversationId) {
  state.conversationId = conversationId;
  persistConversation();
  renderConversationList();
  await Promise.all([loadHistory(), loadDocuments()]);
}

async function createConversation(title) {
  return apiRequest("/conversations", {
    method: "POST",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      title,
    },
  });
}

async function renameConversation(conversation) {
  const currentTitle = String(conversation.title || "新会话").trim();
  const input = window.prompt("输入新的会话名称", currentTitle);
  if (input === null) {
    return;
  }

  const title = input.trim();
  if (!title) {
    showToast("会话名称不能为空", true);
    return;
  }

  if (title === currentTitle) {
    return;
  }

  await apiRequest(`/conversations/${encodeURIComponent(conversation.conversation_id)}`, {
    method: "PATCH",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      title,
    },
  });

  await loadConversations();
  showToast("会话已重命名");
}

async function pinConversation(conversationId, pinned) {
  await apiRequest(`/conversations/${encodeURIComponent(conversationId)}/pin`, {
    method: "PATCH",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      pinned,
    },
  });
  await loadConversations();
  showToast(pinned ? "已顶置会话" : "已取消顶置");
}

async function createAndSwitchConversation() {
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账号", true);
    return;
  }

  if (!state.conversationId) {
    await ensureActiveConversation();
  }

  const created = await createConversation("新会话");
  state.conversationId = created.conversation_id;
  persistConversation();
  await loadConversations();
  clearConversation();
  await Promise.all([loadDocuments(), loadHistory()]);
}

async function deleteConversation(conversationId) {
  if (!window.confirm("确认删除这个会话？会同时删除该会话下的聊天记录和会话文件。")) {
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
  });
  await apiRequest(`/conversations/${encodeURIComponent(conversationId)}?${query.toString()}`, {
    method: "DELETE",
  });

  if (state.conversationId === conversationId) {
    state.conversationId = "";
    persistConversation();
  }

  await loadConversations();
  await ensureActiveConversation();
  await Promise.all([loadHistory(), loadDocuments()]);
  showToast("会话已删除");
}

async function loadHistory() {
  if (!state.conversationId) {
    clearConversation();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
    conversation_id: state.conversationId,
    limit: "200",
  });
  const response = await apiRequest(`/chat/history?${query.toString()}`);
  state.history = Array.isArray(response.items) ? response.items : [];
  renderCurrentConversationMessages();
}

async function deleteHistoryMessage(messageId) {
  if (!messageId) {
    return;
  }

  if (!window.confirm("确认删除这一轮对话吗？")) {
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
    conversation_id: state.conversationId,
  });

  await apiRequest(`/chat/history/${encodeURIComponent(messageId)}?${query.toString()}`, {
    method: "DELETE",
  });
  await loadHistory();
  showToast("消息已删除");
}

async function editHistoryMessage(messageId, currentText, channel) {
  if (!messageId) {
    return;
  }

  if (channel === "action") {
    showToast("工具调用消息不支持编辑", true);
    return;
  }

  const input = window.prompt("编辑用户消息", currentText || "");
  if (input === null) {
    return;
  }

  const requestText = input.trim();
  if (!requestText) {
    showToast("消息不能为空", true);
    return;
  }

  if (requestText === (currentText || "").trim()) {
    return;
  }

  await apiRequest(`/chat/history/${encodeURIComponent(messageId)}`, {
    method: "PUT",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      request_text: requestText,
    },
  });

  await loadHistory();
  showToast("消息已更新并重新生成回复");
}

async function copyMessageText(content) {
  const normalized = String(content || "").trim();
  if (!normalized) {
    return;
  }

  try {
    await navigator.clipboard.writeText(normalized);
    showToast("已复制回复");
  } catch {
    showToast("复制失败，请检查浏览器权限", true);
  }
}

async function regenerateAssistantMessage(messageId, requestText, channel) {
  if (!messageId || !requestText) {
    return;
  }

  if (channel === "action") {
    showToast("工具调用消息不支持重生成", true);
    return;
  }

  const availableModels = dedupeStrings([
    DEFAULT_MODEL_ID,
    NONE_MODEL_ID,
    ...state.modelConfigs.map((item) => item.model_name),
  ]);
  const selected = window.prompt(
    `选择重生成模型：${availableModels.join(", ")}`,
    state.selectedModel || DEFAULT_MODEL_ID,
  );
  if (selected === null) {
    return;
  }

  const normalizedModel = selected.trim() || state.selectedModel || DEFAULT_MODEL_ID;
  if (!availableModels.includes(normalizedModel)) {
    showToast("模型不存在，请先在模型列表中添加", true);
    return;
  }

  const payload = {
    team_id: state.teamId,
    user_id: state.userId,
    request_text: requestText,
    embedding_model: state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
  };
  if (normalizedModel !== DEFAULT_MODEL_ID) {
    payload.model = normalizedModel;
  }

  await apiRequest(`/chat/history/${encodeURIComponent(messageId)}`, {
    method: "PUT",
    body: payload,
  });

  state.selectedModel = normalizedModel;
  persistSelectedModel();
  initModelOptions();
  await loadHistory();
  showToast(`已使用 ${normalizedModel} 重新生成`);
}

function renderCurrentConversationMessages() {
  clearConversation();
  if (!state.history.length) {
    return;
  }

  const ordered = [...state.history].reverse();
  for (const item of ordered) {
    appendMessage("user", item.request_text || "", {
      createdAt: item.created_at,
      messageId: item.message_id,
      channel: item.channel,
      editable: item.channel !== "action",
      deletable: true,
    });
    const hits = item.response_payload && Array.isArray(item.response_payload.hits) ? item.response_payload.hits : [];
    const model = item.response_payload && item.response_payload.model ? item.response_payload.model : "";
    const mode = item.response_payload && item.response_payload.mode ? item.response_payload.mode : "";
    appendMessage("assistant", item.response_text || "", {
      createdAt: item.created_at,
      hits,
      mode,
      model,
      messageId: item.message_id,
      requestText: item.request_text || "",
      channel: item.channel,
    });
  }
}

async function loadDocuments() {
  if (!state.conversationId) {
    state.documents = [];
    renderDocuments();
    renderDocSelect();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    conversation_id: state.conversationId,
  });
  const response = await apiRequest(`/documents?${query.toString()}`);
  state.documents = Array.isArray(response) ? response : [];
  renderDocuments();
  renderDocSelect();
}

function renderDocuments() {
  els.documentList.innerHTML = "";

  if (!state.documents.length) {
    appendEmpty(els.documentList, "暂无项目文档");
    return;
  }

  for (const doc of state.documents) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div class="doc-title">${escapeHtml(doc.source_name)}</div>
      <div class="doc-meta">${escapeHtml(doc.document_id.slice(0, 8))} · ${escapeHtml(String(doc.content_type))}</div>
    `;
    li.addEventListener("click", () => {
      els.docSelect.value = doc.document_id;
      showToast(`问答范围已切到 ${doc.source_name}`);
    });
    els.documentList.appendChild(li);
  }
}

function renderDocSelect() {
  const previous = els.docSelect.value;
  els.docSelect.innerHTML = "";

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "当前会话文档（session_only）";
  els.docSelect.appendChild(allOption);

  for (const doc of state.documents) {
    const option = document.createElement("option");
    option.value = doc.document_id;
    option.textContent = doc.source_name;
    els.docSelect.appendChild(option);
  }

  if (state.documents.some((doc) => doc.document_id === previous)) {
    els.docSelect.value = previous;
  }
}

async function handleSend() {
  const question = els.messageInput.value.trim();
  if (!question || state.sending) {
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账号", true);
    return;
  }

  state.sending = true;
  els.sendBtn.disabled = true;

  appendMessage("user", question);
  els.messageInput.value = "";
  autoGrowTextarea();

  try {
    const payload = {
      user_id: state.userId,
      team_id: state.teamId,
      conversation_id: state.conversationId,
      question,
      top_k: 5,
      embedding_model: state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
    };

    if (state.selectedModel !== DEFAULT_MODEL_ID) {
      payload.model = state.selectedModel;
    }

    if (els.docSelect.value) {
      payload.document_id = els.docSelect.value;
    }

    const response = await apiRequest("/chat/ask", {
      method: "POST",
      body: payload,
    });

    appendMessage("assistant", response.answer || "", {
      hits: Array.isArray(response.hits) ? response.hits : [],
      mode: response.mode || "",
      model: response.model || state.selectedModel,
    });

    await loadHistory();
  } catch (error) {
    const message = String(error.message || "发送失败");

    const fallbackResult = await tryEchoFallback(question, message);
    if (fallbackResult) {
      appendMessage("assistant", fallbackResult.answer, {
        model: "offline-echo",
      });
      await loadHistory();
      showToast(fallbackResult.notice);
    } else {
      appendMessage("assistant", `请求失败：${message}`);
      showToast(message, true);
    }
  } finally {
    state.sending = false;
    els.sendBtn.disabled = false;
  }
}

function shouldUseEchoFallback(errorMessage) {
  const text = String(errorMessage || "").toLowerCase();
  return (
    text.includes("no indexed chunks found") ||
    text.includes("llm_api_key is required") ||
    text.includes("llm request failed") ||
    text.includes("timed out")
  );
}

async function tryEchoFallback(question, errorMessage) {
  if (!shouldUseEchoFallback(errorMessage)) {
    return null;
  }

  try {
    const echoResponse = await apiRequest("/chat/echo", {
      method: "POST",
      body: {
        user_id: state.userId,
        team_id: state.teamId,
        conversation_id: state.conversationId,
        message: question,
      },
    });

    return {
      answer: `离线回复：${echoResponse.answer || question}`,
      notice: "已自动切换离线回复（Echo）",
    };
  } catch {
    return null;
  }
}

async function handleImportDocument() {
  if (state.importing) {
    return;
  }
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账号", true);
    return;
  }

  const sourceName = els.sourceName.value.trim();
  const content = els.fileContent.value.trim();
  const contentType = els.contentType.value;

  if (!sourceName || !content) {
    showToast("请填写 source_name 并输入内容", true);
    return;
  }

  state.importing = true;
  els.importBtn.disabled = true;

  try {
    const doc = await apiRequest("/documents/import", {
      method: "POST",
      body: {
        team_id: state.teamId,
        conversation_id: state.conversationId,
        source_name: sourceName,
        content_type: contentType,
        content,
      },
    });

    const documentId = doc.document_id;

    if (els.autoChunk.checked) {
      await apiRequest(`/documents/${encodeURIComponent(documentId)}/chunk`, {
        method: "POST",
        body: {
          team_id: state.teamId,
          conversation_id: state.conversationId,
          max_chars: Number(els.maxChars.value || 600),
          overlap: Number(els.overlap.value || 80),
        },
      });
    }

    if (els.autoIndex.checked) {
      await apiRequest("/retrieval/index", {
        method: "POST",
        body: {
          team_id: state.teamId,
          user_id: state.userId,
          conversation_id: state.conversationId,
          document_id: documentId,
          embedding_model: state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
        },
      });
    }

    await loadDocuments();
    els.docSelect.value = documentId;
    showToast(`导入完成：${sourceName}`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    state.importing = false;
    els.importBtn.disabled = false;
  }
}

async function handleFileInputChange(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    els.fileContent.value = text;
    if (!els.sourceName.value.trim()) {
      els.sourceName.value = file.name;
    }
    if (file.name.toLowerCase().endsWith(".txt")) {
      els.contentType.value = "txt";
    } else {
      els.contentType.value = "md";
    }
  } catch {
    showToast("读取文件失败，请改用粘贴文本", true);
  }
}

function appendMessage(role, content, options = {}) {
  if (!content) {
    return;
  }

  setHeroVisible(false);

  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const message = document.createElement("article");
  message.className = `message ${role}`;

  const head = document.createElement("div");
  head.className = "message-head";

  const left = document.createElement("span");
  left.textContent = role === "user" ? state.displayName || "你" : "CaiBao";

  const createdDate = options.createdAt ? new Date(options.createdAt) : new Date();
  const timeText = Number.isNaN(createdDate.valueOf()) ? formatClock(new Date()) : formatClock(createdDate);

  const right = document.createElement("span");
  if (role === "assistant") {
    const meta = [timeText];
    if (options.mode) {
      meta.push(options.mode);
    }
    if (options.model) {
      meta.push(options.model);
    }
    right.textContent = meta.join(" · ");
  } else {
    right.textContent = timeText;
  }

  head.appendChild(left);
  head.appendChild(right);

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = content;

  message.appendChild(head);
  message.appendChild(body);

  if (role === "assistant" && Array.isArray(options.hits) && options.hits.length) {
    const hitBox = document.createElement("div");
    hitBox.className = "hit-box";

    const topHits = options.hits.slice(0, 3);
    for (const hit of topHits) {
      const item = document.createElement("div");
      item.className = "hit-item";

      const meta = document.createElement("div");
      meta.className = "hit-meta";
      const score = Number(hit.score || 0).toFixed(4);
      const sourceName = hit.source_name ? `source=${hit.source_name} · ` : "";
      meta.textContent = `${sourceName}doc=${hit.document_id} · chunk=${hit.chunk_index} · score=${score}`;

      const snippet = document.createElement("div");
      snippet.className = "hit-content";
      snippet.textContent = truncate(String(hit.content || ""), 180);

      item.appendChild(meta);
      item.appendChild(snippet);
      hitBox.appendChild(item);
    }

    message.appendChild(hitBox);
  }

  row.appendChild(message);

  const actionRail = document.createElement("div");
  actionRail.className = "message-action-rail";

  if (role === "user" && options.messageId) {
    if (options.editable) {
      const editBtn = document.createElement("button");
      editBtn.className = "message-icon-btn";
      editBtn.type = "button";
      editBtn.title = "编辑";
      editBtn.textContent = "✎";
      editBtn.addEventListener("click", () => {
        editHistoryMessage(options.messageId, content, options.channel).catch((error) => {
          showToast(error.message, true);
        });
      });
      actionRail.appendChild(editBtn);
    }
    if (options.deletable) {
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "message-icon-btn";
      deleteBtn.type = "button";
      deleteBtn.title = "删除";
      deleteBtn.textContent = "⌫";
      deleteBtn.addEventListener("click", () => {
        deleteHistoryMessage(options.messageId).catch((error) => {
          showToast(error.message, true);
        });
      });
      actionRail.appendChild(deleteBtn);
    }
  }

  if (role === "assistant") {
    const copyBtn = document.createElement("button");
    copyBtn.className = "message-icon-btn";
    copyBtn.type = "button";
    copyBtn.title = "复制";
    copyBtn.textContent = "⧉";
    copyBtn.addEventListener("click", () => {
      copyMessageText(content).catch((error) => showToast(error.message, true));
    });
    actionRail.appendChild(copyBtn);

    if (options.messageId && options.requestText) {
      const regenBtn = document.createElement("button");
      regenBtn.className = "message-icon-btn";
      regenBtn.type = "button";
      regenBtn.title = "切换模型重生成";
      regenBtn.textContent = "↻";
      regenBtn.addEventListener("click", () => {
        regenerateAssistantMessage(
          options.messageId,
          options.requestText,
          options.channel,
        ).catch((error) => showToast(error.message, true));
      });
      actionRail.appendChild(regenBtn);
    }
  }

  if (actionRail.childElementCount > 0) {
    row.appendChild(actionRail);
  }

  els.messageList.appendChild(row);
  scrollToBottom();
}

function clearConversation() {
  els.messageList.innerHTML = "";
  setHeroVisible(true);
}

function setHeroVisible(visible) {
  els.heroTitle.style.display = visible ? "block" : "none";
  if (els.scenarioCards) {
    els.scenarioCards.style.display = visible ? "grid" : "none";
  }
}

function applyScenarioCard(scene) {
  const templates = {
    summary: "请帮我总结以下资料，输出：1）关键结论 2）风险点 3）下一步行动建议。",
    plan: "请基于这个目标帮我写方案，包含：背景、目标、里程碑、资源投入、风险与验收标准。",
    qa: "请做知识问答：先给结论，再列出依据来源和不确定项。",
  };

  const prompt = templates[scene];
  if (!prompt) {
    return;
  }
  els.messageInput.value = prompt;
  autoGrowTextarea();
  els.messageInput.focus();
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    const container = document.querySelector(".conversation");
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  });
}

function openAuthModal() {
  updateIdentityCard();
  els.authModal.classList.remove("hidden");
}

function closeAuthModal() {
  els.authModal.classList.add("hidden");
}

function ensureIdentity() {
  return Boolean(state.teamId && state.userId);
}

function autoGrowTextarea() {
  els.messageInput.style.height = "auto";
  els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 180)}px`;
}

function appendEmpty(listEl, text) {
  const li = document.createElement("li");
  li.className = "empty-item";
  li.textContent = text;
  listEl.appendChild(li);
}

function dedupeStrings(values) {
  const result = [];
  for (const item of values) {
    const value = String(item || "").trim();
    if (value && !result.includes(value)) {
      result.push(value);
    }
  }
  return result;
}

function formatClock(dateObj) {
  const hour = String(dateObj.getHours()).padStart(2, "0");
  const minute = String(dateObj.getMinutes()).padStart(2, "0");
  return `${hour}:${minute}`;
}

function formatTime(iso) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.valueOf())) {
    return "--";
  }
  return `${dt.getMonth() + 1}-${dt.getDate()} ${formatClock(dt)}`;
}

function truncate(text, length) {
  if (text.length <= length) {
    return text;
  }
  return `${text.slice(0, length - 1)}…`;
}

function escapeHtml(raw) {
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

async function apiRequest(path, options = {}) {
  const requestOptions = {
    method: options.method || "GET",
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  };

  const response = await fetch(`${API_PREFIX}${path}`, requestOptions);
  const text = await response.text();
  let data;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : response.statusText;
    throw new Error(String(detail || `请求失败(${response.status})`));
  }

  return data;
}

function setButtonLoading(button, loading, loadingText) {
  if (!button) {
    return;
  }

  if (loading) {
    button.dataset.originText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
    return;
  }

  button.textContent = button.dataset.originText || button.textContent;
  button.disabled = false;
}

function showToast(message, isError = false) {
  clearTimeout(toastTimer);

  els.toast.textContent = message;
  els.toast.classList.remove("hidden", "error");
  if (isError) {
    els.toast.classList.add("error");
  }

  toastTimer = setTimeout(() => {
    els.toast.classList.add("hidden");
  }, 2600);
}
