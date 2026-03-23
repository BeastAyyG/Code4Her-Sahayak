// ===== SAHAYAK SAFE MAPS — BRIGHTEST PATH NAVIGATION =====

(function () {
  'use strict';

  const RUNTIME_CONFIG = window.SAHAYAK_CONFIG || {};

  // ===== CONFIGURATION =====
  function getSatelliteDate() {
      const d = new Date();
      d.setHours(12, 0, 0, 0);
      d.setDate(d.getDate() - 1);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
  }

  const CONFIG = {
    defaultCenter: [16.5062, 80.6480], // VGM region (Vijayawada)
    defaultZoom: 13,
    tileUrl: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    nasaViirsUrl: `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_Black_Marble/default/${getSatelliteDate()}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`,
    nominatimUrl: 'https://nominatim.openstreetmap.org/search',
    osrmUrl: 'https://router.project-osrm.org/route/v1/driving',
    searchDelay: 400,
    googlePlacesApiKey: RUNTIME_CONFIG.googlePlacesApiKey || null,
    googlePlaces: {
      cooldownMs: 120000,
      maxCallsPerDay: 25,
      cachePrecision: 2,
      searchRadiusMeters: 1000,
      maxResultCount: 8,
      allowedAreas: [
        { name: 'Vijayawada', lat: 16.5062, lng: 80.6480, radiusKm: 18 },
        { name: 'Guntur', lat: 16.3067, lng: 80.4365, radiusKm: 14 },
        { name: 'Mangalagiri', lat: 16.4300, lng: 80.5680, radiusKm: 8 }
      ]
    },
    routeColors: {
      brightest: '#00ff88',
      shortest: '#667eea',
      danger: '#ff4757',
      caution: '#ffa502'
    },
    // Vector Tile Configuration (OPTIONAL - for datasets > 10MB)
    // For 100% free deployment, keep useVectorTiles: false
    // GeoJSON under 5MB works perfectly on modern smartphones
    useVectorTiles: false, 
    
    // Mapbox (requires credit card - NOT recommended for free projects)
    // mapboxToken: 'YOUR_MAPBOX_TOKEN',
    // mapboxTilesetId: 'YOUR_USERNAME.YOUR_TILESET_ID',
    
    // Protomaps (FREE - no API key needed! Recommended alternative)
    // Download your .pmtiles file from https://app.protomaps.com/
    protomapsUrl: null, // e.g., './vgm_streets.pmtiles'
    
    vectorTileUrl: null
  };

  // ===== DANGER ZONES DATABASE =====
  // These are sample known danger zones — in a production app, these would come from a database
  // with community reports + official crime data. Adjust coordinates to your city.
  let DANGER_ZONES = []; /*
    {
      id: 1,
      name: 'Isolated Underpass',
      lat: 28.6200,
      lng: 77.2150,
      radius: 200,
      severity: 'high',
      description: 'Poorly lit underpass with no CCTV. Multiple incidents reported at night.',
      type: 'underpass',
      reports: 23
    },
    {
      id: 2,
      name: 'Dark Alley — Sector 5',
      lat: 28.6080,
      lng: 77.2020,
      radius: 150,
      severity: 'high',
      description: 'Narrow unlit lane with no foot traffic after 8 PM. Avoid at night.',
      type: 'dark_alley',
      reports: 18
    },
    {
      id: 3,
      name: 'Construction Zone',
      lat: 28.6180,
      lng: 77.1980,
      radius: 250,
      severity: 'medium',
      description: 'Active construction site with poor visibility and limited pedestrian access.',
      type: 'construction',
      reports: 8
    },
    {
      id: 4,
      name: 'Deserted Park Area',
      lat: 28.6050,
      lng: 77.2180,
      radius: 300,
      severity: 'medium',
      description: 'Park area that gets completely deserted after sunset. No streetlights inside.',
      type: 'park',
      reports: 12
    },
    {
      id: 5,
      name: 'Industrial Back Road',
      lat: 28.6230,
      lng: 77.2250,
      radius: 200,
      severity: 'high',
      description: 'Road behind industrial area. No lighting, no shops, no foot traffic.',
      type: 'industrial',
      reports: 31
    },
    {
      id: 6,
      name: 'Railway Crossing Zone',
      lat: 28.6120,
      lng: 77.2300,
      radius: 180,
      severity: 'medium',
      description: 'Unmanned railway crossing area. Poorly lit at night with low visibility.',
      type: 'railway',
      reports: 9
    },
    {
      id: 7,
      name: 'Abandoned Building Stretch',
      lat: 28.6160,
      lng: 77.1920,
      radius: 170,
      severity: 'high',
      description: 'Row of abandoned buildings along the road. Known for anti-social activity.',
      type: 'abandoned',
      reports: 27
    }
  */

  // ===== SAFE PLACES DATABASE =====
  let SAFE_PLACES = []; /*
    { id: 1, name: 'Central Police Station', lat: 28.6155, lng: 77.2100, type: 'police', icon: 'shield-check', open: '24/7' },
    { id: 2, name: 'City Hospital', lat: 28.6100, lng: 77.2090, type: 'hospital', icon: 'hospital', open: '24/7' },
    { id: 3, name: 'MedPlus Pharmacy', lat: 28.6170, lng: 77.2060, type: 'pharmacy', icon: 'pill', open: '24/7' },
    { id: 4, name: 'Metro Station Gate 2', lat: 28.6130, lng: 77.2120, type: 'metro', icon: 'train-track', open: '5AM-11PM' },
    { id: 5, name: 'Women Help Desk', lat: 28.6190, lng: 77.2040, type: 'helpdesk', icon: 'shield', open: '24/7' },
    { id: 6, name: 'Fire Station', lat: 28.6090, lng: 77.2200, type: 'fire', icon: 'flame', open: '24/7' },
    { id: 7, name: 'SafeSpot Convenience Store', lat: 28.6210, lng: 77.2130, type: 'store', icon: 'store', open: '6AM-12AM' },
    { id: 8, name: 'Community Center', lat: 28.6070, lng: 77.2060, type: 'community', icon: 'landmark', open: '8AM-10PM' },
    { id: 9, name: 'Night Patrol Checkpoint', lat: 28.6145, lng: 77.2210, type: 'patrol', icon: 'flashlight', open: '8PM-6AM' },
    { id: 10, name: 'Emergency Booth — Park Rd', lat: 28.6175, lng: 77.2175, type: 'booth', icon: 'phone-call', open: '24/7' }
  */

  // ===== STATE =====
  let map;
  let userLocation = null;
  let fromCoords = null;
  let toCoords = null;
  let brightestRoute = null;
  let shortestRoute = null;
  let dangerLayerGroup;
  let safeLayerGroup;
  let routeLayerGroup;
  let userMarker = null;
  let destMarker = null;
  let searchTimeout = null;
  let dangerVisible = true;
  let safeVisible = true;
  let watchId = null;
  const COMMUNITY_REPORTS_STORAGE_KEY = 'sahayak-community-reports-v1';

  // VGM Specific Variables
  let vgmStreetsData = null;
  let havensCache = {};
  let pendingHavensRequest = null;
  let lastGooglePlacesCallAt = 0;
  const GOOGLE_PLACES_USAGE_KEY = 'sahayak_google_places_usage_v1';

  // ===== DOM ELEMENTS =====
  const $ = (sel) => document.querySelector(sel);
  const fromInput = $('#fromInput');
  const toInput = $('#toInput');
  const fromResults = $('#fromResults');
  const toResults = $('#toResults');
  const findRouteBtn = $('#findRouteBtn');
  const findShortestBtn = $('#findShortestBtn');
  const useMyLocationBtn = $('#useMyLocation');
  const locateBtn = $('#locateBtn');
  const toggleDangerBtn = $('#toggleDangerBtn');
  const toggleSafeBtn = $('#toggleSafeBtn');
  const clearRouteBtn = $('#clearRouteBtn');
  const statusText = $('#statusText');
  const mapLoading = $('#mapLoading');
  const routeInfoPanel = $('#routeInfoPanel');
  const routeCards = $('#routeCards');
  const dangerList = $('#dangerList');
  const safeList = $('#safeList');
  const sidebarToggle = $('#sidebarToggle');
  const mapSidebar = $('#mapSidebar');
  const sosBtn = $('#sosBtn');
  const reportNameInput = $('#reportName');
  const reportSeverityInput = $('#reportSeverity');
  const reportLatInput = $('#reportLat');
  const reportLngInput = $('#reportLng');
  const reportRadiusInput = $('#reportRadius');
  const reportTypeInput = $('#reportType');
  const reportDescriptionInput = $('#reportDescription');
  const useMapCenterReportBtn = $('#useMapCenterReportBtn');
  const saveReportBtn = $('#saveReportBtn');
  const reportImportInput = $('#reportImportInput');
  const exportReportsBtn = $('#exportReportsBtn');
  const clearReportsBtn = $('#clearReportsBtn');

  function isSecureForGeolocation() {
    return window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  }

  // ===== INITIALIZE MAP =====
  function initMap() {
    map = L.map('map', {
      center: CONFIG.defaultCenter,
      zoom: CONFIG.defaultZoom,
      zoomControl: true,
      attributionControl: true
    });

    L.tileLayer(CONFIG.tileUrl, {
      attribution: CONFIG.tileAttribution,
      maxZoom: 19,
      subdomains: 'abcd'
    }).addTo(map);

    // NASA VIIRS Black Marble Layer
    L.tileLayer(CONFIG.nasaViirsUrl, {
      attribution: '&copy; NASA GIBS Black Marble',
      maxZoom: 8,
      opacity: 0.6,
      className: 'nasa-viirs-layer'
    }).addTo(map);

    // Create layer groups
    dangerLayerGroup = L.layerGroup().addTo(map);
    safeLayerGroup = typeof L.markerClusterGroup === 'function'
      ? L.markerClusterGroup({
        disableClusteringAtZoom: 16,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        maxClusterRadius: 40
      }).addTo(map)
      : L.layerGroup().addTo(map);
    routeLayerGroup = L.layerGroup().addTo(map);

    // Add danger zones & safe places to map
    addDangerZones();
    addSafePlaces();

    // Try to get user location automatically
    getUserLocation(true);

    // Ensure Lucide icons are rendered inside dynamically created Leaflet popups
    map.on('popupopen', function () {
      if (typeof lucide !== 'undefined') lucide.createIcons();
    });

    updateStatus('Map ready. Enter locations or use your live position.');
  }

  // ===== GET USER LIVE LOCATION =====
  function getUserLocation(silent = false) {
    if (!navigator.geolocation) {
      if (!silent) updateStatus('Geolocation not supported by your browser.');
      return;
    }

    if (!isSecureForGeolocation()) {
      updateStatus('Location access requires HTTPS. Open this app on GitHub Pages, Vercel, Netlify, or a secure tunnel such as ngrok.');
      return;
    }

    updateStatus('Getting your live location...');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        userLocation = [latitude, longitude];
        fromCoords = [latitude, longitude];

        // Center map on user
        map.setView(userLocation, 15);

        // Place or move user marker
        if (userMarker) {
          userMarker.setLatLng(userLocation);
        } else {
          userMarker = L.marker(userLocation, {
            icon: createCustomIcon('user', 'marker-user'),
            zIndexOffset: 1000
          }).addTo(map);
          userMarker.bindPopup(createPopupHTML(
            '<i data-lucide="user"></i> Your Location',
            `Lat: ${latitude.toFixed(5)}, Lng: ${longitude.toFixed(5)}<br/>Accuracy: ~${Math.round(accuracy)}m`,
            ['info']
          ));
        }

        // Add accuracy circle
        L.circle(userLocation, {
          radius: accuracy,
          color: '#8b5cf6',
          fillColor: '#8b5cf6',
          fillOpacity: 0.08,
          weight: 1,
          dashArray: '5,5'
        }).addTo(map);

        fromInput.value = `My Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;

        updateStatus('Live location acquired. Enter your destination.');

        // Start watching position for live updates
        startLocationWatch();
      },
      (error) => {
        console.warn('Geolocation error:', error);
        if (!silent) {
          updateStatus('Could not get location. Please enter manually.');
        } else {
          updateStatus('Map ready. Enter your location or tap 📌 for GPS.');
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000
      }
    );
  }

  // ===== WATCH POSITION FOR LIVE UPDATES =====
  function startLocationWatch() {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);

    watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        userLocation = [latitude, longitude];
        if (userMarker) {
          userMarker.setLatLng(userLocation);
        }
      },
      () => { },
      { enableHighAccuracy: true, maximumAge: 5000 }
    );
  }

  // ===== GENERATE DANGER ZONES NEAR USER =====
  /*
  function generateLocalDangerZones(lat, lng) {
    // Create realistic danger zones around the user's actual location
    DANGER_ZONES = [
      {
        id: 1, name: 'Unlit Underpass', lat: lat + 0.004, lng: lng + 0.005,
        radius: 150, severity: 'high',
        description: 'Poorly lit underpass with no CCTV. Multiple incidents reported after dark.',
        type: 'underpass', reports: 23
      },
      {
        id: 2, name: 'Dark Side Street', lat: lat - 0.003, lng: lng - 0.006,
        radius: 120, severity: 'high',
        description: 'Narrow unlit lane with no pedestrian traffic after 8 PM.',
        type: 'dark_alley', reports: 18
      },
      {
        id: 3, name: 'Construction Zone', lat: lat + 0.006, lng: lng - 0.004,
        radius: 200, severity: 'medium',
        description: 'Active construction site. Poor visibility and blocked pedestrian paths.',
        type: 'construction', reports: 8
      },
      {
        id: 4, name: 'Abandoned Park', lat: lat - 0.005, lng: lng + 0.007,
        radius: 250, severity: 'medium',
        description: 'Deserted after sunset. No streetlights or security cameras.',
        type: 'park', reports: 14
      },
      {
        id: 5, name: 'Industrial Back Road', lat: lat + 0.008, lng: lng + 0.009,
        radius: 180, severity: 'high',
        description: 'No lighting, shops, or foot traffic. Known for vehicle theft.',
        type: 'industrial', reports: 31
      },
      {
        id: 6, name: 'Isolated Railway Area', lat: lat - 0.007, lng: lng + 0.003,
        radius: 160, severity: 'medium',
        description: 'Unmanned railway crossing. Very low visibility at night.',
        type: 'railway', reports: 9
      },
      {
        id: 7, name: 'Derelict Buildings', lat: lat + 0.002, lng: lng - 0.008,
        radius: 140, severity: 'high',
        description: 'Row of abandoned buildings. Reported anti-social activity.',
        type: 'abandoned', reports: 26
      },
      {
        id: 8, name: 'Poorly Lit Market Lane', lat: lat - 0.002, lng: lng + 0.004,
        radius: 100, severity: 'medium',
        description: 'Market lane that shuts down after 7 PM. Very dark and empty.',
        type: 'market', reports: 11
      },
      {
        id: 9, name: 'Vacant Lot', lat: lat + 0.005, lng: lng - 0.002,
        radius: 130, severity: 'medium',
        description: 'Large empty lot with overgrown vegetation blocking visibility.',
        type: 'vacant', reports: 7
      },
      {
        id: 10, name: 'Secluded Bus Depot', lat: lat - 0.006, lng: lng - 0.003,
        radius: 170, severity: 'high',
        description: 'Bus depot area that is completely deserted after last buses leave at 10 PM.',
        type: 'depot', reports: 19
      }
    ];

    // Refresh the map layers
    dangerLayerGroup.clearLayers();
    addDangerZones();
    updateDangerList();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ===== GENERATE SAFE PLACES NEAR USER =====
  function generateLocalSafePlaces(lat, lng) {
    SAFE_PLACES = [
      { id: 1, name: 'Nearest Police Station', lat: lat + 0.003, lng: lng + 0.002, type: 'police', icon: 'shield-check', open: '24/7' },
      { id: 2, name: 'District Hospital', lat: lat - 0.004, lng: lng + 0.003, type: 'hospital', icon: 'hospital', open: '24/7' },
      { id: 3, name: 'Apollo Pharmacy', lat: lat + 0.001, lng: lng - 0.003, type: 'pharmacy', icon: 'pill', open: '24/7' },
      { id: 4, name: 'Metro Station', lat: lat + 0.002, lng: lng + 0.006, type: 'metro', icon: 'train-track', open: '5 AM–11 PM' },
      { id: 5, name: 'Women Help Desk', lat: lat - 0.001, lng: lng + 0.001, type: 'helpdesk', icon: 'shield', open: '24/7' },
      { id: 6, name: 'Fire Station', lat: lat - 0.005, lng: lng - 0.004, type: 'fire', icon: 'flame', open: '24/7' },
      { id: 7, name: '24hr Convenience Store', lat: lat + 0.004, lng: lng - 0.001, type: 'store', icon: 'store', open: '24/7' },
      { id: 8, name: 'Community Center', lat: lat - 0.002, lng: lng - 0.005, type: 'community', icon: 'landmark', open: '8 AM–10 PM' },
      { id: 9, name: 'Night Patrol Booth', lat: lat + 0.006, lng: lng + 0.004, type: 'patrol', icon: 'flashlight', open: '8 PM–6 AM' },
      { id: 10, name: 'Emergency Call Booth', lat: lat - 0.003, lng: lng + 0.006, type: 'booth', icon: 'phone-call', open: '24/7' },
      { id: 11, name: 'ATM Booth (CCTV)', lat: lat + 0.001, lng: lng + 0.004, type: 'atm', icon: 'credit-card', open: '24/7' },
      { id: 12, name: 'Petrol Station', lat: lat - 0.006, lng: lng + 0.002, type: 'petrol', icon: 'fuel', open: '24/7' }
    ];

    safeLayerGroup.clearLayers();
    addSafePlaces();
    updateSafeList();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }
  */

  // ===== ADD DANGER ZONES TO MAP =====
  function addDangerZones() {
    DANGER_ZONES.forEach(zone => {
      const color = zone.severity === 'high' ? CONFIG.routeColors.danger : CONFIG.routeColors.caution;
      const fillOpacity = zone.severity === 'high' ? 0.18 : 0.12;

      // Danger circle
      const circle = L.circle([zone.lat, zone.lng], {
        radius: zone.radius,
        color: color,
        fillColor: color,
        fillOpacity: fillOpacity,
        weight: 2,
        dashArray: zone.severity === 'high' ? '' : '8,6',
        className: 'danger-zone-circle'
      });

      // Danger marker
      const marker = L.marker([zone.lat, zone.lng], {
        icon: createCustomIcon('alert-triangle', 'marker-danger')
      });

      const severityLabel = zone.severity.charAt(0).toUpperCase() + zone.severity.slice(1);
      marker.bindPopup(createPopupHTML(
        `<i data-lucide="alert-triangle"></i> ${zone.name}`,
        `${zone.description}<br/><br/><strong>${zone.reports} reports</strong> from community`,
        [zone.severity === 'high' ? 'danger' : 'caution', 'info'],
        [`Severity: ${severityLabel}`, zone.type.replace('_', ' ')]
      ));

      dangerLayerGroup.addLayer(circle);
      dangerLayerGroup.addLayer(marker);
    });
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ===== ADD SAFE PLACES TO MAP =====
  function addSafePlaces() {
    SAFE_PLACES.forEach(place => {
      const marker = L.marker([place.lat, place.lng], {
        icon: createCustomIcon(place.icon, 'marker-safe')
      });

      marker.bindPopup(createPopupHTML(
        `<i data-lucide="${place.icon}"></i> ${place.name}`,
        `Type: ${place.type.charAt(0).toUpperCase() + place.type.slice(1)}<br/>Hours: <strong>${place.open}</strong>`,
        ['safe'],
        ['High-Activity Area', place.open === '24/7' ? '24/7 Open' : 'Limited Hours']
      ));

      safeLayerGroup.addLayer(marker);
    });
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ===== CREATE CUSTOM MAP ICON =====
  function createCustomIcon(iconName, className) {
    return L.divIcon({
      html: `<div class="custom-marker ${className}"><i data-lucide="${iconName}"></i></div>`,
      className: '',
      iconSize: [36, 36],
      iconAnchor: [18, 18],
      popupAnchor: [0, -20]
    });
  }

  // ===== CREATE POPUP HTML =====
  function createPopupHTML(title, description, tagTypes = [], tagLabels = []) {
    let tagsHtml = '';
    if (tagLabels.length > 0) {
      tagsHtml = '<div class="popup-tags">';
      tagLabels.forEach((label, i) => {
        const type = tagTypes[i] || 'info';
        tagsHtml += `<span class="popup-tag ${type}">${label}</span>`;
      });
      tagsHtml += '</div>';
    }

    return `
      <div class="popup-content">
        <h4>${title}</h4>
        <p>${description}</p>
        ${tagsHtml}
      </div>
    `;
  }

  // ===== GEOCODING SEARCH =====
  async function searchLocation(query) {
    if (!query || query.length < 3) return [];

    try {
      const params = new URLSearchParams({
        q: query,
        format: 'json',
        limit: '5',
        addressdetails: '1'
      });

      // If user location is known, bias results toward it
      if (userLocation) {
        params.append('viewbox', `${userLocation[1] - 0.5},${userLocation[0] + 0.5},${userLocation[1] + 0.5},${userLocation[0] - 0.5}`);
        params.append('bounded', '0');
      }

      const response = await fetch(`${CONFIG.nominatimUrl}?${params}`, {
        headers: { 'Accept-Language': 'en' }
      });

      if (!response.ok) throw new Error('Search failed');
      return await response.json();
    } catch (err) {
      console.error('Search error:', err);
      return [];
    }
  }

  // ===== RENDER SEARCH RESULTS =====
  function renderSearchResults(results, container, inputField, isFrom) {
    container.innerHTML = '';

    if (results.length === 0) {
      container.classList.remove('active');
      return;
    }

    results.forEach(result => {
      const item = document.createElement('div');
      item.className = 'search-result-item';
      item.textContent = result.display_name;
      item.addEventListener('click', () => {
        const lat = parseFloat(result.lat);
        const lon = parseFloat(result.lon);
        inputField.value = result.display_name.split(',').slice(0, 2).join(',');

        if (isFrom) {
          fromCoords = [lat, lon];

          if (userMarker) userMarker.setLatLng([lat, lon]);
          else {
            userMarker = L.marker([lat, lon], {
              icon: createCustomIcon('user', 'marker-user'),
              zIndexOffset: 1000
            }).addTo(map);
          }
          if (typeof lucide !== 'undefined') lucide.createIcons();
          map.setView([lat, lon], 15);
        } else {
          toCoords = [lat, lon];
          if (destMarker) destMarker.setLatLng([lat, lon]);
          else {
            destMarker = L.marker([lat, lon], {
              icon: createCustomIcon('map-pin', 'marker-destination'),
              zIndexOffset: 900
            }).addTo(map);
          }
          if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        container.classList.remove('active');
      });
      container.appendChild(item);
    });

    container.classList.add('active');
  }

  // ===== CALCULATE ROUTE =====
  async function calculateRoute(from, to, isBrightest = true) {
    showLoading(true);
    updateStatus(isBrightest ? 'Calculating brightest path avoiding danger zones...' : 'Calculating shortest path...');

    try {
      let waypoints;

      if (isBrightest) {
        // BRIGHTEST PATH: Generate waypoints that route through safe areas
        // and around danger zones
        waypoints = generateBrightestWaypoints(from, to);
      } else {
        waypoints = [from, to];
      }

      // Build OSRM URL with waypoints
      const coordsString = waypoints.map(wp => `${wp[1]},${wp[0]}`).join(';');
      const url = `${CONFIG.osrmUrl}/${coordsString}?overview=full&geometries=geojson&steps=true&alternatives=false`;

      const response = await fetch(url);
      if (!response.ok) throw new Error('Routing failed');

      const data = await response.json();

      if (!data.routes || data.routes.length === 0) {
        throw new Error('No route found');
      }

      const route = data.routes[0];
      const coordinates = route.geometry.coordinates.map(c => [c[1], c[0]]);
      const distance = (route.distance / 1000).toFixed(1);
      const duration = Math.ceil(route.duration / 60);

      // Draw route on map
      drawRoute(coordinates, isBrightest);

      // Calculate illumination score
      const safetyScore = calculateIlluminationScore(coordinates, isBrightest);

      // Async fetch VGM havens to update map dynamically based on Google Places activity
      getVGMHavens(coordinates[Math.floor(coordinates.length / 2)][0], coordinates[Math.floor(coordinates.length / 2)][1]).then(havens => {
        if (havens && havens.places && havens.places.length > 0) {
          syncSafePlacesFromGoogle(havens.places);
        }
      });

      // Show route info
      showRouteInfo({
        isBrightest,
        distance,
        duration,
        safetyScore,
        coordinates
      });

      // Fit map to route
      const routeBounds = L.latLngBounds(coordinates);
      map.fitBounds(routeBounds, { padding: [60, 60] });
      const scoreLabel = safetyScore === 'Unknown'
        ? 'Data unavailable for this area'
        : `Illumination Index: ${safetyScore}/100`;

      updateStatus(isBrightest
        ? `Brightest path found: ${distance} km, ~${duration} min. ${scoreLabel}`
        : `Shortest path: ${distance} km, ~${duration} min. ${scoreLabel}`
      );

    } catch (err) {
      console.error('Routing error:', err);
      updateStatus('❌ Route calculation failed. Please try different locations.');
    } finally {
      showLoading(false);
    }
  }

  // ===== GENERATE BRIGHTEST PATH WAYPOINTS =====
  function generateBrightestWaypoints(from, to) {
    // This function creates intermediate waypoints that steer the route
    // through safe places and away from danger zones

    const waypoints = [from];
    const midLat = (from[0] + to[0]) / 2;
    const midLng = (from[1] + to[1]) / 2;

    // Find safe places near the route corridor
    const routeCorridorSafePlaces = SAFE_PLACES.filter(place => {
      const distToMid = haversineDistance(place.lat, place.lng, midLat, midLng);
      return distToMid < 3; // within 3km of route midpoint
    });

    // Find danger zones near the direct path
    const dangerZonesNearPath = DANGER_ZONES.filter(zone => {
      return isNearLine(zone.lat, zone.lng, from, to, 0.005); // ~500m buffer
    });

    // If there are danger zones near the direct path, create detour waypoints
    if (dangerZonesNearPath.length > 0) {
      // For each danger zone, find a safe place nearby to route through instead
      const safeWaypoints = [];

      dangerZonesNearPath.forEach(dangerZone => {
        // Find the closest safe place to this danger zone
        let closestSafe = null;
        let closestDist = Infinity;

        routeCorridorSafePlaces.forEach(safe => {
          const dist = haversineDistance(dangerZone.lat, dangerZone.lng, safe.lat, safe.lng);
          if (dist < closestDist && dist > 0.1) { // at least 100m away from danger
            closestDist = dist;
            closestSafe = safe;
          }
        });

        if (closestSafe) {
          safeWaypoints.push([closestSafe.lat, closestSafe.lng]);
        } else {
          // Create a deflection waypoint away from the danger zone
          const deflection = getDeflectionPoint(from, to, dangerZone);
          safeWaypoints.push(deflection);
        }
      });

      // Sort waypoints by distance from origin
      safeWaypoints.sort((a, b) => {
        return haversineDistance(from[0], from[1], a[0], a[1]) -
          haversineDistance(from[0], from[1], b[0], b[1]);
      });

      // Remove duplicate or very close waypoints
      const filtered = [];
      safeWaypoints.forEach(wp => {
        if (filtered.length === 0 || haversineDistance(wp[0], wp[1], filtered[filtered.length - 1][0], filtered[filtered.length - 1][1]) > 0.1) {
          filtered.push(wp);
        }
      });

      // Limit to max 3 intermediate waypoints for OSRM
      filtered.slice(0, 3).forEach(wp => waypoints.push(wp));
    } else if (routeCorridorSafePlaces.length > 0) {
      // Even without danger zones, route through well-lit safe places
      const bestSafe = routeCorridorSafePlaces
        .filter(sp => sp.open === '24/7')
        .sort((a, b) => {
          const dA = haversineDistance(midLat, midLng, a.lat, a.lng);
          const dB = haversineDistance(midLat, midLng, b.lat, b.lng);
          return dA - dB;
        })[0];

      if (bestSafe) {
        waypoints.push([bestSafe.lat, bestSafe.lng]);
      }
    }

    waypoints.push(to);
    return waypoints;
  }

  // ===== HELPER: Check if point is near a line =====
  function isNearLine(px, py, lineStart, lineEnd, threshold) {
    const dx = lineEnd[1] - lineStart[1];
    const dy = lineEnd[0] - lineStart[0];
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return false;

    const t = Math.max(0, Math.min(1, ((px - lineStart[0]) * dy + (py - lineStart[1]) * dx) / (len * len)));
    const closestX = lineStart[0] + t * dy;
    const closestY = lineStart[1] + t * dx;

    const dist = Math.sqrt((px - closestX) ** 2 + (py - closestY) ** 2);
    return dist < threshold;
  }

  // ===== HELPER: Get deflection point away from danger =====
  function getDeflectionPoint(from, to, dangerZone) {
    const midLat = (from[0] + to[0]) / 2;
    const midLng = (from[1] + to[1]) / 2;

    // Calculate perpendicular direction from danger zone
    const dx = to[1] - from[1];
    const dy = to[0] - from[0];
    const perpLat = -dx;
    const perpLng = dy;
    const perpLen = Math.sqrt(perpLat * perpLat + perpLng * perpLng);

    if (perpLen === 0) return [midLat + 0.003, midLng];

    // Determine which side of the route to deflect to (away from danger)
    const side = (dangerZone.lat - midLat) * perpLat + (dangerZone.lng - midLng) * perpLng > 0 ? -1 : 1;

    const offset = 0.004; // ~400m deflection
    return [
      midLat + side * (perpLat / perpLen) * offset,
      midLng + side * (perpLng / perpLen) * offset
    ];
  }

  // ===== HAVERSINE DISTANCE (km) =====
  function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function getGooglePlacesUsage() {
    try {
      const raw = localStorage.getItem(GOOGLE_PLACES_USAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function recordGooglePlacesUsage(now) {
    try {
      const windowStart = now - 24 * 60 * 60 * 1000;
      const usage = getGooglePlacesUsage().filter(timestamp => Number.isFinite(timestamp) && timestamp >= windowStart);
      usage.push(now);
      localStorage.setItem(GOOGLE_PLACES_USAGE_KEY, JSON.stringify(usage));
    } catch (e) {
      console.warn('Failed to persist Google Places usage window', e);
    }
  }

  function canUseGooglePlaces(now) {
    const windowStart = now - 24 * 60 * 60 * 1000;
    const recentUsage = getGooglePlacesUsage().filter(timestamp => Number.isFinite(timestamp) && timestamp >= windowStart);
    return recentUsage.length < CONFIG.googlePlaces.maxCallsPerDay;
  }

  function isWithinAllowedGooglePlacesArea(lat, lng) {
    return CONFIG.googlePlaces.allowedAreas.some(area =>
      haversineDistance(lat, lng, area.lat, area.lng) <= area.radiusKm
    );
  }

  // ===== DRAW ROUTE ON MAP =====
  function drawRoute(coordinates, isBrightest) {
    const color = isBrightest ? CONFIG.routeColors.brightest : CONFIG.routeColors.shortest;
    const weight = isBrightest ? 6 : 4;
    const opacity = isBrightest ? 0.9 : 0.7;

    // Glow effect (thicker, more transparent background line)
    if (isBrightest) {
      const glowLine = L.polyline(coordinates, {
        color: color,
        weight: 16,
        opacity: 0.15,
        smoothFactor: 1,
        lineCap: 'round',
        lineJoin: 'round'
      });
      routeLayerGroup.addLayer(glowLine);

      const midGlow = L.polyline(coordinates, {
        color: color,
        weight: 10,
        opacity: 0.3,
        smoothFactor: 1,
        lineCap: 'round',
        lineJoin: 'round'
      });
      routeLayerGroup.addLayer(midGlow);
    }

    // Main route line
    const routeLine = L.polyline(coordinates, {
      color: color,
      weight: weight,
      opacity: opacity,
      smoothFactor: 1,
      lineCap: 'round',
      lineJoin: 'round',
      dashArray: isBrightest ? '' : '12,8'
    });

    routeLayerGroup.addLayer(routeLine);

    // Animated dot along brightest path
    if (isBrightest) {
      animateRouteMarker(coordinates, color);
    }
  }

  // ===== ANIMATE A DOT ALONG THE ROUTE =====
  function animateRouteMarker(coordinates, color) {
    const animDot = L.circleMarker(coordinates[0], {
      radius: 5,
      color: color,
      fillColor: '#fff',
      fillOpacity: 1,
      weight: 2
    });
    routeLayerGroup.addLayer(animDot);

    let idx = 0;
    const step = Math.max(1, Math.floor(coordinates.length / 200));

    function animate() {
      if (idx >= coordinates.length) idx = 0;
      animDot.setLatLng(coordinates[idx]);
      idx += step;
      requestAnimationFrame(animate);
    }
    animate();
  }

  // ===== DEBOUNCED GOOGLE PLACES API (FREE TIER GUARD) =====
  async function getVGMHavens(lat, lon) {
    if (!CONFIG.googlePlacesApiKey || CONFIG.googlePlacesApiKey === 'YOUR_GOOGLE_KEY') {
      return { places: [] };
    }

    if (!isWithinAllowedGooglePlacesArea(lat, lon)) {
      console.log('Skipping Google Places call outside approved VGM areas');
      return { places: [] };
    }

    const roundedLat = Number(lat).toFixed(CONFIG.googlePlaces.cachePrecision);
    const roundedLon = Number(lon).toFixed(CONFIG.googlePlaces.cachePrecision);
    const cacheKey = `${roundedLat},${roundedLon}`;
    if (havensCache[cacheKey]) return havensCache[cacheKey];

    if (pendingHavensRequest && pendingHavensRequest.cacheKey === cacheKey) {
      return pendingHavensRequest.promise;
    }

    const now = Date.now();
    if (now - lastGooglePlacesCallAt < CONFIG.googlePlaces.cooldownMs) {
      console.log('Skipping Google Places call during cooldown window');
      return { places: [] };
    }

    if (!canUseGooglePlaces(now)) {
      console.log('Skipping Google Places call because daily local browser cap was reached');
      return { places: [] };
    }

    lastGooglePlacesCallAt = now;

    try {
      const url = 'https://places.googleapis.com/v1/places:searchNearby';
      const requestPromise = fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Api-Key': CONFIG.googlePlacesApiKey,
          'X-Goog-FieldMask': 'places.displayName,places.location,places.businessStatus' // FREE TIER FIELD MASK
        },
        body: JSON.stringify({
          includedTypes: ["police", "hospital", "pharmacy", "convenience_store"],
          maxResultCount: CONFIG.googlePlaces.maxResultCount,
          locationRestriction: {
            circle: { center: { latitude: lat, longitude: lon }, radius: CONFIG.googlePlaces.searchRadiusMeters }
          }
        })
      })
        .then(async response => {
          if (!response.ok) return { places: [] };
          const data = await response.json();
          havensCache[cacheKey] = data;
          recordGooglePlacesUsage(now);
          return data;
        })
        .catch(() => ({ places: [] }))
        .finally(() => {
          if (pendingHavensRequest && pendingHavensRequest.cacheKey === cacheKey) {
            pendingHavensRequest = null;
          }
        });

      pendingHavensRequest = { cacheKey, promise: requestPromise };
      return await requestPromise;
    } catch (e) {
      return { places: [] };
    }
  }

  function syncSafePlacesFromGoogle(places) {
    const normalized = places
      .filter(place => place.location && typeof place.location.latitude === 'number' && typeof place.location.longitude === 'number')
      .map((place, index) => ({
        id: `google-${index}-${place.location.latitude}-${place.location.longitude}`,
        name: place.displayName?.text || 'Nearby Active Area',
        lat: place.location.latitude,
        lng: place.location.longitude,
        type: 'active_area',
        icon: 'shield-check',
        open: place.businessStatus || 'OPERATIONAL'
      }));

    SAFE_PLACES = normalized;
    safeLayerGroup.clearLayers();
    addSafePlaces();
    updateSafeList();
  }

  function havenWeight(type) {
    switch (type) {
      case 'police':
      case 'hospital':
      case 'fire_station':
        return 1.0;
      case 'pharmacy':
      case 'railway_station':
      case 'bus_station':
        return 0.75;
      case 'fuel':
      case 'convenience':
      case 'atm':
        return 0.55;
      case 'clinic':
        return 0.45;
      default:
        return 0.35;
    }
  }

  function reportPenaltyForRoute(coordinates) {
    if (DANGER_ZONES.length === 0 || typeof turf === 'undefined' || coordinates.length < 2) return 0;

    const routeLine = turf.lineString(coordinates.map(c => [c[1], c[0]]));
    const routeBuffer = turf.buffer(routeLine, 0.05, { units: 'kilometers' });
    let penalty = 0;

    DANGER_ZONES.forEach((zone) => {
      const zonePoint = turf.point([zone.lng, zone.lat]);
      if (turf.booleanPointInPolygon(zonePoint, routeBuffer)) {
        penalty += zone.severity === 'high' ? 18 : 9;
      }
    });

    return penalty;
  }

  // ===== CALCULATE ILLUMINATION SCORE (Fusion) =====
  function calculateIlluminationScore(coordinates, isBrightest) {
    let streetScore = 0; // 55% max
    let activityScore = 0; // 30% max
    let visualScore = 5; // 5% baseline for urban night-light context
    let riskPenalty = 0;

    // Integration of Turf.js and in-memory VGM_STREETS.json fallback
    if (vgmStreetsData && typeof turf !== 'undefined' && coordinates.length > 1) {
      let litCoverage = 0;
      let darkCoverage = 0;
      let matchedSegments = 0;
      
      // Draw a 25-meter (0.025 km) buffer around the entire route to handle noisy GPS
      const routeLine = turf.lineString(coordinates.map(c => [c[1], c[0]]));
      const routeBuffer = turf.buffer(routeLine, 0.025, {units: 'kilometers'});

      turf.featureEach(vgmStreetsData, function (currentFeature) {
        // Proxy Tags Fix: If 'lit=yes' is missing, assume trunk, primary, secondary, or commercial highways are lit
        const props = currentFeature.properties || {};
        const isExplicitlyLit = props.lit === 'yes';
        const isProxyLit = props.lit === 'assumed_yes' || ['trunk', 'primary', 'secondary', 'commercial'].includes(props.highway);
        const isDark = props.lit === 'no';

        if (currentFeature.geometry.type === 'LineString') {
          // Check if buffer touches the lit street
          const intersects = turf.booleanIntersects(routeBuffer, currentFeature);
          if (!intersects) return;

          matchedSegments += 1;
          if (isExplicitlyLit) litCoverage += 1.0;
          else if (isProxyLit) litCoverage += 0.72;
          if (isDark) darkCoverage += 1.0;
        }
      });

      if (matchedSegments > 0) {
        const normalizedCoverage = Math.max(0, (litCoverage - darkCoverage * 0.65) / matchedSegments);
        streetScore = Math.round(Math.min(55, normalizedCoverage * 55));
      }
    } else {
      streetScore = 0; // Cold start default
    }

    // Activity check
    let havenSignal = 0;
    const sampleStep = Math.max(1, Math.floor(coordinates.length / 25));
    coordinates.filter((_, index) => index % sampleStep === 0).forEach(coord => {
      SAFE_PLACES.forEach(place => {
        const dist = haversineDistance(coord[0], coord[1], place.lat, place.lng);
        if (dist < 0.2) {
          havenSignal += havenWeight(place.type);
        } else if (dist < 0.5) {
          havenSignal += havenWeight(place.type) * 0.4;
        }
      });
    });

    activityScore = Math.min(30, Math.round(havenSignal));
    riskPenalty = reportPenaltyForRoute(coordinates);

    let score = streetScore + activityScore + visualScore - riskPenalty;
    
    // Cold Start Fallback
    if (streetScore === 0 && activityScore === 0) {
      return 'Unknown'; 
    }

    if (isBrightest) score += 5; // brightest path bonus
    score = Math.max(15, Math.min(98, Math.round(score)));

    return score;
  }

  // ===== SHOW ROUTE INFO =====
  function showRouteInfo(routeData) {
    routeInfoPanel.style.display = 'block';

    const isUnknown = routeData.safetyScore === 'Unknown';

    const card = document.createElement('div');
    card.className = `route-card ${isUnknown ? 'unknown-card' : (routeData.isBrightest ? 'safe' : 'shortest')}`;

    const badgeHTML = routeData.isBrightest && !isUnknown
      ? '<span class="route-badge recommended">✓ Recommended</span>'
      : '';

    const walkDuration = Math.ceil(routeData.duration * 3.5); // walking is ~3.5x driving
    const cardTitle = isUnknown ? 'Data Unavailable for this Area' : (routeData.isBrightest ? '💡 Well-Lit Route' : '📏 Shortest Path');
    const lightingLevel = isUnknown ? 'Unknown' : (routeData.isBrightest ? 'High' : 'Standard');

    card.innerHTML = `
      <div class="route-card-header">
        <div class="route-card-title ${isUnknown ? 'text-gray' : ''}">
          ${cardTitle}
        </div>
        ${badgeHTML}
      </div>
      <div class="route-card-stats">
        <div class="route-stat">
          <strong>${routeData.distance} km</strong>
          Distance
        </div>
        <div class="route-stat">
          <strong>~${walkDuration} min</strong>
          Walking
        </div>
        <div class="route-stat">
          <strong>${routeData.safetyScore !== 'Unknown' ? routeData.safetyScore + '/100' : '<span style="color:gray;">Unknown</span>'}</strong>
          Illumination Index
        </div>
        <div class="route-stat">
          <strong>${lightingLevel}</strong>
          Lighting
        </div>
      </div>
    `;

    routeCards.appendChild(card);
  }

  // ===== UPDATE DANGER LIST IN SIDEBAR =====
  function updateDangerList() {
    dangerList.innerHTML = '';
    if (DANGER_ZONES.length === 0) {
      dangerList.innerHTML = '<p class="placeholder-text">No verified low-light reports loaded for this area yet.</p>';
      return;
    }
    DANGER_ZONES.forEach(zone => {
      const item = document.createElement('div');
      item.className = 'danger-item';
      item.innerHTML = `
        <span class="danger-icon">⚠️</span>
        <span class="danger-name">${zone.name}</span>
        <span class="danger-severity ${zone.severity}">${zone.severity}</span>
      `;
      item.addEventListener('click', () => {
        map.setView([zone.lat, zone.lng], 16);
      });
      dangerList.appendChild(item);
    });
  }

  // ===== UPDATE SAFE LIST IN SIDEBAR =====
  function updateSafeList() {
    safeList.innerHTML = '';
    if (SAFE_PLACES.length === 0) {
      safeList.innerHTML = '<p class="placeholder-text">No active-area data loaded. Add a Google Places key or use a curated civic dataset.</p>';
      return;
    }
    SAFE_PLACES.forEach(place => {
      const item = document.createElement('div');
      item.className = 'safe-item';
      item.innerHTML = `
        <span class="safe-icon">${place.icon}</span>
        <span class="safe-name">${place.name}</span>
      `;
      item.addEventListener('click', () => {
        map.setView([place.lat, place.lng], 16);
      });
      safeList.appendChild(item);
    });
  }

  // ===== UI HELPERS =====
  function updateStatus(text) {
    if (statusText) statusText.textContent = text;
  }

  function showLoading(show) {
    if (mapLoading) mapLoading.style.display = show ? 'flex' : 'none';
  }

  // ===== EVENT LISTENERS =====

  // Sidebar toggle
  sidebarToggle.addEventListener('click', () => {
    mapSidebar.classList.toggle('collapsed');
    setTimeout(() => map.invalidateSize(), 350);
  });

  // Use my location
  useMyLocationBtn.addEventListener('click', () => {
    getUserLocation(false);
  });

  locateBtn.addEventListener('click', () => {
    getUserLocation(false);
  });

  // From input search
  fromInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = fromInput.value.trim();
    if (query.length < 3) {
      fromResults.classList.remove('active');
      return;
    }
    searchTimeout = setTimeout(async () => {
      const results = await searchLocation(query);
      renderSearchResults(results, fromResults, fromInput, true);
    }, CONFIG.searchDelay);
  });

  // To input search
  toInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = toInput.value.trim();
    if (query.length < 3) {
      toResults.classList.remove('active');
      return;
    }
    searchTimeout = setTimeout(async () => {
      const results = await searchLocation(query);
      renderSearchResults(results, toResults, toInput, false);
    }, CONFIG.searchDelay);
  });

  // Close search results when clicking outside
  document.addEventListener('click', (e) => {
    if (!fromInput.contains(e.target) && !fromResults.contains(e.target)) {
      fromResults.classList.remove('active');
    }
    if (!toInput.contains(e.target) && !toResults.contains(e.target)) {
      toResults.classList.remove('active');
    }
  });

  // Find brightest path
  findRouteBtn.addEventListener('click', () => {
    if (!fromCoords) {
      updateStatus('⚠️ Please set your starting location first.');
      return;
    }
    if (!toCoords) {
      updateStatus('⚠️ Please set your destination.');
      return;
    }
    // Clear previous brightest route
    routeLayerGroup.clearLayers();
    routeCards.innerHTML = '';
    brightestRoute = null;
    shortestRoute = null;

    calculateRoute(fromCoords, toCoords, true);
  });

  // Find shortest path
  findShortestBtn.addEventListener('click', () => {
    if (!fromCoords) {
      updateStatus('⚠️ Please set your starting location first.');
      return;
    }
    if (!toCoords) {
      updateStatus('⚠️ Please set your destination.');
      return;
    }
    calculateRoute(fromCoords, toCoords, false);
  });

  // Toggle danger zones
  toggleDangerBtn.addEventListener('click', () => {
    dangerVisible = !dangerVisible;
    toggleDangerBtn.classList.toggle('active', dangerVisible);
    if (dangerVisible) {
      dangerLayerGroup.addTo(map);
    } else {
      map.removeLayer(dangerLayerGroup);
    }
  });

  // Toggle safe places
  toggleSafeBtn.addEventListener('click', () => {
    safeVisible = !safeVisible;
    toggleSafeBtn.classList.toggle('active', safeVisible);
    if (safeVisible) {
      safeLayerGroup.addTo(map);
    } else {
      map.removeLayer(safeLayerGroup);
    }
  });

  if (useMapCenterReportBtn) {
    useMapCenterReportBtn.addEventListener('click', () => {
      const center = map.getCenter();
      populateReportCoordinates(center.lat, center.lng);
      updateStatus('Report coordinates set from current map center.');
    });
  }

  if (saveReportBtn) {
    saveReportBtn.addEventListener('click', () => {
      const lat = parseFloat(reportLatInput.value);
      const lng = parseFloat(reportLngInput.value);

      if (!reportNameInput.value.trim() || Number.isNaN(lat) || Number.isNaN(lng)) {
        updateStatus('Enter a report title and valid coordinates before saving.');
        return;
      }

      DANGER_ZONES.push({
        id: Date.now(),
        name: reportNameInput.value.trim(),
        lat,
        lng,
        radius: Math.max(50, parseInt(reportRadiusInput.value || '150', 10)),
        severity: reportSeverityInput.value === 'high' ? 'high' : 'medium',
        description: reportDescriptionInput.value.trim() || 'Community-submitted field report.',
        type: reportTypeInput.value.trim() || 'community_report',
        reports: 1
      });

      persistCommunityReports();
      dangerLayerGroup.clearLayers();
      addDangerZones();
      updateDangerList();
      clearReportForm();
      populateReportCoordinates(lat, lng);
      updateStatus('Community report saved locally.');
    });
  }

  if (reportImportInput) {
    reportImportInput.addEventListener('change', async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = JSON.parse(text);
        applyCommunityReports(data);
        persistCommunityReports();
        updateStatus('Community reports imported successfully.');
      } catch (error) {
        console.error('Import failed', error);
        updateStatus('Import failed. Use the same structure as community_reports.example.json.');
      } finally {
        reportImportInput.value = '';
      }
    });
  }

  if (exportReportsBtn) {
    exportReportsBtn.addEventListener('click', () => {
      exportCommunityReports();
      updateStatus('Community reports exported as JSON.');
    });
  }

  if (clearReportsBtn) {
    clearReportsBtn.addEventListener('click', () => {
      DANGER_ZONES = [];
      localStorage.removeItem(COMMUNITY_REPORTS_STORAGE_KEY);
      dangerLayerGroup.clearLayers();
      updateDangerList();
      updateStatus('Local community reports cleared.');
    });
  }

  // Clear routes
  clearRouteBtn.addEventListener('click', () => {
    routeLayerGroup.clearLayers();
    routeCards.innerHTML = '';
    routeInfoPanel.style.display = 'none';
    if (destMarker) {
      map.removeLayer(destMarker);
      destMarker = null;
    }
    toCoords = null;
    toInput.value = '';
    updateStatus('Routes cleared. Enter a new destination.');
  });

  // SOS button
  if (sosBtn) {
    sosBtn.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = 'dialer.html?sos=1';
    });
  }

  // Allow clicking on map to set destination
  let clickLocked = false;
  map = null; // will be set in initMap

  // ===== LOAD OFFLINE VGM STREETS =====
  async function loadVGMStreets() {
    // PRIORITY 1: If Protomaps URL is set, use it (FREE, no API key!)
    if (CONFIG.protomapsUrl) {
      loadProtomapsTiles();
      return;
    }
    
    // PRIORITY 2: If Mapbox is configured (requires paid account)
    if (CONFIG.useVectorTiles && CONFIG.mapboxToken && CONFIG.mapboxTilesetId) {
      loadMapboxTiles();
      return;
    }
    
    // DEFAULT: Load GeoJSON directly (RECOMMENDED for files < 5MB)
    // This is 100% FREE - no accounts, no API keys, no credit cards!
    try {
      const res = await fetch('vgm_streets.json');
      if (res.ok) {
        vgmStreetsData = await res.json();
        console.log('✅ Loaded GeoJSON streets data:', vgmStreetsData.features.length, 'features');
        console.log('💡 Tip: GeoJSON under 5MB works great on mobile!');
        
        // Add GeoJSON layer to map for visualization
        addStreetsLayer();
      }
    } catch (e) {
      console.error('❌ Failed to load vgm_streets.json:', e);
      console.log('💡 Make sure vgm_streets.json is in the same folder as safemap.html');
    }
  }

  async function loadVGMHavens() {
    try {
      const res = await fetch('vgm_havens.json');
      if (!res.ok) return;

      const data = await res.json();
      const features = Array.isArray(data.features) ? data.features : [];

      SAFE_PLACES = features
        .filter((feature) => feature.geometry?.type === 'Point' && Array.isArray(feature.geometry.coordinates))
        .map((feature, index) => {
          const [lng, lat] = feature.geometry.coordinates;
          const props = feature.properties || {};
          return {
            id: props.osm_id || `local-${index}`,
            name: props.name || 'Nearby Active Area',
            lat,
            lng,
            type: props.type || 'active_area',
            icon: props.icon || 'map-pin',
            open: props.open || 'Unknown'
          };
        });

      safeLayerGroup.clearLayers();
      addSafePlaces();
      updateSafeList();
      console.log('Loaded local VGM active places:', SAFE_PLACES.length);
    } catch (e) {
      console.error('Failed to load vgm_havens.json', e);
    }
  }

  async function loadCommunityReports() {
    try {
      const stored = loadStoredCommunityReports();
      if (stored.length > 0) {
        applyCommunityReports(stored);
        return;
      }

      const res = await fetch('community_reports.json');
      if (!res.ok) return;

      const data = await res.json();
      applyCommunityReports(data);
    } catch (e) {
      console.error('Failed to load community_reports.json', e);
    }
  }

  function normalizeCommunityReports(data) {
    if (!Array.isArray(data)) return [];

    return data
      .filter((item) => typeof item.lat === 'number' && typeof item.lng === 'number')
      .map((item, index) => ({
        id: item.id || index + 1,
        name: item.name || 'Reported Low-Visibility Area',
        lat: item.lat,
        lng: item.lng,
        radius: item.radius || 150,
        severity: item.severity === 'high' ? 'high' : 'medium',
        description: item.description || 'Community-submitted field report.',
        type: item.type || 'community_report',
        reports: item.reports || 1
      }));
  }

  function applyCommunityReports(data) {
    DANGER_ZONES = normalizeCommunityReports(data);
    dangerLayerGroup.clearLayers();
    addDangerZones();
    updateDangerList();
    console.log('Loaded community danger reports:', DANGER_ZONES.length);
  }

  function loadStoredCommunityReports() {
    try {
      const raw = localStorage.getItem(COMMUNITY_REPORTS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (error) {
      console.error('Failed to read local community reports', error);
      return [];
    }
  }

  function persistCommunityReports() {
    try {
      localStorage.setItem(COMMUNITY_REPORTS_STORAGE_KEY, JSON.stringify(DANGER_ZONES));
    } catch (error) {
      console.error('Failed to persist community reports', error);
    }
  }

  function clearReportForm() {
    reportNameInput.value = '';
    reportSeverityInput.value = 'medium';
    reportRadiusInput.value = '150';
    reportTypeInput.value = '';
    reportDescriptionInput.value = '';
  }

  function populateReportCoordinates(lat, lng) {
    reportLatInput.value = lat.toFixed(6);
    reportLngInput.value = lng.toFixed(6);
  }

  function exportCommunityReports() {
    const blob = new Blob([JSON.stringify(DANGER_ZONES, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'community_reports.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // ===== LOAD PROTOMAPS TILES (FREE - No API Key!) =====
  // Protomaps: https://protomaps.com - completely free, open-source
  function loadProtomapsTiles() {
    console.log('🗺️ Loading Protomaps tiles (FREE - no API key needed)...');
    
    // Note: Requires pmtiles.js library to be added to HTML
    // <script src="https://unpkg.com/pmtiles@2.11.0/dist/index.js"></script>
    if (typeof pmtiles === 'undefined') {
      console.error('❌ pmtiles.js not loaded. Add this to your HTML:');
      console.error('<script src="https://unpkg.com/pmtiles@2.11.0/dist/index.js"><\/script>');
      console.log('⚠️ Falling back to GeoJSON...');
      return;
    }
    
    const protocol = new pmtiles.Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    
    console.log('✅ Protomaps loaded from:', CONFIG.protomapsUrl);
    console.log('💡 Protomaps is 100% free - no accounts needed!');
  }

  // ===== LOAD MAPBOX VECTOR TILES (Paid - Requires Credit Card) =====
  function loadMapboxTiles() {
    console.warn('⚠️ Mapbox requires a credit card. Consider Protomaps for free alternative.');
    
    if (!L.vectorGrid) {
      console.error('❌ Leaflet.VectorGrid not loaded. Falling back to GeoJSON.');
      return;
    }
    
    const vectorUrl = `https://api.mapbox.com/v4/${CONFIG.mapboxTilesetId}/{z}/{x}/{y}.vector.pbf?access_token=${CONFIG.mapboxToken}`;
    
    const vectorLayer = L.vectorGrid.protobuf(vectorUrl, {
      vectorTileLayerStyles: {
        'vgm_streets': {
          weight: 3,
          color: '#FFD700',
          opacity: 0.8,
          fill: false
        },
        default: {
          weight: 2,
          color: '#00ff88',
          opacity: 0.7
        }
      },
      interactive: true,
      getFeatureId: function(f) {
        return f.properties.name || f.id;
      }
    });
    
    vectorLayer.addTo(map);
    console.log('✅ Mapbox vector tiles loaded');
  }

  // ===== ADD STREETS LAYER TO MAP (GeoJSON Mode) =====
  function addStreetsLayer() {
    if (!vgmStreetsData) return;
    
    const streetsLayer = L.geoJSON(vgmStreetsData, {
      style: function(feature) {
        const lighting = feature.properties.lit;
        const isLit = lighting === 'yes' || lighting === 'assumed_yes';
        return {
          color: lighting === 'no' ? '#ff4757' : '#FFD700',
          weight: 3,
          opacity: 0.8,
          dashArray: lighting === 'no' ? '5,5' : (lighting === 'assumed_yes' ? '8,4' : '')
        };
      },
      onEachFeature: function(feature, layer) {
        const props = feature.properties;
        const lightingLabel = props.lit === 'yes'
          ? '✅ Well-lit (mapped)'
          : props.lit === 'assumed_yes'
            ? '💡 Likely lit (major road proxy)'
            : props.lit === 'no'
              ? '⚠️ Unlit'
              : 'Unknown';
        layer.bindPopup(`
          <b>${props.name || 'Unnamed Street'}</b><br>
          Type: ${props.highway || 'unknown'}<br>
          Lighting: ${lightingLabel}
        `);
      }
    });
    
    streetsLayer.addTo(map);
  }

  // ===== INITIALIZE =====
  function boot() {
    initMap();
    loadVGMStreets();
    loadVGMHavens();
    loadCommunityReports();
    const initialCenter = CONFIG.defaultCenter;
    populateReportCoordinates(initialCenter[0], initialCenter[1]);

    // Enable map click to set destination
    map.on('click', (e) => {
      if (clickLocked) return;

      toCoords = [e.latlng.lat, e.latlng.lng];
      toInput.value = `${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;

      if (destMarker) {
        destMarker.setLatLng(e.latlng);
      } else {
        destMarker = L.marker(e.latlng, {
          icon: createCustomIcon('map-pin', 'marker-destination'),
          zIndexOffset: 900
        }).addTo(map);
      }

      destMarker.bindPopup(createPopupHTML(
        '🏁 Destination',
        `Lat: ${e.latlng.lat.toFixed(5)}, Lng: ${e.latlng.lng.toFixed(5)}`,
        ['info'],
        ['Destination']
      )).openPopup();

      updateStatus('Destination set! Click "Find Brightest Path" to navigate. (NASA Tiles & OSM Data Active)');
    });

    // Set initial toggle states
    toggleDangerBtn.classList.add('active');
    toggleSafeBtn.classList.add('active');

    // Initial sidebar lists
    updateDangerList();
    updateSafeList();
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // Boot when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
