# Deploying to GitHub Pages

Host your trip as a PWA on GitHub Pages for free HTTPS and mobile installability.

## 1. Export the trip

```bash
python -m vacationeer export trips/valencia-2026/trip.json
```

This creates `export/valencia-2026/` with:
- `index.html` (redirect)
- `valencia-2026-app.html` (main app)
- `valencia-2026-map.html` (interactive map)
- `manifest.json` (PWA manifest)
- `sw.js` (service worker for offline caching)
- `icon.svg` (app icon)

## 2. Create a GitHub repo

```bash
cd export/valencia-2026
git init
git add .
git commit -m "Initial export"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Or push to an existing repo's `gh-pages` branch:
```bash
git checkout --orphan gh-pages
git add export/valencia-2026/*
git commit -m "Deploy trip"
git push origin gh-pages
```

## 3. Enable GitHub Pages

1. Go to **Settings > Pages** in your repo
2. Under **Source**, select the branch (`main` or `gh-pages`)
3. Set folder to `/ (root)`
4. Click **Save**

Your trip is now live at: `https://YOUR_USERNAME.github.io/YOUR_REPO/`

## 4. Install on your phone

1. Open the URL in Chrome on your phone
2. Chrome will show an "Install" or "Add to Home Screen" prompt
3. Tap it — the app appears as a standalone icon on your home screen
4. Works offline (service worker caches the app shell and CDN assets)

## 5. Editing on mobile

All edits are saved to your browser's localStorage:
- Add/edit/delete attractions
- Schedule activities via drag-and-drop
- Reorder activities, swap days
- Changes persist across sessions

**Note:** AI features (chat, day planning, new trip pipeline) require the Python server and are not available in the hosted version.

## 6. Syncing changes back to PC

1. On your phone, tap the **Export** button in the sidebar
2. This downloads a `trip.json` file with all your edits
3. Transfer it to your PC (email, Google Drive, USB, etc.)
4. Replace `trips/<slug>/trip.json` with the exported file
5. Re-export and push to update GitHub Pages:

```bash
python -m vacationeer export trips/valencia-2026/trip.json
cd export/valencia-2026
git add . && git commit -m "Update from mobile" && git push
```

## 7. Updating after desktop edits

After editing on the desktop (via `vacationeer serve`), re-export and push:

```bash
python -m vacationeer export trips/valencia-2026/trip.json
cd export/valencia-2026
git add . && git commit -m "Update trip" && git push
```

The next time you open the app on your phone, the service worker will pick up the new version.

## Limitations

- **Map tiles need internet** — the map uses CartoDB tiles loaded from CDN
- **No automatic sync** — desktop and mobile edits are independent; use export/import to merge
- **AI features need the server** — chat, AI planning, and new trip creation are disabled offline
