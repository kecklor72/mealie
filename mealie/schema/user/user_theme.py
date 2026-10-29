from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from mealie.schema._mealie import MealieModel

HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
"""A 6-digit hex color, e.g. `#E58325`"""

FontName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9 \-]{1,64}$", strip_whitespace=True)]
"""A font family name. Restricted to safe characters so it can be used in CSS and Google Fonts URLs."""

ThemeId = Annotated[str, StringConstraints(pattern=r"^(lib:)?[A-Za-z0-9\-_]{1,64}$")]
"""A theme ID. IDs starting with `lib:` refer to themes in the shared theme library."""

LIBRARY_THEME_PREFIX = "lib:"

LibrarySlug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,47}$")]
"""Identifier of a theme in the shared theme library"""

LibraryFileName = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}\.webp$")]

LIBRARY_IMAGE_URL_PATTERN = r"^/api/themes/library/[a-z0-9][a-z0-9-]{0,47}/files/[a-z0-9][a-z0-9_-]{0,63}\.webp$"
LibraryImageUrl = Annotated[str, StringConstraints(pattern=LIBRARY_IMAGE_URL_PATTERN)]
"""URL of an image that belongs to a theme in the shared theme library"""

MonthDay = Annotated[str, StringConstraints(pattern=r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")]
"""A date without a year, as `MM-DD`"""

ThemeImageId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]
"""ID of an image uploaded with `POST /api/users/self/themes/images`"""

MAX_THEMES = 50
MAX_CUSTOM_CSS_LENGTH = 100_000


class UserThemeColors(MealieModel):
    primary: HexColor = "#E58325"
    accent: HexColor = "#007A99"
    secondary: HexColor = "#973542"
    success: HexColor = "#43A047"
    info: HexColor = "#1976D2"
    warning: HexColor = "#FF6D00"
    error: HexColor = "#EF5350"
    background: HexColor | None = None
    surface: HexColor | None = None


class UserTheme(MealieModel):
    id: ThemeId
    name: Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)]
    light: UserThemeColors = Field(default_factory=UserThemeColors)
    dark: UserThemeColors = Field(default_factory=UserThemeColors)
    font_body: FontName | None = None
    font_heading: FontName | None = None
    custom_css: Annotated[str, StringConstraints(max_length=MAX_CUSTOM_CSS_LENGTH)] = ""

    background_image: ThemeImageId | None = None
    """Full screen background image, shown behind the whole app"""
    sidebar_image: ThemeImageId | None = None
    """Optional separate image for the navigation sidebar"""
    background_dim: Annotated[float, Field(ge=0, le=0.95)] = 0.3
    """How much to darken the background image (0 = not at all)"""
    panel_opacity: Annotated[float, Field(ge=0, le=1)] = 0.75
    """Opacity of the top bar and sidebar when a background image is set"""
    card_opacity: Annotated[float, Field(ge=0, le=1)] = 0.9
    """Opacity of cards when a background image is set"""

    background_image_url: LibraryImageUrl | None = None
    """Background image from the theme library. Used when `background_image` is not set."""
    sidebar_image_url: LibraryImageUrl | None = None
    """Sidebar image from the theme library. Used when `sidebar_image` is not set."""


class UserThemeImage(MealieModel):
    id: ThemeImageId
    url: str


class UserThemeSettings(MealieModel):
    active_theme_id: ThemeId | None = None
    """The user's own theme, or `lib:<slug>` for a theme from the shared library"""
    auto_seasonal: bool = True
    """Automatically use library themes on their scheduled dates (e.g. holidays)"""
    themes: Annotated[list[UserTheme], Field(max_length=MAX_THEMES)] = []

    @model_validator(mode="after")
    def validate_ids(self):
        ids = [t.id for t in self.themes]
        if len(ids) != len(set(ids)):
            raise ValueError("theme ids must be unique")
        if any(i.startswith(LIBRARY_THEME_PREFIX) for i in ids):
            raise ValueError("your own themes can't use ids starting with 'lib:'")

        if self.active_theme_id is not None and self.active_theme_id.startswith(LIBRARY_THEME_PREFIX):
            # library themes are checked when they're loaded; unknown ones fall back to the default
            return self

        if self.active_theme_id is not None and self.active_theme_id not in ids:
            # Gracefully fall back to the default theme rather than erroring
            self.active_theme_id = None

        return self

    def referenced_images(self) -> set[str]:
        images: set[str] = set()
        for theme in self.themes:
            for image in (theme.background_image, theme.sidebar_image):
                if image:
                    images.add(image)
        return images


# ======================================================================
# Shared theme library (built-in themes + theme packs uploaded by admins)


class ThemeSchedule(MealieModel):
    """Dates (every year) when a library theme is used automatically. May wrap around the new year."""

    start: MonthDay
    end: MonthDay


class ThemePackManifest(MealieModel):
    """
    The `theme.json` file in a theme pack (zip). Images and CSS are given as file names in the zip.
    Also used to store library themes on disk, where image names point at converted `.webp` files.
    """

    id: LibrarySlug | None = None
    name: Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)]
    description: Annotated[str, StringConstraints(max_length=300)] = ""
    light: UserThemeColors = Field(default_factory=UserThemeColors)
    dark: UserThemeColors = Field(default_factory=UserThemeColors)
    font_body: FontName | None = None
    font_heading: FontName | None = None
    custom_css: Annotated[str, StringConstraints(max_length=MAX_CUSTOM_CSS_LENGTH)] = ""
    css: Annotated[str, StringConstraints(max_length=255)] | None = None
    """Name of a CSS file in the pack. Its contents are added after `customCss`."""
    background_image: Annotated[str, StringConstraints(max_length=255)] | None = None
    sidebar_image: Annotated[str, StringConstraints(max_length=255)] | None = None
    background_dim: Annotated[float, Field(ge=0, le=0.95)] = 0.3
    panel_opacity: Annotated[float, Field(ge=0, le=1)] = 0.75
    card_opacity: Annotated[float, Field(ge=0, le=1)] = 0.9
    schedule: ThemeSchedule | None = None


class LibraryTheme(MealieModel):
    slug: LibrarySlug
    builtin: bool
    """Built-in themes ship with Mealie and can't be deleted (only disabled)"""
    enabled: bool = True
    """Disabled themes are hidden from users and never used automatically"""
    description: str = ""
    schedule: ThemeSchedule | None = None
    theme: UserTheme
    """The theme itself, ready to apply. Its id is `lib:<slug>`."""


class LibraryThemeUpdate(MealieModel):
    enabled: bool | None = None
    schedule: ThemeSchedule | None = None
    clear_schedule: bool = False
    """Set to true to remove the schedule"""


class LibraryImportResult(MealieModel):
    imported: list[LibraryTheme]
