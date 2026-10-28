import json
import os
import tempfile
import time
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import UUID4, ValidationError

from mealie.core.config import get_app_dirs
from mealie.core.root_logger import get_logger
from mealie.schema.user.user_theme import UserThemeSettings

logger = get_logger()

USER_THEMES_DIR_NAME = "user-themes"

MAX_IMAGE_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_IMAGE_DIMENSION = 3840
MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGES_PER_USER = 30
ORPHAN_IMAGE_GRACE_SECONDS = 24 * 60 * 60


class ThemeImageError(Exception):
    pass


class UserThemeService:
    """
    Stores per-user theme settings as JSON files in `DATA_DIR/user-themes/<user_id>.json`.

    File storage (instead of a database table) keeps this feature free of database migrations,
    so the fork can be merged with upstream releases easily and switching back to the official
    image never breaks the database. The data directory is included in Mealie backups.

    These files are intentionally NOT stored in the user's media directory, since that
    directory is served publicly by the media routes.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or get_app_dirs().DATA_DIR / USER_THEMES_DIR_NAME

    def _path(self, user_id: UUID4) -> Path:
        # UUID4 is validated by pydantic, so this is safe from path traversal
        return self.base_dir / f"{user_id}.json"

    def get(self, user_id: UUID4) -> UserThemeSettings:
        path = self._path(user_id)
        if not path.is_file():
            return UserThemeSettings()

        try:
            return UserThemeSettings.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, ValidationError) as e:
            logger.error(f"Unable to read theme settings for user {user_id}: {e}")
            return UserThemeSettings()

    def save(self, user_id: UUID4, settings: UserThemeSettings) -> UserThemeSettings:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(user_id)

        # write atomically so a crash mid-write can't corrupt the file
        fd, tmp_name = tempfile.mkstemp(dir=self.base_dir, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(settings.model_dump_json(by_alias=True, indent=2))
            os.replace(tmp_name, path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

        return settings

    def save_and_cleanup(self, user_id: UUID4, settings: UserThemeSettings) -> UserThemeSettings:
        saved = self.save(user_id, settings)
        self.cleanup_images(user_id, saved)
        return saved

    def delete(self, user_id: UUID4) -> None:
        self._path(user_id).unlink(missing_ok=True)
        image_dir = self._image_dir(user_id)
        if image_dir.is_dir():
            for f in image_dir.glob("*.webp"):
                f.unlink(missing_ok=True)

    # ==================================================================
    # Background images
    #
    # Stored in `DATA_DIR/user-themes/images/<user_id>/<image_id>.webp`

    def _image_dir(self, user_id: UUID4) -> Path:
        return self.base_dir / "images" / str(user_id)

    def image_path(self, user_id: UUID4, image_id: str) -> Path | None:
        # image_id is validated as 32 hex characters by the route, so this is safe from traversal
        path = self._image_dir(user_id) / f"{image_id}.webp"
        return path if path.is_file() else None

    def add_image(self, user_id: UUID4, file: BinaryIO) -> str:
        image_dir = self._image_dir(user_id)
        image_dir.mkdir(parents=True, exist_ok=True)

        if len(list(image_dir.glob("*.webp"))) >= MAX_IMAGES_PER_USER:
            raise ThemeImageError(f"You can have at most {MAX_IMAGES_PER_USER} theme images")

        data = file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
        if len(data) > MAX_IMAGE_UPLOAD_BYTES:
            raise ThemeImageError("Image is too large (max 25 MB)")

        with tempfile.NamedTemporaryFile(dir=image_dir, prefix=".upload-", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            try:
                with Image.open(tmp.name) as img:
                    if img.width * img.height > MAX_IMAGE_PIXELS:
                        raise ThemeImageError("Image has too many pixels")
                    img = ImageOps.exif_transpose(img)
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                    img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

                    image_id = uuid4().hex
                    dest = image_dir / f"{image_id}.webp"
                    img.save(dest, "WEBP", quality=85, method=4)
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
                raise ThemeImageError("That file is not a supported image") from e

        return image_id

    def delete_image(self, user_id: UUID4, image_id: str) -> None:
        path = self.image_path(user_id, image_id)
        if path:
            path.unlink(missing_ok=True)

    def cleanup_images(self, user_id: UUID4, settings: UserThemeSettings) -> None:
        """Deletes uploaded images that no theme uses anymore.

        Recently uploaded images are kept for a while, so an image uploaded for a theme
        that's still being edited isn't removed by a save from somewhere else.
        """
        image_dir = self._image_dir(user_id)
        if not image_dir.is_dir():
            return

        used = settings.referenced_images()
        cutoff = time.time() - ORPHAN_IMAGE_GRACE_SECONDS
        for f in image_dir.glob("*.webp"):
            if f.stem not in used and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
