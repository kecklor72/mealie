from functools import cached_property
from typing import Annotated

from fastapi import File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse

from mealie.routes._base import BaseUserController, controller
from mealie.routes._base.routers import UserAPIRouter
from mealie.schema.response.responses import ErrorResponse
from mealie.schema.user.user_theme import UserThemeImage, UserThemeSettings
from mealie.services.user_services.user_theme_service import ThemeImageError, UserThemeService

router = UserAPIRouter(prefix="/users/self/themes", tags=["Users: Themes"])

ImageIdPath = Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")]


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
        return self.service.save_and_cleanup(self.user.id, data)

    @router.delete("", response_model=UserThemeSettings)
    def reset_theme_settings(self):
        """Delete all of the logged in user's themes and theme images, and go back to the server default"""
        self.service.delete(self.user.id)
        return UserThemeSettings()

    @router.post("/images", response_model=UserThemeImage, status_code=status.HTTP_201_CREATED)
    def upload_theme_image(self, image: UploadFile = File(...)):
        """Upload a background image for use in a theme. Images are converted to WebP."""
        try:
            image_id = self.service.add_image(self.user.id, image.file)
        except ThemeImageError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond(str(e))) from e

        return UserThemeImage(id=image_id, url=f"/api/users/self/themes/images/{image_id}")

    @router.get("/images/{image_id}", response_class=FileResponse)
    def get_theme_image(self, image_id: ImageIdPath):
        """Get one of the logged in user's theme images"""
        path = self.service.image_path(self.user.id, image_id)
        if not path:
            raise HTTPException(status.HTTP_404_NOT_FOUND)

        # Image IDs never change, so browsers can cache them forever
        return FileResponse(
            path, media_type="image/webp", headers={"Cache-Control": "private, max-age=31536000, immutable"}
        )

    @router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_theme_image(self, image_id: ImageIdPath):
        """Delete one of the logged in user's theme images"""
        self.service.delete_image(self.user.id, image_id)
