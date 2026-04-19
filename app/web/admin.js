const API_PREFIX = "/api/v1";
const STORAGE_KEYS = {
  adminToken: "caibao.admin.token",
};

const state = {
  token: "",
  session: null,
  dashboard: null,
  teams: [],
  users: [],
  conversations: [],
  documents: [],
  filters: {
    usersTeamId: "",
    conversationsTeamId: "",
    conversationsUserId: "",
    documentsTeamId: "",
    documentsUserId: "",
    documentsConversationId: "",
  },
};

const els = {};
let toastTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindEvents();
  hydrateToken();
  updateAuthUi();
  if (state.token) {
    loginAndLoad().catch((error) => {
      resetAuth();
      showToast(error.message, true);
    });
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDocModal();
  }
});

function bindElements() {
  els.adminTokenInput = document.getElementById("adminTokenInput");
  els.adminLoginBtn = document.getElementById("adminLoginBtn");
  els.adminLogoutBtn = document.getElementById("adminLogoutBtn");
  els.authHint = document.getElementById("authHint");
  els.adminMain = document.getElementById("adminMain");

  els.statTeams = document.getElementById("statTeams");
  els.statUsers = document.getElementById("statUsers");
  els.statConversations = document.getElementById("statConversations");
  els.statDocuments = document.getElementById("statDocuments");
  els.statMessages = document.getElementById("statMessages");

  els.refreshTeamsBtn = document.getElementById("refreshTeamsBtn");
  els.refreshUsersBtn = document.getElementById("refreshUsersBtn");
  els.refreshConversationsBtn = document.getElementById("refreshConversationsBtn");
  els.refreshDocumentsBtn = document.getElementById("refreshDocumentsBtn");

  els.usersTeamFilter = document.getElementById("usersTeamFilter");
  els.conversationsTeamFilter = document.getElementById("conversationsTeamFilter");
  els.conversationsUserFilter = document.getElementById("conversationsUserFilter");
  els.documentsTeamFilter = document.getElementById("documentsTeamFilter");
  els.documentsUserFilter = document.getElementById("documentsUserFilter");
  els.documentsConversationFilter = document.getElementById("documentsConversationFilter");

  els.teamsTableBody = document.getElementById("teamsTableBody");
  els.usersTableBody = document.getElementById("usersTableBody");
  els.conversationsTableBody = document.getElementById("conversationsTableBody");
  els.documentsTableBody = document.getElementById("documentsTableBody");

  els.docModal = document.getElementById("docModal");
  els.docBackdrop = document.getElementById("docBackdrop");
  els.closeDocModalBtn = document.getElementById("closeDocModalBtn");
  els.docTitle = document.getElementById("docTitle");
  els.docMeta = document.getElementById("docMeta");
  els.docContent = document.getElementById("docContent");
  els.adminToast = document.getElementById("adminToast");
}

function bindEvents() {
  els.adminLoginBtn.addEventListener("click", () => {
    loginFromInput().catch((error) => showToast(error.message, true));
  });
  els.adminLogoutBtn.addEventListener("click", () => {
    resetAuth();
    showToast("已退出管理员账号");
  });
  els.refreshTeamsBtn.addEventListener("click", () => loadTeams().catch((error) => showToast(error.message, true)));
  els.refreshUsersBtn.addEventListener("click", () => loadUsers().catch((error) => showToast(error.message, true)));
  els.refreshConversationsBtn.addEventListener("click", () => {
    loadConversations().catch((error) => showToast(error.message, true));
  });
  els.refreshDocumentsBtn.addEventListener("click", () => {
    syncDocumentConversationFilter();
    loadDocuments().catch((error) => showToast(error.message, true));
  });

  els.usersTeamFilter.addEventListener("change", () => {
    state.filters.usersTeamId = els.usersTeamFilter.value;
    renderUsers();
  });
  els.conversationsTeamFilter.addEventListener("change", () => {
    state.filters.conversationsTeamId = els.conversationsTeamFilter.value;
    ensureConversationUserFilterIsValid();
    renderConversationUserFilterOptions();
    loadConversations().catch((error) => showToast(error.message, true));
  });
  els.conversationsUserFilter.addEventListener("change", () => {
    state.filters.conversationsUserId = els.conversationsUserFilter.value;
    loadConversations().catch((error) => showToast(error.message, true));
  });
  els.documentsTeamFilter.addEventListener("change", () => {
    state.filters.documentsTeamId = els.documentsTeamFilter.value;
    ensureDocumentUserFilterIsValid();
    renderDocumentUserFilterOptions();
    loadDocuments().catch((error) => showToast(error.message, true));
  });
  els.documentsUserFilter.addEventListener("change", () => {
    state.filters.documentsUserId = els.documentsUserFilter.value;
    loadDocuments().catch((error) => showToast(error.message, true));
  });
  els.documentsConversationFilter.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      syncDocumentConversationFilter();
      loadDocuments().catch((error) => showToast(error.message, true));
    }
  });
  els.documentsConversationFilter.addEventListener("blur", syncDocumentConversationFilter);

  els.docBackdrop.addEventListener("click", closeDocModal);
  els.closeDocModalBtn.addEventListener("click", closeDocModal);
}

function hydrateToken() {
  state.token = localStorage.getItem(STORAGE_KEYS.adminToken) || "";
  els.adminTokenInput.value = state.token;
}

function persistToken() {
  if (state.token) {
    localStorage.setItem(STORAGE_KEYS.adminToken, state.token);
  } else {
    localStorage.removeItem(STORAGE_KEYS.adminToken);
  }
}

async function loginFromInput() {
  const token = els.adminTokenInput.value.trim();
  if (!token) {
    showToast("请输入管理员 token", true);
    return;
  }

  state.token = token;
  persistToken();
  await loginAndLoad();
}

async function loginAndLoad() {
  setButtonLoading(els.adminLoginBtn, true, "登录中...");
  try {
    await loadSession();
    await loadAllData();
    els.adminMain.classList.remove("hidden");
    updateAuthUi();
  } catch (error) {
    if (String(error.message || "").toLowerCase().includes("token")) {
      resetAuth(false);
    }
    throw error;
  } finally {
    setButtonLoading(els.adminLoginBtn, false, "登录管理员");
  }
}

function resetAuth(showMessage = false) {
  state.token = "";
  state.session = null;
  state.dashboard = null;
  state.teams = [];
  state.users = [];
  state.conversations = [];
  state.documents = [];
  persistToken();
  els.adminTokenInput.value = "";
  els.adminMain.classList.add("hidden");
  renderAllTables();
  updateStats();
  updateAuthUi();
  if (showMessage) {
    showToast("已清理登录态");
  }
}

function updateAuthUi() {
  if (state.session) {
    els.authHint.textContent = `已登录：${state.session.display_name} (${state.session.account_id})`;
  } else {
    els.authHint.textContent = "未登录";
  }
}

async function loadAllData() {
  await loadDashboard();
  await loadTeams();
  await loadUsers();
  await loadConversations();
  await loadDocuments();
}

async function loadSession() {
  const data = await apiRequest("/admin/session");
  state.session = data;
  updateAuthUi();
}

async function loadDashboard() {
  state.dashboard = await apiRequest("/admin/dashboard");
  updateStats();
}

function updateStats() {
  const dashboard = state.dashboard || {};
  els.statTeams.textContent = String(dashboard.teams || 0);
  els.statUsers.textContent = String(dashboard.users || 0);
  els.statConversations.textContent = String(dashboard.conversations || 0);
  els.statDocuments.textContent = String(dashboard.documents || 0);
  els.statMessages.textContent = String(dashboard.messages || 0);
}

async function loadTeams() {
  state.teams = await apiRequest("/admin/teams?limit=500");
  renderTeamFilterOptions();
  renderTeams();
}

async function loadUsers() {
  state.users = await apiRequest("/admin/users?limit=800");
  renderConversationUserFilterOptions();
  renderDocumentUserFilterOptions();
  renderUsers();
}

async function loadConversations() {
  const query = new URLSearchParams({ limit: "500" });
  if (state.filters.conversationsTeamId) {
    query.set("team_id", state.filters.conversationsTeamId);
  }
  if (state.filters.conversationsUserId) {
    query.set("user_id", state.filters.conversationsUserId);
  }
  state.conversations = await apiRequest(`/admin/conversations?${query.toString()}`);
  renderConversations();
}

async function loadDocuments() {
  const query = new URLSearchParams({ limit: "500" });
  if (state.filters.documentsTeamId) {
    query.set("team_id", state.filters.documentsTeamId);
  }
  if (state.filters.documentsUserId) {
    query.set("user_id", state.filters.documentsUserId);
  }
  if (state.filters.documentsConversationId) {
    query.set("conversation_id", state.filters.documentsConversationId);
  }
  state.documents = await apiRequest(`/admin/documents?${query.toString()}`);
  renderDocuments();
}

function renderAllTables() {
  renderTeams();
  renderUsers();
  renderConversations();
  renderDocuments();
}

function renderTeamFilterOptions() {
  const options = [{ value: "", label: "全部" }];
  for (const team of state.teams) {
    options.push({ value: team.team_id, label: `${team.team_id} · ${team.name}` });
  }
  setSelectOptions(els.usersTeamFilter, options, state.filters.usersTeamId);
  setSelectOptions(els.conversationsTeamFilter, options, state.filters.conversationsTeamId);
  setSelectOptions(els.documentsTeamFilter, options, state.filters.documentsTeamId);
  state.filters.usersTeamId = els.usersTeamFilter.value;
  state.filters.conversationsTeamId = els.conversationsTeamFilter.value;
  state.filters.documentsTeamId = els.documentsTeamFilter.value;
}

function renderConversationUserFilterOptions() {
  const teamId = state.filters.conversationsTeamId;
  const users = teamId ? state.users.filter((item) => item.team_id === teamId) : state.users;
  const options = [{ value: "", label: "全部" }];
  for (const user of users) {
    options.push({ value: user.user_id, label: `${user.user_id} · ${user.display_name}` });
  }
  setSelectOptions(els.conversationsUserFilter, options, state.filters.conversationsUserId);
  state.filters.conversationsUserId = els.conversationsUserFilter.value;
}

function renderDocumentUserFilterOptions() {
  const teamId = state.filters.documentsTeamId;
  const users = teamId ? state.users.filter((item) => item.team_id === teamId) : state.users;
  const options = [{ value: "", label: "全部" }];
  for (const user of users) {
    options.push({ value: user.user_id, label: `${user.user_id} · ${user.display_name}` });
  }
  setSelectOptions(els.documentsUserFilter, options, state.filters.documentsUserId);
  state.filters.documentsUserId = els.documentsUserFilter.value;
}

function ensureConversationUserFilterIsValid() {
  if (!state.filters.conversationsUserId) {
    return;
  }
  const exists = state.users.some((item) => {
    if (item.user_id !== state.filters.conversationsUserId) {
      return false;
    }
    if (!state.filters.conversationsTeamId) {
      return true;
    }
    return item.team_id === state.filters.conversationsTeamId;
  });
  if (!exists) {
    state.filters.conversationsUserId = "";
  }
}

function ensureDocumentUserFilterIsValid() {
  if (!state.filters.documentsUserId) {
    return;
  }
  const exists = state.users.some((item) => {
    if (item.user_id !== state.filters.documentsUserId) {
      return false;
    }
    if (!state.filters.documentsTeamId) {
      return true;
    }
    return item.team_id === state.filters.documentsTeamId;
  });
  if (!exists) {
    state.filters.documentsUserId = "";
  }
}

function renderTeams() {
  els.teamsTableBody.innerHTML = "";
  if (!state.teams.length) {
    appendEmptyRow(els.teamsTableBody, 7, "暂无团队");
    return;
  }

  for (const item of state.teams) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(item.team_id)}</td>
      <td>${escapeHtml(item.name)}</td>
      <td>${item.user_count}</td>
      <td>${item.conversation_count}</td>
      <td>${item.document_count}</td>
      <td>${formatTime(item.created_at)}</td>
      <td></td>
    `;
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(
      createActionButton("删除", "danger", () => deleteTeam(item)),
    );
    tr.lastElementChild.appendChild(actions);
    els.teamsTableBody.appendChild(tr);
  }
}

function renderUsers() {
  els.usersTableBody.innerHTML = "";
  const teamId = state.filters.usersTeamId;
  const users = teamId ? state.users.filter((item) => item.team_id === teamId) : state.users;
  if (!users.length) {
    appendEmptyRow(els.usersTableBody, 8, "暂无账户");
    return;
  }

  for (const item of users) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(item.user_id)}</td>
      <td>${escapeHtml(item.team_id)}</td>
      <td>${escapeHtml(item.display_name)}</td>
      <td>${escapeHtml(item.role)}</td>
      <td>${item.conversation_count}</td>
      <td>${item.document_count}</td>
      <td>${formatTime(item.created_at)}</td>
      <td></td>
    `;
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(
      createActionButton("改角色", "", () => updateUserRole(item)),
      createActionButton("删除", "danger", () => deleteUser(item)),
    );
    tr.lastElementChild.appendChild(actions);
    els.usersTableBody.appendChild(tr);
  }
}

function renderConversations() {
  els.conversationsTableBody.innerHTML = "";
  if (!state.conversations.length) {
    appendEmptyRow(els.conversationsTableBody, 8, "暂无会话");
    return;
  }

  for (const item of state.conversations) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(item.conversation_id)}</td>
      <td>${escapeHtml(item.title)}</td>
      <td>${escapeHtml(item.team_id)}</td>
      <td>${escapeHtml(item.user_id)}</td>
      <td>${item.message_count}</td>
      <td>${item.document_count}</td>
      <td>${formatTime(item.created_at)}</td>
      <td></td>
    `;
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(createActionButton("删除", "danger", () => deleteConversation(item)));
    tr.lastElementChild.appendChild(actions);
    els.conversationsTableBody.appendChild(tr);
  }
}

function renderDocuments() {
  els.documentsTableBody.innerHTML = "";
  if (!state.documents.length) {
    appendEmptyRow(els.documentsTableBody, 9, "暂无文件");
    return;
  }

  for (const item of state.documents) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(item.document_id)}</td>
      <td>${escapeHtml(item.source_name)}</td>
      <td>${escapeHtml(item.team_id)}</td>
      <td>${escapeHtml(item.conversation_id || "-")}</td>
      <td>${escapeHtml(item.status)}</td>
      <td>${item.char_count}</td>
      <td>${escapeHtml(item.content_preview)}</td>
      <td>${formatTime(item.created_at)}</td>
      <td></td>
    `;
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(
      createActionButton("查看", "", () => openDocument(item.document_id)),
      createActionButton("删除", "danger", () => deleteDocument(item)),
    );
    tr.lastElementChild.appendChild(actions);
    els.documentsTableBody.appendChild(tr);
  }
}

async function deleteTeam(team) {
  const ok = window.confirm(`确认删除团队 ${team.team_id}？该团队下用户、会话、文件会一并删除。`);
  if (!ok) {
    return;
  }
  await apiRequest(`/admin/teams/${encodeURIComponent(team.team_id)}`, { method: "DELETE" });
  await loadAllData();
  showToast(`已删除团队 ${team.team_id}`);
}

async function updateUserRole(user) {
  const nextRole = window.prompt(`请输入 ${user.user_id} 的新角色`, user.role || "member");
  if (nextRole === null) {
    return;
  }
  const role = nextRole.trim();
  if (!role) {
    showToast("角色不能为空", true);
    return;
  }
  await apiRequest(`/admin/users/${encodeURIComponent(user.user_id)}/role`, {
    method: "PATCH",
    body: { role },
  });
  await Promise.all([loadUsers(), loadDashboard()]);
  showToast(`已更新用户 ${user.user_id} 的角色为 ${role}`);
}

async function deleteUser(user) {
  const ok = window.confirm(`确认删除用户 ${user.user_id}？该用户的会话和文件会被删除。`);
  if (!ok) {
    return;
  }
  await apiRequest(`/admin/users/${encodeURIComponent(user.user_id)}`, { method: "DELETE" });
  await loadAllData();
  showToast(`已删除用户 ${user.user_id}`);
}

async function deleteConversation(item) {
  const ok = window.confirm(`确认删除会话 ${item.conversation_id}？会话下文件会一并删除。`);
  if (!ok) {
    return;
  }
  await apiRequest(`/admin/conversations/${encodeURIComponent(item.conversation_id)}`, { method: "DELETE" });
  await Promise.all([loadDashboard(), loadConversations(), loadDocuments()]);
  showToast("已删除会话");
}

async function openDocument(documentId) {
  const detail = await apiRequest(`/admin/documents/${encodeURIComponent(documentId)}`);
  els.docTitle.textContent = `${detail.source_name} (${detail.document_id})`;
  els.docMeta.textContent = `team=${detail.team_id} | conversation=${detail.conversation_id || "-"} | chars=${detail.char_count}`;
  els.docContent.textContent = detail.content || "";
  els.docModal.classList.remove("hidden");
  els.docModal.setAttribute("aria-hidden", "false");
}

function closeDocModal() {
  els.docModal.classList.add("hidden");
  els.docModal.setAttribute("aria-hidden", "true");
}

async function deleteDocument(item) {
  const ok = window.confirm(`确认删除文件 ${item.source_name} (${item.document_id})？`);
  if (!ok) {
    return;
  }
  await apiRequest(`/admin/documents/${encodeURIComponent(item.document_id)}`, { method: "DELETE" });
  await Promise.all([loadDashboard(), loadDocuments()]);
  showToast(`已删除文件 ${item.source_name}`);
}

function syncDocumentConversationFilter() {
  state.filters.documentsConversationId = els.documentsConversationFilter.value.trim();
}

function setSelectOptions(selectEl, options, selectedValue) {
  selectEl.innerHTML = "";
  for (const optionData of options) {
    const option = document.createElement("option");
    option.value = optionData.value;
    option.textContent = optionData.label;
    selectEl.appendChild(option);
  }
  selectEl.value = options.some((item) => item.value === selectedValue) ? selectedValue : "";
}

function appendEmptyRow(tbody, colSpan, text) {
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = colSpan;
  td.textContent = text;
  td.style.color = "#5a6b7f";
  tr.appendChild(td);
  tbody.appendChild(tr);
}

function createActionButton(text, extraClass, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `action-btn${extraClass ? ` ${extraClass}` : ""}`;
  button.textContent = text;
  button.addEventListener("click", () => {
    onClick().catch((error) => showToast(error.message, true));
  });
  return button;
}

function formatTime(iso) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.valueOf())) {
    return "--";
  }
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  const hh = String(dt.getHours()).padStart(2, "0");
  const mm = String(dt.getMinutes()).padStart(2, "0");
  return `${m}-${d} ${hh}:${mm}`;
}

function escapeHtml(raw) {
  return String(raw ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function apiRequest(path, options = {}) {
  const requestOptions = {
    method: options.method || "GET",
    headers: {
      Accept: "application/json",
      ...(state.token ? { "X-Dev-Admin-Token": state.token } : {}),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  };

  const response = await fetch(`${API_PREFIX}${path}`, requestOptions);
  const raw = await response.text();
  let data;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
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
  els.adminToast.textContent = message;
  els.adminToast.classList.remove("hidden", "error");
  if (isError) {
    els.adminToast.classList.add("error");
  }
  toastTimer = setTimeout(() => {
    els.adminToast.classList.add("hidden");
  }, 2600);
}
