# Mealie + Theme Manager (custom fork)

This fork adds a per-user **Theme Manager** to Mealie, at **Profile → Themes** (`/user/profile/themes`).

- Create, name, and switch between multiple themes
- All 9 colors (primary, secondary, accent, success, info, warning, error, background, surface) for **light and dark mode**
- Live preview while editing: the whole app updates as you change things
- Body and heading fonts (system fonts or any Google Font)
- A custom CSS box for anything else
- Background images: one for the whole app plus an optional one for the sidebar, with sliders for dimming and see-through panels and cards
- 6 presets to start from, plus duplicate / import / export (copy theme JSON)
- Each user has their own themes, and "Mealie Default" uses the server's `THEME_*` settings

## Theme library (built-in holiday themes + admin theme packs)

- **Built-in themes** ship inside the image in `mealie/assets/themes/`: Halloween, Haunted Halloween (with the haunted-house background), Thanksgiving, Christmas and 4th of July.
- Every user sees them under **Profile → Themes → Theme Library**. They can **Use Theme** or **Customize** (makes an editable copy in *My Themes*, keeping the images).
- **Use holiday themes automatically** (on by default, per user): a library theme with a schedule is used on its dates every year, then the user's own pick comes back.
  - Haunted Halloween: Oct 1 – Oct 31
  - Thanksgiving: Nov 1 – Nov 30
  - Christmas: Dec 1 – Dec 26
  - 4th of July: Jun 28 – Jul 5
- **Admins** manage the library at **Admin → Theme Library** (`/admin/themes`): upload theme packs (zip), enable/disable themes, change the dates, download any theme as a pack, delete uploaded themes. Built-in themes can only be disabled.
- Uploaded packs are stored in `/app/data/user-themes/library/`; admin settings in `/app/data/user-themes/library.json`.

### Theme pack format

```
my-theme.zip
├── theme.json        (required)
├── style.css         (optional)
├── background.jpg    (optional)
└── images/…          (optional, can be used from the CSS)
```

`theme.json` — only `name` is required:

```json
{
  "id": "spring",
  "name": "Spring",
  "description": "Fresh greens and pastels",
  "light": { "primary": "#4CAF50", "secondary": "#F48FB1", "accent": "#81D4FA" },
  "dark": { "primary": "#81C784", "background": "#102016", "surface": "#18301F" },
  "fontHeading": "Quicksand",
  "fontBody": "Nunito",
  "customCss": "",
  "css": "style.css",
  "backgroundImage": "background.jpg",
  "sidebarImage": "sidebar.jpg",
  "backgroundDim": 0.2,
  "panelOpacity": 0.6,
  "cardOpacity": 0.85,
  "schedule": { "start": "03-20", "end": "04-30" }
}
```

- Images (JPG, PNG, WebP, GIF, AVIF, HEIC) are converted to WebP and scaled down to 3840 px.
- CSS can use the pack's images with relative paths, e.g. `url("images/flower.png")`.
- `schedule` dates are `MM-DD` and may wrap around New Year (e.g. `12-20` to `01-05`).
- A zip can contain several themes, each in its own folder with its own `theme.json`.
- Uploading a theme with the same `id` again replaces it. Ids that clash with a built-in theme get a `-2` suffix.
- Limits: 60 MB zip, 30 MB per file, 300 files, 20 themes per zip, 100 KB of CSS per theme.

## How it's built (and why it's easy to keep updated)

- **No database changes.** Themes are saved as JSON files in the data volume at `/app/data/user-themes/<user-id>.json`. They are included in Mealie backups. You can switch back to the official image at any time without breaking anything, and the themes stay put if you come back.
- API: `GET / PUT / DELETE /api/users/self/themes`, plus `POST /api/users/self/themes/images` and `GET / DELETE /api/users/self/themes/images/{id}` (only for the logged-in user)
- Background images are converted to WebP and stored in `/app/data/user-themes/images/<user-id>/`. Images that no theme uses are cleaned up automatically after a day.
- Almost all of the code is in new files, so merging new Mealie releases rarely conflicts.

| Area | Files |
| --- | --- |
| Backend | `mealie/schema/user/user_theme.py`, `mealie/services/user_services/user_theme_service.py`, `mealie/routes/users/themes.py` |
| Frontend | `frontend/app/pages/user/profile/themes.vue`, `frontend/app/composables/use-user-themes.ts`, `frontend/app/plugins/user-theme.client.ts`, `frontend/app/components/Domain/User/UserTheme*.vue`, `frontend/app/lib/user-themes/presets.ts` |
| Tests | `tests/integration_tests/user_tests/test_user_themes.py` |
| Build | `.github/workflows/custom-image.yml` (builds `ghcr.io/<you>/mealie:themes`) |

## One-time setup

### 1. Fork and push the code

1. On GitHub, fork <https://github.com/mealie-recipes/mealie>.
2. On a computer with git installed:

```bash
git clone https://github.com/<you>/mealie.git
cd mealie
git remote add upstream https://github.com/mealie-recipes/mealie.git
git fetch upstream --tags
git checkout -b themes v3.29.0          # the release this patch was built on
git am /path/to/mealie-theme-manager.patch
git push -u origin themes
```

### 2. Let GitHub build the image

1. In your fork, open the **Actions** tab and click **"I understand my workflows, go ahead and enable them"**. Mealie's own workflows only run on the `mealie-next` branch, so they stay idle.
2. The push in step 1 starts **Build custom Mealie image**. If it didn't run, open it and click **Run workflow**. The first build takes about 10–15 minutes.
3. When it finishes, go to your GitHub profile → **Packages** → `mealie` → **Package settings**. Either change the visibility to **Public**, or add GHCR as a registry in Portainer (step 3).

For an ARM server (Raspberry Pi and similar), run the workflow manually with platforms set to `linux/amd64,linux/arm64`.

### 3. Switch your Portainer stack

1. **Back up first.** In Mealie, go to Admin → Backups → Create, and download the backup.
2. *(Only if the package is private)* In Portainer, go to **Registries → Add registry → Custom**. Use URL `ghcr.io`, your GitHub username, and a token with the `read:packages` scope.
3. Go to **Stacks →** your Mealie stack **→ Editor** and change the image line:

```yaml
services:
  mealie:
    image: ghcr.io/<you>/mealie:themes   # was ghcr.io/mealie-recipes/mealie:vX.Y.Z
    # everything else (volumes, environment, ports) stays the same
```

4. Click **Update the stack** and turn on **Re-pull image**.
5. Open Mealie → your profile → **Themes**.

## Updating to a new Mealie release

```bash
cd mealie
git fetch upstream --tags
git checkout themes
git merge v3.30.0        # the new release tag
git push                 # GitHub Actions rebuilds :themes automatically
```

Then in Portainer, update the stack with **Re-pull image** turned on.

Always merge a **release tag**, never upstream's development branch. Don't run an image that is *older* than the Mealie version you've already run, because database migrations only go forward.

## Going back to the official image

Change the stack's image back to `ghcr.io/mealie-recipes/mealie:<same or newer version>` and redeploy. The `user-themes` folder is simply ignored.
