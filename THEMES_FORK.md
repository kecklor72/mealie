# Mealie + Theme Manager (custom fork)

This fork adds a per-user **Theme Manager** to Mealie, at **Profile → Themes** (`/user/profile/themes`).

- Create, name, and switch between multiple themes
- All 9 colors (primary, secondary, accent, success, info, warning, error, background, surface) for **light and dark mode**
- Live preview while editing: the whole app updates as you change things
- Body and heading fonts (system fonts or any Google Font)
- A custom CSS box for anything else
- 6 presets to start from, plus duplicate / import / export (copy theme JSON)
- Each user has their own themes, and "Mealie Default" uses the server's `THEME_*` settings

## How it's built (and why it's easy to keep updated)

- **No database changes.** Themes are saved as JSON files in the data volume at `/app/data/user-themes/<user-id>.json`. They are included in Mealie backups. You can switch back to the official image at any time without breaking anything, and the themes stay put if you come back.
- API: `GET / PUT / DELETE /api/users/self/themes` (only for the logged-in user)
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
