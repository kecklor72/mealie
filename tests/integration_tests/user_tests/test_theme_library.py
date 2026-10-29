import io
import json
import shutil
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from mealie.core.config import get_app_dirs
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser

BUILTIN_SLUGS = {"halloween", "haunted-halloween", "thanksgiving", "christmas", "fourth-of-july"}

LIBRARY = "/api/themes/library"
ADMIN_LIBRARY = "/api/admin/themes/library"


def _png(color=(200, 80, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), color).save(buf, "PNG")
    return buf.getvalue()


def _zip(files: dict[str, bytes | str | dict]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            if isinstance(data, dict):
                data = json.dumps(data)
            zf.writestr(name, data)
    return buf.getvalue()


def _upload(api_client: TestClient, user: TestUser, data: bytes):
    return api_client.post(ADMIN_LIBRARY, files={"archive": ("pack.zip", data)}, headers=user.token)


@pytest.fixture(autouse=True)
def clean_library():
    yield
    base = get_app_dirs().DATA_DIR / "user-themes"
    shutil.rmtree(base / "library", ignore_errors=True)
    (base / "library.json").unlink(missing_ok=True)


def test_builtin_themes_listed(api_client: TestClient, unique_user: TestUser):
    response = api_client.get(LIBRARY, headers=unique_user.token)
    assert response.status_code == 200
    themes = {t["slug"]: t for t in response.json()}
    assert BUILTIN_SLUGS <= set(themes)

    haunted = themes["haunted-halloween"]
    assert haunted["builtin"] is True
    assert haunted["schedule"] == {"start": "10-01", "end": "10-31"}
    assert haunted["theme"]["id"] == "lib:haunted-halloween"
    url = haunted["theme"]["backgroundImageUrl"]
    assert url == "/api/themes/library/haunted-halloween/files/background.webp"

    image = api_client.get(url, headers=unique_user.token)
    assert image.status_code == 200
    assert image.headers["Content-Type"] == "image/webp"


def test_library_requires_login(api_client: TestClient):
    assert api_client.get(LIBRARY).status_code == 401
    assert api_client.get(f"{LIBRARY}/haunted-halloween/files/background.webp").status_code == 401


def test_only_admins_can_manage_library(api_client: TestClient, unique_user: TestUser):
    pack = _zip({"theme.json": {"name": "Nope"}})
    assert _upload(api_client, unique_user, pack).status_code == 403
    assert api_client.get(ADMIN_LIBRARY, headers=unique_user.token).status_code == 403
    assert api_client.delete(f"{ADMIN_LIBRARY}/halloween", headers=unique_user.token).status_code == 403


def test_upload_theme_pack(api_client: TestClient, unique_admin: TestUser, unique_user: TestUser):
    pack = _zip(
        {
            "my-pack/theme.json": {
                "id": "spooky-test",
                "name": "Spooky Test",
                "light": {"primary": "#112233"},
                "css": "css/style.css",
                "backgroundImage": "images/Background Photo.PNG",
                "sidebarImage": "images/side.png",
                "panelOpacity": 0.5,
                "schedule": {"start": "12-20", "end": "01-05"},
            },
            "my-pack/css/style.css": (
                ".v-card { background: url('../images/web.png') }\n.x { background: url(https://example.com/a.png) }"
            ),
            "my-pack/images/Background Photo.PNG": _png(),
            "my-pack/images/side.png": _png((10, 10, 10)),
            "my-pack/images/web.png": _png((0, 255, 0)),
            "my-pack/readme.txt": "ignored",
            "__MACOSX/._theme.json": "junk",
        }
    )
    response = _upload(api_client, unique_admin, pack)
    assert response.status_code == 201, response.text
    imported = response.json()["imported"]
    assert len(imported) == 1
    theme = imported[0]
    assert theme["slug"] == "spooky-test"
    assert theme["builtin"] is False
    assert theme["schedule"] == {"start": "12-20", "end": "01-05"}
    assert theme["theme"]["light"]["primary"] == "#112233"
    assert theme["theme"]["panelOpacity"] == 0.5
    assert theme["theme"]["backgroundImageUrl"] == "/api/themes/library/spooky-test/files/background-photo.webp"
    assert theme["theme"]["sidebarImageUrl"] == "/api/themes/library/spooky-test/files/side.webp"
    css = theme["theme"]["customCss"]
    assert 'url("/api/themes/library/spooky-test/files/web.webp")' in css
    assert "https://example.com/a.png" in css  # external URLs are left alone

    # everyone can see and use it
    slugs = [t["slug"] for t in api_client.get(LIBRARY, headers=unique_user.token).json()]
    assert "spooky-test" in slugs
    image = api_client.get(theme["theme"]["backgroundImageUrl"], headers=unique_user.token)
    assert image.status_code == 200

    # uploading again replaces it
    pack2 = _zip({"theme.json": {"id": "spooky-test", "name": "Spooky Test v2"}})
    assert _upload(api_client, unique_admin, pack2).status_code == 201
    themes = {t["slug"]: t for t in api_client.get(LIBRARY, headers=unique_user.token).json()}
    assert themes["spooky-test"]["theme"]["name"] == "Spooky Test v2"
    assert themes["spooky-test"]["theme"]["backgroundImageUrl"] is None


def test_upload_multiple_themes_and_builtin_collision(api_client: TestClient, unique_admin: TestUser):
    pack = _zip(
        {
            "a/theme.json": {"name": "Halloween"},  # same slug as a built-in theme
            "b/theme.json": {"name": "Second Theme"},
        }
    )
    response = _upload(api_client, unique_admin, pack)
    assert response.status_code == 201, response.text
    slugs = {t["slug"] for t in response.json()["imported"]}
    assert slugs == {"halloween-2", "second-theme"}


@pytest.mark.parametrize(
    "files, message",
    [
        ({"readme.txt": "no manifest"}, "No theme.json"),
        ({"theme.json": "{not json"}, "not valid JSON"),
        ({"theme.json": {"name": "X", "light": {"primary": "red"}}}, "invalid settings"),
        ({"theme.json": {"name": "X", "backgroundImage": "missing.png"}}, "not in the zip"),
        ({"theme.json": {"name": "X", "css": "missing.css"}}, "not in the zip"),
        (
            {"theme.json": {"name": "X", "backgroundImage": "fake.png"}, "fake.png": "not an image"},
            "not a supported image",
        ),
        ({"../evil/theme.json": {"name": "X"}}, "Invalid path"),
    ],
)
def test_upload_rejects_bad_packs(api_client: TestClient, unique_admin: TestUser, files, message):
    response = _upload(api_client, unique_admin, _zip(files))
    assert response.status_code == 400
    assert message in response.text


def test_upload_rejects_non_zip(api_client: TestClient, unique_admin: TestUser):
    response = _upload(api_client, unique_admin, b"definitely not a zip")
    assert response.status_code == 400


def test_failed_upload_changes_nothing(api_client: TestClient, unique_admin: TestUser):
    pack = _zip(
        {
            "a/theme.json": {"name": "Good One"},
            "b/theme.json": {"name": "Bad One", "backgroundImage": "nope.png"},
        }
    )
    assert _upload(api_client, unique_admin, pack).status_code == 400
    slugs = [t["slug"] for t in api_client.get(ADMIN_LIBRARY, headers=unique_admin.token).json()]
    assert "good-one" not in slugs


def test_disable_and_reschedule(api_client: TestClient, unique_admin: TestUser, unique_user: TestUser):
    url = f"{ADMIN_LIBRARY}/christmas"
    response = api_client.patch(url, json={"enabled": False}, headers=unique_admin.token)
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    user_slugs = [t["slug"] for t in api_client.get(LIBRARY, headers=unique_user.token).json()]
    assert "christmas" not in user_slugs
    admin_slugs = [t["slug"] for t in api_client.get(ADMIN_LIBRARY, headers=unique_admin.token).json()]
    assert "christmas" in admin_slugs

    response = api_client.patch(
        url, json={"enabled": True, "schedule": {"start": "11-25", "end": "12-31"}}, headers=unique_admin.token
    )
    assert response.json()["schedule"] == {"start": "11-25", "end": "12-31"}

    response = api_client.patch(url, json={"clearSchedule": True}, headers=unique_admin.token)
    assert response.json()["schedule"] is None

    bad = api_client.patch(url, json={"schedule": {"start": "13-01", "end": "12-31"}}, headers=unique_admin.token)
    assert bad.status_code == 422
    assert api_client.patch(f"{ADMIN_LIBRARY}/nope", json={}, headers=unique_admin.token).status_code == 404


def test_delete(api_client: TestClient, unique_admin: TestUser, unique_user: TestUser):
    assert api_client.delete(f"{ADMIN_LIBRARY}/halloween", headers=unique_admin.token).status_code == 400

    pack = _zip({"theme.json": {"id": "to-delete", "name": "To Delete", "backgroundImage": "bg.png"}, "bg.png": _png()})
    image_url = _upload(api_client, unique_admin, pack).json()["imported"][0]["theme"]["backgroundImageUrl"]

    assert api_client.delete(f"{ADMIN_LIBRARY}/to-delete", headers=unique_admin.token).status_code == 204
    assert api_client.get(image_url, headers=unique_user.token).status_code == 404
    assert api_client.delete(f"{ADMIN_LIBRARY}/to-delete", headers=unique_admin.token).status_code == 404


def test_export_round_trip(api_client: TestClient, unique_admin: TestUser):
    response = api_client.get(f"{ADMIN_LIBRARY}/haunted-halloween/export", headers=unique_admin.token)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("theme.json"))
    assert {"theme.json", "style.css", "background.webp"} <= names
    assert manifest["backgroundImage"] == "background.webp"
    assert manifest["css"] == "style.css"

    # the exported pack can be uploaded again as a new theme
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        files = {n: zf.read(n) for n in zf.namelist()}
    manifest["id"] = "haunted-copy"
    files["theme.json"] = json.dumps(manifest).encode()
    result = _upload(api_client, unique_admin, _zip(files))
    assert result.status_code == 201, result.text
    assert result.json()["imported"][0]["theme"]["backgroundImageUrl"].endswith("/haunted-copy/files/background.webp")


def test_user_settings_with_library_theme(api_client: TestClient, unique_user: TestUser):
    settings = api_client.get(api_routes.users_self_themes, headers=unique_user.token).json()
    assert settings["autoSeasonal"] is True

    payload = {
        "activeThemeId": "lib:haunted-halloween",
        "autoSeasonal": False,
        "themes": [
            {
                "id": "my-copy",
                "name": "My Copy",
                "backgroundImageUrl": "/api/themes/library/haunted-halloween/files/background.webp",
            }
        ],
    }
    response = api_client.put(api_routes.users_self_themes, json=payload, headers=unique_user.token)
    assert response.status_code == 200
    data = response.json()
    assert data["activeThemeId"] == "lib:haunted-halloween"
    assert data["autoSeasonal"] is False
    assert data["themes"][0]["backgroundImageUrl"].endswith("background.webp")

    for bad in (
        {"themes": [{"id": "lib:sneaky", "name": "X"}]},
        {"themes": [{"id": "x", "name": "X", "backgroundImageUrl": "https://evil.example/x.webp"}]},
        {"themes": [{"id": "x", "name": "X", "backgroundImageUrl": "/api/themes/library/../x.webp"}]},
    ):
        assert api_client.put(api_routes.users_self_themes, json=bad, headers=unique_user.token).status_code == 422
