import { loadLeafletAssets } from "./shared/leaflet-assets.js";
import { getCountryCodeA2FromProps, normalizeIsoCode } from "./shared/map-utils.js";

const MAP_CENTER = [45, 5];
const MAP_ZOOM = 3;

function getCssVar(name, fallback) {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

const mapPalette = {
  stroke: getCssVar("--color-hub-map-stroke", "#425761"),
  fill: getCssVar("--color-hub-map-fill", "#7ea6b5cc"),
  activeStroke: getCssVar("--color-hub-map-active-stroke", "#111111be"),
  activeFill: getCssVar("--color-hub-map-active-fill", "#a8ceda"),
};

function getCodeCandidates(props) {
  return [
    props?.iso_a2,
    props?.iso_a2_eh,
    props?.wb_a2,
    props?.iso_a3,
    props?.adm0_a3,
    props?.sov_a3,
    props?.wb_a3,
  ];
}

function getContinentFromProps(props, continentNamesByIsoCode) {
  for (const rawCode of getCodeCandidates(props)) {
    const code = normalizeIsoCode(rawCode);
    if (!code) continue;
    const continentName = continentNamesByIsoCode[code];
    if (continentName) return continentName;
  }
  return "";
}

function buildFilterQuery({
  countryCode = "",
  continentCode = "",
}) {
  const params = new URLSearchParams();
  if (countryCode) params.set("country_code", countryCode);
  if (continentCode) params.set("continent_code", continentCode);
  return params.toString();
}

function renderPopupHtml({
  templateRoot,
  countryName,
  continentName,
  countryQuery,
  continentQuery,
  catalogueBaseUrl,
  playBaseUrl,
}) {
  const templateHtml = templateRoot ? templateRoot.innerHTML : "";
  const hasContinentFilter = Boolean(continentQuery);

  const continentBlock = continentName
    ? `<div class="popup-country-code">Continent: ${continentName}</div>`
    : "";

  const continentOption = hasContinentFilter
    ? `<a class="popup-link popup-link-option" href="${catalogueBaseUrl}?${continentQuery}">Continent</a>`
    : '<span class="popup-link popup-link-option popup-link-disabled">Continent</span>';

  const playContinentOption = hasContinentFilter
    ? `<a class="popup-link popup-link-option" href="${playBaseUrl}?${continentQuery}">Continent</a>`
    : '<span class="popup-link popup-link-option popup-link-disabled">Continent</span>';

  return templateHtml
    .replaceAll("__COUNTRY_NAME__", countryName)
    .replaceAll("__CONTINENT_BLOCK__", continentBlock)
    .replaceAll("__CATALOGUE_URL_COUNTRY__", `${catalogueBaseUrl}?${countryQuery}`)
    .replaceAll("__CATALOGUE_OPTION_CONTINENT__", continentOption)
    .replaceAll("__PLAY_URL_COUNTRY__", `${playBaseUrl}?${countryQuery}`)
    .replaceAll("__PLAY_OPTION_CONTINENT__", playContinentOption);
}

function wireExclusiveDropdowns(popupElement) {
  if (!popupElement) return;

  const dropdowns = Array.from(
    popupElement.querySelectorAll(".popup-dropdown"),
  );
  if (dropdowns.length < 2) return;

  dropdowns.forEach((dropdown) => {
    dropdown.addEventListener("toggle", () => {
      if (!dropdown.open) return;
      dropdowns.forEach((otherDropdown) => {
        if (otherDropdown !== dropdown) otherDropdown.open = false;
      });
    });
  });
}

function baseStyle() {
  return {
    weight: 0.5,
    color: mapPalette.stroke,
    fillColor: mapPalette.fill,
    fillOpacity: 0.24,
  };
}

function highlightStyle() {
  return {
    weight: 1.5,
    color: mapPalette.activeStroke,
    fillColor: mapPalette.activeFill,
    fillOpacity: 0.66,
  };
}

async function initHubMap() {
  const bootstrap = window.__hubMapBootstrap || null;
  const mapRoot = document.getElementById("hub-map");
  const popupTemplateRoot = document.getElementById("hub-country-popup-template");

  if (!bootstrap || !mapRoot) return;

  try {
    await loadLeafletAssets();
  } catch (error) {
    console.error("Failed to load map library.", error);
    mapRoot.innerHTML = '<p class="hub-map-error">Map library failed to load.</p>';
    return;
  }

  if (typeof window.L === "undefined") {
    mapRoot.innerHTML = '<p class="hub-map-error">Map library failed to load.</p>';
    return;
  }

  const {
    geojsonUrl,
    continentNamesByIsoCode,
    continentCodesByName,
    countryCodeA2ByIsoCode,
    catalogueBaseUrl,
    playBaseUrl,
  } = bootstrap;

  const map = L.map("hub-map", {
    worldCopyJump: true,
    zoomControl: true,
  }).setView(MAP_CENTER, MAP_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 12,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  try {
    const response = await fetch(geojsonUrl, { cache: "force-cache" });
    if (!response.ok) {
      throw new Error(`Failed to load GeoJSON (${response.status})`);
    }

    const countriesGeoJson = await response.json();
    let lastHighlighted = null;

    function onEachFeature(feature, layer) {
      layer.on("click", (event) => {
        if (lastHighlighted) lastHighlighted.setStyle(baseStyle());

        lastHighlighted = layer;
        layer.setStyle(highlightStyle());

        const props = feature.properties || {};
        const countryName = props.name || props.ADMIN || props.admin || "Unknown";
        const countryCode = getCountryCodeA2FromProps(props, countryCodeA2ByIsoCode);
        const continentName = getContinentFromProps(props, continentNamesByIsoCode);
        const continentCode = continentCodesByName[continentName] || "";

        const countryQuery = buildFilterQuery({ countryCode });
        const continentQuery = buildFilterQuery({
          continentCode,
        });

        const popupHtml = renderPopupHtml({
          templateRoot: popupTemplateRoot,
          countryName,
          continentName,
          countryQuery,
          continentQuery,
          catalogueBaseUrl,
          playBaseUrl,
        });

        const popup = L.popup({ closeButton: true, autoPan: true })
          .setLatLng(event.latlng)
          .setContent(popupHtml)
          .openOn(map);

        const popupElement = popup.getElement();
        if (popupElement) {
          wireExclusiveDropdowns(popupElement);
        } else {
          map.once("popupopen", ({ popup: openedPopup }) => {
            wireExclusiveDropdowns(openedPopup.getElement());
          });
        }
      });

      layer.on("mouseover", () => {
        if (layer !== lastHighlighted) {
          layer.setStyle({ fillOpacity: 0.35 });
        }
      });

      layer.on("mouseout", () => {
        if (layer !== lastHighlighted) {
          layer.setStyle(baseStyle());
        }
      });
    }

    const countriesLayer = L.geoJSON(countriesGeoJson, {
      style: baseStyle,
      onEachFeature,
    }).addTo(map);

    const constraintBounds = countriesLayer.getBounds().pad(0.05);
    map.setMaxBounds(constraintBounds);
    map.options.maxBoundsViscosity = 0.9;

    function applyViewportMinZoom() {
      const minZoom = Math.max(1, map.getBoundsZoom(constraintBounds, true));
      map.setMinZoom(minZoom);
      if (map.getZoom() < minZoom) {
        map.setZoom(minZoom, { animate: false });
      }
    }

    map.whenReady(() => {
      applyViewportMinZoom();
    });

    let resizeTimer = null;
    window.addEventListener("resize", () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        map.invalidateSize({ pan: false, debounceMoveend: true });
        applyViewportMinZoom();
      }, 120);
    });
  } catch (error) {
    console.error(error);
    mapRoot.innerHTML = '<p class="hub-map-error">Map data failed to load.</p>';
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initHubMap, { once: true });
} else {
  initHubMap();
}
