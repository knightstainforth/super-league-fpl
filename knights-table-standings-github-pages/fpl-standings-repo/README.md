# Knights Table Super League — live standings page (GitHub Pages)

This little repo fetches your league's live scores from the official FPL
API and republishes a standings page automatically — no more manual
uploads, no Dropbox paste, nothing to remember. It runs entirely on
GitHub's own servers on a schedule, then GitHub Pages serves the result
as a normal web page. You embed that page once in WordPress and it's done
for good.

There are three one-time setup steps. None of them need coding — just
following along. Should take about 10 minutes.

## Step 1 — Create the GitHub repo

1. Go to https://github.com and sign in (create a free account if you
   don't have one — any email works).
2. Click the **+** in the top-right corner → **New repository**.
3. Name it something like `knights-table-standings`. Keep it **Public**
   (GitHub Pages needs Public on a free account — nothing sensitive is in
   here, it's just scores and team names that are already public on the
   FPL site).
4. Don't add a README/gitignore/license on this screen — leave those
   unchecked, since you already have files to upload. Click **Create
   repository**.
5. On the empty repo's page, click **uploading an existing file** (or drag
   and drop). Upload these three files/folders from this zip, keeping the
   folder structure exactly as-is:
   - `fetch_and_render.py`
   - `render_frontpage.py`
   - `.github/workflows/refresh.yml` (GitHub will recreate the `.github`
     and `workflows` folders automatically when you drag the whole zip
     contents in — if your browser flattens folders, create the folders
     manually by typing `.github/workflows/refresh.yml` as the filename
     when you upload that one file, GitHub will make the folders for you)
6. Scroll down and click **Commit changes**.

## Step 2 — Turn on GitHub Pages and let it run once

1. In your new repo, click **Settings** (top tab bar) → **Pages** (left
   sidebar).
2. Under "Build and deployment", set **Source** to **Deploy from a
   branch**, branch **main**, folder **/ (root)**. Click **Save**.
3. Click the **Actions** tab (top tab bar). You should see a workflow
   called "Refresh standings page". Click into it, then click **Run
   workflow** (top-right dropdown) → **Run workflow** button, to trigger
   the very first run by hand rather than waiting for the schedule.
4. Wait about 30-60 seconds, refresh the page — you should see a green
   checkmark. This means it just fetched your league's live data and
   committed a fresh `index.html` to the repo.
5. Go back to **Settings → Pages** — it should now show "Your site is
   live at `https://<your-github-username>.github.io/<repo-name>/`".
   That's your permanent standings URL. Open it in a browser to check it
   looks right (FPL purple header, Overall/1st Half/2nd Half tabs, prize
   pot at the bottom).

From now on, this workflow re-runs automatically on the same schedule as
the Claude triggers (hourly Fri-Mon during matchday windows, plus a
Tuesday-morning settled pass) and commits a fresh page every time
something changes. You never have to touch this again unless you want
to change the schedule or the design.

## Step 3 — Embed it in WordPress (one-time paste)

1. In WordPress, edit the `/knights-table-super-league/` page (or wherever
   you want the live standings to show).
2. Add a **Custom HTML** block and paste this, swapping in your actual
   Pages URL from Step 2:

   ```html
   <iframe
     src="https://<your-github-username>.github.io/<repo-name>/"
     style="width:100%; max-width:720px; height:1400px; border:none; display:block; margin:0 auto;"
     loading="lazy">
   </iframe>
   ```

3. Publish/update the page. From now on the iframe always shows whatever
   GitHub last published — no further manual steps, ever.

   (The fixed `height` is a simple way to make sure the iframe has enough
   room; adjust the number if the page ends up with a lot of extra blank
   space or gets cut off — a rough guide is more entrants = taller page.)

## What to send back once this is live

Once you've done the above and confirmed the WordPress page shows live
data, just tell Claude "the GitHub Pages standings are live" (and paste
the Pages URL if you have it handy). That updates the project notes and
lets Claude decide whether the two scheduled Claude triggers should stop
also building/sending the standings `.html` file to Dropbox (since it'd
then be redundant with this) — the workbook `.xlsx` keeps going to
Dropbox either way, that's unaffected by any of this.

## If something goes wrong

- **Actions tab shows a red X**: click into the failed run to see the
  error. The most likely cause is a temporary FPL API hiccup — the
  workflow retries automatically, so it usually clears on the next
  scheduled run. If it keeps failing, copy the error text back to Claude.
- **Page looks empty / "no entrants found"**: this only happens if the
  league ID is wrong or pre-season with zero joiners — shouldn't apply
  here since the league's already running.
- **iframe shows nothing in WordPress**: double check the URL you pasted
  matches exactly what GitHub Pages showed you in Step 2 (including the
  trailing slash), and that the repo is Public.
