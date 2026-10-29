<template>
  <v-card
    variant="outlined"
    class="theme-image-field"
  >
    <div
      class="theme-image-field__preview"
      :class="{ 'theme-image-field__preview--tall': tall }"
    >
      <img
        v-if="previewUrl"
        :src="previewUrl"
        :alt="label"
      >
      <div
        v-else
        class="theme-image-field__empty text-medium-emphasis"
      >
        <v-icon
          :icon="$globals.icons.fileImage"
          size="32"
        />
      </div>
    </div>
    <v-card-text class="pb-1">
      <div class="text-subtitle-2">
        {{ label }}
      </div>
      <div class="text-caption text-medium-emphasis">
        {{ hint }}
      </div>
    </v-card-text>
    <v-card-actions>
      <input
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif,image/avif,image/heic"
        hidden
        @change="onFile"
      >
      <v-btn
        variant="text"
        color="primary"
        :loading="uploading"
        :prepend-icon="$globals.icons.upload"
        @click="fileInput?.click()"
      >
        {{ previewUrl ? $t('user-themes.replace-image') : $t('user-themes.upload-image') }}
      </v-btn>
      <v-spacer />
      <v-btn
        v-if="previewUrl"
        variant="text"
        :prepend-icon="$globals.icons.delete"
        @click="clear"
      >
        {{ $t('user-themes.remove-image') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import { resolveThemeImage } from "~/composables/use-user-themes";

defineProps({
  label: { type: String, required: true },
  hint: { type: String, default: "" },
  tall: { type: Boolean, default: false },
});

/** ID of an image the user uploaded */
const modelValue = defineModel<string | null | undefined>({ default: null });
/** Image from the theme library (used when no image was uploaded) */
const libraryUrl = defineModel<string | null | undefined>("libraryUrl", { default: null });

const previewUrl = computed(() => resolveThemeImage(modelValue.value, libraryUrl.value));

function clear() {
  modelValue.value = null;
  libraryUrl.value = null;
}

const i18n = useI18n();
const api = useUserApi();
const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) {
    return;
  }

  uploading.value = true;
  const { data } = await api.userThemes.uploadImage(file);
  uploading.value = false;

  if (data?.id) {
    modelValue.value = data.id;
    libraryUrl.value = null;
  }
  else {
    alert.error(i18n.t("user-themes.image-upload-failed"));
  }
}
</script>

<style scoped>
.theme-image-field__preview {
  height: 120px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  overflow: hidden;
}
.theme-image-field__preview--tall img {
  object-position: left center;
}
.theme-image-field__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.theme-image-field__empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
