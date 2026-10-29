<template>
  <v-container class="narrow-container">
    <BasePageTitle divider>
      <template #header>
        <v-img
          width="100%"
          max-height="200px"
          max-width="200px"
          src="/svgs/manage-themes.svg"
        />
      </template>
      <template #title>
        {{ $t('user-themes.theme-library') }}
      </template>
      {{ $t('user-themes.admin-description') }}
    </BasePageTitle>

    <section class="d-flex flex-wrap align-center ga-2 mb-4">
      <h2 class="text-h5 mr-auto">
        {{ $t('user-themes.library-themes') }}
      </h2>
      <input
        ref="fileInput"
        type="file"
        accept=".zip,application/zip"
        hidden
        @change="onFile"
      >
      <BaseButton
        :loading="uploading"
        :icon="$globals.icons.upload"
        @click="fileInput?.click()"
      >
        {{ $t('user-themes.upload-theme-pack') }}
      </BaseButton>
    </section>

    <v-alert
      v-if="uploadError"
      type="error"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="uploadError = ''"
    >
      {{ uploadError }}
    </v-alert>

    <v-expansion-panels class="mb-6">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon
            start
            :icon="$globals.icons.zip"
          />
          {{ $t('user-themes.pack-help-title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p class="mb-3">
            {{ $t('user-themes.pack-help-intro') }}
          </p>
          <pre class="pack-example mb-3">{{ examplePack }}</pre>
          <p class="mb-3">
            {{ $t('user-themes.pack-help-manifest') }}
          </p>
          <pre class="pack-example mb-3">{{ exampleManifest }}</pre>
          <ul class="pack-notes">
            <li>{{ $t('user-themes.pack-help-images') }}</li>
            <li>{{ $t('user-themes.pack-help-css') }}</li>
            <li>{{ $t('user-themes.pack-help-schedule') }}</li>
            <li>{{ $t('user-themes.pack-help-multiple') }}</li>
            <li>{{ $t('user-themes.pack-help-export') }}</li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-row>
      <v-col
        v-for="item in items"
        :key="item.slug"
        cols="12"
        md="6"
      >
        <UserThemeCard
          :name="item.theme.name"
          :subtitle="item.description"
          :image="item.theme.backgroundImageUrl ?? null"
          :light="item.theme.light"
          :dark="item.theme.dark"
          :schedule="item.schedule ?? null"
          :class="{ 'library-item--disabled': !item.enabled }"
        >
          <template #actions>
            <div class="w-100">
              <div class="d-flex flex-wrap align-center ga-2 mb-2">
                <v-chip
                  size="small"
                  :color="item.builtin ? 'info' : 'secondary'"
                  variant="tonal"
                >
                  {{ item.builtin ? $t('user-themes.built-in') : $t('user-themes.uploaded') }}
                </v-chip>
                <v-spacer />
                <v-switch
                  :model-value="item.enabled"
                  color="success"
                  hide-details
                  density="compact"
                  inset
                  :label="item.enabled ? $t('user-themes.enabled') : $t('user-themes.disabled')"
                  @update:model-value="v => setEnabled(item, !!v)"
                />
              </div>
              <div class="d-flex flex-wrap align-center ga-2">
                <v-text-field
                  v-model="scheduleDraft[item.slug]!.start"
                  :label="$t('user-themes.schedule-start')"
                  placeholder="MM-DD"
                  :rules="[validateMonthDay]"
                  density="compact"
                  variant="outlined"
                  hide-details="auto"
                  maxlength="5"
                  class="schedule-field"
                />
                <v-text-field
                  v-model="scheduleDraft[item.slug]!.end"
                  :label="$t('user-themes.schedule-end')"
                  placeholder="MM-DD"
                  :rules="[validateMonthDay]"
                  density="compact"
                  variant="outlined"
                  hide-details="auto"
                  maxlength="5"
                  class="schedule-field"
                />
                <v-btn
                  variant="text"
                  color="primary"
                  size="small"
                  :disabled="!scheduleChanged(item)"
                  @click="saveSchedule(item)"
                >
                  {{ $t('general.save') }}
                </v-btn>
              </div>
              <div class="d-flex flex-wrap align-center mt-2">
                <v-btn
                  variant="text"
                  size="small"
                  :prepend-icon="$globals.icons.download"
                  @click="exportPack(item)"
                >
                  {{ $t('user-themes.download-pack') }}
                </v-btn>
                <v-spacer />
                <v-btn
                  v-if="!item.builtin"
                  variant="text"
                  size="small"
                  color="error"
                  :prepend-icon="$globals.icons.delete"
                  @click="confirmDelete(item)"
                >
                  {{ $t('general.delete') }}
                </v-btn>
              </div>
            </div>
          </template>
        </UserThemeCard>
      </v-col>
    </v-row>

    <BaseDialog
      v-model="deleteDialog"
      :title="$t('user-themes.delete-theme')"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="deleteConfirmed"
    >
      <v-card-text>
        {{ $t('user-themes.delete-library-theme-confirm', { name: deleteTarget?.theme.name ?? '' }) }}
      </v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import { useAdminApi } from "~/composables/api";
import { useDownloader } from "~/composables/api/use-downloader";
import { alert } from "~/composables/use-toast";
import { useUserThemes } from "~/composables/use-user-themes";
import type { LibraryTheme } from "~/lib/api/types/user";

definePageMeta({
  layout: "admin",
});

const i18n = useI18n();
useSeoMeta({ title: i18n.t("user-themes.theme-library") });

const api = useAdminApi();
const download = useDownloader();
const { refresh: refreshUserThemes } = useUserThemes();

const items = ref<LibraryTheme[]>([]);
const scheduleDraft = reactive<Record<string, { start: string; end: string }>>({});
const MONTH_DAY = /^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$/;

async function load() {
  const { data } = await api.themeLibrary.getAll();
  if (data) {
    items.value = data;
    for (const item of data) {
      scheduleDraft[item.slug] = { start: item.schedule?.start ?? "", end: item.schedule?.end ?? "" };
    }
  }
}

onMounted(load);

/** Keep the user's own Themes page and the applied theme in sync with library changes */
async function changed() {
  await Promise.all([load(), refreshUserThemes()]);
}

// ----- upload

const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const uploadError = ref("");

function errorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail;
  return detail?.message || i18n.t("user-themes.upload-failed");
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) {
    return;
  }

  uploading.value = true;
  uploadError.value = "";
  const { data, error } = await api.themeLibrary.importPack(file);
  uploading.value = false;

  if (data) {
    const names = data.imported.map(t => t.theme.name).join(", ");
    alert.success(i18n.t("user-themes.upload-success", { names }));
    await changed();
  }
  else {
    uploadError.value = errorMessage(error);
  }
}

// ----- enable / schedule

async function setEnabled(item: LibraryTheme, enabled: boolean) {
  const { data } = await api.themeLibrary.update(item.slug, { enabled });
  if (!data) {
    alert.error(i18n.t("user-themes.theme-save-failed"));
  }
  await changed();
}

function validateMonthDay(value: string) {
  return !value || MONTH_DAY.test(value) || i18n.t("user-themes.invalid-month-day");
}

function scheduleChanged(item: LibraryTheme) {
  const draft = scheduleDraft[item.slug];
  return !!draft && (draft.start !== (item.schedule?.start ?? "") || draft.end !== (item.schedule?.end ?? ""));
}

async function saveSchedule(item: LibraryTheme) {
  const draft = scheduleDraft[item.slug];
  if (!draft) {
    return;
  }
  const start = draft.start.trim();
  const end = draft.end.trim();

  if (!start && !end) {
    await api.themeLibrary.update(item.slug, { clearSchedule: true });
  }
  else if (MONTH_DAY.test(start) && MONTH_DAY.test(end)) {
    const { data } = await api.themeLibrary.update(item.slug, { schedule: { start, end } });
    if (!data) {
      alert.error(i18n.t("user-themes.theme-save-failed"));
    }
  }
  else {
    alert.error(i18n.t("user-themes.invalid-month-day"));
    return;
  }
  alert.success(i18n.t("user-themes.theme-saved"));
  await changed();
}

// ----- export / delete

function exportPack(item: LibraryTheme) {
  download(api.themeLibrary.exportUrl(item.slug), `${item.slug}.zip`);
}

const deleteDialog = ref(false);
const deleteTarget = ref<LibraryTheme | null>(null);

function confirmDelete(item: LibraryTheme) {
  deleteTarget.value = item;
  deleteDialog.value = true;
}

async function deleteConfirmed() {
  if (!deleteTarget.value) {
    return;
  }
  const { error } = await api.themeLibrary.delete(deleteTarget.value.slug);
  if (error) {
    alert.error(errorMessage(error));
  }
  else {
    alert.success(i18n.t("user-themes.theme-deleted"));
  }
  deleteTarget.value = null;
  await changed();
}

// ----- help

const examplePack = `my-theme.zip
├── theme.json
├── style.css          (optional)
├── background.jpg     (optional)
└── sidebar.jpg        (optional)`;

const exampleManifest = `{
  "id": "spring",
  "name": "Spring",
  "description": "Fresh greens and pastels",
  "light": { "primary": "#4CAF50", "secondary": "#F48FB1", "accent": "#81D4FA" },
  "dark":  { "primary": "#81C784", "background": "#102016", "surface": "#18301F" },
  "fontHeading": "Quicksand",
  "fontBody": "Nunito",
  "css": "style.css",
  "backgroundImage": "background.jpg",
  "sidebarImage": "sidebar.jpg",
  "backgroundDim": 0.2,
  "panelOpacity": 0.6,
  "cardOpacity": 0.85,
  "schedule": { "start": "03-20", "end": "04-30" }
}`;
</script>

<style scoped>
.pack-example {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8rem;
  background: rgba(var(--v-theme-on-surface), 0.06);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre;
}
.pack-notes {
  padding-left: 20px;
}
.pack-notes li {
  margin-bottom: 4px;
}
.schedule-field {
  max-width: 130px;
}
.library-item--disabled {
  opacity: 0.6;
}
</style>
