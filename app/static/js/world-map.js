// Interactive World Map with Leaflet
// Features: Clickable countries with heat map coloring and navigation

let map;
let geojsonLayer;

// Country data with heat values (0-1 scale for demonstration)
// You can replace this with actual data from your backend
const countryHeatData = {
  USA: 0.9,
  CAN: 0.7,
  MEX: 0.6,
  BRA: 0.8,
  ARG: 0.5,
  GBR: 0.85,
  FRA: 0.75,
  DEU: 0.88,
  ESP: 0.65,
  ITA: 0.7,
  RUS: 0.6,
  CHN: 0.95,
  IND: 0.82,
  JPN: 0.78,
  AUS: 0.72,
  // Add more countries as needed
};

// Initialize the map
function initMap() {
  // Create map centered on world view
  map = L.map("world-map", {
    center: [20, 0],
    zoom: 2,
    minZoom: 1.5,
    maxZoom: 10,
    worldCopyJump: true,
    zoomControl: true,
  });

  // Add tile layer (base map)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    noWrap: false,
  }).addTo(map);

  // Load GeoJSON data for countries
  loadCountriesGeoJSON();
}

// Load country boundaries from GeoJSON
function loadCountriesGeoJSON() {
  // Using a CDN for world countries GeoJSON
  fetch(
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
  )
    .then((response) => response.json())
    .then((data) => {
      createGeoJSONLayer(data);
    })
    .catch((error) => {
      console.error("Error loading GeoJSON:", error);
      // Show error in console only - no info panel in integrated version
    });
}

// Create the GeoJSON layer with styling and interactions
function createGeoJSONLayer(geojsonData) {
  geojsonLayer = L.geoJSON(geojsonData, {
    style: styleCountry,
    onEachFeature: onEachCountry,
  }).addTo(map);
}

// Style each country based on heat data
function styleCountry(feature) {
  const countryCode = feature.properties.ISO_A3;
  const countryName = feature.properties.ADMIN;
  const heatValue = getHeatValue(countryCode, countryName);

  return {
    fillColor: getHeatColor(heatValue),
    weight: 1,
    opacity: 1,
    color: "#666",
    dashArray: "",
    fillOpacity: 0.7,
  };
}

// Get heat value for a country (0-1 scale)
function getHeatValue(countryCode, countryName) {
  // Check by ISO code first, then by name
  if (countryHeatData[countryCode] !== undefined) {
    return countryHeatData[countryCode];
  }

  // Fallback: generate value based on country name hash (for demo)
  let hash = 0;
  for (let i = 0; i < countryName.length; i++) {
    hash = (hash << 5) - hash + countryName.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash % 100) / 100;
}

// Convert heat value to color (gradient from blue to red)
function getHeatColor(value) {
  // Color gradient: blue (low) -> yellow (medium) -> red (high)
  const colors = [
    "#2c7bb6", // 0.0 - dark blue
    "#abd9e9", // 0.25 - light blue
    "#ffffbf", // 0.5 - yellow
    "#fdae61", // 0.75 - orange
    "#d7191c", // 1.0 - red
  ];

  const index = Math.min(Math.floor(value * colors.length), colors.length - 1);
  return colors[index];
}

// Add interactions to each country
function onEachCountry(feature, layer) {
  const countryName = feature.properties.ADMIN;
  const countryCode = feature.properties.ISO_A3;

  // Hover effect
  layer.on({
    mouseover: highlightCountry,
    mouseout: resetHighlight,
    click: onCountryClick,
  });

  // Bind popup
  layer.bindPopup(`<strong>${countryName}</strong><br>Click to explore!`);
}

// Highlight country on hover
function highlightCountry(e) {
  const layer = e.target;

  layer.setStyle({
    weight: 3,
    color: "#fff",
    dashArray: "",
    fillOpacity: 0.9,
  });

  layer.bringToFront();
}

// Reset highlight on mouse out
function resetHighlight(e) {
  geojsonLayer.resetStyle(e.target);
}

// Handle country click
function onCountryClick(e) {
  const layer = e.target;
  const countryName = layer.feature.properties.ADMIN;
  const countryCode = layer.feature.properties.ISO_A3;

  // Zoom to country
  map.fitBounds(layer.getBounds());

  // Redirect to country detail page
  // Modify this URL pattern to match your routing structure
  redirectToCountry(countryName, countryCode);
}

// Redirect to country detail page with country name as parameter
function redirectToCountry(countryName, countryCode) {
  // Option 1: Redirect to a Flask route with country name
  window.location.href = `/play/country?name=${encodeURIComponent(
    countryName
  )}&code=${countryCode}`;

  // Option 2: If you want to just log it for now (comment out option 1 and uncomment this)
  // console.log(`Clicked on ${countryName} (${countryCode})`);
  // alert(`Redirecting to ${countryName}...`);
}

// Alternative: Function to load custom heat data from backend
async function loadHeatDataFromBackend() {
  try {
    const response = await fetch("/api/country-heat-data");
    const data = await response.json();
    // Update countryHeatData with backend data
    Object.assign(countryHeatData, data);
    // Refresh the map styling
    if (geojsonLayer) {
      geojsonLayer.setStyle(styleCountry);
    }
  } catch (error) {
    console.error("Error loading heat data:", error);
  }
}

// Initialize map when DOM is ready
document.addEventListener("DOMContentLoaded", initMap);
