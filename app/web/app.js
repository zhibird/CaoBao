const API_PREFIX = "/api/v1";
const STORAGE_KEYS = {
  teamId: "caibao.teamId",
  teamName: "caibao.teamName",
  userId: "caibao.userId",
  displayName: "caibao.displayName",
  conversationId: "caibao.conversationId",
  selectedModel: "caibao.selectedModel",
  customModels: "caibao.customModels",
};

const PRESET_MODELS = ["gpt-4.1-mini", "gpt-4o-mini", "gpt-5-mini"];

const state = {
  teamId: "",
  teamName: "",
  userId: "",
  displayName: "",
  conversationId: "",
  selectedModel: PRESET_MODELS[0],
  customModels: [],
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
  els.docSelect = document.getElementById("docSelect");
  els.refreshAllBtn = document.getElementById("refreshAllBtn");
  els.heroTitle = document.getElementById("heroTitle");
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
  els.teamIdInput = document.getElementById("teamIdInput");
  els.teamNameInput = document.getElementById("teamNameInput");
  els.userIdInput = document.getElementById("userIdInput");
  els.displayNameInput = document.getElementById("displayNameInput");
  els.cancelAuthBtn = document.getElementById("cancelAuthBtn");
  els.saveAuthBtn = document.getElementById("saveAuthBtn");

  els.toast = document.getElementById("toast");
}

function bindEvents() {
  els.profileBtn.addEventListener("click", openAuthModal);
  els.cancelAuthBtn.addEventListener("click", () => {
    if (!state.teamId || !state.userId) {
      showToast("请先登录后再开始聊天", true);
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

  els.modelSelect.addEventListener("change", handleModelChange);
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
}

function hydrateState() {
  state.teamId = localStorage.getItem(STORAGE_KEYS.teamId) || "";
  state.teamName = localStorage.getItem(STORAGE_KEYS.teamName) || "";
  state.userId = localStorage.getItem(STORAGE_KEYS.userId) || "";
  state.displayName = localStorage.getItem(STORAGE_KEYS.displayName) || "";
  state.conversationId = localStorage.getItem(STORAGE_KEYS.conversationId) || "";
  state.selectedModel = localStorage.getItem(STORAGE_KEYS.selectedModel) || PRESET_MODELS[0];

  try {
    const raw = localStorage.getItem(STORAGE_KEYS.customModels);
    const parsed = raw ? JSON.parse(raw) : [];
    state.customModels = Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
  } catch {
    state.customModels = [];
  }
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

function updateIdentityCard() {
  const name = state.displayName || "未登录";
  const team = state.teamId ? `${state.teamName || state.teamId} · ${state.userId}` : "点击登录或切换用户";
  els.profileName.textContent = name;
  els.profileTeam.textContent = team;
  els.avatarText.textContent = name.slice(0, 1) || "未";

  els.teamIdInput.value = state.teamId;
  els.teamNameInput.value = state.teamName;
  els.userIdInput.value = state.userId;
  els.displayNameInput.value = state.displayName;
}

function initModelOptions() {
  const allModels = dedupeStrings([...PRESET_MODELS, ...state.customModels, state.selectedModel]);
  els.modelSelect.innerHTML = "";

  for (const model of allModels) {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    els.modelSelect.appendChild(option);
  }

  const customOption = document.createElement("option");
  customOption.value = "__custom__";
  customOption.textContent = "自定义模型...";
  els.modelSelect.appendChild(customOption);

  els.modelSelect.value = allModels.includes(state.selectedModel) ? state.selectedModel : PRESET_MODELS[0];
  state.selectedModel = els.modelSelect.value;
  localStorage.setItem(STORAGE_KEYS.selectedModel, state.selectedModel);
}

function handleModelChange() {
  if (els.modelSelect.value !== "__custom__") {
    state.selectedModel = els.modelSelect.value;
    localStorage.setItem(STORAGE_KEYS.selectedModel, state.selectedModel);
    showToast(`模型已切换为 ${state.selectedModel}`);
    return;
  }

  const custom = window.prompt("请输入模型名（例如 gpt-4.1-mini）");
  if (!custom) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  const normalized = custom.trim();
  if (!normalized) {
    els.modelSelect.value = state.selectedModel;
    return;
  }

  if (!state.customModels.includes(normalized)) {
    state.customModels.push(normalized);
    state.customModels = dedupeStrings(state.customModels);
    localStorage.setItem(STORAGE_KEYS.customModels, JSON.stringify(state.customModels));
  }

  state.selectedModel = normalized;
  localStorage.setItem(STORAGE_KEYS.selectedModel, state.selectedModel);
  initModelOptions();
  els.modelSelect.value = normalized;
  showToast(`已添加并切换到模型 ${normalized}`);
}

async function handleSaveAuth() {
  const teamId = els.teamIdInput.value.trim();
  const teamName = els.teamNameInput.value.trim() || teamId;
  const userId = els.userIdInput.value.trim();
  const displayName = els.displayNameInput.value.trim() || userId;

  if (!teamId || !userId) {
    showToast("team_id 和 user_id 不能为空", true);
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
    showToast(`已登录：${displayName}`);
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
    throw new Error(`用户 ${userId} 已属于团队 ${existing.team_id}，请换一个 user_id。`);
  }
}

async function loadAllData() {
  if (!state.teamId || !state.userId) {
    return;
  }

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

    li.innerHTML = `
      <div class="history-row">
        <div class="history-title">${escapeHtml(title)}</div>
        <div class="history-actions">
          <button class="history-rename" type="button" data-id="${escapeHtml(item.conversation_id)}">改名</button>
          <button class="history-delete" type="button" data-id="${escapeHtml(item.conversation_id)}">删</button>
        </div>
      </div>
      <div class="history-meta">${escapeHtml(createdAt)}</div>
    `;

    li.addEventListener("click", () => {
      switchConversation(item.conversation_id).catch((error) => showToast(error.message, true));
    });
    const deleteBtn = li.querySelector(".history-delete");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        deleteConversation(item.conversation_id).catch((error) => showToast(error.message, true));
      });
    }
    const renameBtn = li.querySelector(".history-rename");
    if (renameBtn) {
      renameBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        renameConversation(item).catch((error) => showToast(error.message, true));
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

async function createAndSwitchConversation() {
  if (!ensureIdentity()) {
    openAuthModal();
    showToast("请先登录团队与用户", true);
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
    appendMessage("assistant", item.response_text || "", {
      createdAt: item.created_at,
      hits,
      model,
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
  allOption.textContent = "全部文档";
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
    showToast("请先登录团队与用户", true);
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
      model: state.selectedModel,
    };

    if (els.docSelect.value) {
      payload.document_id = els.docSelect.value;
    }

    const response = await apiRequest("/chat/ask", {
      method: "POST",
      body: payload,
    });

    appendMessage("assistant", response.answer || "", {
      hits: Array.isArray(response.hits) ? response.hits : [],
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
    showToast("请先登录团队与用户", true);
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
          conversation_id: state.conversationId,
          document_id: documentId,
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

  if (els.heroTitle.style.display !== "none") {
    els.heroTitle.style.display = "none";
  }

  const message = document.createElement("article");
  message.className = `message ${role}`;

  const head = document.createElement("div");
  head.className = "message-head";

  const left = document.createElement("span");
  left.textContent = role === "user" ? state.displayName || "你" : "CaiBao";

  const createdDate = options.createdAt ? new Date(options.createdAt) : new Date();
  const timeText = Number.isNaN(createdDate.valueOf()) ? formatClock(new Date()) : formatClock(createdDate);

  const right = document.createElement("span");
  if (role === "assistant" && options.model) {
    right.textContent = `${timeText} · ${options.model}`;
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

  if (role === "user" && options.messageId && (options.editable || options.deletable)) {
    const tools = document.createElement("div");
    tools.className = "message-tools";

    if (options.editable) {
      const editBtn = document.createElement("button");
      editBtn.className = "message-tool-btn";
      editBtn.type = "button";
      editBtn.textContent = "编辑";
      editBtn.addEventListener("click", () => {
        editHistoryMessage(options.messageId, content, options.channel).catch((error) => {
          showToast(error.message, true);
        });
      });
      tools.appendChild(editBtn);
    }

    if (options.deletable) {
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "message-tool-btn";
      deleteBtn.type = "button";
      deleteBtn.textContent = "删除";
      deleteBtn.addEventListener("click", () => {
        deleteHistoryMessage(options.messageId).catch((error) => {
          showToast(error.message, true);
        });
      });
      tools.appendChild(deleteBtn);
    }

    message.appendChild(tools);
  }

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
      meta.textContent = `doc=${hit.document_id} · chunk=${hit.chunk_index} · score=${score}`;

      const snippet = document.createElement("div");
      snippet.className = "hit-content";
      snippet.textContent = truncate(String(hit.content || ""), 180);

      item.appendChild(meta);
      item.appendChild(snippet);
      hitBox.appendChild(item);
    }

    message.appendChild(hitBox);
  }

  els.messageList.appendChild(message);
  scrollToBottom();
}

function clearConversation() {
  els.messageList.innerHTML = "";
  els.heroTitle.style.display = "block";
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
