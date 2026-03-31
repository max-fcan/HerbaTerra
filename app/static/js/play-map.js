// AI note: This script was realised with the help of AI.
import { loadLeafletAssets } from "./shared/leaflet-assets.js";
import { getCountryNameFromProps, normalizeIsoCode } from "./shared/map-utils.js";

const MAP_CENTER = [20, 0];
const MAP_ZOOM = 2;

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

function normalizeLabel(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function getFeatureCountryCodeA2(props) {
  for (const rawCode of getCodeCandidates(props)) {
    const code = normalizeIsoCode(rawCode);
    if (!code) continue;
    if (code.length === 2) return code.toUpperCase();
  }
  return "";
}

function getFeatureContinentName(props, continentNamesByIsoCode) {
  const rawFromProps = String(props?.continent || "").trim();
  if (rawFromProps) return rawFromProps;
  return getContinentFromProps(props, continentNamesByIsoCode);
}

function featureIsInScope(feature, scope, continentNamesByIsoCode) {
  const scopeType = String(scope?.scope_type || "world").toLowerCase();
  if (scopeType === "world") return true;

  const props = feature?.properties || {};
  if (scopeType === "country") {
    const scopeCountryCode = String(scope?.country_code || "")
      .trim()
      .toUpperCase();
    if (scopeCountryCode) {
      return getFeatureCountryCodeA2(props) === scopeCountryCode;
    }

    const scopeCountryName = normalizeLabel(scope?.country || "");
    if (!scopeCountryName) return false;
    return normalizeLabel(getCountryNameFromProps(props)) === scopeCountryName;
  }

  if (scopeType === "continent") {
    const featureContinent = normalizeLabel(
      getFeatureContinentName(props, continentNamesByIsoCode),
    );
    const scopeContinent = normalizeLabel(scope?.continent || "");
    return Boolean(
      featureContinent && scopeContinent && featureContinent === scopeContinent,
    );
  }

  return true;
}

function getScopeStyleFactory(scope, continentNamesByIsoCode) {
  const scopeType = String(scope?.scope_type || "world").toLowerCase();
  if (scopeType === "world") {
    return () => ({
      weight: 0.6,
      color: "rgba(205, 231, 214, 0.52)",
      fillColor: "rgba(115, 170, 146, 0.14)",
      fillOpacity: 0.14,
    });
  }

  return (feature) => {
    const inScope = featureIsInScope(feature, scope, continentNamesByIsoCode);
    if (inScope) {
      return {
        weight: 0.9,
        color: "rgba(216, 247, 221, 0.9)",
        fillColor: "rgba(132, 205, 156, 0.36)",
        fillOpacity: 0.36,
      };
    }
    return {
      weight: 0.5,
      color: "rgba(178, 189, 182, 0.62)",
      fillColor: "rgba(122, 132, 127, 0.54)",
      fillOpacity: 0.54,
    };
  };
}

function formatCoordinateLabel(latlng) {
  return `${latlng.lat.toFixed(3)}, ${latlng.lng.toFixed(3)}`;
}

function formatCoordinateValue(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return "Unknown";
  return numericValue.toFixed(5);
}

function formatTimer(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
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

async function initPlayPage() {
  const bootstrap = window.__playBootstrap || null;
  const mapRoot = document.getElementById("play-map");

  if (!bootstrap || !mapRoot) return;

  try {
    await loadLeafletAssets();
  } catch (error) {
    console.error("Failed to load map library.", error);
    mapRoot.innerHTML =
      '<p class="play-map-error">Map library failed to load.</p>';
    return;
  }

  if (typeof window.L === "undefined") {
    mapRoot.innerHTML =
      '<p class="play-map-error">Map library failed to load.</p>';
    return;
  }

  const map = L.map(mapRoot, {
    worldCopyJump: true,
    zoomControl: true,
  }).setView(MAP_CENTER, MAP_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    noWrap: true,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let selectedMarker = null;
  const guessForm = bootstrap.guessForm || {};
  const latitudeInput = document.getElementById(guessForm.latitudeInputId || "");
  const longitudeInput = document.getElementById(
    guessForm.longitudeInputId || "",
  );
  const submitButton = document.getElementById(guessForm.submitButtonId || "");
  const selectionSummary = document.getElementById(
    guessForm.selectionSummaryId || "",
  );
  const timeCard = document.getElementById("play-time-card");
  const timerValue = document.getElementById("play-timer-value");
  const timeUpPopup = document.getElementById("play-timeup-popup");
  const timeUpCloseButtons = document.querySelectorAll("[data-play-timeup-close]");
  const resultPopup = document.getElementById("play-result-popup");
  const resultOpenButtons = document.querySelectorAll("[data-play-result-open]");
  const resultCloseButtons = document.querySelectorAll("[data-play-result-close]");
  const resultDragHandle = document.querySelector("[data-play-result-drag-handle]");
  let remainingSeconds = Number(bootstrap.timerSecondsRemaining);
  let roundExpired = false;
  let resultPopupPositioned = false;

  function getNavbarBottomOffset() {
    const appNav = document.querySelector(".app-nav");
    if (!appNav) return 0;
    return appNav.getBoundingClientRect().bottom;
  }

  function getResultPopupBounds() {
    const navBottom = getNavbarBottomOffset();
    const popupWidth = resultPopup?.offsetWidth || 0;
    const popupHeight = resultPopup?.offsetHeight || 0;
    return {
      minLeft: 8,
      maxLeft: Math.max(8, window.innerWidth - popupWidth - 8),
      minTop: navBottom + 8,
      maxTop: Math.max(navBottom + 8, window.innerHeight - popupHeight - 8),
    };
  }

  function setResultPopupPosition(left, top) {
    if (!resultPopup) return;
    const bounds = getResultPopupBounds();
    const clampedLeft = Math.min(bounds.maxLeft, Math.max(bounds.minLeft, left));
    const clampedTop = Math.min(bounds.maxTop, Math.max(bounds.minTop, top));
    resultPopup.style.left = `${clampedLeft}px`;
    resultPopup.style.top = `${clampedTop}px`;
    resultPopup.style.transform = "none";
    resultPopupPositioned = true;
  }

  function openResultPopup() {
    if (!resultPopup) return;
    resultPopup.hidden = false;
  }

  function openTimeUpPopup() {
    if (!timeUpPopup) return;
    timeUpPopup.hidden = false;
  }

  function closeResultPopup() {
    if (!resultPopup) return;
    resultPopup.hidden = true;
  }

  function closeTimeUpPopup() {
    if (!timeUpPopup) return;
    timeUpPopup.hidden = true;
  }

  if (timeUpPopup) {
    for (const button of timeUpCloseButtons) {
      button.addEventListener("click", closeTimeUpPopup);
    }
  }

  if (resultPopup || timeUpPopup) {
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeResultPopup();
        closeTimeUpPopup();
      }
    });
  }

  if (resultPopup) {
    for (const button of resultOpenButtons) {
      button.addEventListener("click", openResultPopup);
    }
    for (const button of resultCloseButtons) {
      button.addEventListener("click", closeResultPopup);
    }
    window.addEventListener("resize", () => {
      if (!resultPopupPositioned) return;
      const currentLeft = Number.parseFloat(resultPopup.style.left);
      const currentTop = Number.parseFloat(resultPopup.style.top);
      if (Number.isFinite(currentLeft) && Number.isFinite(currentTop)) {
        setResultPopupPosition(currentLeft, currentTop);
      }
    });
  }

  if (resultPopup && resultDragHandle) {
    let dragOffsetX = 0;
    let dragOffsetY = 0;

    resultDragHandle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      const rect = resultPopup.getBoundingClientRect();
      dragOffsetX = event.clientX - rect.left;
      dragOffsetY = event.clientY - rect.top;
      setResultPopupPosition(rect.left, rect.top);
      resultDragHandle.setPointerCapture(event.pointerId);
      event.preventDefault();
    });

    resultDragHandle.addEventListener("pointermove", (event) => {
      if (!resultDragHandle.hasPointerCapture(event.pointerId)) return;
      setResultPopupPosition(
        event.clientX - dragOffsetX,
        event.clientY - dragOffsetY,
      );
    });

    const releaseDrag = (event) => {
      if (resultDragHandle.hasPointerCapture(event.pointerId)) {
        resultDragHandle.releasePointerCapture(event.pointerId);
      }
    };

    resultDragHandle.addEventListener("pointerup", releaseDrag);
    resultDragHandle.addEventListener("pointercancel", releaseDrag);
  }

  function updateTimerUi() {
    if (timerValue) {
      timerValue.textContent = formatTimer(remainingSeconds);
    }
    if (timeCard) {
      timeCard.classList.toggle("play-timer-urgent", remainingSeconds <= 20);
    }
  }

  function expireRound() {
    if (roundExpired) return;
    roundExpired = true;
    remainingSeconds = 0;
    updateTimerUi();
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = "Reveal round";
    }
    if (selectionSummary) {
      selectionSummary.textContent = "Time is up. Submit to reveal the round.";
    }
    openTimeUpPopup();
  }

  function placeGuess(latlng) {
    if (roundExpired) return;
    if (!latitudeInput || !longitudeInput || !submitButton) return;

    if (selectedMarker) {
      map.removeLayer(selectedMarker);
    }
    selectedMarker = L.marker(latlng, { title: "Your guess" }).addTo(map);
    latitudeInput.value = String(latlng.lat);
    longitudeInput.value = String(latlng.lng);
    submitButton.disabled = false;
    if (selectionSummary) {
      selectionSummary.textContent = `Selected guess: ${formatCoordinateLabel(latlng)}`;
    }
  }

  try {
    const response = await fetch(bootstrap.geojsonUrl, {
      cache: "force-cache",
    });
    if (!response.ok) throw new Error(`GeoJSON failed (${response.status})`);
    const geojson = await response.json();
    const scopeStyle = getScopeStyleFactory(
      bootstrap.scope || {},
      bootstrap.continentNamesByIsoCode || {},
    );

    const geojsonLayer = L.geoJSON(geojson, {
      style: scopeStyle,
      interactive: false,
    }).addTo(map);
    const bounds = applyBoundedViewport(map, geojsonLayer.getBounds());
    map.fitBounds(bounds, { padding: [12, 12] });
  } catch (error) {
    console.error(error);
    mapRoot.innerHTML =
      '<p class="play-map-error">Map data failed to load.</p>';
    return;
  }

  if (bootstrap.mode === "guess") {
    updateTimerUi();
    if (remainingSeconds <= 0) {
      expireRound();
    } else {
      const countdownInterval = window.setInterval(() => {
        remainingSeconds -= 1;
        if (remainingSeconds <= 0) {
          window.clearInterval(countdownInterval);
          expireRound();
          return;
        }
        updateTimerUi();
      }, 1000);
    }

    map.on("click", (event) => {
      placeGuess(event.latlng);
    });
    return;
  }

  const guess = bootstrap.guess || null;
  const solution = bootstrap.solution || null;
  const bounds = [];

  if (guess && Number.isFinite(Number(guess.latitude)) && Number.isFinite(Number(guess.longitude))) {
    const guessLatLng = L.latLng(Number(guess.latitude), Number(guess.longitude));
    L.marker(guessLatLng, { title: "Your guess" }).addTo(map);
    bounds.push(guessLatLng);
  }

  if (
    solution &&
    Number.isFinite(Number(solution.latitude)) &&
    Number.isFinite(Number(solution.longitude))
  ) {
    const solutionLatLng = L.latLng(
      Number(solution.latitude),
      Number(solution.longitude),
    );
    L.circleMarker(solutionLatLng, {
      radius: 9,
      color: "#fff0f0",
      weight: 2,
      fillColor: "#db6060",
      fillOpacity: 0.95,
    })
      .addTo(map)
      .bindPopup(
        `<div class="play-solution-popup"><div class="play-solution-title">Solution</div><div class="play-solution-country">${escapeHtml(
          solution.country || "Unknown",
        )}</div><div class="play-solution-coordinates"><div><strong>Lat:</strong> ${escapeHtml(
          formatCoordinateValue(solution.latitude),
        )}</div><div><strong>Lon:</strong> ${escapeHtml(
          formatCoordinateValue(solution.longitude),
        )}</div></div></div>`,
      );
    bounds.push(solutionLatLng);

    if (guess && Number.isFinite(Number(guess.latitude)) && Number.isFinite(Number(guess.longitude))) {
      const guessLatLng = L.latLng(Number(guess.latitude), Number(guess.longitude));
      L.polyline([guessLatLng, solutionLatLng], {
        color: "#f4dd7f",
        weight: 2,
        opacity: 0.75,
        dashArray: "6 6",
      }).addTo(map);
    }
  }

  if (bounds.length === 1) {
    map.setView(bounds[0], 4, { animate: false });
  } else if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [24, 24] });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPlayPage, { once: true });
} else {
  initPlayPage();
}
