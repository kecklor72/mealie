import os
import time

from fastapi.testclient import TestClient

from mealie.core.config import get_app_dirs
from tests import data as test_data
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


# ----- background images


def _upload(api_client: TestClient, user: TestUser, data: bytes, name: str = "bg.jpg"):
    return api_client.post(api_routes.users_self_themes_images, files={"image": (name, data)}, headers=user.token)


def test_upload_and_get_theme_image(api_client: TestClient, unique_user: TestUser):
    response = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes())
    assert response.status_code == 201
    data = response.json()
    assert len(data["id"]) == 32
    assert data["url"] == f"/api/users/self/themes/images/{data['id']}"

    response = api_client.get(data["url"], headers=unique_user.token)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/webp"


def test_theme_images_are_private(api_client: TestClient, unique_user: TestUser, g2_user: TestUser):
    image_id = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes()).json()["id"]
    url = api_routes.users_self_themes_images_image_id(image_id)

    assert api_client.get(url).status_code == 401
    assert api_client.get(url, headers=g2_user.token).status_code == 404


def test_upload_rejects_non_images(api_client: TestClient, unique_user: TestUser):
    response = _upload(api_client, unique_user, b"<svg onload=alert(1)>", "evil.svg")
    assert response.status_code == 400


def test_invalid_image_ids(api_client: TestClient, unique_user: TestUser):
    assert api_client.get(
        api_routes.users_self_themes_images_image_id("../../etc"), headers=unique_user.token
    ).status_code in (404, 422)
    payload = {"themes": [_theme(backgroundImage="../../secret")]}
    response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
    assert response.status_code == 422


def test_save_theme_with_images(api_client: TestClient, unique_user: TestUser):
    bg = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes()).json()["id"]
    side = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes()).json()["id"]
    payload = {
        "activeThemeId": "ocean",
        "themes": [
            _theme(backgroundImage=bg, sidebarImage=side, backgroundDim=0.5, panelOpacity=0.6, cardOpacity=0.85)
        ],
    }
    response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
    assert response.status_code == 200
    theme = response.json()["themes"][0]
    assert theme["backgroundImage"] == bg
    assert theme["sidebarImage"] == side
    assert theme["panelOpacity"] == 0.6

    bad = {"themes": [_theme(backgroundDim=2)]}
    assert api_client.put(api_routes.users_self_themes, json=bad, headers=unique_user.token).status_code == 422


def test_delete_theme_image(api_client: TestClient, unique_user: TestUser):
    image_id = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes()).json()["id"]
    url = api_routes.users_self_themes_images_image_id(image_id)
    assert api_client.delete(url, headers=unique_user.token).status_code == 204
    assert api_client.get(url, headers=unique_user.token).status_code == 404


def test_unused_images_cleaned_up_after_grace_period(api_client: TestClient, unique_user: TestUser):
    image_id = _upload(api_client, unique_user, test_data.images_test_image_1.read_bytes()).json()["id"]
    path = get_app_dirs().DATA_DIR / "user-themes" / "images" / str(unique_user.user_id) / f"{image_id}.webp"
    assert path.is_file()

    # recently uploaded unused images survive a save
    api_client.put(api_routes.users_self_themes, json={"themes": []}, headers=unique_user.token)
    assert path.is_file()

    # ...but are removed once they are old
    old = time.time() - 2 * 24 * 60 * 60
    os.utime(path, (old, old))
    api_client.put(api_routes.users_self_themes, json={"themes": []}, headers=unique_user.token)
    assert not path.is_file()
