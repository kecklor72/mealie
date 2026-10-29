<template>
  <v-card
    variant="outlined"
    class="theme-card"
    :class="{ 'theme-card--active': active }"
  >
    <img
      v-if="image"
      :src="image"
      :alt="name"
      class="theme-card__image"
      loading="lazy"
    >
    <div class="swatch-strip">
      <span
        v-for="(c, i) in lightSwatches"
        :key="`l-${i}`"
        :style="{ backgroundColor: c }"
      />
    </div>
    <div class="swatch-strip swatch-strip--dark">
      <span
        v-for="(c, i) in darkSwatches"
        :key="`d-${i}`"
        :style="{ backgroundColor: c }"
      />
    </div>
    <v-card-title class="d-flex align-center flex-wrap ga-1">
      <span class="text-truncate mr-1">{{ name }}</span>
      <v-chip
        v-if="active"
        color="success"
        size="small"
      >
        {{ $t('user-themes.active') }}
      </v-chip>
      <v-chip
        v-else-if="selected"
        color="success"
        variant="outlined"
        size="small"
      >
        {{ $t('user-themes.your-pick') }}
      </v-chip>
      <v-chip
        v-if="scheduleLabel"
        size="small"
        variant="tonal"
        :prepend-icon="$globals.icons.calendar"
      >
        {{ scheduleLabel }}
      </v-chip>
    </v-card-title>
    <v-card-subtitle class="theme-card__subtitle">
      {{ subtitle }}
    </v-card-subtitle>
    <v-card-actions>
      <slot name="actions" />
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import type { ThemeSchedule, UserThemeColors } from "~/lib/api/types/user";
import { getBaseColors, type ThemeMode } from "~/composables/use-user-themes";

const props = defineProps({
  name: { type: String, required: true },
  subtitle: { type: String, default: "" },
  image: { type: String as PropType<string | null>, default: null },
  light: { type: Object as PropType<UserThemeColors | undefined>, default: undefined },
  dark: { type: Object as PropType<UserThemeColors | undefined>, default: undefined },
  schedule: { type: Object as PropType<ThemeSchedule | null>, default: null },
  active: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
});

const i18n = useI18n();

function swatches(colors: UserThemeColors | undefined, mode: ThemeMode) {
  const c = { ...getBaseColors(mode) } as Record<string, string>;
  for (const [k, v] of Object.entries(colors ?? {})) {
    if (v) {
      c[k] = v as string;
    }
  }
  return [c.background, c.primary, c.secondary, c.accent, c.success, c.warning, c.error];
}

const lightSwatches = computed(() => swatches(props.light, "light"));
const darkSwatches = computed(() => swatches(props.dark, "dark"));

function formatMonthDay(value: string) {
  const [month, day] = value.split("-").map(Number);
  return new Date(2000, (month ?? 1) - 1, day ?? 1).toLocaleDateString(i18n.locale.value, { month: "short", day: "numeric" });
}

const scheduleLabel = computed(() =>
  props.schedule ? `${formatMonthDay(props.schedule.start)} – ${formatMonthDay(props.schedule.end)}` : "",
);
</script>

<style scoped>
.theme-card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.theme-card--active {
  border: 2px solid rgb(var(--v-theme-success));
}
.theme-card__image {
  display: block;
  width: 100%;
  height: 110px;
  object-fit: cover;
}
.theme-card__subtitle {
  white-space: normal;
  flex-grow: 1;
}
.swatch-strip {
  display: flex;
  height: 22px;
}
.swatch-strip span {
  flex: 1;
}
.swatch-strip--dark {
  height: 14px;
}
</style>
