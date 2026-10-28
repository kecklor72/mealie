import type { ThemeInstance } from "vuetify";
import type { Composer } from "vue-i18n";
import type { UserTheme, UserThemeColors, UserThemeSettings } from "~/lib/api/types/user";
import { useUserApi } from "~/composables/api";

/**
 * Per-user theme manager.
 *
 * Themes are stored server side (`/api/users/self/themes`) and applied at runtime by
 * mutating Vuetify's light/dark theme colors, plus an injected <style> tag for fonts
 * and custom CSS. The active theme is also cached in localStorage so it can be applied
 * instantly on page load, before the API responds.
 */

export const THEME_COLOR_KEYS = [
  "primary",
  "secondary",
  "accent",
  "success",
  "info",
  "warning",
  "error",
  "background",
  "surface",
] as const;

export type ThemeColorKey = (typeof THEME_COLOR_KEYS)[number];
export type ThemeMode = "light" | "dark";
export type FullThemeColors = Record<ThemeColorKey, string>;

const STYLE_ELEMENT_ID = "mealie-user-theme-style";
const FONT_LINK_ID_PREFIX = "mealie-user-theme-font-";
const CACHE_KEY = "mealie-user-theme-cache";

/** Fonts that are available without loading anything from Google Fonts */
export const SYSTEM_FONTS: Record<string, string> = {
  "System UI": "system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif",
  "Serif": "Georgia, Cambria, \"Times New Roman\", Times, serif",
  "Monospace": "ui-monospace, SFMono-Regular, Menlo, Consolas, \"Liberation Mono\", monospace",
};

/** Suggested Google Fonts. Any other Google Font name can be typed in as well. */
export const SUGGESTED_FONTS = [
  "Atkinson Hyperlegible",
  "Bitter",
  "Caveat",
  "Comfortaa",
  "DM Sans",
  "Fira Sans",
  "Inter",
  "Josefin Sans",
  "Lato",
  "Libre Baskerville",
  "Lora",
  "Merriweather",
  "Montserrat",
  "Nunito",
  "Open Sans",
  "Outfit",
  "Patrick Hand",
  "Playfair Display",
  "Poppins",
  "Quicksand",
  "Raleway",
  "Roboto Slab",
  "Source Sans 3",
  "Space Grotesk",
  "Work Sans",
];

export const FONT_NAME_PATTERN = /^[A-Za-z0-9 -]{1,64}$/;

// Server/default colors, captured from Vuetify before any user theme is applied
let baseColors: Record<ThemeMode, FullThemeColors> | null = null;
let vuetifyTheme: ThemeInstance | null = null;

const FALLBACK_BACKGROUNDS: Record<ThemeMode, { background: string; surface: string }> = {
  light: { background: "#FFFFFF", surface: "#FFFFFF" },
  dark: { background: "#1E1E1E", surface: "#1E1E1E" },
};

function captureBaseColors(theme: ThemeInstance) {
  if (baseColors) {
    return;
  }

  const capture = (mode: ThemeMode): FullThemeColors => {
    const colors = (theme.themes.value[mode]?.colors ?? {}) as Record<string, string | undefined>;
    const out = {} as FullThemeColors;
    for (const key of THEME_COLOR_KEYS) {
      out[key] = colors[key] ?? FALLBACK_BACKGROUNDS[mode][key as "background" | "surface"] ?? "#000000";
    }
    return out;
  };

  baseColors = { light: capture("light"), dark: capture("dark") };
}

export function registerVuetifyTheme(theme: ThemeInstance) {
  vuetifyTheme = theme;
  captureBaseColors(theme);
}

/** The colors Mealie uses when no user theme is active (server defaults / THEME_* env vars) */
export function getBaseColors(mode: ThemeMode): FullThemeColors {
  if (!baseColors && vuetifyTheme) {
    captureBaseColors(vuetifyTheme);
  }
  return { ...(baseColors?.[mode] ?? { ...FALLBACK_BACKGROUNDS[mode], primary: "#E58325", accent: "#007A99", secondary: "#973542", success: "#43A047", info: "#1976D2", warning: "#FF6D00", error: "#EF5350" }) };
}

export function newThemeId() {
  return `theme-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/** Returns a brand new theme using the server default colors */
export function createDefaultTheme(name: string): UserTheme {
  const light = getBaseColors("light");
  const dark = getBaseColors("dark");
  return {
    id: newThemeId(),
    name,
    light: { ...light, background: null, surface: null },
    dark: { ...dark, background: null, surface: null },
    fontBody: null,
    fontHeading: null,
    customCss: "",
  };
}

function fontStack(name: string | null | undefined): string | null {
  if (!name || !FONT_NAME_PATTERN.test(name)) {
    return null;
  }
  return SYSTEM_FONTS[name] ?? `"${name}", "Roboto", sans-serif`;
}

function applyColors(theme: UserTheme | null) {
  if (!vuetifyTheme) {
    return;
  }

  for (const mode of ["light", "dark"] as ThemeMode[]) {
    const target = vuetifyTheme.themes.value[mode];
    if (!target) {
      continue;
    }

    const defaults = getBaseColors(mode);
    const custom = (theme?.[mode] ?? {}) as UserThemeColors;
    for (const key of THEME_COLOR_KEYS) {
      const value = custom[key] || defaults[key];
      if (target.colors[key] !== value) {
        target.colors[key] = value;
      }
    }
  }
}

function loadGoogleFont(name: string) {
  if (SYSTEM_FONTS[name] || !FONT_NAME_PATTERN.test(name)) {
    return;
  }

  const id = `${FONT_LINK_ID_PREFIX}${name.replace(/\s+/g, "-").toLowerCase()}`;
  if (document.getElementById(id)) {
    return;
  }

  const family = encodeURIComponent(name).replace(/%20/g, "+");
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  // Not every font has every weight; Google returns an error for missing weights,
  // so fall back to the plain family if the weighted request fails.
  link.href = `https://fonts.googleapis.com/css2?family=${family}:wght@400;500;700&display=swap`;
  link.onerror = () => {
    link.onerror = null;
    link.href = `https://fonts.googleapis.com/css2?family=${family}&display=swap`;
  };
  document.head.appendChild(link);
}

function buildFontCss(theme: UserTheme | null): string {
  const body = fontStack(theme?.fontBody);
  const heading = fontStack(theme?.fontHeading) ?? body;
  let css = "";

  if (body) {
    css += `
.v-application, .v-application .v-btn, .v-application input, .v-application textarea,
.v-application .v-field, .v-application .v-label, .v-application .v-list-item-title,
.v-application [class*="text-body"], .v-application [class*="text-subtitle"],
.v-application .text-caption, .v-application .text-button, .v-application .text-overline {
  font-family: ${body} !important;
}`;
  }

  if (heading) {
    css += `
.v-application h1, .v-application h2, .v-application h3, .v-application h4, .v-application h5, .v-application h6,
.v-application [class*="text-h"], .v-application [class*="text-display"], .v-application [class*="text-headline"],
.v-application [class*="text-title"], .v-application .v-card-title, .v-application .v-toolbar-title {
  font-family: ${heading} !important;
}`;
  }

  return css;
}

function applyStyles(theme: UserTheme | null) {
  if (typeof document === "undefined") {
    return;
  }

  for (const font of [theme?.fontBody, theme?.fontHeading]) {
    if (font) {
      loadGoogleFont(font);
    }
  }

  const css = `${buildFontCss(theme)}\n${theme?.customCss ?? ""}`.trim();
  let el = document.getElementById(STYLE_ELEMENT_ID) as HTMLStyleElement | null;

  if (!css) {
    el?.remove();
    return;
  }

  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ELEMENT_ID;
  }
  // textContent (not innerHTML) so the CSS can never be interpreted as markup.
  el.textContent = css;
  // Always (re)append so user CSS comes after all app styles and wins ties
  document.head.appendChild(el);
}

/** Applies a theme to the running app. Pass `null` to restore the default theme. */
export function applyUserTheme(theme: UserTheme | null) {
  applyColors(theme);
  applyStyles(theme);
}

function readCache(): { userId: string; theme: UserTheme | null } | null {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  }
  catch {
    return null;
  }
}

function writeCache(userId: string, theme: UserTheme | null) {
  try {
    window.localStorage.setItem(CACHE_KEY, JSON.stringify({ userId, theme }));
  }
  catch {
    // storage unavailable (private mode, etc). Not critical.
  }
}

/** Instantly applies the cached theme for this user, if any, to avoid a flash of the default theme */
export function applyCachedUserTheme(userId: string) {
  const cached = readCache();
  if (cached && cached.userId === userId && cached.theme) {
    applyUserTheme(cached.theme);
  }
}

export function getActiveTheme(settings: UserThemeSettings | null): UserTheme | null {
  if (!settings?.activeThemeId) {
    return null;
  }
  return settings.themes?.find(t => t.id === settings.activeThemeId) ?? null;
}

export function useUserThemes(i18n?: Composer) {
  const api = useUserApi(i18n);
  const auth = useMealieAuth();
  const settings = useState<UserThemeSettings | null>("user-theme-settings", () => null);
  const loading = useState<boolean>("user-theme-settings-loading", () => false);

  const themes = computed(() => settings.value?.themes ?? []);
  const activeThemeId = computed(() => settings.value?.activeThemeId ?? null);
  const activeTheme = computed(() => getActiveTheme(settings.value));

  function applyActive() {
    applyUserTheme(activeTheme.value);
    const userId = auth.user.value?.id;
    if (userId) {
      writeCache(userId, activeTheme.value);
    }
  }

  async function refresh() {
    loading.value = true;
    const { data } = await api.userThemes.getSettings();
    loading.value = false;
    if (data) {
      settings.value = data;
      applyActive();
    }
    return data;
  }

  async function save(newSettings: UserThemeSettings) {
    const { data, error } = await api.userThemes.updateSettings(newSettings);
    if (data) {
      settings.value = data;
      applyActive();
    }
    return { data, error };
  }

  async function setActive(themeId: string | null) {
    return await save({ activeThemeId: themeId, themes: themes.value });
  }

  async function upsertTheme(theme: UserTheme, makeActive = false) {
    const list = [...themes.value];
    const idx = list.findIndex(t => t.id === theme.id);
    if (idx >= 0) {
      list[idx] = theme;
    }
    else {
      list.push(theme);
    }
    return await save({ activeThemeId: makeActive ? theme.id : activeThemeId.value, themes: list });
  }

  async function deleteTheme(themeId: string) {
    const list = themes.value.filter(t => t.id !== themeId);
    const active = activeThemeId.value === themeId ? null : activeThemeId.value;
    return await save({ activeThemeId: active, themes: list });
  }

  return {
    settings,
    loading,
    themes,
    activeThemeId,
    activeTheme,
    refresh,
    save,
    setActive,
    upsertTheme,
    deleteTheme,
    applyActive,
  };
}
