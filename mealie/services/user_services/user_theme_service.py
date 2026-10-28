import json
import os
import tempfile
from pathlib import Path

from pydantic import UUID4, ValidationError

from mealie.core.config import get_app_dirs
from mealie.core.root_logger import get_logger
from mealie.schema.user.user_theme import UserThemeSettings

logger = get_logger()

USER_THEMES_DIR_NAME = "user-themes"


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

    def delete(self, user_id: UUID4) -> None:
        self._path(user_id).unlink(missing_ok=True)
