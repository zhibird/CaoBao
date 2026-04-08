import re


def _get_web_app_script(client) -> str:
    response = client.get("/web/app.js")
    assert response.status_code == 200
    return response.text


def _get_web_index(client) -> str:
    response = client.get("/")
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


def test_workspace_modal_uses_product_language_instead_of_account_fields(client) -> None:
    html = _get_web_index(client)

    assert "进入 / 切换工作台" in html
    assert 'for="accountIdInput">工作台 ID<' in html
    assert 'for="accountNameInput">工作台名称<' in html
    assert "系统会按这个工作台隔离会话、资料和偏好设置。" in html
    assert "account_id" not in html
    assert "account_name" not in html
    assert "登录 / 切换账户" not in html


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


def test_workspace_bootstrap_uses_idempotent_ensure_routes(client) -> None:
    script = _get_web_app_script(client)

    ensure_team_block = re.search(r"async function ensureTeam\(.*?\n\}", script, re.DOTALL)
    assert ensure_team_block is not None
    assert 'method: "PUT"' in ensure_team_block.group(0)
    assert "/teams/${encodeURIComponent(teamId)}" in ensure_team_block.group(0)

    ensure_user_block = re.search(r"async function ensureUser\(.*?\n\}", script, re.DOTALL)
    assert ensure_user_block is not None
    assert 'method: "PUT"' in ensure_user_block.group(0)
    assert "/users/${encodeURIComponent(userId)}" in ensure_user_block.group(0)

    assert "already exists" not in script


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
