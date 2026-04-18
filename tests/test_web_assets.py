import re


def _get_web_app_script(client) -> str:
    response = client.get("/web/app.js")
    assert response.status_code == 200
    return response.text


def _get_web_index(client) -> str:
    response = client.get("/")
    assert response.status_code == 200
    return response.text


def _get_web_styles(client) -> str:
    response = client.get("/web/styles.css")
    assert response.status_code == 200
    return response.text


def test_chat_message_card_exposes_favorite_as_only_capture_action(client) -> None:
    script = _get_web_app_script(client)
    capture_guard = 'if (assistantCaptureContext && assistantCaptureContext.channel !== "action") {'
    copy_action = "copyMessageText(extractCopyText(content, contentParts))"

    capture_start = script.find(capture_guard)
    assert capture_start != -1

    capture_end = script.find(copy_action, capture_start)
    assert capture_end != -1

    capture_body = script[capture_start:capture_end]
    assert "toggleAssistantFavorite(assistantCaptureContext)" in capture_body
    assert "promoteFavoriteToMemory" not in capture_body
    assert "promoteFavoriteToConclusion" not in capture_body
    assert "publishFavoriteToLibrary" not in capture_body


def test_chat_message_capture_loader_only_prefetches_favorites(client) -> None:
    script = _get_web_app_script(client)
    loader_block = re.search(
        r"async function loadMessageCaptures\(\) \{(?P<body>.*?)\n\}",
        script,
        re.DOTALL,
    )
    assert loader_block is not None

    loader_body = loader_block.group("body")
    assert "/favorites/answers?" in loader_body
    assert "/memory/cards?" not in loader_body
    assert "/conclusions?" not in loader_body
    assert "/library/documents?" not in loader_body


def test_favorites_workspace_is_present_in_frontend_shell(client) -> None:
    html = _get_web_index(client)

    assert 'id="favoritesWorkspaceBtn"' in html
    assert 'id="favoritesPanel"' in html
    assert 'id="favoriteList"' in html


def test_homepage_uses_workspace_settings_instead_of_exposing_admin_entry(client) -> None:
    html = _get_web_index(client)

    assert 'id="workspaceSettingsBtn"' in html
    assert 'class="admin-link"' not in html
    assert ">Admin<" not in html


def test_homepage_uses_workspace_rail_and_recall_drawers(client) -> None:
    html = _get_web_index(client)

    assert 'id="workspaceRail"' in html
    assert 'id="railNewChatBtn"' in html
    assert """onclick="document.getElementById('newSessionBtn').click()" """[:-1] in html
    assert 'id="railConversationsBtn" class="rail-btn" type="button" title="Conversations"' in html
    assert 'id="railFilesBtn" class="rail-btn" type="button" title="Files"' in html
    assert 'id="railConversationsBtn" class="rail-btn" type="button" title="Conversations" onclick="' not in html
    assert 'id="railFilesBtn" class="rail-btn" type="button" title="Files" onclick="' not in html
    assert """id="railSettingsBtn" class="rail-btn rail-btn-bottom" type="button" title="Me / Settings" onclick="document.getElementById('workspaceSettingsBtn').click()" """[:-1] in html
    assert 'id="conversationDrawer"' in html
    assert 'id="fileDrawer"' in html
    assert """id="drawerNewChatBtn" class="primary-btn compact-primary-btn" type="button" onclick="document.getElementById('newSessionBtn').click()" """[:-1] in html
    assert 'id="conversationDrawer" class="surface-drawer conversation-drawer hidden" aria-hidden="true"' in html
    assert 'id="fileDrawer" class="surface-drawer file-drawer hidden" aria-hidden="true"' in html


def test_styles_define_workspace_rail_drawers_and_dock(client) -> None:
    css = _get_web_styles(client)
    drawer_list_start = css.find(".surface-panel .history-list,")
    drawer_list_end = css.find(".launch-panel", drawer_list_start)

    assert ".workspace-rail" in css
    assert ".surface-drawer" in css
    assert ".surface-panel" in css
    assert ".composer-dock" in css
    assert ".composer-context-row" in css
    assert ".composer-context-chip" in css
    assert drawer_list_start != -1
    assert drawer_list_end != -1
    drawer_list_block = css[drawer_list_start:drawer_list_end]
    assert ".surface-panel .document-list" in drawer_list_block
    assert "flex: 1 1 auto;" in drawer_list_block
    assert "overflow-y: auto;" in drawer_list_block


def test_styles_define_motion_and_reduced_motion_rules(client) -> None:
    css = _get_web_styles(client)

    assert ".launch-panel" in css
    assert ".workspace-stage-chat" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition:" in css


def test_frontend_binds_rail_drawer_and_settings_controls(client) -> None:
    script = _get_web_app_script(client)

    assert 'els.railNewChatBtn = document.getElementById("railNewChatBtn");' in script
    assert 'els.railSettingsBtn = document.getElementById("railSettingsBtn");' in script
    assert 'els.drawerNewChatBtn = document.getElementById("drawerNewChatBtn");' in script
    assert 'els.composerContextRow = document.getElementById("composerContextRow");' in script

    bind_start = script.find("function bindEvents() {")
    bind_end = script.find("function handleGlobalDocumentClick(event)", bind_start)
    assert bind_start != -1
    assert bind_end != -1
    bind_body = script[bind_start:bind_end]
    assert 'els.railNewChatBtn.addEventListener("click"' in bind_body
    assert 'els.drawerNewChatBtn.addEventListener("click"' in bind_body
    assert 'els.railSettingsBtn.addEventListener("click", openSettingsModal);' in bind_body
    assert "createAndSwitchConversation()" in bind_body


def test_homepage_uses_launch_panel_and_dock_context_row(client) -> None:
    html = _get_web_index(client)

    assert 'id="heroPanel" class="hero-panel launch-panel"' in html
    context_start = html.find('<div id="composerContextRow" class="composer-context-row">')
    assert context_start != -1
    context_end = html.find('<div class="chat-mode-row">', context_start)
    assert context_end != -1
    context_body = html[context_start:context_end]
    assert 'id="composerPresence"' in context_body
    assert 'id="composerScope"' in context_body
    assert 'id="composerSession"' in context_body
    assert 'class="composer-context-row hidden"' not in html
    assert 'class="composer-status-row"' not in html
    assert '<section id="heroPanel" class="hero-panel launch-panel">' in html
    assert '<div class="launch-panel">' not in html


def test_frontend_renders_composer_context_row_and_refresh_helper(client) -> None:
    script = _get_web_app_script(client)

    render_start = script.find("function renderComposerContextRow() {")
    refresh_start = script.find("function refreshComposerChrome() {")
    assert render_start != -1
    assert refresh_start != -1
    refresh_end = script.find("function refreshWorkspaceUi()", refresh_start)
    assert refresh_end != -1

    render_body = script[render_start:refresh_start]
    assert 'if (!els.composerContextRow)' in render_body
    assert "state.chatMode" in render_body
    assert "state.documents.length" in render_body
    assert "state.selectedDocumentIds.length" in render_body
    assert "getReadyDocumentCount()" in render_body

    refresh_body = script[refresh_start:refresh_end]
    assert "renderComposerContextRow();" in refresh_body
    assert "renderAttachmentStrip();" in refresh_body

    set_chat_start = script.find("function setChatMode(mode, { silent = false } = {}) {")
    set_chat_end = script.find("function setWorkspaceStage(stage) {", set_chat_start)
    assert set_chat_start != -1
    assert set_chat_end != -1
    set_chat_body = script[set_chat_start:set_chat_end]
    assert "refreshComposerChrome();" in set_chat_body

    render_docs_start = script.find("function renderDocuments() {")
    render_docs_end = script.find("function renderAttachmentStrip()", render_docs_start)
    assert render_docs_start != -1
    assert render_docs_end != -1
    render_docs_body = script[render_docs_start:render_docs_end]
    assert "refreshComposerChrome();" in render_docs_body

    import_start = script.find("async function importDocumentWithContent({ sourceName, content, contentType }) {")
    import_end = script.find("function upsertDocumentState(doc) {", import_start)
    assert import_start != -1
    assert import_end != -1
    import_body = script[import_start:import_end]
    assert "renderDocuments();" in import_body

    upload_start = script.find("async function uploadDocumentFile(file) {")
    upload_end = script.find("function hasDraggedFiles(event) {", upload_start)
    assert upload_start != -1
    assert upload_end != -1
    upload_body = script[upload_start:upload_end]
    assert "renderDocuments();" in upload_body


def test_homepage_keeps_workspace_switch_visible(client) -> None:
    html = _get_web_index(client)

    assert 'class="workspace-intro hidden"' not in html
    assert 'id="workspaceEyebrow"' in html
    assert 'id="workspaceDescription"' in html
    assert 'id="chatWorkspaceBtn"' in html
    assert 'id="favoritesWorkspaceBtn"' in html


def test_auth_modal_uses_login_and_register_forms(client) -> None:
    html = _get_web_index(client)

    assert 'id="authLoginTab"' in html
    assert 'id="authRegisterTab"' in html
    assert 'id="loginUserIdInput"' in html
    assert 'id="loginPasswordInput"' in html
    assert 'id="registerUserIdInput"' in html
    assert 'id="registerDisplayNameInput"' in html
    assert 'id="registerPasswordInput"' in html
    assert 'id="registerConfirmPasswordInput"' in html
    assert 'id="accountIdInput"' not in html
    assert 'id="accountNameInput"' not in html
    assert 'id="saveAuthBtn"' not in html


def test_settings_modal_exposes_account_controls(client) -> None:
    html = _get_web_index(client)

    assert 'id="switchAccountBtn"' in html
    assert 'id="logoutBtn"' in html
    assert 'id="switchWorkspaceBtn"' not in html


def test_advanced_model_configuration_moves_out_of_main_topbar(client) -> None:
    html = _get_web_index(client)

    assert "工作台设置" in html
    assert "高级设置" in html
    assert "主界面默认隐藏模型与密钥配置" in html
    assert 'for="modelSelect">模型<' not in html
    assert 'for="embeddingSelect">向量模型<' not in html


def test_model_configuration_uses_settings_modals_instead_of_prompt_flows(client) -> None:
    script = _get_web_app_script(client)

    assert "openSettingsModal" in script
    assert "openCustomModelModal" in script
    assert "openCustomEmbeddingModal" in script
    assert 'window.prompt("输入 API Base URL"' not in script
    assert 'window.prompt("输入 API Key")' not in script
    assert 'window.prompt("输入 Embedding API Base URL"' not in script
    assert 'window.prompt("输入 Embedding API Key")' not in script


def test_frontend_bootstrap_uses_auth_session_routes(client) -> None:
    script = _get_web_app_script(client)

    assert "bootstrapAuthSession" in script
    assert "/auth/me" in script
    assert "/auth/login" in script
    assert "/auth/register" in script
    assert "/auth/logout" in script
    assert "/auth/refresh" in script
    assert 'credentials: "same-origin"' in script
    assert "retryOn401" in script


def test_frontend_formats_fastapi_validation_errors_for_auth_forms(client) -> None:
    script = _get_web_app_script(client)

    assert "Array.isArray(data.detail)" in script
    assert "VALIDATION_FIELD_LABELS" in script
    assert "string_too_short" in script
    assert "min_length" in script


def test_auth_forms_validate_password_rules_before_submit(client) -> None:
    script = _get_web_app_script(client)

    assert "password.length < 8" in script
    assert "confirmPassword.length < 8" in script
    assert "password !== confirmPassword" in script


def test_frontend_bootstrap_no_longer_depends_on_team_user_upserts(client) -> None:
    script = _get_web_app_script(client)

    assert "/teams/${encodeURIComponent" not in script
    assert "/users/${encodeURIComponent" not in script


def test_favorite_workflow_supports_toggle_and_secondary_actions(client) -> None:
    script = _get_web_app_script(client)

    assert "/favorites/answers/" in script
    assert 'method: "DELETE"' in script
    assert "loadFavoriteWorkspaceAssets" in script
    assert 'getFavoriteWorkspaceAsset("memoriesByMessageId"' in script
    assert 'getFavoriteWorkspaceAsset("conclusionsByMessageId"' in script
    assert 'getFavoriteWorkspaceAsset("libraryDocsByMessageId"' in script
    assert "/promote-to-memory" in script
    assert "/promote-to-conclusion" in script
    assert "/documents/import" in script


def test_frontend_tracks_workspace_stage_and_active_surface(client) -> None:
    script = _get_web_app_script(client)
    set_stage_start = script.find("function setWorkspaceStage(stage) {")
    set_stage_end = script.find("function syncWorkspaceStage()", set_stage_start)
    set_surface_start = script.find("function setActiveSurface(surface) {")
    stage_sync_start = set_stage_end
    sync_start = script.find("function syncActiveSurface() {")
    sync_end = script.find("function syncWorkspaceView()", sync_start)

    assert 'const WORKSPACE_STAGE_LAUNCH = "launch"' in script
    assert 'const WORKSPACE_STAGE_CHAT = "chat"' in script
    assert 'const ACTIVE_SURFACE_NONE = "none"' in script
    assert 'const ACTIVE_SURFACE_CONVERSATIONS = "conversations"' in script
    assert 'const ACTIVE_SURFACE_FILES = "files"' in script
    assert 'const ACTIVE_SURFACE_SETTINGS = "settings"' in script
    assert "workspaceStage:" in script
    assert "activeSurface:" in script
    assert "function setWorkspaceStage(stage)" in script
    assert "function setActiveSurface(surface)" in script
    assert "function syncWorkspaceStage()" in script
    assert "function syncActiveSurface()" in script
    assert set_stage_start != -1
    assert set_stage_end != -1
    assert set_surface_start != -1
    assert sync_start != -1
    assert sync_end != -1
    set_stage_body = script[set_stage_start:set_stage_end]
    stage_sync_body = script[stage_sync_start:sync_start]
    set_surface_body = script[set_surface_start:sync_start]
    assert "syncWorkspaceStage();" in set_stage_body
    assert 'els.shell.classList.toggle("workspace-stage-launch", !isChatStage)' in stage_sync_body
    assert 'els.shell.classList.toggle("workspace-stage-chat", isChatStage)' in stage_sync_body
    assert "syncActiveSurface();" in set_surface_body
    sync_body = script[sync_start:sync_end]
    assert 'els.conversationDrawer.classList.toggle("hidden", !isConversationSurface)' in sync_body
    assert 'els.conversationDrawer.setAttribute("aria-hidden", String(!isConversationSurface))' in sync_body
    assert 'els.fileDrawer.classList.toggle("hidden", !isFileSurface)' in sync_body
    assert 'els.fileDrawer.setAttribute("aria-hidden", String(!isFileSurface))' in sync_body


def test_frontend_workspace_stage_rail_toggles_use_active_surface_state(client) -> None:
    script = _get_web_app_script(client)

    conv_start = script.find("if (els.railConversationsBtn) {")
    conv_end = script.find("if (els.railFilesBtn) {", conv_start)
    assert conv_start != -1
    assert conv_end != -1
    conv_body = script[conv_start:conv_end]
    assert "state.activeSurface === ACTIVE_SURFACE_CONVERSATIONS" in conv_body
    assert "? ACTIVE_SURFACE_NONE" in conv_body
    assert ": ACTIVE_SURFACE_CONVERSATIONS" in conv_body
    assert 'classList.contains("hidden")' not in conv_body

    file_start = conv_end
    file_end = script.find("els.newSessionBtn.addEventListener", file_start)
    assert file_end != -1
    file_body = script[file_start:file_end]
    assert "state.activeSurface === ACTIVE_SURFACE_FILES" in file_body
    assert "? ACTIVE_SURFACE_NONE" in file_body
    assert ": ACTIVE_SURFACE_FILES" in file_body
    assert 'classList.contains("hidden")' not in file_body


def test_frontend_workspace_stage_auth_success_resets_to_launch_with_no_surface(client) -> None:
    script = _get_web_app_script(client)

    auth_start = script.find("async function finalizeAuthSuccess(session, toastMessage) {")
    auth_end = script.find("async function bootstrapAuthSession()", auth_start)
    assert auth_start != -1
    assert auth_end != -1
    auth_body = script[auth_start:auth_end]
    assert "setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);" in auth_body
    assert "setActiveSurface(ACTIVE_SURFACE_NONE);" in auth_body
    assert "setRequiresFreshConversation(true);" in auth_body
    assert "loadAllData();" not in auth_body
    assert "loadConversations()" in auth_body
    assert "els.messageInput.focus();" in auth_body

    send_start = script.find("async function handleSend() {")
    send_end = script.find("function getExplicitSelectedDocumentIds()", send_start)
    assert send_start != -1
    assert send_end != -1
    send_body = script[send_start:send_end]
    assert "setWorkspaceStage(WORKSPACE_STAGE_CHAT);" in send_body
    assert "setActiveSurface(ACTIVE_SURFACE_NONE);" in send_body


def test_frontend_new_chat_returns_to_launch_and_focuses_composer(client) -> None:
    script = _get_web_app_script(client)

    create_start = script.find("async function createAndSwitchConversation({")
    create_end = script.find("async function switchConversation(conversationId) {", create_start)
    assert create_start != -1
    assert create_end != -1
    create_body = script[create_start:create_end]
    assert "restoreLaunch = true" in create_body
    assert "closeSurface = true" in create_body
    assert "focusComposer = true" in create_body
    assert "if (restoreLaunch) {" in create_body
    assert "setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);" in create_body
    assert "if (closeSurface) {" in create_body
    assert "setActiveSurface(ACTIVE_SURFACE_NONE);" in create_body
    assert "if (focusComposer && els.messageInput) {" in create_body
    assert "els.messageInput.focus();" in create_body


def test_frontend_requires_a_fresh_conversation_after_auth_success(client) -> None:
    script = _get_web_app_script(client)

    assert "requiresFreshConversation:" in script
    assert "function setRequiresFreshConversation(required)" in script

    create_start = script.find("async function createAndSwitchConversation({")
    create_end = script.find("async function switchConversation(conversationId) {", create_start)
    assert create_start != -1
    assert create_end != -1
    create_body = script[create_start:create_end]
    assert "setRequiresFreshConversation(false);" in create_body
    assert "await loadConversations();" in create_body
    assert 'showToast("已创建新会话");' in create_body

    switch_start = create_end
    switch_end = script.find("async function renameConversation(conversation)", switch_start)
    assert switch_end != -1
    switch_body = script[switch_start:switch_end]
    assert "setRequiresFreshConversation(false);" in switch_body

    ready_start = script.find("async function ensureConversationReady() {")
    ready_end = script.find("function syncSendButtonState()", ready_start)
    assert ready_start != -1
    assert ready_end != -1
    ready_body = script[ready_start:ready_end]
    assert "if (state.requiresFreshConversation) {" in ready_body
    assert "await createAndSwitchConversation({" in ready_body
    assert "silent: true," in ready_body
    assert "restoreLaunch: false," in ready_body
    assert "closeSurface: false," in ready_body
    assert "focusComposer: false," in ready_body
    assert "await ensureActiveConversation();" in ready_body


def test_frontend_persists_pending_fresh_conversation_across_reload(client) -> None:
    script = _get_web_app_script(client)

    assert 'pendingFreshConversationPrefix: "caibao.pendingFreshConversation"' in script
    assert "function freshConversationStorageKey()" in script
    assert "function loadFreshConversationRequirement()" in script
    assert "function persistFreshConversationRequirement()" in script

    apply_start = script.find("function applyAuthSession(session, { resetConversation = false } = {}) {")
    apply_end = script.find("function resetAuthenticatedWorkspace()", apply_start)
    assert apply_start != -1
    assert apply_end != -1
    apply_body = script[apply_start:apply_end]
    assert "state.requiresFreshConversation = loadFreshConversationRequirement();" in apply_body

    load_all_start = script.find("async function loadAllData() {")
    load_all_end = script.find("async function loadModelConfigs()", load_all_start)
    assert load_all_start != -1
    assert load_all_end != -1
    load_all_body = script[load_all_start:load_all_end]
    assert "if (state.requiresFreshConversation) {" in load_all_body
    assert "setWorkspaceStage(WORKSPACE_STAGE_LAUNCH);" in load_all_body
    assert "setActiveSurface(ACTIVE_SURFACE_NONE);" in load_all_body
    assert "clearConversation();" in load_all_body
    assert "await ensureActiveConversation();" in load_all_body

    signed_out_start = script.find("function handleSignedOutState({ openAuthDialog = false } = {}) {")
    signed_out_end = script.find("async function finalizeAuthSuccess(session, toastMessage) {", signed_out_start)
    assert signed_out_start != -1
    assert signed_out_end != -1
    signed_out_body = script[signed_out_start:signed_out_end]
    assert "setRequiresFreshConversation(false);" in signed_out_body


def test_homepage_keeps_preview_auth_and_settings_surfaces_while_using_recall_shell(client) -> None:
    html = _get_web_index(client)
    script = _get_web_app_script(client)

    assert 'id="previewDrawer"' in html
    assert 'id="imageViewer"' in html
    assert 'id="authModal"' in html
    assert 'id="settingsModal"' in html
    assert "openDocumentPreview(doc)" in script
    assert "openSettingsModal()" in script
    assert "openAuthModal(AUTH_MODE_LOGIN)" in script
    assert 'showToast("当前还没有可用资料，先上传并等待文件处理完成。", true);' in script
    assert "doc.error_message || doc.error_code" in script


def test_frontend_supports_escape_to_close_recall_surfaces(client) -> None:
    script = _get_web_app_script(client)

    assert 'if (event.key === "Escape") {' in script
    assert "setActiveSurface(ACTIVE_SURFACE_NONE)" in script
