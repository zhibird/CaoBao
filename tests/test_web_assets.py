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
