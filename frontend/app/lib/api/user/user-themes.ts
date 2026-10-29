import { BaseAPI } from "../base/base-clients";
import type { LibraryTheme, UserThemeImage, UserThemeSettings } from "~/lib/api/types/user";

const prefix = "/api";

const routes = {
  themesSelf: `${prefix}/users/self/themes`,
  themesSelfImages: `${prefix}/users/self/themes/images`,
  themesSelfImagesId: (id: string) => `${prefix}/users/self/themes/images/${id}`,
  library: `${prefix}/themes/library`,
};

/** URL of an uploaded theme image. Requests are authenticated with the session cookie. */
export function themeImageUrl(imageId: string) {
  return routes.themesSelfImagesId(imageId);
}

export class UserThemesAPI extends BaseAPI {
  async getSettings() {
    return await this.requests.get<UserThemeSettings>(routes.themesSelf);
  }

  async updateSettings(payload: UserThemeSettings) {
    return await this.requests.put<UserThemeSettings, UserThemeSettings>(routes.themesSelf, payload);
  }

  async resetSettings() {
    return await this.requests.delete<UserThemeSettings>(routes.themesSelf);
  }

  async uploadImage(file: File) {
    const form = new FormData();
    form.append("image", file);
    return await this.requests.post<UserThemeImage>(routes.themesSelfImages, form);
  }

  async getLibrary() {
    return await this.requests.get<LibraryTheme[]>(routes.library);
  }

  async deleteImage(imageId: string) {
    return await this.requests.delete(routes.themesSelfImagesId(imageId));
  }
}
