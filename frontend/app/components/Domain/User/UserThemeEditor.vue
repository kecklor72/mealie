<template>
  <v-form
    ref="form"
    @submit.prevent
  >
    <v-text-field
      v-model="theme.name"
      :label="$t('user-themes.theme-name')"
      :rules="[(v: string) => !!v?.trim() || $t('general.a-name-is-required')]"
      maxlength="64"
      variant="outlined"
      density="comfortable"
      class="mb-2"
    />

    <h3 class="text-h6 mb-2">
      {{ $t('user-themes.colors') }}
    </h3>
    <v-tabs
      v-model="mode"
      color="primary"
      density="compact"
      class="mb-4"
    >
      <v-tab value="light">
        <v-icon
          start
          :icon="$globals.icons.weatherSunny"
        />
        {{ $t('user-themes.light-mode') }}
      </v-tab>
      <v-tab value="dark">
        <v-icon
          start
          :icon="$globals.icons.weatherNight"
        />
        {{ $t('user-themes.dark-mode') }}
      </v-tab>
    </v-tabs>

    <v-row
      :key="mode"
      dense
    >
      <v-col
        v-for="key in THEME_COLOR_KEYS"
        :key="`${mode}-${key}`"
        cols="12"
        sm="6"
      >
        <UserThemeColorField
          v-model="currentColors[key]"
          :label="$t(`user-themes.color-${key}`)"
          :default-color="baseColors[mode][key]"
          :clearable="key === 'background' || key === 'surface'"
        />
      </v-col>
    </v-row>
    <div class="d-flex justify-end mt-2 mb-6">
      <v-btn
        variant="text"
        size="small"
        :prepend-icon="$globals.icons.contentCopy"
        @click="copyFromOtherMode"
      >
        {{ mode === 'light' ? $t('user-themes.copy-from-dark') : $t('user-themes.copy-from-light') }}
      </v-btn>
    </div>

    <h3 class="text-h6 mb-2">
      {{ $t('user-themes.fonts') }}
    </h3>
    <v-row dense>
      <v-col
        cols="12"
        sm="6"
      >
        <v-combobox
          v-model="theme.fontBody"
          :items="fontItems"
          :label="$t('user-themes.body-font')"
          :placeholder="$t('user-themes.default-font')"
          :hint="$t('user-themes.font-hint')"
          :rules="[validateFont]"
          persistent-placeholder
          clearable
          variant="outlined"
          density="compact"
        />
      </v-col>
      <v-col
        cols="12"
        sm="6"
      >
        <v-combobox
          v-model="theme.fontHeading"
          :items="fontItems"
          :label="$t('user-themes.heading-font')"
          :placeholder="theme.fontBody || $t('user-themes.default-font')"
          :hint="$t('user-themes.font-hint')"
          :rules="[validateFont]"
          persistent-placeholder
          clearable
          variant="outlined"
          density="compact"
        />
      </v-col>
    </v-row>

    <h3 class="text-h6 mt-4 mb-1">
      {{ $t('user-themes.background') }}
    </h3>
    <p class="text-body-2 mb-3">
      {{ $t('user-themes.background-description') }}
    </p>
    <v-row dense>
      <v-col
        cols="12"
        sm="6"
      >
        <UserThemeImageField
          v-model="theme.backgroundImage"
          :label="$t('user-themes.background-image')"
          :hint="$t('user-themes.background-image-hint')"
        />
      </v-col>
      <v-col
        cols="12"
        sm="6"
      >
        <UserThemeImageField
          v-model="theme.sidebarImage"
          :label="$t('user-themes.sidebar-image')"
          :hint="$t('user-themes.sidebar-image-hint')"
          tall
        />
      </v-col>
    </v-row>
    <div
      v-if="theme.backgroundImage || theme.sidebarImage"
      class="mt-4"
    >
      <v-slider
        v-if="theme.backgroundImage"
        v-model="theme.backgroundDim"
        :label="$t('user-themes.background-dim')"
        :min="0"
        :max="0.9"
        :step="0.05"
        color="primary"
        thumb-label
        hide-details
        class="mb-2"
      >
        <template #thumb-label="{ modelValue: v }">
          {{ Math.round(v * 100) }}%
        </template>
      </v-slider>
      <v-slider
        v-model="theme.panelOpacity"
        :label="$t('user-themes.panel-opacity')"
        :min="0"
        :max="1"
        :step="0.05"
        color="primary"
        thumb-label
        hide-details
        class="mb-2"
      >
        <template #thumb-label="{ modelValue: v }">
          {{ Math.round(v * 100) }}%
        </template>
      </v-slider>
      <v-slider
        v-if="theme.backgroundImage"
        v-model="theme.cardOpacity"
        :label="$t('user-themes.card-opacity')"
        :min="0"
        :max="1"
        :step="0.05"
        color="primary"
        thumb-label
        hide-details
      >
        <template #thumb-label="{ modelValue: v }">
          {{ Math.round(v * 100) }}%
        </template>
      </v-slider>
    </div>

    <h3 class="text-h6 mt-4 mb-1">
      {{ $t('user-themes.custom-css') }}
    </h3>
    <p class="text-body-2 mb-3">
      {{ $t('user-themes.custom-css-description') }}
    </p>
    <v-textarea
      v-model="theme.customCss"
      class="theme-css"
      variant="outlined"
      rows="6"
      auto-grow
      spellcheck="false"
      placeholder=".v-card { border-radius: 16px; }"
      :counter="50000"
      :rules="[(v: string) => (v ?? '').length <= 50000 || $t('user-themes.theme-save-failed')]"
    />
  </v-form>
</template>

<script setup lang="ts">
import type { VForm } from "vuetify/components";
import type { UserTheme, UserThemeColors } from "~/lib/api/types/user";
import {
  FONT_NAME_PATTERN,
  SUGGESTED_FONTS,
  SYSTEM_FONTS,
  THEME_COLOR_KEYS,
  getBaseColors,
  type ThemeMode,
} from "~/composables/use-user-themes";

const theme = defineModel<UserTheme>({ required: true });

const i18n = useI18n();
const form = ref<VForm | null>(null);
const mode = ref<ThemeMode>("light");

const baseColors = { light: getBaseColors("light"), dark: getBaseColors("dark") };
const fontItems = [...Object.keys(SYSTEM_FONTS), ...SUGGESTED_FONTS];

// make sure both color sets exist so v-model bindings are reactive
if (!theme.value.light) theme.value.light = {};
if (!theme.value.dark) theme.value.dark = {};
// fill in background defaults for themes saved before backgrounds existed
theme.value.backgroundImage ??= null;
theme.value.sidebarImage ??= null;
theme.value.backgroundDim ??= 0.3;
theme.value.panelOpacity ??= 0.75;
theme.value.cardOpacity ??= 0.9;

const currentColors = computed<UserThemeColors>(() => theme.value[mode.value] as UserThemeColors);

function copyFromOtherMode() {
  const other: ThemeMode = mode.value === "light" ? "dark" : "light";
  theme.value[mode.value] = { ...(theme.value[other] ?? {}) };
}

function validateFont(value: string | null) {
  if (!value) {
    return true;
  }
  return FONT_NAME_PATTERN.test(value.trim()) || i18n.t("user-themes.invalid-font");
}

async function validate() {
  const result = await form.value?.validate();
  return result?.valid ?? false;
}

defineExpose({ validate });
</script>

<style scoped>
.theme-css :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  font-size: 0.85rem;
}
</style>
