from functools import cached_property

from mealie.routes._base import BaseUserController, controller
from mealie.routes._base.routers import UserAPIRouter
from mealie.schema.user.user_theme import UserThemeSettings
from mealie.services.user_services.user_theme_service import UserThemeService

router = UserAPIRouter(prefix="/users/self/themes", tags=["Users: Themes"])


@controller(router)
class UserThemesController(BaseUserController):
    @cached_property
    def service(self) -> UserThemeService:
        return UserThemeService()

    @router.get("", response_model=UserThemeSettings)
    def get_theme_settings(self):
        """Get the logged in user's saved themes and active theme"""
        return self.service.get(self.user.id)

    @router.put("", response_model=UserThemeSettings)
    def update_theme_settings(self, data: UserThemeSettings):
        """Replace the logged in user's saved themes and active theme"""
        return self.service.save(self.user.id, data)

    @router.delete("", response_model=UserThemeSettings)
    def reset_theme_settings(self):
        """Delete all of the logged in user's themes and go back to the server default"""
        self.service.delete(self.user.id)
        return UserThemeSettings()
