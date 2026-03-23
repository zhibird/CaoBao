const API_PREFIX = "/api/v1";
const DEFAULT_MODEL_ID = "default";
const NONE_MODEL_ID = "none";
const ADD_MODEL_OPTION = "__add_model__";
const DEFAULT_EMBEDDING_ID = "default";
const MOCK_EMBEDDING_ID = "mock";
const ADD_EMBEDDING_OPTION = "__add_embedding_model__";
const DOCUMENT_STATUS_POLL_INTERVAL_MS = 2000;
const DOCUMENT_STATUS_POLL_TIMEOUT_MS = 120000;

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
  selectedDocumentIds: [],
  sending: false,
  importing: false,
};

const els = {};
let toastTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  hydrateState();
  bindEvents();
  updateIdentityCard();
  initModelOptions();
  initEmbeddingOptions();
  renderAttachmentStrip();

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
  els.refreshAllBtn = document.getElementById("refreshAllBtn");
  els.heroTitle = document.getElementById("heroTitle");
  els.scenarioCards = document.getElementById("scenarioCards");
  els.messageList = document.getElementById("messageList");
  els.newSessionBtn = document.getElementById("newSessionBtn");
  els.toggleImportBtn = document.getElementById("toggleImportBtn");
  els.attachMenu = document.getElementById("attachMenu");
  els.uploadFileBtn = document.getElementById("uploadFileBtn");
  els.pasteTextBtn = document.getElementById("pasteTextBtn");
  els.importComposer = document.getElementById("importComposer");
  els.attachmentStrip = document.getElementById("attachmentStrip");
  els.messageInput = document.getElementById("messageInput");
  els.sendBtn = document.getElementById("sendBtn");
  els.fileInput = document.getElementById("fileInput");
  els.sourceName = document.getElementById("sourceName");
  els.fileContent = document.getElementById("fileContent");
  els.importBtn = document.getElementById("importBtn");
  els.cancelImportBtn = document.getElementById("cancelImportBtn");
  els.previewDrawer = document.getElementById("previewDrawer");
  els.previewBackdrop = document.getElementById("previewBackdrop");
  els.closePreviewBtn = document.getElementById("closePreviewBtn");
  els.previewTitle = document.getElementById("previewTitle");
  els.previewMeta = document.getElementById("previewMeta");
  els.previewSnippet = document.getElementById("previewSnippet");
  els.previewContent = document.getElementById("previewContent");
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
      showToast("请先登录账户后再开始聊天", true);
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

  els.modelSelect.addEventListener("change", () => {
    handleModelChange().catch((error) => showToast(error.message, true));
  });
  els.embeddingSelect.addEventListener("change", () => {
    handleEmbeddingChange().catch((error) => showToast(error.message, true));
  });

  els.toggleImportBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    els.attachMenu.classList.toggle("hidden");
  });
  els.uploadFileBtn.addEventListener("click", () => {
    closeAttachMenu();
    els.fileInput.click();
  });
  els.pasteTextBtn.addEventListener("click", () => {
    closeAttachMenu();
    showImportComposer();
  });
  els.cancelImportBtn.addEventListener("click", hideImportComposer);
  els.fileInput.addEventListener("change", handleFileInputChange);
  els.importBtn.addEventListener("click", handleImportFromComposer);

  els.sendBtn.addEventListener("click", handleSend);
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  });
  els.messageInput.addEventListener("input", autoGrowTextarea);

  els.previewBackdrop.addEventListener("click", closePreviewDrawer);
  els.closePreviewBtn.addEventListener("click", closePreviewDrawer);

  document.addEventListener("click", handleGlobalDocumentClick);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAttachMenu();
      closePreviewDrawer();
    }
  });

  const sceneButtons = document.querySelectorAll(".scenario-card");
  for (const button of sceneButtons) {
    button.addEventListener("click", () => {
      applyScenarioCard(button.dataset.scene || "");
    });
  }
}

function handleGlobalDocumentClick(event) {
  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }
  if (!els.attachMenu.classList.contains("hidden")) {
    const clickInside = els.attachMenu.contains(target) || els.toggleImportBtn.contains(target);
    if (!clickInside) {
      closeAttachMenu();
    }
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
  localStorage.setItem(selectedEmbeddingStorageKey(), state.selectedEmbedding || DEFAULT_EMBEDDING_ID);
}

function updateIdentityCard() {
  const name = state.displayName || state.teamName || "未登录";
  const accountId = state.teamId || state.userId;
  els.profileName.textContent = name;
  els.profileTeam.textContent = accountId ? `account: ${accountId}` : "点击登录或切换账户";
  els.avatarText.textContent = name.slice(0, 1) || "未";
  els.accountIdInput.value = accountId || "";
  els.accountNameInput.value = accountId ? name : "";
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
  const allModels = dedupeStrings([DEFAULT_EMBEDDING_ID, MOCK_EMBEDDING_ID, ...configuredModels]);
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

  state.selectedEmbedding = allModels.includes(state.selectedEmbedding) ? state.selectedEmbedding : DEFAULT_EMBEDDING_ID;
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
    return "default (.env)";
  }
  if (model === MOCK_EMBEDDING_ID) {
    return "mock (hashing)";
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
      showToast(`模型已切换为 ${selected}`);
    }
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const modelName = window.prompt("输入模型名称，例如 gpt-4.1-mini");
  if (!modelName) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const normalizedModelName = modelName.trim();
  if (!normalizedModelName || normalizedModelName.toLowerCase() === DEFAULT_MODEL_ID || normalizedModelName.toLowerCase() === NONE_MODEL_ID) {
    els.modelSelect.value = state.selectedModel;
    showToast("模型名称无效", true);
    return;
  }

  const baseUrl = window.prompt("输入 API Base URL", "https://api.openai.com/v1");
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
  showToast(`已添加并切换到模型 ${normalizedModelName}`);
}

async function handleEmbeddingChange() {
  const selected = els.embeddingSelect.value;
  if (selected !== ADD_EMBEDDING_OPTION) {
    state.selectedEmbedding = selected;
    persistSelectedEmbedding();
    if (selected === DEFAULT_EMBEDDING_ID) {
      showToast("当前使用 default（读取 .env 向量模型配置）");
    } else if (selected === MOCK_EMBEDDING_ID) {
      showToast("当前使用 mock（hashing 向量）");
    } else {
      showToast(`向量模型已切换为 ${selected}`);
    }
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }

  const modelName = window.prompt("输入向量模型名称，例如 text-embedding-3-small");
  if (!modelName) {
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }

  const normalizedModelName = modelName.trim();
  if (!normalizedModelName || normalizedModelName.toLowerCase() === DEFAULT_EMBEDDING_ID) {
    els.embeddingSelect.value = state.selectedEmbedding;
    showToast("向量模型名称无效", true);
    return;
  }

  const providerInput = window.prompt("输入 provider（openai / volcengine / mock）", "openai");
  if (!providerInput || !providerInput.trim()) {
    els.embeddingSelect.value = state.selectedEmbedding;
    return;
  }
  const provider = providerInput.trim().toLowerCase();

  let baseUrl = null;
  let apiKey = null;
  if (provider !== "mock") {
    baseUrl = window.prompt("输入 Embedding API Base URL", "https://api.openai.com/v1");
    if (!baseUrl || !baseUrl.trim()) {
      els.embeddingSelect.value = state.selectedEmbedding;
      return;
    }
    apiKey = window.prompt("输入 Embedding API Key");
    if (!apiKey || !apiKey.trim()) {
      els.embeddingSelect.value = state.selectedEmbedding;
      return;
    }
  }

  await apiRequest("/embedding/models", {
    method: "POST",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      model_name: normalizedModelName,
      provider,
      base_url: baseUrl ? baseUrl.trim() : null,
      api_key: apiKey ? apiKey.trim() : null,
    },
  });

  state.selectedEmbedding = normalizedModelName;
  persistSelectedEmbedding();
  await loadEmbeddingConfigs();
  showToast(`已添加并切换到向量模型 ${normalizedModelName}`);
}

async function handleSaveAuth() {
  const rawAccountId = els.accountIdInput.value.trim();
  const accountId = rawAccountId.replace(/\s+/g, "_").slice(0, 64);
  const accountName = els.accountNameInput.value.trim() || accountId;

  if (!accountId) {
    showToast("account_id 不能为空", true);
    return;
  }

  setButtonLoading(els.saveAuthBtn, true, "保存中...");

  try {
    await createOrReuseTeam(accountId, accountName);
    await createOrReuseUser(accountId, accountId, accountName);

    state.teamId = accountId;
    state.teamName = accountName;
    state.userId = accountId;
    state.displayName = accountName;
    state.conversationId = "";
    state.selectedDocumentIds = [];
    persistIdentity();
    persistConversation();
    state.selectedModel = loadSelectedModelFromStorage();
    state.selectedEmbedding = loadSelectedEmbeddingFromStorage();

    updateIdentityCard();
    closeAuthModal();
    clearConversation();
    await loadAllData();
    showToast(`已登录账户：${accountName}`);
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
  } catch (error) {
    if (!String(error.message).includes("already exists")) {
      throw error;
    }
  }
}

async function loadAllData() {
  if (!ensureIdentity()) {
    return;
  }

  await Promise.all([loadModelConfigs(), loadEmbeddingConfigs()]);
  initModelOptions();
  initEmbeddingOptions();
  await loadConversations();
  await ensureActiveConversation();
  await Promise.all([loadHistory(), loadDocuments()]);
}

async function loadModelConfigs() {
  if (!ensureIdentity()) {
    state.modelConfigs = [];
    initModelOptions();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
  });
  const response = await apiRequest(`/llm/models?${query.toString()}`);
  state.modelConfigs = Array.isArray(response.items) ? response.items : [];
  initModelOptions();
}

async function loadEmbeddingConfigs() {
  if (!ensureIdentity()) {
    state.embeddingConfigs = [];
    initEmbeddingOptions();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    user_id: state.userId,
  });
  const response = await apiRequest(`/embedding/models?${query.toString()}`);
  state.embeddingConfigs = Array.isArray(response.items) ? response.items : [];
  initEmbeddingOptions();
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

    const row = document.createElement("div");
    row.className = "history-row";

    const titleWrap = document.createElement("div");
    titleWrap.className = "history-title-wrap";

    const title = document.createElement("button");
    title.type = "button";
    title.className = "doc-card-action";
    title.textContent = item.title || "新会话";
    title.addEventListener("click", () => {
      switchConversation(item.conversation_id).catch((error) => showToast(error.message, true));
    });
    titleWrap.appendChild(title);

    if (item.is_pinned) {
      const pinTag = document.createElement("span");
      pinTag.className = "history-pin-tag";
      pinTag.textContent = "置顶";
      titleWrap.appendChild(pinTag);
    }

    const actions = document.createElement("div");
    actions.className = "history-actions";

    const menu = document.createElement("details");
    menu.className = "history-menu";

    const summary = document.createElement("summary");
    summary.className = "history-more";
    summary.textContent = "...";

    const panel = document.createElement("div");
    panel.className = "history-menu-panel";
    panel.append(
      createHistoryActionButton("重命名", () => {
        menu.open = false;
        renameConversation(item).catch((error) => showToast(error.message, true));
      }),
      createHistoryActionButton(item.is_pinned ? "取消置顶" : "置顶", () => {
        menu.open = false;
        pinConversation(item.conversation_id, !item.is_pinned).catch((error) => showToast(error.message, true));
      }),
      createHistoryActionButton("删除", () => {
        menu.open = false;
        deleteConversation(item.conversation_id).catch((error) => showToast(error.message, true));
      }, true),
    );

    menu.append(summary, panel);
    actions.appendChild(menu);
    row.append(titleWrap, actions);
    li.appendChild(row);

    const meta = document.createElement("div");
    meta.className = "history-meta";
    meta.textContent = `${item.status || "active"} · ${formatTime(item.created_at)}`;
    li.appendChild(meta);

    els.historyList.appendChild(li);
  }
}

function createHistoryActionButton(label, onClick, danger = false) {
  const button = document.createElement("button");
  button.className = `history-action-btn${danger ? " danger" : ""}`;
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
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

async function createAndSwitchConversation() {
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    return;
  }

  const created = await createConversation("新会话");
  state.conversationId = created.conversation_id;
  state.selectedDocumentIds = [];
  persistConversation();
  await loadConversations();
  clearConversation();
  await Promise.all([loadHistory(), loadDocuments()]);
  showToast("已创建新会话");
}

async function switchConversation(conversationId) {
  if (!conversationId || state.conversationId === conversationId) {
    return;
  }
  state.conversationId = conversationId;
  state.selectedDocumentIds = [];
  persistConversation();
  renderConversationList();
  clearConversation();
  await Promise.all([loadHistory(), loadDocuments()]);
}

async function renameConversation(conversation) {
  const currentTitle = String(conversation.title || "新会话").trim();
  const nextTitle = window.prompt("输入新的会话标题", currentTitle);
  if (nextTitle === null) {
    return;
  }
  const normalizedTitle = nextTitle.trim();
  if (!normalizedTitle) {
    showToast("会话标题不能为空", true);
    return;
  }

  await apiRequest(`/conversations/${encodeURIComponent(conversation.conversation_id)}`, {
    method: "PATCH",
    body: {
      team_id: state.teamId,
      user_id: state.userId,
      title: normalizedTitle,
    },
  });
  await loadConversations();
  showToast("会话标题已更新");
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
  showToast(pinned ? "已置顶会话" : "已取消置顶");
}

async function deleteConversation(conversationId) {
  if (!window.confirm("确认删除这个会话吗？")) {
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
    state.selectedDocumentIds = [];
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

    const responsePayload = item.response_payload || {};
    appendMessage("assistant", item.response_text || "", {
      createdAt: item.created_at,
      sources: normalizeResponseSources(responsePayload),
      mode: responsePayload.mode || "",
      model: responsePayload.model || "",
      messageId: item.message_id,
      requestText: item.request_text || "",
      channel: item.channel,
    });
  }
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
    showToast("工具调用消息不支持重新生成", true);
    return;
  }

  const availableModels = dedupeStrings([
    DEFAULT_MODEL_ID,
    NONE_MODEL_ID,
    ...state.modelConfigs.map((item) => item.model_name),
  ]);
  const selected = window.prompt(`选择重新生成模型：${availableModels.join(", ")}`, state.selectedModel || DEFAULT_MODEL_ID);
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

async function loadDocuments() {
  if (!state.conversationId) {
    state.documents = [];
    state.selectedDocumentIds = [];
    renderDocuments();
    renderAttachmentStrip();
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    conversation_id: state.conversationId,
  });
  const response = await apiRequest(`/documents?${query.toString()}`);
  state.documents = Array.isArray(response) ? response : [];
  state.selectedDocumentIds = state.selectedDocumentIds.filter((documentId) => {
    return state.documents.some((doc) => doc.document_id === documentId && normalizeStatus(doc.status) === "ready");
  });
  renderDocuments();
  renderAttachmentStrip();
}

function renderDocuments() {
  els.documentList.innerHTML = "";

  if (!state.documents.length) {
    appendEmpty(els.documentList, "还没有导入文件");
    return;
  }

  for (const doc of state.documents) {
    const li = document.createElement("li");

    const head = document.createElement("div");
    head.className = "doc-card-head";

    const titleBtn = document.createElement("button");
    titleBtn.type = "button";
    titleBtn.className = "doc-card-action";
    titleBtn.textContent = doc.source_name;
    titleBtn.addEventListener("click", () => {
      openSourcePreview({
        document_id: doc.document_id,
        source_name: doc.source_name,
        chunk_index: null,
        snippet: null,
      }).catch((error) => showToast(error.message, true));
    });

    const status = document.createElement("span");
    status.className = `doc-status ${normalizeStatus(doc.status)}`;
    status.textContent = formatStatusLabel(doc.status);
    head.append(titleBtn, status);

    const meta = document.createElement("div");
    meta.className = "doc-meta";
    meta.textContent = `${doc.content_type} · ${formatTime(doc.created_at)}`;

    const actions = document.createElement("div");
    actions.className = "doc-card-actions";

    const previewBtn = document.createElement("button");
    previewBtn.type = "button";
    previewBtn.className = "doc-card-action";
    previewBtn.textContent = "预览";
    previewBtn.addEventListener("click", () => {
      openSourcePreview({
        document_id: doc.document_id,
        source_name: doc.source_name,
        chunk_index: null,
        snippet: null,
      }).catch((error) => showToast(error.message, true));
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "doc-card-action danger";
    deleteBtn.textContent = "删除";
    deleteBtn.addEventListener("click", () => {
      deleteDocument(doc.document_id, doc.source_name).catch((error) => showToast(error.message, true));
    });

    actions.append(previewBtn, deleteBtn);
    li.append(head, meta, actions);
    els.documentList.appendChild(li);
  }
}

function renderAttachmentStrip() {
  els.attachmentStrip.innerHTML = "";

  if (!state.documents.length) {
    els.attachmentStrip.classList.add("hidden");
    return;
  }

  els.attachmentStrip.classList.remove("hidden");

  const helper = document.createElement("div");
  helper.className = "attachment-helper";
  if (state.selectedDocumentIds.length) {
    helper.textContent = `本轮已选 ${state.selectedDocumentIds.length} 个文件，发送时只检索这些文件。`;
  } else {
    helper.textContent = "默认自动使用本会话全部 ready 文件。点选附件可切换为本轮精确范围。";
  }
  els.attachmentStrip.appendChild(helper);

  const list = document.createElement("div");
  list.className = "attachment-list";

  for (const doc of state.documents) {
    const chip = document.createElement("div");
    chip.className = `attachment-chip${state.selectedDocumentIds.includes(doc.document_id) ? " active" : ""}`;

    const mainBtn = document.createElement("button");
    mainBtn.type = "button";
    mainBtn.className = "doc-chip-main";
    mainBtn.addEventListener("click", () => handleChipClick(doc));

    const name = document.createElement("span");
    name.className = "doc-chip-name";
    name.textContent = doc.source_name;

    const status = document.createElement("span");
    status.className = `doc-status ${normalizeStatus(doc.status)}`;
    status.textContent = formatStatusLabel(doc.status);

    mainBtn.append(name, status);

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "doc-chip-delete";
    deleteBtn.textContent = "×";
    deleteBtn.title = `删除 ${doc.source_name}`;
    deleteBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteDocument(doc.document_id, doc.source_name).catch((error) => showToast(error.message, true));
    });

    chip.append(mainBtn, deleteBtn);
    list.appendChild(chip);
  }

  els.attachmentStrip.appendChild(list);
}

function handleChipClick(doc) {
  if (normalizeStatus(doc.status) !== "ready") {
    openSourcePreview({
      document_id: doc.document_id,
      source_name: doc.source_name,
      chunk_index: null,
      snippet: null,
    }).catch((error) => showToast(error.message, true));
    return;
  }
  toggleDocumentSelection(doc.document_id);
}

function toggleDocumentSelection(documentId) {
  if (state.selectedDocumentIds.includes(documentId)) {
    state.selectedDocumentIds = state.selectedDocumentIds.filter((item) => item !== documentId);
  } else {
    state.selectedDocumentIds = [...state.selectedDocumentIds, documentId];
  }
  renderAttachmentStrip();
}

async function deleteDocument(documentId, sourceName) {
  if (!window.confirm(`确认删除文件“${sourceName}”吗？`)) {
    return;
  }

  const query = new URLSearchParams({
    team_id: state.teamId,
    conversation_id: state.conversationId,
  });
  await apiRequest(`/documents/${encodeURIComponent(documentId)}?${query.toString()}`, {
    method: "DELETE",
  });

  state.selectedDocumentIds = state.selectedDocumentIds.filter((item) => item !== documentId);
  closePreviewDrawer();
  await loadDocuments();
  showToast(`已删除文件：${sourceName}`);
}
async function openSourcePreview(source) {
  const document = await getDocumentFromStateOrApi(source.document_id);
  els.previewTitle.textContent = document.source_name || source.source_name || "文件预览";
  els.previewMeta.innerHTML = "";

  const pageLabel = source.locator_label
    || (Number.isInteger(source.page_no) ? `Page ${Number(source.page_no)}` : null);
  const metaLines = [
    `状态：${formatStatusLabel(document.status)}`,
    `类型：${document.content_type}${document.mime_type ? ` (${document.mime_type})` : ""}`,
    Number.isFinite(Number(document.size_bytes)) ? `大小：${Math.max(0, Number(document.size_bytes))} bytes` : null,
    Number.isInteger(document.page_count) ? `页数：${document.page_count}` : null,
    pageLabel || (source.chunk_index === null || source.chunk_index === undefined ? null : `定位：第 ${Number(source.chunk_index) + 1} 段`),
    document.error_message ? `错误：${document.error_message}` : null,
  ].filter(Boolean);

  for (const line of metaLines) {
    const div = document.createElement("div");
    div.textContent = line;
    els.previewMeta.appendChild(div);
  }

  if (source.snippet) {
    els.previewSnippet.classList.remove("hidden");
    els.previewSnippet.textContent = source.snippet;
  } else {
    els.previewSnippet.classList.add("hidden");
    els.previewSnippet.textContent = "";
  }

  const filePreviewUrl = buildDocumentFileUrl(document.document_id);
  if (["pdf", "png", "jpg", "jpeg", "webp"].includes(String(document.content_type || "").toLowerCase())) {
    const previewHint = [
      `原文件预览：${filePreviewUrl}`,
      "",
      "以下是提取文本（若有）：",
      document.content || "",
    ].join("\n");
    els.previewContent.textContent = previewHint;
  } else {
    els.previewContent.textContent = document.content || "";
  }
  els.previewDrawer.classList.remove("hidden");
  els.previewDrawer.setAttribute("aria-hidden", "false");
}

function closePreviewDrawer() {
  els.previewDrawer.classList.add("hidden");
  els.previewDrawer.setAttribute("aria-hidden", "true");
}

function buildDocumentFileUrl(documentId) {
  const query = new URLSearchParams({ team_id: state.teamId });
  if (state.conversationId) {
    query.set("conversation_id", state.conversationId);
  }
  return `${API_PREFIX}/documents/${encodeURIComponent(documentId)}/file?${query.toString()}`;
}

async function getDocumentFromStateOrApi(documentId) {
  const cached = state.documents.find((item) => item.document_id === documentId);
  if (cached) {
    return cached;
  }

  const query = new URLSearchParams({ team_id: state.teamId });
  if (state.conversationId) {
    query.set("conversation_id", state.conversationId);
  }
  return apiRequest(`/documents/${encodeURIComponent(documentId)}?${query.toString()}`);
}

function showImportComposer() {
  els.importComposer.classList.remove("hidden");
  if (!els.sourceName.value.trim()) {
    els.sourceName.focus();
  } else {
    els.fileContent.focus();
  }
}

function hideImportComposer() {
  els.importComposer.classList.add("hidden");
  els.sourceName.value = "";
  els.fileContent.value = "";
}

function closeAttachMenu() {
  els.attachMenu.classList.add("hidden");
}

async function ensureConversationReady() {
  if (state.conversationId) {
    return;
  }
  await loadConversations();
  await ensureActiveConversation();
}

async function handleSend() {
  const question = els.messageInput.value.trim();
  if (!question || state.sending) {
    return;
  }

  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    return;
  }

  await ensureConversationReady();
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

    const selectedDocumentIds = getExplicitSelectedDocumentIds();
    if (selectedDocumentIds.length) {
      payload.selected_document_ids = selectedDocumentIds;
    }

    const response = await apiRequest("/chat/ask", {
      method: "POST",
      body: payload,
    });

    appendMessage("assistant", response.answer || "", {
      sources: normalizeResponseSources(response),
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

function getExplicitSelectedDocumentIds() {
  return state.selectedDocumentIds.filter((documentId) => {
    return state.documents.some((doc) => doc.document_id === documentId && normalizeStatus(doc.status) === "ready");
  });
}

function shouldUseEchoFallback(errorMessage) {
  const text = String(errorMessage || "").toLowerCase();
  return (
    text.includes("no indexed chunks found")
    || text.includes("llm_api_key is required")
    || text.includes("llm request failed")
    || text.includes("timed out")
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

async function handleImportFromComposer() {
  const sourceName = els.sourceName.value.trim();
  const content = els.fileContent.value.trim();
  if (!sourceName || !content) {
    showToast("请填写文件名并粘贴内容", true);
    return;
  }

  await importDocumentWithContent({
    sourceName,
    content,
    contentType: inferContentType(sourceName),
  });
  hideImportComposer();
}

async function importDocumentWithContent({ sourceName, content, contentType }) {
  if (state.importing) {
    return;
  }
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    return;
  }

  await ensureConversationReady();
  state.importing = true;
  setButtonLoading(els.importBtn, true, "导入中...");

  try {
    const doc = await apiRequest("/documents/import", {
      method: "POST",
      body: {
        team_id: state.teamId,
        user_id: state.userId,
        conversation_id: state.conversationId,
        source_name: sourceName,
        content_type: contentType,
        content,
        auto_index: true,
        embedding_model: state.selectedEmbedding || DEFAULT_EMBEDDING_ID,
      },
    });

    upsertDocumentState(doc);
    renderDocuments();
    renderAttachmentStrip();
    await pollDocumentsUntilSettled([doc.document_id]);
    const latest = state.documents.find((item) => item.document_id === doc.document_id);
    if (latest && normalizeStatus(latest.status) === "failed") {
      showToast(`导入失败：${latest.error_message || latest.error_code || sourceName}`, true);
    } else {
      showToast(`导入完成：${sourceName}`);
    }
  } catch (error) {
    await loadDocuments();
    showToast(error.message, true);
  } finally {
    state.importing = false;
    setButtonLoading(els.importBtn, false, "导入");
  }
}

function upsertDocumentState(doc) {
  const existingIndex = state.documents.findIndex((item) => item.document_id === doc.document_id);
  if (existingIndex >= 0) {
    state.documents[existingIndex] = doc;
  } else {
    state.documents = [doc, ...state.documents];
  }
}

function setDocumentStatusLocal(documentId, status) {
  state.documents = state.documents.map((doc) => {
    if (doc.document_id === documentId) {
      return { ...doc, status };
    }
    return doc;
  });
  renderDocuments();
  renderAttachmentStrip();
}

async function handleFileInputChange(event) {
  const file = event.target.files && event.target.files[0];
  event.target.value = "";
  if (!file) {
    return;
  }

  try {
    await uploadDocumentFile(file);
  } catch (error) {
    showToast(error.message || "上传文件失败", true);
  }
}

async function uploadDocumentFile(file) {
  if (state.importing) {
    return;
  }
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录账户", true);
    return;
  }

  await ensureConversationReady();
  state.importing = true;
  setButtonLoading(els.importBtn, true, "上传中...");

  try {
    const formData = new FormData();
    formData.append("team_id", state.teamId);
    formData.append("user_id", state.userId);
    formData.append("conversation_id", state.conversationId);
    formData.append("auto_index", "true");
    formData.append("embedding_model", state.selectedEmbedding || DEFAULT_EMBEDDING_ID);
    formData.append("file", file);

    const doc = await apiRequest("/documents/upload", {
      method: "POST",
      formData,
    });

    upsertDocumentState(doc);
    renderDocuments();
    renderAttachmentStrip();

    await pollDocumentsUntilSettled([doc.document_id]);
    const latest = state.documents.find((item) => item.document_id === doc.document_id);
    if (latest && normalizeStatus(latest.status) === "failed") {
      showToast(`上传失败：${latest.error_message || latest.error_code || file.name}`, true);
    } else {
      showToast(`上传完成：${file.name}`);
    }
  } finally {
    state.importing = false;
    setButtonLoading(els.importBtn, false, "导入");
  }
}

async function pollDocumentsUntilSettled(documentIds) {
  if (!Array.isArray(documentIds) || !documentIds.length) {
    return;
  }

  const deduped = dedupeStrings(documentIds);
  const deadline = Date.now() + DOCUMENT_STATUS_POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await sleep(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    await loadDocuments();
    const targets = state.documents.filter((doc) => deduped.includes(doc.document_id));
    if (!targets.length) {
      return;
    }
    const allSettled = targets.every((doc) => {
      const normalized = normalizeStatus(doc.status);
      return normalized === "ready" || normalized === "failed";
    });
    if (allSettled) {
      return;
    }
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

  head.append(left, right);

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = content;

  message.append(head, body);
  if (role === "assistant" && Array.isArray(options.sources) && options.sources.length) {
    const sourceBox = document.createElement("div");
    sourceBox.className = "source-box";

    const title = document.createElement("div");
    title.className = "source-title";
    title.textContent = "引用来源";
    sourceBox.appendChild(title);

    const sourceList = document.createElement("div");
    sourceList.className = "source-list";
    for (const source of options.sources.slice(0, 4)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "source-pill";
      button.addEventListener("click", () => {
        openSourcePreview(source).catch((error) => showToast(error.message, true));
      });

      const sourceTitle = document.createElement("div");
      sourceTitle.className = "source-pill-title";
      const locator = source.locator_label
        || (Number.isInteger(source.page_no) ? `Page ${Number(source.page_no)}` : null)
        || (Number.isInteger(source.chunk_index) ? `第 ${Number(source.chunk_index) + 1} 段` : null);
      sourceTitle.textContent = locator
        ? `${source.source_name || "未命名文件"} · ${locator}`
        : (source.source_name || "未命名文件");

      const sourceSnippet = document.createElement("div");
      sourceSnippet.className = "source-pill-snippet";
      sourceSnippet.textContent = source.snippet || "点击查看文件预览";

      button.append(sourceTitle, sourceSnippet);
      sourceList.appendChild(button);
    }

    sourceBox.appendChild(sourceList);
    message.appendChild(sourceBox);
  }

  row.appendChild(message);

  const actionRail = document.createElement("div");
  actionRail.className = "message-action-rail";

  if (role === "user" && options.messageId) {
    if (options.editable) {
      actionRail.appendChild(createMessageActionButton("编辑", "✎", () => {
        editHistoryMessage(options.messageId, content, options.channel).catch((error) => {
          showToast(error.message, true);
        });
      }));
    }
    if (options.deletable) {
      actionRail.appendChild(createMessageActionButton("删除", "⌫", () => {
        deleteHistoryMessage(options.messageId).catch((error) => {
          showToast(error.message, true);
        });
      }));
    }
  }

  if (role === "assistant") {
    actionRail.appendChild(createMessageActionButton("复制", "⧉", () => {
      copyMessageText(content).catch((error) => showToast(error.message, true));
    }));

    if (options.messageId && options.requestText) {
      actionRail.appendChild(createMessageActionButton("重新生成", "↻", () => {
        regenerateAssistantMessage(options.messageId, options.requestText, options.channel).catch((error) => {
          showToast(error.message, true);
        });
      }));
    }
  }

  if (actionRail.childElementCount > 0) {
    row.appendChild(actionRail);
  }

  els.messageList.appendChild(row);
  scrollToBottom();
}

function createMessageActionButton(title, text, onClick) {
  const button = document.createElement("button");
  button.className = "message-icon-btn";
  button.type = "button";
  button.title = title;
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function normalizeResponseSources(payload) {
  if (Array.isArray(payload.sources) && payload.sources.length) {
    return payload.sources.map((item) => ({
      document_id: item.document_id,
      source_name: item.source_name || "",
      chunk_id: item.chunk_id || "",
      chunk_index: Number.isFinite(Number(item.chunk_index)) ? Number(item.chunk_index) : null,
      page_no: Number.isFinite(Number(item.page_no)) ? Number(item.page_no) : null,
      locator_label: item.locator_label || "",
      snippet: item.snippet || "",
      score: Number(item.score || 0),
    }));
  }

  if (Array.isArray(payload.hits) && payload.hits.length) {
    return payload.hits.map((item) => ({
      document_id: item.document_id,
      source_name: item.source_name || "",
      chunk_id: item.chunk_id || "",
      chunk_index: Number.isFinite(Number(item.chunk_index)) ? Number(item.chunk_index) : null,
      page_no: Number.isFinite(Number(item.page_no)) ? Number(item.page_no) : null,
      locator_label: item.locator_label || "",
      snippet: truncate(String(item.content || "").replace(/\s+/g, " ").trim(), 220),
      score: Number(item.score || 0),
    }));
  }

  return [];
}

function clearConversation() {
  els.messageList.innerHTML = "";
  setHeroVisible(true);
}

function setHeroVisible(visible) {
  els.heroTitle.style.display = visible ? "block" : "none";
  els.scenarioCards.style.display = visible ? "grid" : "none";
}

function applyScenarioCard(scene) {
  const templates = {
    summary: "请帮我总结以下资料，输出：1）关键信息 2）风险点 3）下一步行动建议。",
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

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function normalizeStatus(status) {
  const normalized = String(status || "uploaded").trim().toLowerCase();
  if (["pending", "uploaded", "parsing", "chunking", "indexing", "ready", "failed", "deleted"].includes(normalized)) {
    return normalized;
  }
  return "uploaded";
}

function formatStatusLabel(status) {
  switch (normalizeStatus(status)) {
    case "uploaded":
      return "已上传";
    case "parsing":
      return "解析中";
    case "chunking":
      return "切块中";
    case "indexing":
      return "索引中";
    case "ready":
      return "可用";
    case "failed":
      return "失败";
    case "deleted":
      return "已删除";
    case "pending":
      return "待处理";
    default:
      return "已上传";
  }
}

function inferContentType(sourceName) {
  const normalized = String(sourceName || "").trim().toLowerCase();
  const candidates = ["txt", "md", "pdf", "png", "jpg", "jpeg", "webp"];
  for (const ext of candidates) {
    if (normalized.endsWith(`.${ext}`)) {
      return ext;
    }
  }
  if (!normalized) {
    return "md";
  }
  throw new Error("当前仅支持 .txt/.md/.pdf/.png/.jpg/.jpeg/.webp 文件。");
}

async function apiRequest(path, options = {}) {
  const useFormData = options.formData instanceof FormData;
  const requestOptions = {
    method: options.method || "GET",
    headers: {
      Accept: "application/json",
      ...(!useFormData && options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: useFormData ? options.formData : (options.body ? JSON.stringify(options.body) : undefined),
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
    throw new Error(String(detail || `请求失败（${response.status}）`));
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
