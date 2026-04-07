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
    capture_block = re.search(
        r'if \(assistantCaptureContext && assistantCaptureContext\.channel !== "action"\) \{(?P<body>.*?)\n\s*\}\n\n\s*actionRail\.appendChild\(createMessageActionButton\(',
        script,
        re.DOTALL,
    )
    assert capture_block is not None

    capture_body = capture_block.group("body")
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
