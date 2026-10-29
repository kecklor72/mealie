"""
The shared theme library: built-in themes that ship with Mealie, plus theme packs (zip files)
uploaded by admins. Every user can use these themes, copy them into their own themes, and have
scheduled ones (e.g. holidays) applied automatically.

Layout of a stored library theme (built-in or uploaded):

    <slug>/
        theme.json      a `ThemePackManifest`; image names point at files in `files/`, and
                        CSS refers to those files as `__THEME_FILES__/<name>.webp`
        files/*.webp    converted images

Built-in themes live in `mealie/assets/themes`, uploaded ones in `DATA_DIR/user-themes/library`.
Admin changes (enabled / schedule) are kept in `DATA_DIR/user-themes/library.json`, so built-in
themes can be adjusted without touching the files that ship with the app.
"""

import io
import json
import os
import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from pydantic import ValidationError

import mealie.assets
from mealie.core.config import get_app_dirs
from mealie.core.root_logger import get_logger
from mealie.schema.user.user_theme import (
    LIBRARY_THEME_PREFIX,
    LibraryTheme,
    LibraryThemeUpdate,
    ThemePackManifest,
    ThemeSchedule,
    UserTheme,
)
from mealie.services.user_services.user_theme_service import (
    USER_THEMES_DIR_NAME,
    ThemeImageError,
    convert_image_to_webp,
)

logger = get_logger()

BUILTIN_THEMES_DIR = Path(mealie.assets.__file__).parent / "themes"

FILES_TOKEN = "__THEME_FILES__"
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
FILE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}\.webp$")
CSS_URL_PATTERN = re.compile(r"""url\(\s*(['"]?)([^'")]+?)\1\s*\)""")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".heic", ".heif"}

MAX_ZIP_BYTES = 60 * 1024 * 1024
MAX_ZIP_ENTRIES = 300
MAX_ZIP_FILE_BYTES = 30 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 300 * 1024 * 1024
MAX_CSS_FILE_BYTES = 200 * 1024
MAX_THEMES_PER_ZIP = 20


class ThemeLibraryError(Exception):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48].strip("-")
    return slug or "theme"


def _safe_file_stem(value: str) -> str:
    stem = re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-_")[:58].strip("-_")
    return stem or "image"


class ThemeLibraryService:
    def __init__(self, data_dir: Path | None = None, builtin_dir: Path | None = None) -> None:
        base = data_dir or get_app_dirs().DATA_DIR / USER_THEMES_DIR_NAME
        self.library_dir = base / "library"
        self.config_path = base / "library.json"
        self.builtin_dir = builtin_dir or BUILTIN_THEMES_DIR

    # ==================================================================
    # Reading

    def _theme_dir(self, slug: str) -> tuple[Path, bool] | None:
        """Returns (directory, is_builtin) for a library theme"""
        if not SLUG_PATTERN.match(slug):
            return None
        builtin = self.builtin_dir / slug
        if (builtin / "theme.json").is_file():
            return builtin, True
        uploaded = self.library_dir / slug
        if (uploaded / "theme.json").is_file():
            return uploaded, False
        return None

    def _load_manifest(self, theme_dir: Path) -> ThemePackManifest | None:
        try:
            return ThemePackManifest.model_validate(json.loads((theme_dir / "theme.json").read_text("utf-8")))
        except (OSError, ValueError, ValidationError) as e:
            logger.error(f"Skipping invalid library theme in {theme_dir}: {e}")
            return None

    def _load_config(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.config_path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except OSError, ValueError:
            return {}

    def _save_config(self, config: dict[str, dict[str, Any]]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.config_path.parent, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp, self.config_path)

    @staticmethod
    def file_url(slug: str, name: str) -> str:
        return f"/api/themes/library/{slug}/files/{name}"

    def _to_library_theme(
        self, slug: str, builtin: bool, manifest: ThemePackManifest, config: dict[str, Any]
    ) -> LibraryTheme:
        files_url = f"/api/themes/library/{slug}/files"
        schedule = manifest.schedule
        if "schedule" in config:
            schedule = ThemeSchedule.model_validate(config["schedule"]) if config["schedule"] else None

        theme = UserTheme(
            id=f"{LIBRARY_THEME_PREFIX}{slug}",
            name=manifest.name,
            light=manifest.light,
            dark=manifest.dark,
            font_body=manifest.font_body,
            font_heading=manifest.font_heading,
            custom_css=manifest.custom_css.replace(FILES_TOKEN, files_url),
            background_dim=manifest.background_dim,
            panel_opacity=manifest.panel_opacity,
            card_opacity=manifest.card_opacity,
            background_image_url=self.file_url(slug, manifest.background_image) if manifest.background_image else None,
            sidebar_image_url=self.file_url(slug, manifest.sidebar_image) if manifest.sidebar_image else None,
        )
        return LibraryTheme(
            slug=slug,
            builtin=builtin,
            enabled=bool(config.get("enabled", True)),
            description=manifest.description,
            schedule=schedule,
            theme=theme,
        )

    def list_themes(self, include_disabled: bool = False) -> list[LibraryTheme]:
        config = self._load_config()
        themes: list[LibraryTheme] = []
        seen: set[str] = set()

        for root, builtin in ((self.builtin_dir, True), (self.library_dir, False)):
            if not root.is_dir():
                continue
            for theme_dir in sorted(root.iterdir()):
                slug = theme_dir.name
                if slug in seen or not SLUG_PATTERN.match(slug) or not (theme_dir / "theme.json").is_file():
                    continue
                manifest = self._load_manifest(theme_dir)
                if not manifest:
                    continue
                try:
                    item = self._to_library_theme(slug, builtin, manifest, config.get(slug, {}))
                except ValidationError as e:
                    logger.error(f"Skipping library theme {slug}: {e}")
                    continue
                seen.add(slug)
                if item.enabled or include_disabled:
                    themes.append(item)

        return themes

    def get_theme(self, slug: str) -> LibraryTheme | None:
        found = self._theme_dir(slug)
        if not found:
            return None
        theme_dir, builtin = found
        manifest = self._load_manifest(theme_dir)
        if not manifest:
            return None
        return self._to_library_theme(slug, builtin, manifest, self._load_config().get(slug, {}))

    def file_path(self, slug: str, name: str) -> Path | None:
        if not FILE_NAME_PATTERN.match(name):
            return None
        found = self._theme_dir(slug)
        if not found:
            return None
        path = found[0] / "files" / name
        return path if path.is_file() else None

    # ==================================================================
    # Admin changes

    def update(self, slug: str, data: LibraryThemeUpdate) -> LibraryTheme:
        if not self._theme_dir(slug):
            raise ThemeLibraryError("Theme not found")

        config = self._load_config()
        entry = config.setdefault(slug, {})
        if data.enabled is not None:
            entry["enabled"] = data.enabled
        if data.clear_schedule:
            entry["schedule"] = None
        elif data.schedule is not None:
            entry["schedule"] = data.schedule.model_dump()
        self._save_config(config)

        theme = self.get_theme(slug)
        assert theme
        return theme

    def delete(self, slug: str) -> None:
        found = self._theme_dir(slug)
        if not found:
            raise ThemeLibraryError("Theme not found")
        theme_dir, builtin = found
        if builtin:
            raise ThemeLibraryError("Built-in themes can't be deleted. You can disable them instead.")

        shutil.rmtree(theme_dir)
        config = self._load_config()
        if config.pop(slug, None) is not None:
            self._save_config(config)

    # ==================================================================
    # Import (zip theme packs)

    def import_zip(self, file: BinaryIO) -> list[LibraryTheme]:
        data = file.read(MAX_ZIP_BYTES + 1)
        if len(data) > MAX_ZIP_BYTES:
            raise ThemeLibraryError("The zip file is too large (max 60 MB)")

        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as e:
            raise ThemeLibraryError("That file is not a valid zip file") from e

        with zf:
            members = self._zip_members(zf)
            manifests = sorted(
                (name for name in members if PurePosixPath(name).name.lower() == "theme.json"),
                key=lambda n: (n.count("/"), n),
            )
            if not manifests:
                raise ThemeLibraryError("No theme.json was found in the zip file")
            if len(manifests) > MAX_THEMES_PER_ZIP:
                raise ThemeLibraryError(f"A zip file can contain at most {MAX_THEMES_PER_ZIP} themes")

            # Validate and convert everything before changing the library, so a bad pack changes nothing
            staged: list[tuple[str, Path]] = []
            self.library_dir.mkdir(parents=True, exist_ok=True)
            staging_root = Path(tempfile.mkdtemp(dir=self.library_dir, prefix=".staging-"))
            try:
                used_slugs: set[str] = set()
                for manifest_name in manifests:
                    slug, theme_dir = self._stage_theme(zf, members, manifest_name, staging_root, used_slugs)
                    used_slugs.add(slug)
                    staged.append((slug, theme_dir))

                config = self._load_config()
                for slug, theme_dir in staged:
                    dest = self.library_dir / slug
                    if dest.exists():
                        shutil.rmtree(dest)
                    theme_dir.rename(dest)
                    # a re-uploaded theme uses the schedule from its new theme.json
                    config.get(slug, {}).pop("schedule", None)
                self._save_config(config)
            finally:
                shutil.rmtree(staging_root, ignore_errors=True)

        results = [self.get_theme(slug) for slug, _ in staged]
        return [r for r in results if r]

    def _zip_members(self, zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
        members: dict[str, zipfile.ZipInfo] = {}
        total = 0
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ThemeLibraryError(f"The zip file has too many files (max {MAX_ZIP_ENTRIES})")

        for info in infos:
            name = info.filename.replace("\\", "/")
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts:
                raise ThemeLibraryError(f"Invalid path in zip file: {info.filename}")
            # ignore macOS metadata and hidden files
            if not parts or parts[0] == "__MACOSX" or any(p.startswith(".") for p in parts):
                continue
            if info.file_size > MAX_ZIP_FILE_BYTES:
                raise ThemeLibraryError(f"{info.filename} is too large (max 30 MB per file)")
            total += info.file_size
            if total > MAX_ZIP_TOTAL_BYTES:
                raise ThemeLibraryError("The zip file is too large when unpacked")
            members[posixpath.normpath(name)] = info

        return members

    @staticmethod
    def _read(zf: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
        # read with a hard limit, in case the sizes in the zip header lie
        with zf.open(info) as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise ThemeLibraryError(f"{info.filename} is too large")
        return data

    def _stage_theme(
        self,
        zf: zipfile.ZipFile,
        members: dict[str, zipfile.ZipInfo],
        manifest_name: str,
        staging_root: Path,
        used_slugs: set[str],
    ) -> tuple[str, Path]:
        base = posixpath.dirname(manifest_name)
        label = manifest_name

        try:
            raw = json.loads(self._read(zf, members[manifest_name], 1024 * 1024).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise ThemeLibraryError(f"{label} is not valid JSON") from e
        try:
            manifest = ThemePackManifest.model_validate(raw)
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:5])
            raise ThemeLibraryError(f"{label} has invalid settings: {problems}") from e

        slug = manifest.id or slugify(manifest.name)
        # built-in themes can't be replaced by uploads
        candidate, n = slug, 2
        while (self.builtin_dir / candidate / "theme.json").is_file() or candidate in used_slugs:
            candidate = f"{slug[:44]}-{n}"
            n += 1
        slug = candidate

        theme_dir = staging_root / slug
        files_dir = theme_dir / "files"
        files_dir.mkdir(parents=True)

        # convert every image in this theme's folder
        in_pack = {
            posixpath.relpath(name, base) if base else name: info
            for name, info in members.items()
            if not base or name.startswith(base + "/")
        }
        image_map: dict[str, str] = {}
        used_names: set[str] = set()
        for rel, info in sorted(in_pack.items()):
            ext = PurePosixPath(rel).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            stem = _safe_file_stem(PurePosixPath(rel).stem)
            out_name, i = f"{stem}.webp", 2
            while out_name in used_names:
                out_name = f"{stem[:55]}-{i}.webp"
                i += 1
            used_names.add(out_name)
            try:
                convert_image_to_webp(self._read(zf, info, MAX_ZIP_FILE_BYTES), files_dir / out_name)
            except ThemeImageError as e:
                raise ThemeLibraryError(f"{info.filename}: {e}") from e
            image_map[rel.lower()] = out_name

        def resolve_image(ref: str, relative_to: str = "") -> str | None:
            ref = ref.strip()
            if not ref or ":" in ref or ref.startswith(("/", "#")):
                return None
            ref = ref.split("?")[0].split("#")[0]
            path = posixpath.normpath(posixpath.join(relative_to, ref))
            return image_map.get(path.lower())

        def rewrite_css(css: str, relative_to: str = "") -> str:
            def repl(match: re.Match[str]) -> str:
                name = resolve_image(match.group(2), relative_to)
                return f'url("{FILES_TOKEN}/{name}")' if name else match.group(0)

            return CSS_URL_PATTERN.sub(repl, css)

        css = rewrite_css(manifest.custom_css)
        if manifest.css:
            css_rel = posixpath.normpath(manifest.css)
            css_info = in_pack.get(css_rel)
            if not css_info:
                raise ThemeLibraryError(f"{label}: the CSS file '{manifest.css}' is not in the zip")
            try:
                css_text = self._read(zf, css_info, MAX_CSS_FILE_BYTES).decode("utf-8")
            except UnicodeDecodeError as e:
                raise ThemeLibraryError(f"{manifest.css} must be UTF-8 text") from e
            css = f"{css}\n\n{rewrite_css(css_text, posixpath.dirname(css_rel))}".strip()

        images: dict[str, str | None] = {}
        for field in ("background_image", "sidebar_image"):
            ref = getattr(manifest, field)
            if not ref:
                images[field] = None
                continue
            name = resolve_image(ref)
            if not name:
                raise ThemeLibraryError(f"{label}: the image '{ref}' is not in the zip (or isn't a supported image)")
            images[field] = name

        try:
            stored = manifest.model_copy(
                update={
                    "id": slug,
                    "custom_css": css,
                    "css": None,
                    "background_image": images["background_image"],
                    "sidebar_image": images["sidebar_image"],
                }
            )
            # re-validate (e.g. the combined CSS length)
            stored = ThemePackManifest.model_validate(stored.model_dump())
        except ValidationError as e:
            raise ThemeLibraryError(f"{label}: {e.errors()[0]['msg']}") from e

        (theme_dir / "theme.json").write_text(stored.model_dump_json(by_alias=True, indent=2), "utf-8")
        return slug, theme_dir

    # ==================================================================
    # Export

    def export_zip(self, slug: str) -> bytes:
        """Exports a library theme as a theme pack that can be edited and uploaded again"""
        found = self._theme_dir(slug)
        if not found:
            raise ThemeLibraryError("Theme not found")
        theme_dir, _ = found
        manifest = self._load_manifest(theme_dir)
        if not manifest:
            raise ThemeLibraryError("Theme not found")

        theme = self.get_theme(slug)
        export = manifest.model_copy(
            update={
                "custom_css": "",
                "css": "style.css" if manifest.custom_css else None,
                "schedule": theme.schedule if theme else manifest.schedule,
            }
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest_data = export.model_dump(by_alias=True, exclude_none=True, exclude={"custom_css"})
            zf.writestr("theme.json", json.dumps(manifest_data, indent=2))
            if manifest.custom_css:
                zf.writestr("style.css", manifest.custom_css.replace(f"{FILES_TOKEN}/", ""))
            files_dir = theme_dir / "files"
            if files_dir.is_dir():
                for f in sorted(files_dir.glob("*.webp")):
                    zf.write(f, f.name)
        return buf.getvalue()
