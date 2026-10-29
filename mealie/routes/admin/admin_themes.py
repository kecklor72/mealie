from functools import cached_property
from typing import Annotated

from fastapi import File, HTTPException, Path, UploadFile, status
from fastapi.responses import Response

from mealie.routes._base import BaseAdminController, controller
from mealie.routes._base.routers import AdminAPIRouter
from mealie.schema.response.responses import ErrorResponse
from mealie.schema.user.user_theme import LibraryImportResult, LibraryTheme, LibraryThemeUpdate
from mealie.services.user_services.theme_library_service import ThemeLibraryError, ThemeLibraryService

router = AdminAPIRouter(prefix="/themes/library")

LibrarySlugPath = Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,47}$")]


@controller(router)
class AdminThemeLibraryController(BaseAdminController):
    @cached_property
    def service(self) -> ThemeLibraryService:
        return ThemeLibraryService()

    def _not_found(self) -> HTTPException:
        return HTTPException(status.HTTP_404_NOT_FOUND, ErrorResponse.respond("Theme not found"))

    @router.get("", response_model=list[LibraryTheme])
    def get_all_library_themes(self):
        """All library themes, including disabled ones"""
        return self.service.list_themes(include_disabled=True)

    @router.post("", response_model=LibraryImportResult, status_code=status.HTTP_201_CREATED)
    def import_theme_pack(self, archive: UploadFile = File(...)):
        """
        Upload a theme pack (zip). The zip contains a `theme.json` (or several, one per folder),
        plus any images and CSS files it refers to. Uploading a theme with the same id again replaces it.
        """
        try:
            imported = self.service.import_zip(archive.file)
        except ThemeLibraryError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond(str(e))) from e
        return LibraryImportResult(imported=imported)

    @router.patch("/{slug}", response_model=LibraryTheme)
    def update_library_theme(self, slug: LibrarySlugPath, data: LibraryThemeUpdate):
        """Enable/disable a library theme or change the dates it's used automatically"""
        try:
            return self.service.update(slug, data)
        except ThemeLibraryError as e:
            raise self._not_found() from e

    @router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_library_theme(self, slug: LibrarySlugPath):
        """Delete an uploaded theme. Built-in themes can only be disabled."""
        if not self.service.get_theme(slug):
            raise self._not_found()
        try:
            self.service.delete(slug)
        except ThemeLibraryError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond(str(e))) from e

    @router.get("/{slug}/export")
    def export_library_theme(self, slug: LibrarySlugPath):
        """Download a library theme as a theme pack (zip) to use as a starting point for new themes"""
        try:
            data = self.service.export_zip(slug)
        except ThemeLibraryError as e:
            raise self._not_found() from e
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'},
        )
