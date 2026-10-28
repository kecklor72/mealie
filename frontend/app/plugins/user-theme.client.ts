import type { ThemeInstance } from "vuetify";
import type { Composer } from "vue-i18n";
import { applyCachedUserTheme, applyUserTheme, registerVuetifyTheme, useUserThemes } from "~/composables/use-user-themes";

/**
 * Applies the logged in user's active custom theme (see /user/profile/themes).
 * Plugins run in alphabetical order, so this runs after plugins/init-auth.client.ts has loaded the session.
 */
export default defineNuxtPlugin({
  name: "user-theme",
  setup(nuxtApp) {
    // Composables must be created synchronously in the plugin context (not inside hooks)
    const auth = useMealieAuth();
    const { refresh, settings } = useUserThemes(nuxtApp.$i18n as Composer);
    let started = false;

    const start = (theme: ThemeInstance) => {
      if (started) {
        return;
      }
      started = true;
      registerVuetifyTheme(theme);

      watch(
        () => auth.user.value?.id,
        async (userId) => {
          if (!userId) {
            settings.value = null;
            applyUserTheme(null);
            return;
          }

          applyCachedUserTheme(userId);
          await refresh();
        },
        { immediate: true },
      );
    };

    const existing = (nuxtApp as unknown as { $vuetify?: { theme: ThemeInstance } }).$vuetify;
    if (existing) {
      start(existing.theme);
    }
    else {
      nuxtApp.hook("vuetify:ready", vuetify => start(vuetify.theme));
    }
  },
});
