# 🛡️ Sahayak Safe Maps

**Illumination-aware navigation for safer nighttime travel.**

Sahayak helps you find the brightest, well-lit route to your destination, avoiding poorly lit areas and danger zones. Built for the safety of women and all nighttime travelers in Vijayawada, Guntur, and Mangalagiri (VGM) region.

![Safe Map Demo](https://img.shields.io/badge/Safe-Navigation-brightgreen)
![Powered By](https://img.shields.io/badge/Powered%20By-NASA%20VIIRS%20%7C%20OpenStreetMap-blue)
![100% Free](https://img.shields.io/badge/100%25-Free-success)

> ⚡ **Zero Cost, Zero Credit Card Required** — This entire stack runs on free tiers and open-source tools.

---

## ✨ Features

- 💡 **Brightest Path Algorithm** — Finds routes with maximum street lighting
- 🛰️ **NASA VIIRS Satellite Data** — Real-time nighttime illumination layers
- 📍 **Live GPS Tracking** — Follow your position with high-accuracy updates
- ⚠️ **Danger Zone Alerts** — Avoid reported unsafe areas
- 🏥 **Safe Haven Locations** — Find nearby police, hospitals, and 24/7 stores
- 📱 **Mobile-First Design** — Works perfectly on Android and iOS
- 🆓 **100% Free Forever** — No API keys, no credit cards, no subscriptions

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- A modern web browser (Chrome, Firefox, Safari)
- A local web server for development. For live GPS on a phone, use HTTPS (GitHub Pages, Vercel, Netlify, or an ngrok tunnel).

### Option 1: Python HTTP Server
```bash
cd code4her
python -m http.server 8000
# Open http://localhost:8000/safemap.html
```

### Option 2: Node.js http-server
```bash
npm install -g http-server
cd code4her
http-server -p 8000
# Open http://localhost:8000/safemap.html
```

### Option 3: VS Code Live Server
Install the "Live Server" extension, right-click on `safemap.html`, and select "Open with Live Server".

### Important: HTTPS for Location
Desktop development over `http://localhost` is fine, but mobile browsers usually block `navigator.geolocation` on plain LAN URLs such as `http://192.168.x.x`. For phone testing, use one of these:
- GitHub Pages / Vercel / Netlify deployment
- `ngrok http 8000` for a temporary secure tunnel

## Refresh VGM Data

Pull fresh public data for Vijayawada, Guntur, and Mangalagiri:

```bash
python fetch_vgm_data.py
```

This updates:
- `vgm_streets.json` from OpenStreetMap road and lighting data
- `vgm_havens.json` from OpenStreetMap police, hospitals, pharmacies, fuel stations, convenience stores, and stations

If you have verified local danger reports, copy `community_reports.example.json` to `community_reports.json` and replace the sample points with real ones.
You can also manage community reports directly inside the map UI and export them back to JSON.

## Google Places Setup

Google Places is optional. The app already works with the local OSM havens dataset, but you can enrich it with live nearby places.

### Local development

1. Copy `config.example.js` to `config.js`
2. Put your browser key in:

```js
window.SAHAYAK_CONFIG = {
  googlePlacesApiKey: "YOUR_GOOGLE_PLACES_API_KEY"
};
```

`config.js` is gitignored.

### GitHub Pages deployment

Add a repository secret named `GOOGLE_PLACES_API_KEY`.
The GitHub Actions workflow writes that secret into a runtime `config.js` during deployment.

### Required Google Cloud settings

- Enable `Places API`
- Restrict the key to `Places API`
- Restrict browser referrers to your deployed domain, for example:
  - `https://YOUR_USERNAME.github.io/*`
  - `http://localhost:*/*`

---

## 📦 Deployment (GitHub Pages)

### Step 1: Create a GitHub Repository
1. Go to [GitHub](https://github.com) and create a new repository named `sahayak-maps`
2. Upload all your `code4her` files to this repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/sahayak-maps.git
   git push -u origin main
   ```

### Step 2: Enable GitHub Pages
1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (in the left sidebar)
3. Under "Source", select **GitHub Actions**
4. The included workflow (`.github/workflows/deploy.yml`) will automatically deploy your site!

### Step 3: Access Your Live Site
- Your site will be live at: `https://YOUR_USERNAME.github.io/sahayak-maps/`
- ✅ HTTPS is automatically enabled — GPS location will work on mobile browsers!

---

## 🗺️ Data Strategy (100% Free Options)

### Option 1: Raw GeoJSON (RECOMMENDED) ✅

**Best for:** Files under 5MB (perfect for VGM region)

**Why this works:**
- Modern smartphones process 3MB GeoJSON in under 1 second
- Zero dependencies, zero accounts, zero configuration
- Your current setup already uses this!

**To expand your data:**
1. Go to [Overpass Turbo](https://overpass-turbo.eu/)
2. Run this query for VGM region:
   ```
   [out:json][timeout:25];
   (
     way["highway"~"primary|secondary|trunk|residential"]["lit"="yes"](16.2,80.4,16.7,80.9);
     way["highway"~"primary|secondary|trunk|residential"]["lit"="no"](16.2,80.4,16.7,80.9);
   );
   out body;
   >;
   out skel qt;
   ```
3. Export as GeoJSON → Save as `vgm_streets.json`

### Option 2: Simplified GeoJSON (If File is Too Large)

**Best for:** Files 5-15MB that need compression

Use **Mapshaper** (free, browser-based):
1. Go to [Mapshaper.org](https://mapshaper.org/)
2. Upload your `vgm_streets.json`
3. Click "Simplify" → Set to ~20-30%
4. Export as GeoJSON
5. File size reduced by 60-80% with minimal visual difference!

### Option 3: Protomaps (For City-Scale Data) 🆓

**Best for:** Files > 15MB or multi-city coverage

**Why Protomaps?**
- ✅ 100% FREE — no API keys, no accounts, no credit cards
- ✅ Self-hosted — just a single `.pmtiles` file
- ✅ Open-source — [protomaps.com](https://protomaps.com)

**Setup:**
1. Download `tippecanoe` (free tool):
   ```bash
   # Windows: Download from https://github.com/felt/tippecanoe/releases
   # Mac: brew install tippecanoe
   # Linux: Build from source
   ```

2. Convert your GeoJSON to PMTiles:
   ```bash
   tippecanoe -o vgm_streets.pmtiles -z14 -Z10 --drop-densest-as-needed vgm_streets.json
   ```

3. Upload `vgm_streets.pmtiles` to your GitHub repo

4. Update `safemap.js`:
   ```javascript
   protomapsUrl: './vgm_streets.pmtiles',
   ```

### ❌ NOT RECOMMENDED: Mapbox

**Requires credit card** — Skip this for a truly free project.

---

## 🔧 Configuration Reference

### Core Settings (`safemap.js`)

```javascript
const CONFIG = {
  defaultCenter: [16.5062, 80.6480], // VGM region
  defaultZoom: 13,
  
  // FREE OPTION 1: GeoJSON (default, recommended)
  // Just keep vgm_streets.json in the same folder
  
  // FREE OPTION 2: Protomaps (for large datasets)
  protomapsUrl: null, // Set to './vgm_streets.pmtiles' after converting
  
  // PAID OPTION: Mapbox (requires credit card - NOT recommended)
  useVectorTiles: false,
  mapboxToken: null,
  mapboxTilesetId: null,
};
```

---

## 📁 Project Structure

```
code4her/
├── .github/workflows/deploy.yml  # GitHub Actions (auto-deploy)
├── safemap.html                  # Main map interface
├── safemap.js                    # Core logic (100% free stack)
├── safemap.css                   # Styling
├── vgm_streets.json             # Street data (GeoJSON)
├── index.html                    # Landing page
├── dialer.html                   # Emergency dialer
├── SafetyCall.js                 # SOS functionality
├── start-server.py               # Local dev server
├── README.md                     # This file
├── DEPLOYMENT_CHECKLIST.md       # Step-by-step deployment guide
└── manifest.json                 # PWA manifest
```

---

## 🛰️ Data Sources (All Free)

| Source | Cost | Data Type |
|--------|------|-----------|
| **OpenStreetMap** | Free | Street geometry, lighting tags |
| **NASA GIBS** | Free | VIIRS nighttime satellite imagery |
| **OSRM** | Free | Routing engine |
| **Nominatim** | Free | Geocoding (address search) |
| **GitHub Pages** | Free | Hosting + HTTPS |

**Total Monthly Cost: $0** 🎉

---

## 🛡️ Privacy & Safety

- **GPS data** is processed locally — never sent to our servers
- **No tracking cookies** or analytics without consent
- **No third-party APIs** that require accounts (unless you add them)
- **Disclaimer**: Safety scores are based on lighting/infrastructure data, not live crime statistics
- Always use your judgment and stay aware of your surroundings

---

## 🤝 Expanding Street Data

### Method 1: Overpass Turbo (Free)
1. Go to [Overpass Turbo](https://overpass-turbo.eu/)
2. Adjust the bounding box to your desired area
3. Run the query (from Option 1 above)
4. Export → GeoJSON
5. Merge with existing `vgm_streets.json`

### Method 2: Mapshaper (For Compression)
1. Upload to [Mapshaper](https://mapshaper.org/)
2. Simplify to reduce file size
3. Export clean GeoJSON

---

## 📱 PWA Installation

### Android (Chrome)
1. Open the live site in Chrome
2. Tap the menu (⋮) → "Add to Home screen"
3. The app installs like a native app!

### iOS (Safari)
1. Open the live site in Safari
2. Tap Share (⎘) → "Add to Home Screen"
3. The app appears on your home screen

---

## 🐛 Troubleshooting

### GPS not working?
- ✅ Ensure you're accessing via **HTTPS** (GitHub Pages does this automatically)
- ✅ Check browser permissions for location access
- ✅ Try refreshing the page

### Map not loading?
- ✅ Check browser console for errors (F12 → Console)
- ✅ Verify `vgm_streets.json` is in the same directory
- ✅ Ensure you're using a local server (not `file://`)

### File too large?
- ✅ Use Mapshaper to simplify (reduce 60-80% size)
- ✅ Or switch to Protomaps format

---

## 🎓 Educational Resources

- **Overpass API**: Learn to query OpenStreetMap at [wiki.openstreetmap.org/wiki/Overpass_API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- **Leaflet.js**: Mapping library docs at [leafletjs.com](https://leafletjs.com)
- **Turf.js**: Geospatial analysis at [turfjs.org](https://turfjs.org)
- **Protomaps**: Free vector tiles at [protomaps.com](https://protomaps.com)

---

## 📄 License

MIT License — Built with ❤️ for safer communities.

---

## 🙏 Acknowledgments

- NASA GIBS for VIIRS Black Marble imagery
- OpenStreetMap contributors worldwide
- Leaflet.js for the mapping library
- Turf.js for geospatial analysis
- Protomaps for free vector tile technology
- GitHub for free hosting

---

## 💡 Philosophy

> **"Safety technology should be accessible to everyone, not just those who can pay."**

This project demonstrates that powerful, life-saving technology can be built entirely on free, open-source tools. No credit cards. No subscriptions. No barriers.

---

**Stay Safe. Travel Bright.** 🌟

*Built for Code4Her Hackathon 2024*
