// map.js — Interactive World Map with Leaflet
// Features: Clickable countries with heat map coloring and navigation

let map;
let geojsonLayer;

// Country data with heat values (0-1 scale for demonstration)
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
};

// Initialize the map
function initMap() {
  map = L.map("world-map", {
    center: [20, 0],
    zoom: 2,
    minZoom: 1.5,
    maxZoom: 10,
    worldCopyJump: true,
    zoomControl: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    noWrap: false,
  }).addTo(map);

  loadCountriesGeoJSON();
}

function loadCountriesGeoJSON() {
  fetch(
    "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
  )
    .then((response) => response.json())
    .then((data) => {
      createGeoJSONLayer(data);
    })
    .catch((error) => {
      console.error("Error loading GeoJSON:", error);
    });
}

function createGeoJSONLayer(geojsonData) {
  geojsonLayer = L.geoJSON(geojsonData, {
    style: styleCountry,
    onEachFeature: onEachCountry,
  }).addTo(map);
}

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

function getHeatValue(countryCode, countryName) {
  if (countryHeatData[countryCode] !== undefined) {
    return countryHeatData[countryCode];
  }

  let hash = 0;
  for (let i = 0; i < countryName.length; i++) {
    hash = (hash << 5) - hash + countryName.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash % 100) / 100;
}

function getHeatColor(value) {
  const colors = ["#2c7bb6", "#abd9e9", "#ffffbf", "#fdae61", "#d7191c"];
  const index = Math.min(Math.floor(value * colors.length), colors.length - 1);
  return colors[index];
}

function onEachCountry(feature, layer) {
  const countryName = feature.properties.ADMIN;

  layer.on({
    mouseover: highlightCountry,
    mouseout: resetHighlight,
    click: onCountryClick,
  });

  layer.bindPopup(`<strong>${countryName}</strong><br>Click to explore!`);
}

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

function resetHighlight(e) {
  geojsonLayer.resetStyle(e.target);
}

function onCountryClick(e) {
  const layer = e.target;
  const countryName = layer.feature.properties.ADMIN;
  const countryCode = layer.feature.properties.ISO_A3;

  map.fitBounds(layer.getBounds());
  redirectToCountry(countryName, countryCode);
}

function redirectToCountry(countryName, countryCode) {
  window.location.href = `/game/country?name=${encodeURIComponent(
    countryName,
  )}&code=${countryCode}`;
}

async function loadHeatDataFromBackend() {
  try {
    const response = await fetch("/api/country-heat-data");
    const data = await response.json();
    Object.assign(countryHeatData, data);
    if (geojsonLayer) {
      geojsonLayer.setStyle(styleCountry);
    }
  } catch (error) {
    console.error("Error loading heat data:", error);
  }
}

document.addEventListener("DOMContentLoaded", initMap);
