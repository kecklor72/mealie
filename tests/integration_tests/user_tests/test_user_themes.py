from fastapi.testclient import TestClient

from mealie.core.config import get_app_dirs
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser


def _theme(theme_id: str = "ocean", **overrides) -> dict:
    theme = {
        "id": theme_id,
        "name": "Ocean",
        "light": {"primary": "#0077B6", "accent": "#00B4D8", "background": "#F1FAFF"},
        "dark": {"primary": "#48CAE4", "surface": "#10202A"},
        "fontBody": "Inter",
        "fontHeading": "Playfair Display",
        "customCss": ".v-card { border-radius: 16px; }",
    }
    theme.update(overrides)
    return theme


def test_get_theme_settings_default(api_client: TestClient, unique_user: TestUser):
    response = api_client.get(api_routes.users_self_themes, headers=unique_user.token)
    assert response.status_code == 200
    assert response.json() == {"activeThemeId": None, "themes": []}


def test_requires_auth(api_client: TestClient):
    assert api_client.get(api_routes.users_self_themes).status_code == 401
    assert api_client.put(api_routes.users_self_themes, json={}).status_code == 401


def test_save_and_get_theme_settings(api_client: TestClient, unique_user: TestUser):
    payload = {"activeThemeId": "ocean", "themes": [_theme()]}
    response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_themes, headers=unique_user.token)
    assert response.status_code == 200
    data = response.json()
    assert data["activeThemeId"] == "ocean"
    theme = data["themes"][0]
    assert theme["light"]["primary"] == "#0077B6"
    assert theme["light"]["error"] == "#EF5350"  # default filled in
    assert theme["dark"]["surface"] == "#10202A"
    assert theme["fontHeading"] == "Playfair Display"
    assert theme["customCss"] == ".v-card { border-radius: 16px; }"

    # theme files must not be inside the publicly served user media directory
    theme_file = get_app_dirs().DATA_DIR / "user-themes" / f"{unique_user.user_id}.json"
    assert theme_file.is_file()


def test_themes_are_per_user(api_client: TestClient, unique_user: TestUser, g2_user: TestUser):
    payload = {"activeThemeId": "ocean", "themes": [_theme()]}
    api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)

    response = api_client.get(api_routes.users_self_themes, headers=g2_user.token)
    assert response.json()["themes"] == []


def test_reset_theme_settings(api_client: TestClient, unique_user: TestUser):
    payload = {"activeThemeId": "ocean", "themes": [_theme()]}
    api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)

    response = api_client.delete(api_routes.users_self_themes, headers=unique_user.token)
    assert response.status_code == 200

    response = api_client.get(api_routes.users_self_themes, headers=unique_user.token)
    assert response.json() == {"activeThemeId": None, "themes": []}


def test_unknown_active_theme_falls_back_to_default(api_client: TestClient, unique_user: TestUser):
    payload = {"activeThemeId": "missing", "themes": [_theme()]}
    response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
    assert response.status_code == 200
    assert response.json()["activeThemeId"] is None


def test_invalid_values_rejected(api_client: TestClient, unique_user: TestUser):
    bad_payloads = [
        {"themes": [_theme(light={"primary": "red"})]},
        {"themes": [_theme(light={"primary": "#12345"})]},
        {"themes": [_theme(fontBody="Inter'); } body { background: url(evil")]},
        {"themes": [_theme(id="../../etc")]},
        {"themes": [_theme(name="")]},
        {"themes": [_theme(), _theme()]},  # duplicate ids
        {"themes": [_theme(customCss="a" * 50_001)]},
        {"themes": [_theme(theme_id=f"t{i}") for i in range(51)]},
    ]

    for payload in bad_payloads:
        response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
        assert response.status_code == 422, payload
