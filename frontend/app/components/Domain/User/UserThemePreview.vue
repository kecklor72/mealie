<template>
  <v-card
    variant="outlined"
    class="theme-preview"
  >
    <v-toolbar
      color="primary"
      density="compact"
    >
      <v-toolbar-title class="text-subtitle-1">
        Mealie
      </v-toolbar-title>
      <v-spacer />
      <v-btn
        :icon="isDark ? $globals.icons.weatherSunny : $globals.icons.weatherNight"
        :title="isDark ? $t('user-themes.light-mode') : $t('user-themes.dark-mode')"
        @click="toggleDark()"
      />
    </v-toolbar>
    <v-card-text>
      <h3 class="text-h5 mb-1">
        {{ $t('user-themes.preview-heading') }}
      </h3>
      <p class="text-body-2 mb-4">
        {{ $t('user-themes.preview-body') }}
      </p>
      <v-text-field
        :label="$t('user-themes.preview-input')"
        :prepend-inner-icon="$globals.icons.search"
        density="compact"
        variant="outlined"
        color="primary"
        hide-details
        class="mb-4"
      />
      <div class="d-flex flex-wrap ga-2 mb-4">
        <v-btn color="primary">
          {{ $t('user-themes.color-primary') }}
        </v-btn>
        <v-btn color="secondary">
          {{ $t('user-themes.color-secondary') }}
        </v-btn>
        <v-btn
          color="accent"
          variant="outlined"
        >
          {{ $t('user-themes.color-accent') }}
        </v-btn>
      </div>
      <div class="d-flex flex-wrap ga-2 mb-4">
        <v-chip
          v-for="c in chipColors"
          :key="c"
          :color="c"
          variant="flat"
          size="small"
        >
          {{ $t(`user-themes.color-${c}`) }}
        </v-chip>
      </div>
      <v-alert
        type="info"
        density="compact"
        variant="tonal"
        class="mb-2"
      >
        {{ $t('user-themes.preview-description') }}
      </v-alert>
      <v-progress-linear
        model-value="65"
        color="accent"
        rounded
        height="6"
      />
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { useDark } from "@vueuse/core";

const isDark = useDark();
const toggleDark = useToggleDarkMode();
const chipColors = ["success", "info", "warning", "error"];
</script>

<style scoped>
.theme-preview {
  overflow: hidden;
}
</style>
