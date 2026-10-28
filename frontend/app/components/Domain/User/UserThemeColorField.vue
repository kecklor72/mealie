<template>
  <v-text-field
    :model-value="text"
    :label="label"
    :placeholder="placeholderColor"
    :persistent-placeholder="clearable"
    :rules="[validate]"
    density="compact"
    variant="outlined"
    hide-details="auto"
    maxlength="7"
    spellcheck="false"
    @update:model-value="onType"
  >
    <template #prepend-inner>
      <v-menu
        v-model="menu"
        :close-on-content-click="false"
        location="bottom start"
      >
        <template #activator="{ props: activatorProps }">
          <button
            v-bind="activatorProps"
            type="button"
            class="theme-swatch"
            :style="{ backgroundColor: displayColor }"
            :aria-label="label"
          />
        </template>
        <v-card>
          <v-color-picker
            :model-value="displayColor"
            mode="hex"
            :modes="['hex']"
            show-swatches
            swatches-max-height="160"
            flat
            @update:model-value="onPick"
          />
        </v-card>
      </v-menu>
    </template>
    <template
      v-if="clearable && modelValue"
      #append-inner
    >
      <v-btn
        :icon="$globals.icons.close"
        size="x-small"
        variant="text"
        :title="$t('user-themes.use-default')"
        @click="modelValue = null"
      />
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
const HEX = /^#[0-9a-fA-F]{6}$/;

const props = defineProps({
  label: { type: String, required: true },
  /** Color shown when the value is empty (only for clearable fields) */
  defaultColor: { type: String, default: "#000000" },
  clearable: { type: Boolean, default: false },
});

const modelValue = defineModel<string | null | undefined>({ default: null });

const i18n = useI18n();
const menu = ref(false);
const text = ref(modelValue.value ?? "");

watch(modelValue, (v) => {
  if ((v ?? "") !== text.value) {
    text.value = v ?? "";
  }
});

const placeholderColor = computed(() => (props.clearable ? props.defaultColor : undefined));
const displayColor = computed(() => (modelValue.value && HEX.test(modelValue.value) ? modelValue.value : props.defaultColor));

function normalize(value: string) {
  let v = value.trim();
  if (v && !v.startsWith("#")) {
    v = `#${v}`;
  }
  return v.toUpperCase();
}

function onType(value: string) {
  text.value = value;
  const v = normalize(value);
  if (!v && props.clearable) {
    modelValue.value = null;
  }
  else if (HEX.test(v)) {
    modelValue.value = v;
  }
}

function onPick(value: string | Record<string, unknown>) {
  if (typeof value !== "string") {
    return;
  }
  // the picker may return #RRGGBBAA; drop alpha
  const v = normalize(value.slice(0, 7));
  if (HEX.test(v)) {
    modelValue.value = v;
  }
}

function validate(value: string) {
  const v = normalize(value ?? "");
  if (!v && props.clearable) {
    return true;
  }
  return HEX.test(v) || i18n.t("user-themes.invalid-color");
}
</script>

<style scoped>
.theme-swatch {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid rgba(var(--v-border-color), 0.4);
  cursor: pointer;
  flex-shrink: 0;
  margin-right: 6px;
}
</style>
