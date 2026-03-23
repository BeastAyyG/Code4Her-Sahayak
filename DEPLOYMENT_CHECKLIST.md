# 🚀 Sahayak Safe Maps - Deployment Checklist

**100% FREE — No Credit Cards Required** ✨

Use this checklist to track your progress deploying Sahayak Safe Maps using only free, open-source tools.

---

## Phase 1: Local Testing ✅

- [ ] **Start local server**
  ```bash
  python start-server.py
  # or
  python -m http.server 8000
  ```

- [ ] **Test core functionality**
  - [ ] Map loads without errors (check browser console: F12)
  - [ ] GPS location works (allow location permission)
  - [ ] Search for locations works
  - [ ] Route calculation works
  - [ ] Street lighting overlay visible (gold = lit, red = unlit)

- [ ] **Test on mobile over HTTPS**
  - [ ] Preferred: deploy to GitHub Pages and open the `https://` URL on your phone
  - [ ] Or use a secure tunnel such as `ngrok http 8000`
  - [ ] Verify GPS permission is granted and live location works on the mobile browser

- [ ] **Check file size**
  - [ ] `vgm_streets.json` is under 5MB ✨ (perfect!)
  - [ ] If 5-15MB: Use Mapshaper to simplify (see Phase 4)
  - [ ] If > 15MB: Consider Protomaps (see Phase 5)

---

## Phase 2: GitHub Setup ✅

- [ ] **Create GitHub account** (if needed)
  - Go to https://github.com/join

- [ ] **Create new repository**
  - Name: `sahayak-maps` (or your preferred name)
  - Visibility: Public (for free GitHub Pages)
  - **DO NOT** initialize with README (we already have one)

- [ ] **Upload your code**
  ```bash
  # In your code4her folder
  git init
  git add .
  git commit -m "Initial commit - Sahayak Safe Maps"
  git branch -M main
  git remote add origin https://github.com/YOUR_USERNAME/sahayak-maps.git
  git push -u origin main
  ```
  
  Or use GitHub Desktop: https://desktop.github.com/

- [ ] **Verify files are uploaded**
  - [ ] `safemap.html`
  - [ ] `safemap.js`
  - [ ] `safemap.css`
  - [ ] `vgm_streets.json`
  - [ ] `index.html`
  - [ ] `.github/workflows/deploy.yml`

---

## Phase 3: GitHub Pages Deployment ✅

- [ ] **Enable GitHub Pages**
  1. Go to repository → Settings → Pages
  2. Source: **GitHub Actions**
  3. The workflow file (`.github/workflows/deploy.yml`) is already included!

- [ ] **Trigger deployment**
  - Make any small change and push, or
  - Go to Actions tab → check that deployment starts automatically

- [ ] **Wait for deployment** (~2-5 minutes)
  - Check the Actions tab for green checkmark ✅

- [ ] **Access live site**
  - URL: `https://YOUR_USERNAME.github.io/sahayak-maps/safemap.html`
  - Verify HTTPS is working (🔒 lock icon in browser)

- [ ] **Test GPS on live site**
  - [ ] Open on mobile browser
  - [ ] Allow location permission
  - [ ] Confirm GPS accuracy circle appears

---

## Phase 4: Optimize Large Files (If Needed) ⚡

> **Skip this if your `vgm_streets.json` is under 5MB!**

### Option A: Simplify with Mapshaper (Free, Browser-Based)

- [ ] Go to [Mapshaper.org](https://mapshaper.org/)
- [ ] Upload your `vgm_streets.json`
- [ ] Click **"Simplify"**
- [ ] Drag slider to **20-30%** (visually check quality)
- [ ] Click **"Apply"**
- [ ] Export → **GeoJSON**
- [ ] Replace old file with new simplified version
- [ ] Test locally: `python start-server.py`
- [ ] Commit and push changes

**Expected result:** 60-80% file size reduction

### Option B: Command Line with Tippecanoe

```bash
# Install tippecanoe (Mac)
brew install tippecanoe

# Or download for Windows/Linux from:
# https://github.com/felt/tippecanoe/releases

# Simplify GeoJSON
tippecanoe -o vgm_streets.pmtiles -z14 -Z10 --drop-densest-as-needed vgm_streets.json

# Now follow Phase 5 for Protomaps setup
```

---

## Phase 5: Protomaps Setup (Optional - For Large Datasets) 🗺️

> **Use this if your data is > 15MB or you need multi-city coverage**
> 
> **100% FREE — No accounts, no API keys!**

- [ ] **Convert GeoJSON to PMTiles**
  ```bash
  # Install tippecanoe
  brew install tippecanoe  # Mac
  # OR download from GitHub for Windows

  # Convert
  tippecanoe -o vgm_streets.pmtiles -z14 -Z10 --drop-densest-as-needed vgm_streets.json
  ```

- [ ] **Upload PMTiles to GitHub**
  ```bash
  git add vgm_streets.pmtiles
  git commit -m "Add Protomaps vector tiles"
  git push
  ```

- [ ] **Update safemap.html**
  Uncomment the Protomaps script:
  ```html
  <script src="https://unpkg.com/pmtiles@2.11.0/dist/index.js"></script>
  ```

- [ ] **Update safemap.js**
  ```javascript
  protomapsUrl: './vgm_streets.pmtiles',
  ```

- [ ] **Commit and push**
  ```bash
  git add safemap.html safemap.js
  git commit -m "Enable Protomaps vector tiles"
  git push
  ```

- [ ] **Test**
  - Wait for GitHub Actions deployment
  - Check browser console for "Protomaps loaded"

---

## Phase 6: PWA Installation ✅

- [ ] **Test install prompt (Android)**
  - [ ] Open site in Chrome
  - [ ] Look for "Add to Home screen" popup
  - [ ] Or: Menu → Add to Home screen

- [ ] **Test iOS installation**
  - [ ] Open in Safari
  - [ ] Share → Add to Home Screen

- [ ] **Test offline functionality**
  - [ ] Turn on airplane mode
  - [ ] Open the installed app
  - [ ] Check if map interface works

---

## Phase 7: Final Verification ✅

- [ ] **Cross-browser testing**
  - [ ] Chrome (desktop)
  - [ ] Chrome (Android)
  - [ ] Safari (iOS)
  - [ ] Firefox (desktop)

- [ ] **Performance check**
  - [ ] Initial load under 3 seconds
  - [ ] GPS acquisition under 5 seconds
  - [ ] Route calculation under 3 seconds

- [ ] **Accessibility**
  - [ ] Text is readable
  - [ ] Buttons are large enough for touch
  - [ ] Color contrast is sufficient

- [ ] **Security**
  - [ ] Site loads over HTTPS
  - [ ] No mixed content warnings
  - [ ] No API keys exposed (if using any)

- [ ] **Cost verification**
  - [ ] GitHub Pages: **$0** ✅
  - [ ] OpenStreetMap: **$0** ✅
  - [ ] NASA VIIRS: **$0** ✅
  - [ ] Routing (OSRM): **$0** ✅
  - [ ] Total monthly cost: **$0** ✅

---

## 📋 Post-Deployment

- [ ] **Share your app!**
  - [ ] Social media posts
  - [ ] Local community WhatsApp groups
  - [ ] Women's safety organizations
  - [ ] College/school groups

- [ ] **Collect feedback**
  - [ ] Create Google Form for bug reports
  - [ ] Monitor GitHub Issues tab
  - [ ] Ask friends to test on their phones

- [ ] **Plan future updates**
  - [ ] Expand to more neighborhoods
  - [ ] Add user-contributed danger zones
  - [ ] Integrate with local police helplines
  - [ ] Add public transport safety data

---

## 🆘 Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| GPS not working | Ensure HTTPS (GitHub Pages does this automatically), check browser permissions |
| Map blank | Check console for JS errors, verify file paths |
| 404 errors | Verify all files uploaded to GitHub, check case sensitivity |
| File too large (> 5MB) | Use Mapshaper to simplify, or switch to Protomaps |
| Mobile crashes | Simplify GeoJSON, reduce number of features |
| Slow loading | Check file size, consider Protomaps for large datasets |
| "Cannot fetch" errors | Ensure using local server (not `file://` protocol) |

---

## 🎉 Success Checklist

When everything is complete:

- ✅ App is live at `https://YOUR_USERNAME.github.io/sahayak-maps/`
- ✅ Works on mobile with GPS
- ✅ Costs $0/month to run
- ✅ No credit cards required
- ✅ Open-source and self-hosted
- ✅ Ready to help people travel safely!

---

## 💰 Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| GitHub Pages | **$0** | Unlimited bandwidth for public repos |
| OpenStreetMap | **$0** | Free geocoding & tile data |
| NASA GIBS | **$0** | Free satellite imagery |
| OSRM Routing | **$0** | Free routing API |
| Protomaps | **$0** | Self-hosted vector tiles |
| Domain | **$0** | Use github.io subdomain |
| **TOTAL** | **$0** | Forever free! 🎉 |

---

## 🎯 Mission Accomplished!

Your Sahayak Safe Maps app is now:
- 🌐 Live on the internet
- 📱 Installable as a PWA
- 💸 100% free forever
- 🔒 Privacy-respecting
- 🚀 Ready to make a difference!

**Share the link:** `https://YOUR_USERNAME.github.io/sahayak-maps/`

---

*Last updated: 2024*
*Built with ❤️ for safer communities*
*100% Free — No Credit Cards Required*