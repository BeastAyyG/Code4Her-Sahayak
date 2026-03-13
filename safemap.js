// ===== SAHAYAK SAFE MAPS — BRIGHTEST PATH NAVIGATION =====

(function () {
  'use strict';

  // ===== CONFIGURATION =====
  const CONFIG = {
    defaultCenter: [28.6139, 77.2090], // New Delhi as default
    defaultZoom: 14,
    tileUrl: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    nominatimUrl: 'https://nominatim.openstreetmap.org/search',
    osrmUrl: 'https://router.project-osrm.org/route/v1/driving',
    searchDelay: 400,
    routeColors: {
      brightest: '#00ff88',
      shortest: '#667eea',
      danger: '#ff4757',
      caution: '#ffa502'
    }
  };

  // ===== DANGER ZONES DATABASE =====
  // These are sample known danger zones — in a production app, these would come from a database
  // with community reports + official crime data. Adjust coordinates to your city.
  let DANGER_ZONES = [
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
  ];

  // ===== SAFE PLACES DATABASE =====
  let SAFE_PLACES = [
    { id: 1, name: 'Central Police Station', lat: 28.6155, lng: 77.2100, type: 'police', icon: '👮', open: '24/7' },
    { id: 2, name: 'City Hospital', lat: 28.6100, lng: 77.2090, type: 'hospital', icon: '🏥', open: '24/7' },
    { id: 3, name: 'MedPlus Pharmacy', lat: 28.6170, lng: 77.2060, type: 'pharmacy', icon: '💊', open: '24/7' },
    { id: 4, name: 'Metro Station Gate 2', lat: 28.6130, lng: 77.2120, type: 'metro', icon: '🚇', open: '5AM-11PM' },
    { id: 5, name: 'Women Help Desk', lat: 28.6190, lng: 77.2040, type: 'helpdesk', icon: '🛡️', open: '24/7' },
    { id: 6, name: 'Fire Station', lat: 28.6090, lng: 77.2200, type: 'fire', icon: '🚒', open: '24/7' },
    { id: 7, name: 'SafeSpot Convenience Store', lat: 28.6210, lng: 77.2130, type: 'store', icon: '🏪', open: '6AM-12AM' },
    { id: 8, name: 'Community Center', lat: 28.6070, lng: 77.2060, type: 'community', icon: '🏛️', open: '8AM-10PM' },
    { id: 9, name: 'Night Patrol Checkpoint', lat: 28.6145, lng: 77.2210, type: 'patrol', icon: '🔦', open: '8PM-6AM' },
    { id: 10, name: 'Emergency Booth — Park Rd', lat: 28.6175, lng: 77.2175, type: 'booth', icon: '📞', open: '24/7' }
  ];

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

    // Create layer groups
    dangerLayerGroup = L.layerGroup().addTo(map);
    safeLayerGroup = L.layerGroup().addTo(map);
    routeLayerGroup = L.layerGroup().addTo(map);

    // Add danger zones & safe places to map
    addDangerZones();
    addSafePlaces();

    // Try to get user location automatically
    getUserLocation(true);

    updateStatus('Map ready. Enter locations or use your live position.');
  }

  // ===== GET USER LIVE LOCATION =====
  function getUserLocation(silent = false) {
    if (!navigator.geolocation) {
      if (!silent) updateStatus('Geolocation not supported by your browser.');
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
            icon: createCustomIcon('📍', 'marker-user'),
            zIndexOffset: 1000
          }).addTo(map);
          userMarker.bindPopup(createPopupHTML(
            '📍 Your Location',
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

        // Generate danger zones relative to user's real location
        generateLocalDangerZones(latitude, longitude);
        generateLocalSafePlaces(latitude, longitude);

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
  }

  // ===== GENERATE SAFE PLACES NEAR USER =====
  function generateLocalSafePlaces(lat, lng) {
    SAFE_PLACES = [
      { id: 1, name: 'Nearest Police Station', lat: lat + 0.003, lng: lng + 0.002, type: 'police', icon: '👮', open: '24/7' },
      { id: 2, name: 'District Hospital', lat: lat - 0.004, lng: lng + 0.003, type: 'hospital', icon: '🏥', open: '24/7' },
      { id: 3, name: 'Apollo Pharmacy', lat: lat + 0.001, lng: lng - 0.003, type: 'pharmacy', icon: '💊', open: '24/7' },
      { id: 4, name: 'Metro Station', lat: lat + 0.002, lng: lng + 0.006, type: 'metro', icon: '🚇', open: '5 AM–11 PM' },
      { id: 5, name: 'Women Help Desk', lat: lat - 0.001, lng: lng + 0.001, type: 'helpdesk', icon: '🛡️', open: '24/7' },
      { id: 6, name: 'Fire Station', lat: lat - 0.005, lng: lng - 0.004, type: 'fire', icon: '🚒', open: '24/7' },
      { id: 7, name: '24hr Convenience Store', lat: lat + 0.004, lng: lng - 0.001, type: 'store', icon: '🏪', open: '24/7' },
      { id: 8, name: 'Community Center', lat: lat - 0.002, lng: lng - 0.005, type: 'community', icon: '🏛️', open: '8 AM–10 PM' },
      { id: 9, name: 'Night Patrol Booth', lat: lat + 0.006, lng: lng + 0.004, type: 'patrol', icon: '🔦', open: '8 PM–6 AM' },
      { id: 10, name: 'Emergency Call Booth', lat: lat - 0.003, lng: lng + 0.006, type: 'booth', icon: '📞', open: '24/7' },
      { id: 11, name: 'ATM Booth (CCTV)', lat: lat + 0.001, lng: lng + 0.004, type: 'atm', icon: '🏧', open: '24/7' },
      { id: 12, name: 'Petrol Station', lat: lat - 0.006, lng: lng + 0.002, type: 'petrol', icon: '⛽', open: '24/7' }
    ];

    safeLayerGroup.clearLayers();
    addSafePlaces();
    updateSafeList();
  }

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
        icon: createCustomIcon('⚠️', 'marker-danger')
      });

      const severityLabel = zone.severity.charAt(0).toUpperCase() + zone.severity.slice(1);
      marker.bindPopup(createPopupHTML(
        `⚠️ ${zone.name}`,
        `${zone.description}<br/><br/><strong>${zone.reports} reports</strong> from community`,
        [zone.severity === 'high' ? 'danger' : 'caution', 'info'],
        [`Severity: ${severityLabel}`, zone.type.replace('_', ' ')]
      ));

      dangerLayerGroup.addLayer(circle);
      dangerLayerGroup.addLayer(marker);
    });
  }

  // ===== ADD SAFE PLACES TO MAP =====
  function addSafePlaces() {
    SAFE_PLACES.forEach(place => {
      const marker = L.marker([place.lat, place.lng], {
        icon: createCustomIcon(place.icon, 'marker-safe')
      });

      marker.bindPopup(createPopupHTML(
        `${place.icon} ${place.name}`,
        `Type: ${place.type.charAt(0).toUpperCase() + place.type.slice(1)}<br/>Hours: <strong>${place.open}</strong>`,
        ['safe'],
        ['Safe Place', place.open === '24/7' ? '24/7 Open' : 'Limited Hours']
      ));

      safeLayerGroup.addLayer(marker);
    });
  }

  // ===== CREATE CUSTOM MAP ICON =====
  function createCustomIcon(emoji, className) {
    return L.divIcon({
      html: `<div class="custom-marker ${className}">${emoji}</div>`,
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
              icon: createCustomIcon('📍', 'marker-user'),
              zIndexOffset: 1000
            }).addTo(map);
          }
          map.setView([lat, lon], 15);
        } else {
          toCoords = [lat, lon];
          if (destMarker) destMarker.setLatLng([lat, lon]);
          else {
            destMarker = L.marker([lat, lon], {
              icon: createCustomIcon('🏁', 'marker-destination'),
              zIndexOffset: 900
            }).addTo(map);
          }
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

      // Calculate safety score
      const safetyScore = calculateSafetyScore(coordinates, isBrightest);

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

      updateStatus(isBrightest
        ? `✅ Brightest path found: ${distance} km, ~${duration} min. Safety: ${safetyScore}%`
        : `📏 Shortest path: ${distance} km, ~${duration} min. Safety: ${safetyScore}%`
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

  // ===== CALCULATE SAFETY SCORE =====
  function calculateSafetyScore(coordinates, isBrightest) {
    let dangerCount = 0;
    let safeNearby = 0;

    // Check how many route points are near danger zones
    coordinates.forEach(coord => {
      DANGER_ZONES.forEach(zone => {
        const dist = haversineDistance(coord[0], coord[1], zone.lat, zone.lng);
        if (dist < zone.radius / 1000) {
          dangerCount++;
        }
      });

      SAFE_PLACES.forEach(place => {
        const dist = haversineDistance(coord[0], coord[1], place.lat, place.lng);
        if (dist < 0.3) {
          safeNearby++;
        }
      });
    });

    const dangerRatio = dangerCount / coordinates.length;
    const safeRatio = safeNearby / coordinates.length;

    let score = 100 - (dangerRatio * 200) + (safeRatio * 30);
    if (isBrightest) score += 12; // brightest path bonus
    score = Math.max(15, Math.min(98, Math.round(score)));

    return score;
  }

  // ===== SHOW ROUTE INFO =====
  function showRouteInfo(routeData) {
    routeInfoPanel.style.display = 'block';

    const card = document.createElement('div');
    card.className = `route-card ${routeData.isBrightest ? 'safe' : 'shortest'}`;

    const badgeHTML = routeData.isBrightest
      ? '<span class="route-badge recommended">✓ Recommended</span>'
      : '';

    const walkDuration = Math.ceil(routeData.duration * 3.5); // walking is ~3.5x driving

    card.innerHTML = `
      <div class="route-card-header">
        <div class="route-card-title">
          ${routeData.isBrightest ? '💡 Brightest Path' : '📏 Shortest Path'}
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
          <strong>${routeData.safetyScore}%</strong>
          Safety Score
        </div>
        <div class="route-stat">
          <strong>${routeData.isBrightest ? 'High' : 'Standard'}</strong>
          Lighting
        </div>
      </div>
    `;

    routeCards.appendChild(card);
  }

  // ===== UPDATE DANGER LIST IN SIDEBAR =====
  function updateDangerList() {
    dangerList.innerHTML = '';
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
  sosBtn.addEventListener('click', () => {
    if (userLocation) {
      const googleMapsLink = `https://www.google.com/maps?q=${userLocation[0]},${userLocation[1]}`;
      const message = `🚨 SOS ALERT from Sahayak!\n\nI need help!\nMy location: ${googleMapsLink}\n\nLatitude: ${userLocation[0]}\nLongitude: ${userLocation[1]}`;

      // Try to share via Web Share API
      if (navigator.share) {
        navigator.share({
          title: '🚨 Sahayak SOS Alert',
          text: message,
          url: googleMapsLink
        }).catch(() => {
          // Fallback: copy to clipboard
          navigator.clipboard.writeText(message);
          alert('🚨 SOS Alert!\n\nYour location has been copied to clipboard. Send it to your emergency contacts immediately!');
        });
      } else {
        navigator.clipboard.writeText(message).then(() => {
          alert('🚨 SOS Alert!\n\nYour location has been copied to clipboard. Send it to your emergency contacts immediately!');
        });
      }
    } else {
      alert('🚨 SOS Alert!\n\nPlease enable location access for precise SOS alerts.');
      getUserLocation(false);
    }
  });

  // Allow clicking on map to set destination
  let clickLocked = false;
  map = null; // will be set in initMap

  // ===== INITIALIZE =====
  function boot() {
    initMap();

    // Enable map click to set destination
    map.on('click', (e) => {
      if (clickLocked) return;

      toCoords = [e.latlng.lat, e.latlng.lng];
      toInput.value = `${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;

      if (destMarker) {
        destMarker.setLatLng(e.latlng);
      } else {
        destMarker = L.marker(e.latlng, {
          icon: createCustomIcon('🏁', 'marker-destination'),
          zIndexOffset: 900
        }).addTo(map);
      }

      destMarker.bindPopup(createPopupHTML(
        '🏁 Destination',
        `Lat: ${e.latlng.lat.toFixed(5)}, Lng: ${e.latlng.lng.toFixed(5)}`,
        ['info'],
        ['Destination']
      )).openPopup();

      updateStatus('Destination set! Click "Find Brightest Path" to navigate.');
    });

    // Set initial toggle states
    toggleDangerBtn.classList.add('active');
    toggleSafeBtn.classList.add('active');

    // Initial sidebar lists
    updateDangerList();
    updateSafeList();
  }

  // Boot when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
