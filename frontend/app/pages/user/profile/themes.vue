<template>
  <v-container :class="editing ? '' : 'narrow-container'">
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
        {{ $t('user-themes.themes') }}
      </template>
      {{ $t('user-themes.page-description') }}
    </BasePageTitle>

    <!-- Editor -->
    <section v-if="editing && draft">
      <v-row>
        <v-col
          cols="12"
          md="7"
        >
          <h2 class="text-h5 mb-4">
            {{ $t('user-themes.edit-theme') }}
          </h2>
          <UserThemeEditor
            ref="editor"
            v-model="draft"
          />
          <div class="d-flex flex-wrap ga-2 justify-end mt-2">
            <BaseButton
              cancel
              @click="cancelEdit"
            />
            <BaseButton
              save
              :loading="saving"
              @click="saveDraft(false)"
            />
            <BaseButton
              :loading="saving"
              :icon="$globals.icons.check"
              @click="saveDraft(true)"
            >
              {{ $t('user-themes.save-and-use') }}
            </BaseButton>
          </div>
        </v-col>
        <v-col
          cols="12"
          md="5"
        >
          <div class="preview-sticky">
            <h2 class="text-h5 mb-4">
              {{ $t('user-themes.preview') }}
            </h2>
            <UserThemePreview />
          </div>
        </v-col>
      </v-row>
    </section>

    <!-- Theme list -->
    <section v-else>
      <div class="d-flex flex-wrap align-center ga-2 mb-4">
        <h2 class="text-h5 mr-auto">
          {{ $t('user-themes.my-themes') }}
        </h2>
        <BaseButton
          secondary
          :icon="$globals.icons.import"
          @click="importDialog = true"
        >
          {{ $t('general.import') }}
        </BaseButton>
        <v-menu location="bottom end">
          <template #activator="{ props: menuProps }">
            <BaseButton
              v-bind="menuProps"
              create
            >
              {{ $t('user-themes.new-theme') }}
            </BaseButton>
          </template>
          <v-list density="compact">
            <v-list-item
              :prepend-icon="$globals.icons.createAlt"
              :title="$t('user-themes.default-theme')"
              @click="startNew()"
            />
            <v-divider />
            <v-list-subheader>{{ $t('user-themes.start-from-preset') }}</v-list-subheader>
            <v-list-item
              v-for="preset in THEME_PRESETS"
              :key="preset.name"
              :title="preset.name"
              @click="startNew(preset)"
            >
              <template #prepend>
                <div class="d-flex mr-3">
                  <span
                    v-for="c in swatchColors(preset.light)"
                    :key="c"
                    class="mini-swatch"
                    :style="{ backgroundColor: c }"
                  />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>

      <v-row>
        <!-- Server default -->
        <v-col
          cols="12"
          sm="6"
        >
          <v-card
            variant="outlined"
            class="theme-card"
            :class="{ 'theme-card--active': !activeThemeId }"
          >
            <div class="swatch-strip">
              <span
                v-for="c in swatchColors(defaultColors.light)"
                :key="`dl-${c}`"
                :style="{ backgroundColor: c }"
              />
            </div>
            <div class="swatch-strip swatch-strip--dark">
              <span
                v-for="c in swatchColors(defaultColors.dark)"
                :key="`dd-${c}`"
                :style="{ backgroundColor: c }"
              />
            </div>
            <v-card-title class="d-flex align-center">
              {{ $t('user-themes.default-theme') }}
              <v-chip
                v-if="!activeThemeId"
                color="success"
                size="small"
                class="ml-2"
              >
                {{ $t('user-themes.active') }}
              </v-chip>
            </v-card-title>
            <v-card-subtitle>{{ $t('user-themes.default-theme-description') }}</v-card-subtitle>
            <v-card-actions>
              <v-spacer />
              <v-btn
                v-if="activeThemeId"
                color="primary"
                variant="text"
                @click="activate(null)"
              >
                {{ $t('user-themes.use-theme') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>

        <!-- User themes -->
        <v-col
          v-for="theme in themes"
          :key="theme.id"
          cols="12"
          sm="6"
        >
          <v-card
            variant="outlined"
            class="theme-card"
            :class="{ 'theme-card--active': theme.id === activeThemeId }"
          >
            <img
              v-if="theme.backgroundImage"
              :src="themeImageUrl(theme.backgroundImage)"
              :alt="theme.name"
              class="theme-card__image"
            >
            <div class="swatch-strip">
              <span
                v-for="(c, i) in swatchColors(theme.light, 'light')"
                :key="`l-${i}`"
                :style="{ backgroundColor: c }"
              />
            </div>
            <div class="swatch-strip swatch-strip--dark">
              <span
                v-for="(c, i) in swatchColors(theme.dark, 'dark')"
                :key="`d-${i}`"
                :style="{ backgroundColor: c }"
              />
            </div>
            <v-card-title class="d-flex align-center">
              <span class="text-truncate">{{ theme.name }}</span>
              <v-chip
                v-if="theme.id === activeThemeId"
                color="success"
                size="small"
                class="ml-2"
              >
                {{ $t('user-themes.active') }}
              </v-chip>
            </v-card-title>
            <v-card-subtitle>
              {{ [theme.fontHeading, theme.fontBody].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(' / ') || $t('user-themes.default-font') }}
            </v-card-subtitle>
            <v-card-actions>
              <v-btn
                variant="text"
                :prepend-icon="$globals.icons.edit"
                @click="startEdit(theme)"
              >
                {{ $t('general.edit') }}
              </v-btn>
              <v-menu location="bottom start">
                <template #activator="{ props: menuProps }">
                  <v-btn
                    v-bind="menuProps"
                    :icon="$globals.icons.dotsVertical"
                    variant="text"
                    size="small"
                  />
                </template>
                <v-list density="compact">
                  <v-list-item
                    :prepend-icon="$globals.icons.duplicate"
                    :title="$t('user-themes.duplicate')"
                    @click="duplicate(theme)"
                  />
                  <v-list-item
                    :prepend-icon="$globals.icons.contentCopy"
                    :title="$t('user-themes.export-theme')"
                    @click="copyJson(theme)"
                  />
                  <v-list-item
                    :prepend-icon="$globals.icons.delete"
                    :title="$t('general.delete')"
                    base-color="error"
                    @click="confirmDelete(theme)"
                  />
                </v-list>
              </v-menu>
              <v-spacer />
              <v-btn
                v-if="theme.id !== activeThemeId"
                color="primary"
                variant="text"
                @click="activate(theme.id)"
              >
                {{ $t('user-themes.use-theme') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </section>

    <!-- Delete -->
    <BaseDialog
      v-model="deleteDialog"
      :title="$t('user-themes.delete-theme')"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="deleteConfirmed"
    >
      <v-card-text>
        {{ $t('user-themes.delete-theme-confirm', { name: deleteTarget?.name ?? '' }) }}
      </v-card-text>
    </BaseDialog>

    <!-- Import -->
    <BaseDialog
      v-model="importDialog"
      :title="$t('user-themes.import-theme')"
      :icon="$globals.icons.import"
      can-submit
      disable-submit-on-enter
      :submit-text="$t('general.import')"
      @submit="importTheme"
    >
      <v-card-text>
        <p class="mb-3">
          {{ $t('user-themes.import-theme-description') }}
        </p>
        <v-textarea
          v-model="importText"
          variant="outlined"
          rows="8"
          class="theme-json"
          spellcheck="false"
          placeholder="{ &quot;name&quot;: &quot;My Theme&quot;, &quot;light&quot;: { ... }, &quot;dark&quot;: { ... } }"
        />
      </v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import type { UserTheme, UserThemeColors } from "~/lib/api/types/user";
import { THEME_PRESETS, type ThemePreset } from "~/lib/user-themes/presets";
import {
  applyUserTheme,
  createDefaultTheme,
  getBaseColors,
  newThemeId,
  useUserThemes,
  type ThemeMode,
} from "~/composables/use-user-themes";
import { alert } from "~/composables/use-toast";
import { themeImageUrl } from "~/lib/api/user/user-themes";

definePageMeta({
  middleware: ["auth"],
});

const i18n = useI18n();
useSeoMeta({ title: i18n.t("user-themes.themes") });

const { themes, activeThemeId, refresh, upsertTheme, deleteTheme, setActive, applyActive } = useUserThemes();

const defaultColors = { light: getBaseColors("light"), dark: getBaseColors("dark") };

onMounted(async () => {
  await refresh();
});

// ----- swatches

function swatchColors(colors: UserThemeColors | undefined, mode: ThemeMode = "light") {
  const base = getBaseColors(mode);
  const c = { ...base, ...Object.fromEntries(Object.entries(colors ?? {}).filter(([, v]) => !!v)) } as Record<string, string>;
  return [c.background, c.primary, c.secondary, c.accent, c.success, c.warning, c.error];
}

// ----- editing

const editing = ref(false);
const draft = ref<UserTheme | null>(null);
const original = ref<string>("");
const saving = ref(false);
const editor = ref<{ validate: () => Promise<boolean> } | null>(null);

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

function normalizeTheme(theme: UserTheme): UserTheme {
  const t = clone(theme);
  t.light ??= {};
  t.dark ??= {};
  t.fontBody ??= null;
  t.fontHeading ??= null;
  t.customCss ??= "";
  t.backgroundImage ??= null;
  t.sidebarImage ??= null;
  t.backgroundDim ??= 0.3;
  t.panelOpacity ??= 0.75;
  t.cardOpacity ??= 0.9;
  return t;
}

function openEditor(theme: UserTheme) {
  draft.value = normalizeTheme(theme);
  original.value = JSON.stringify(draft.value);
  editing.value = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function startNew(preset?: ThemePreset) {
  const theme = preset
    ? { ...clone(preset), id: newThemeId() }
    : createDefaultTheme(i18n.t("user-themes.new-theme"));
  // An unsaved theme has no original; leaving should always ask
  openEditor(theme);
  original.value = "";
}

function startEdit(theme: UserTheme) {
  openEditor(theme);
}

function duplicate(theme: UserTheme) {
  const copy = clone(theme);
  copy.id = newThemeId();
  copy.name = i18n.t("user-themes.copy-of", { name: theme.name }).slice(0, 64);
  openEditor(copy);
  original.value = "";
}

const isDirty = computed(() => editing.value && !!draft.value && JSON.stringify(draft.value) !== original.value);

// Live preview: apply the draft to the whole app while editing
watch(
  draft,
  (value) => {
    if (editing.value && value) {
      applyUserTheme(value);
    }
  },
  { deep: true },
);

function closeEditor() {
  editing.value = false;
  draft.value = null;
  applyActive();
}

function cancelEdit() {
  if (isDirty.value && !window.confirm(i18n.t("user-themes.unsaved-changes"))) {
    return;
  }
  closeEditor();
}

function cleanDraft(theme: UserTheme): UserTheme {
  const t = clone(theme);
  t.name = t.name.trim();
  t.fontBody = t.fontBody?.trim() || null;
  t.fontHeading = t.fontHeading?.trim() || null;
  t.customCss = t.customCss ?? "";
  return t;
}

async function saveDraft(makeActive: boolean) {
  if (!draft.value) {
    return;
  }
  if (editor.value && !(await editor.value.validate())) {
    return;
  }

  saving.value = true;
  const { data } = await upsertTheme(cleanDraft(draft.value), makeActive);
  saving.value = false;

  if (data) {
    alert.success(i18n.t("user-themes.theme-saved"));
    original.value = JSON.stringify(draft.value);
    closeEditor();
  }
  else {
    alert.error(i18n.t("user-themes.theme-save-failed"));
  }
}

onBeforeRouteLeave(() => {
  if (isDirty.value && !window.confirm(i18n.t("user-themes.unsaved-changes"))) {
    return false;
  }
  if (editing.value) {
    closeEditor();
  }
});

onBeforeUnmount(() => {
  if (editing.value) {
    applyActive();
  }
});

// ----- actions

async function activate(themeId: string | null) {
  const { data } = await setActive(themeId);
  if (data) {
    alert.success(i18n.t("user-themes.theme-activated"));
  }
  else {
    alert.error(i18n.t("user-themes.theme-save-failed"));
  }
}

const deleteDialog = ref(false);
const deleteTarget = ref<UserTheme | null>(null);

function confirmDelete(theme: UserTheme) {
  deleteTarget.value = theme;
  deleteDialog.value = true;
}

async function deleteConfirmed() {
  if (!deleteTarget.value) {
    return;
  }
  const { data } = await deleteTheme(deleteTarget.value.id);
  if (data) {
    alert.success(i18n.t("user-themes.theme-deleted"));
  }
  else {
    alert.error(i18n.t("user-themes.theme-save-failed"));
  }
  deleteTarget.value = null;
}

async function copyJson(theme: UserTheme) {
  // image IDs only work for this account, so they aren't included
  const { id: _id, backgroundImage: _bg, sidebarImage: _side, ...exportable } = theme;
  try {
    await navigator.clipboard.writeText(JSON.stringify(exportable, null, 2));
    alert.success(i18n.t("general.copied-to-clipboard"));
  }
  catch {
    alert.error(i18n.t("user-themes.theme-save-failed"));
  }
}

// ----- import

const importDialog = ref(false);
const importText = ref("");

function importTheme() {
  try {
    const parsed = JSON.parse(importText.value);
    if (!parsed || typeof parsed !== "object" || typeof parsed.name !== "string") {
      throw new Error("invalid");
    }
    const theme: UserTheme = {
      id: newThemeId(),
      name: parsed.name.slice(0, 64) || i18n.t("user-themes.new-theme"),
      light: typeof parsed.light === "object" ? parsed.light : {},
      dark: typeof parsed.dark === "object" ? parsed.dark : {},
      fontBody: typeof parsed.fontBody === "string" ? parsed.fontBody : null,
      fontHeading: typeof parsed.fontHeading === "string" ? parsed.fontHeading : null,
      customCss: typeof parsed.customCss === "string" ? parsed.customCss : "",
      backgroundDim: typeof parsed.backgroundDim === "number" ? parsed.backgroundDim : 0.3,
      panelOpacity: typeof parsed.panelOpacity === "number" ? parsed.panelOpacity : 0.75,
      cardOpacity: typeof parsed.cardOpacity === "number" ? parsed.cardOpacity : 0.9,
    };
    importText.value = "";
    // Open in the editor so the user can review it (and validation runs) before saving
    openEditor(theme);
    original.value = "";
  }
  catch {
    alert.error(i18n.t("user-themes.invalid-theme-json"));
  }
}
</script>

<style scoped>
.theme-card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
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
.mini-swatch {
  width: 12px;
  height: 20px;
}
.mini-swatch:first-child {
  border-radius: 4px 0 0 4px;
}
.mini-swatch:last-child {
  border-radius: 0 4px 4px 0;
}
.preview-sticky {
  position: sticky;
  top: 80px;
}
.theme-json :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  font-size: 0.85rem;
}
</style>
