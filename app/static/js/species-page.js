// AI note: This script was realised with the help of AI.
import { loadLeafletAssets } from "./shared/leaflet-assets.js";
import {
  getCountryCodeA2FromProps,
  getCountryNameFromProps,
  getLargestOuterRing,
  getPolygonCentroid,
} from "./shared/map-utils.js";

function normalizeCode(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function getCssVar(name, fallback) {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

function mixChannel(start, end, ratio) {
  return Math.round(start + (end - start) * ratio);
}

function mixColor(start, end, ratio) {
  return `rgb(${mixChannel(start[0], end[0], ratio)}, ${mixChannel(
    start[1],
    end[1],
    ratio,
  )}, ${mixChannel(start[2], end[2], ratio)})`;
}

function buildFilterUrl(baseUrl, countryCode) {
  try {
    const url = new URL(baseUrl, window.location.origin);
    if (countryCode) {
      url.searchParams.set("country_code", countryCode);
    } else {
      url.searchParams.delete("country_code");
    }
    url.searchParams.delete("continent_code");
    url.searchParams.delete("images_page");
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return baseUrl;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function applyBoundedViewport(map, baseBounds) {
  const constraintBounds = baseBounds.pad(0.05);
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
    resizeTimer = window.setTimeout(() => {
      map.invalidateSize({ pan: false, debounceMoveend: true });
      applyViewportMinZoom();
    }, 120);
  });

  return constraintBounds;
}

async function initSpeciesMap() {
  const pageBootstrap = window.__speciesPageBootstrap || {};
  const bootstrap = pageBootstrap.map || null;
  const mapRoot = document.getElementById("speciesSummaryMap");

  if (!bootstrap || !mapRoot) return;

  try {
    await loadLeafletAssets();
  } catch (error) {
    console.error("Failed to load map library.", error);
    mapRoot.innerHTML =
      '<p class="species-summary-map-error">Map library failed to load.</p>';
    return;
  }

  if (typeof window.L === "undefined") {
    mapRoot.innerHTML =
      '<p class="species-summary-map-error">Map library failed to load.</p>';
    return;
  }

  const statsMap = new Map();
  const rawStats = Array.isArray(bootstrap.countryStats) ? bootstrap.countryStats : [];
  rawStats.forEach((entry) => {
    const code = normalizeCode(entry?.country_code);
    if (!code) return;
    statsMap.set(code, {
      country: String(entry?.country || "").trim() || "Unknown country",
      occurrenceCount: Number(entry?.occurrence_count) || 0,
      imageCount: Number(entry?.image_count) || 0,
    });
  });

  const activeCountryCode = normalizeCode(bootstrap.activeCountryCode);
  const maxOccurrences = Math.max(
    1,
    ...Array.from(statsMap.values(), (entry) => entry.occurrenceCount),
  );

  const map = L.map(mapRoot, {
    worldCopyJump: true,
    zoomControl: true,
  }).setView([18, 0], 2);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 12,
    noWrap: true,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const palette = {
    emptyFill: getCssVar("--color-species-map-fill-empty", "#efe9e9"),
    stroke: getCssVar("--color-species-map-stroke", "#544949"),
    hoverStroke: getCssVar("--color-species-map-hover-stroke", "#3b2a2a"),
    activeStroke: getCssVar("--color-species-map-active-stroke", "#2d1616"),
  };
  const fillStart = [239, 233, 233];
  const fillEnd = [177, 91, 91];

  function getFeatureStyle(feature) {
    const props = feature?.properties || {};
    const countryCode = normalizeCode(
      getCountryCodeA2FromProps(props, bootstrap.countryCodeA2ByIsoCode || {}),
    );
    const stats = statsMap.get(countryCode);
    const ratio = stats ? Math.min(1, stats.occurrenceCount / maxOccurrences) : 0;
    const isActive = Boolean(activeCountryCode && activeCountryCode === countryCode);

    return {
      weight: isActive ? 1.6 : 0.8,
      color: isActive ? palette.activeStroke : palette.stroke,
      fillColor: stats ? mixColor(fillStart, fillEnd, ratio) : palette.emptyFill,
      fillOpacity: stats ? 0.78 : 0.25,
    };
  }

  try {
    const response = await window.fetch(bootstrap.geojsonUrl, {
      cache: "force-cache",
    });
    if (!response.ok) {
      throw new Error(`Failed to load GeoJSON (${response.status})`);
    }

    const geojson = await response.json();
    let highlightedLayer = null;

    const countriesLayer = L.geoJSON(geojson, {
      style: getFeatureStyle,
      onEachFeature(feature, layer) {
        layer.on("mouseover", () => {
          layer.setStyle({
            color: palette.hoverStroke,
            weight: 1.2,
          });
        });

        layer.on("mouseout", () => {
          countriesLayer.resetStyle(layer);
          if (highlightedLayer && highlightedLayer !== layer) {
            highlightedLayer.setStyle(getFeatureStyle(highlightedLayer.feature));
          }
        });

        layer.on("click", (event) => {
          if (highlightedLayer && highlightedLayer !== layer) {
            highlightedLayer.setStyle(getFeatureStyle(highlightedLayer.feature));
          }
          highlightedLayer = layer;
          layer.setStyle({
            ...getFeatureStyle(feature),
            weight: 1.8,
            color: palette.activeStroke,
          });

          const props = feature?.properties || {};
          const countryCode = normalizeCode(
            getCountryCodeA2FromProps(props, bootstrap.countryCodeA2ByIsoCode || {}),
          );
          const countryName = getCountryNameFromProps(props);
          const stats = statsMap.get(countryCode);
          const popupParts = [
            `<div class="species-map-popup">`,
            `<div class="species-map-popup-title"><strong>${escapeHtml(countryName)}</strong></div>`,
          ];

          if (stats) {
            popupParts.push(
              `<div class="species-map-popup-stat">${stats.occurrenceCount.toLocaleString()} observations</div>`,
              `<div class="species-map-popup-stat">${stats.imageCount.toLocaleString()} images</div>`,
              `<a class="species-map-popup-action" href="${buildFilterUrl(
                bootstrap.filterBaseUrl,
                countryCode,
              )}">Filter gallery to this country</a>`,
            );
          } else {
            popupParts.push(
              `<div class="species-map-popup-empty">No observations were mapped for this country.</div>`,
            );
          }

          popupParts.push("</div>");
          L.popup({ closeButton: true, autoPan: true })
            .setLatLng(event.latlng)
            .setContent(popupParts.join(""))
            .openOn(map);
        });
      },
    }).addTo(map);

    const bounds = applyBoundedViewport(map, countriesLayer.getBounds());
    map.fitBounds(bounds, { padding: [12, 12] });

    if (activeCountryCode) {
      countriesLayer.eachLayer((layer) => {
        const props = layer.feature?.properties || {};
        const layerCountryCode = normalizeCode(
          getCountryCodeA2FromProps(props, bootstrap.countryCodeA2ByIsoCode || {}),
        );
        if (layerCountryCode !== activeCountryCode) return;

        highlightedLayer = layer;
        const ring = getLargestOuterRing(layer.feature?.geometry);
        const centroid = ring ? getPolygonCentroid(ring) : null;
        if (centroid) {
          map.setView(centroid, 4, { animate: false });
        } else if (layer.getBounds) {
          map.fitBounds(layer.getBounds(), { padding: [20, 20] });
        }
      });
    }
  } catch (error) {
    console.error(error);
    mapRoot.innerHTML =
      '<p class="species-summary-map-error">Map data failed to load.</p>';
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSpeciesMap, { once: true });
} else {
  initSpeciesMap();
}
