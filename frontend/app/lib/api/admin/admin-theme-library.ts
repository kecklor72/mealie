import { BaseAPI } from "../base/base-clients";
import type { LibraryImportResult, LibraryTheme, LibraryThemeUpdate } from "~/lib/api/types/user";

const prefix = "/api";

const routes = {
  library: `${prefix}/admin/themes/library`,
  librarySlug: (slug: string) => `${prefix}/admin/themes/library/${slug}`,
  libraryExport: (slug: string) => `${prefix}/admin/themes/library/${slug}/export`,
};

export class AdminThemeLibraryApi extends BaseAPI {
  async getAll() {
    return await this.requests.get<LibraryTheme[]>(routes.library);
  }

  async importPack(file: File) {
    const form = new FormData();
    form.append("archive", file);
    return await this.requests.post<LibraryImportResult>(routes.library, form);
  }

  async update(slug: string, payload: LibraryThemeUpdate) {
    return await this.requests.patch<LibraryTheme, LibraryThemeUpdate>(routes.librarySlug(slug), payload);
  }

  async delete(slug: string) {
    return await this.requests.delete(routes.librarySlug(slug));
  }

  exportUrl(slug: string) {
    return routes.libraryExport(slug);
  }
}
