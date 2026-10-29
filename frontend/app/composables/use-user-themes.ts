import type { ThemeInstance } from "vuetify";
import type { Composer } from "vue-i18n";
import type { LibraryTheme, ThemeSchedule, UserTheme, UserThemeColors, UserThemeSettings } from "~/lib/api/types/user";
import { useUserApi } from "~/composables/api";
import { themeImageUrl } from "~/lib/api/user/user-themes";

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
    backgroundImage: null,
    sidebarImage: null,
    backgroundDim: 0.3,
    panelOpacity: 0.75,
    cardOpacity: 0.9,
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

const IMAGE_ID_PATTERN = /^[a-f0-9]{32}$/;
const LIBRARY_IMAGE_URL_PATTERN = /^\/api\/themes\/library\/[a-z0-9][a-z0-9-]{0,47}\/files\/[a-z0-9][a-z0-9_-]{0,63}\.webp$/;

/** Resolves a theme image: an uploaded image (by id) wins over an image from the theme library (by url) */
export function resolveThemeImage(id: string | null | undefined, url: string | null | undefined): string | null {
  if (id && IMAGE_ID_PATTERN.test(id)) {
    return themeImageUrl(id);
  }
  if (url && LIBRARY_IMAGE_URL_PATTERN.test(url)) {
    return url;
  }
  return null;
}

function clamp(value: number | undefined, min: number, max: number, fallback: number) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, value));
}

function buildBackgroundCss(theme: UserTheme | null): string {
  const bg = resolveThemeImage(theme?.backgroundImage, theme?.backgroundImageUrl);
  const side = resolveThemeImage(theme?.sidebarImage, theme?.sidebarImageUrl);
  if (!bg && !side) {
    return "";
  }

  const dim = clamp(theme?.backgroundDim, 0, 0.95, 0.3);
  const panel = clamp(theme?.panelOpacity, 0, 1, 0.75);
  const card = clamp(theme?.cardOpacity, 0, 1, 0.9);
  const panelBg = `rgba(var(--v-theme-surface), ${panel})`;
  let css = "";

  if (bg) {
    css += `
.v-application {
  background-color: rgb(var(--v-theme-background)) !important;
  background-image: linear-gradient(rgba(0, 0, 0, ${dim}), rgba(0, 0, 0, ${dim})), url("${bg}") !important;
  background-size: cover !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
  background-attachment: fixed !important;
}
.v-application .v-main { background: transparent !important; }
.v-application .v-main .v-card { background-color: rgba(var(--v-theme-surface), ${card}) !important; }`;
  }

  css += `
.v-application .v-app-bar.v-toolbar {
  background-color: ${panelBg} !important;
  backdrop-filter: blur(6px);
}
.v-application .v-navigation-drawer {
  background-color: ${panelBg} !important;
  backdrop-filter: blur(6px);
}`;

  if (side) {
    css += `
.v-application .v-navigation-drawer {
  background-image: linear-gradient(${panelBg}, ${panelBg}), url("${side}") !important;
  background-size: cover !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
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

  const css = `${buildBackgroundCss(theme)}\n${buildFontCss(theme)}\n${theme?.customCss ?? ""}`.trim();
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

export const LIBRARY_PREFIX = "lib:";

function monthDay(date: Date) {
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** True when `date` falls inside a yearly schedule. Schedules may wrap around the new year (e.g. 12-20 to 01-05). */
export function isInSchedule(schedule: ThemeSchedule | null | undefined, date = new Date()) {
  if (!schedule?.start || !schedule?.end) {
    return false;
  }
  const today = monthDay(date);
  if (schedule.start <= schedule.end) {
    return today >= schedule.start && today <= schedule.end;
  }
  return today >= schedule.start || today <= schedule.end;
}

/** The library theme that's scheduled for today, if any */
export function getSeasonalTheme(library: LibraryTheme[], date = new Date()): LibraryTheme | null {
  return library.find(t => t.enabled !== false && isInSchedule(t.schedule, date)) ?? null;
}

/** Resolves an active theme id (a user's own theme, or `lib:<slug>`) to a theme */
export function findTheme(id: string | null | undefined, themes: UserTheme[], library: LibraryTheme[]): UserTheme | null {
  if (!id) {
    return null;
  }
  if (id.startsWith(LIBRARY_PREFIX)) {
    return library.find(t => t.theme.id === id)?.theme ?? null;
  }
  return themes.find(t => t.id === id) ?? null;
}

export function useUserThemes(i18n?: Composer) {
  const api = useUserApi(i18n);
  const auth = useMealieAuth();
  const settings = useState<UserThemeSettings | null>("user-theme-settings", () => null);
  const library = useState<LibraryTheme[]>("user-theme-library", () => []);
  const loading = useState<boolean>("user-theme-settings-loading", () => false);

  const themes = computed(() => settings.value?.themes ?? []);
  const activeThemeId = computed(() => settings.value?.activeThemeId ?? null);
  const autoSeasonal = computed(() => settings.value?.autoSeasonal !== false);

  /** The theme the user picked */
  const chosenTheme = computed(() => findTheme(activeThemeId.value, themes.value, library.value));

  /** The holiday/seasonal theme in effect today, if the user has automatic themes turned on */
  const seasonalTheme = computed(() => (autoSeasonal.value ? getSeasonalTheme(library.value) : null));

  /** The theme that's actually applied */
  const activeTheme = computed(() => seasonalTheme.value?.theme ?? chosenTheme.value);

  function applyActive() {
    applyUserTheme(activeTheme.value);
    const userId = auth.user.value?.id;
    if (userId) {
      writeCache(userId, activeTheme.value);
    }
  }

  async function refresh() {
    loading.value = true;
    const [settingsRes, libraryRes] = await Promise.all([api.userThemes.getSettings(), api.userThemes.getLibrary()]);
    loading.value = false;
    if (libraryRes.data) {
      library.value = libraryRes.data;
    }
    if (settingsRes.data) {
      settings.value = settingsRes.data;
    }
    if (settingsRes.data || libraryRes.data) {
      applyActive();
    }
    return settingsRes.data;
  }

  function currentSettings(): UserThemeSettings {
    return {
      activeThemeId: activeThemeId.value,
      autoSeasonal: autoSeasonal.value,
      themes: themes.value,
    };
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
    return await save({ ...currentSettings(), activeThemeId: themeId });
  }

  async function setAutoSeasonal(value: boolean) {
    return await save({ ...currentSettings(), autoSeasonal: value });
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
    return await save({ ...currentSettings(), activeThemeId: makeActive ? theme.id : activeThemeId.value, themes: list });
  }

  async function deleteTheme(themeId: string) {
    const list = themes.value.filter(t => t.id !== themeId);
    const active = activeThemeId.value === themeId ? null : activeThemeId.value;
    return await save({ ...currentSettings(), activeThemeId: active, themes: list });
  }

  return {
    settings,
    library,
    loading,
    themes,
    activeThemeId,
    autoSeasonal,
    chosenTheme,
    seasonalTheme,
    activeTheme,
    refresh,
    save,
    setActive,
    setAutoSeasonal,
    upsertTheme,
    deleteTheme,
    applyActive,
  };
}
