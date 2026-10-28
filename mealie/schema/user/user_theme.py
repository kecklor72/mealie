from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from mealie.schema._mealie import MealieModel

HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
"""A 6-digit hex color, e.g. `#E58325`"""

FontName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9 \-]{1,64}$", strip_whitespace=True)]
"""A font family name. Restricted to safe characters so it can be used in CSS and Google Fonts URLs."""

ThemeId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9\-_]{1,64}$")]

MAX_THEMES = 50
MAX_CUSTOM_CSS_LENGTH = 50_000


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


class UserThemeSettings(MealieModel):
    active_theme_id: ThemeId | None = None
    themes: Annotated[list[UserTheme], Field(max_length=MAX_THEMES)] = []

    @model_validator(mode="after")
    def validate_ids(self):
        ids = [t.id for t in self.themes]
        if len(ids) != len(set(ids)):
            raise ValueError("theme ids must be unique")

        if self.active_theme_id is not None and self.active_theme_id not in ids:
            # Gracefully fall back to the default theme rather than erroring
            self.active_theme_id = None

        return self
