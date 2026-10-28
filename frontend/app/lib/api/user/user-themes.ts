import { BaseAPI } from "../base/base-clients";
import type { UserThemeSettings } from "~/lib/api/types/user";

const prefix = "/api";

const routes = {
  themesSelf: `${prefix}/users/self/themes`,
};

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
}
