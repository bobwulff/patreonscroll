# Patreon Scroll — OBS Browser Source

A scrolling on-stream patron credits graphic, auto-updated from Patreon
every 30 minutes and hosted for free on GitHub Pages so OBS can load it
by URL instead of a local file.

- `index.html` — the graphic itself (fetches `patrons.csv` and animates it)
- `patrons.csv` — the current patron list; **auto-regenerated** by the
  workflow below, you shouldn't need to hand-edit it once this is running
- `scripts/update_patrons.py` — pulls active patrons from the Patreon API
- `.github/workflows/update-patrons.yml` — runs the script on a schedule

## 1. Put this on GitHub

1. Create a new **public** repo (GitHub Pages hosting requires public on
   the free plan) and push these files to it.
2. In the repo, go to **Settings → Pages**, set "Source" to "Deploy from
   a branch," pick `main` / `root`, and save.
3. After a minute or two, GitHub will give you a URL like
   `https://yourusername.github.io/your-repo-name/`. That's what you'll
   paste into OBS.

## 2. Create a Patreon API client

1. Go to <https://www.patreon.com/portal/registration/register-clients>
   while logged into the Patreon account that owns your campaign.
2. Click **Create Client**. Name/description can be anything (e.g.
   "Stream Overlay"). For the redirect URI, `https://www.patreon.com` is
   fine — you won't be using the OAuth login flow, just the direct
   creator tokens.
3. Once created, you'll see:
   - **Client ID**
   - **Client Secret**
   - **Creator's Access Token**
   - **Creator's Refresh Token**

   You only need the Client ID, Client Secret, and Refresh Token for this
   setup (the script fetches a fresh access token itself each run).

## 3. Add your Patreon credentials as GitHub secrets

In your repo: **Settings → Secrets and variables → Actions → New
repository secret**. Add these three:

| Secret name | Value |
|---|---|
| `PATREON_CLIENT_ID` | Client ID from step 2 |
| `PATREON_CLIENT_SECRET` | Client Secret from step 2 |
| `PATREON_REFRESH_TOKEN` | Creator's Refresh Token from step 2 |

If your Patreon account runs more than one campaign, also add
`PATREON_CAMPAIGN_ID` (the script will tell you the available IDs if it
runs and finds more than one, so you can leave it out and check the
Actions log first if you're not sure).

## 4. Run it

Go to the **Actions** tab → "Update patrons.csv from Patreon" → **Run
workflow** to trigger it manually the first time. Check the log — if it
succeeds, `patrons.csv` in your repo will update with your real patron
list. After that, it runs automatically every 30 minutes (edit the
`cron` line in the workflow file to change the frequency).

## 5. Point OBS at it

In OBS, add a **Browser Source**, and instead of a local file, use your
GitHub Pages URL from step 1. Recommended settings:

- **Width / Height**: match your canvas/stream resolution
- Check **"Refresh browser when scene becomes active"** — this makes OBS
  reload the page (and re-fetch the latest `patrons.csv`) each time you
  switch to the scene, instead of showing a stale cached version.

## Notes & gotchas

- **Tier names must match exactly.** The script writes whatever your
  tier titles are in Patreon into `patrons.csv`, and `index.html`
  filters on the exact strings `"Super Cool Guy"` and `"Mega Cool Guy"`.
  If you ever rename a tier in Patreon, update those two strings in
  `index.html` to match.
- **Only active patrons are included.** Declined or former patrons are
  filtered out automatically.
- **This repo will be public**, which means your patron list is
  reachable at a stable URL any time, not just while it's on screen
  during a stream. If that's not okay, you'd need GitHub's paid plan for
  private Pages hosting, or a different host — let me know if you'd
  rather go that route.
- **Refresh token rotation.** Patreon occasionally issues a new refresh
  token when the old one is used. If that happens, the workflow log will
  show a warning with the new token — you'd need to manually update the
  `PATREON_REFRESH_TOKEN` secret when you see that warning, or the next
  run will fail. This is uncommon but worth knowing about; if it becomes
  annoying, this can be automated further (having the workflow update its
  own secret), just say the word.
