import { loadLeafletAssets } from "./shared/leaflet-assets.js";
import {
  getCountryNameFromProps,
  normalizeIsoCode,
} from "./shared/map-utils.js";

const MAP_CENTER = [20, 0];
const MAP_ZOOM = 2;
const WORLD_BOUNDS = [
  [-85, -180],
  [85, 180],
];

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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pointInRing(point, ring) {
  if (!Array.isArray(ring) || ring.length < 3) return false;
  const x = point[0];
  const y = point[1];
  let inside = false;

  for (
    let index = 0, previous = ring.length - 1;
    index < ring.length;
    previous = index, index += 1
  ) {
    const currentPoint = ring[index];
    const previousPoint = ring[previous];
    if (!Array.isArray(currentPoint) || !Array.isArray(previousPoint)) continue;

    const xi = Number(currentPoint[0]);
    const yi = Number(currentPoint[1]);
    const xj = Number(previousPoint[0]);
    const yj = Number(previousPoint[1]);
    if (
      !Number.isFinite(xi) ||
      !Number.isFinite(yi) ||
      !Number.isFinite(xj) ||
      !Number.isFinite(yj)
    ) {
      continue;
    }

    const intersects =
      yi > y !== yj > y &&
      x < ((xj - xi) * (y - yi)) / (yj - yi || Number.EPSILON) + xi;
    if (intersects) inside = !inside;
  }

  return inside;
}

function pointInPolygon(point, polygonCoordinates) {
  if (!Array.isArray(polygonCoordinates) || !polygonCoordinates.length)
    return false;
  const [outerRing, ...holes] = polygonCoordinates;
  if (!pointInRing(point, outerRing)) return false;
  return !holes.some((holeRing) => pointInRing(point, holeRing));
}

function pointInFeature(lat, lng, feature) {
  const geometry = feature?.geometry;
  if (!geometry) return false;

  const candidatePoints = [
    [lng, lat],
    [lng + 360, lat],
    [lng - 360, lat],
  ];

  if (geometry.type === "Polygon") {
    return candidatePoints.some((candidatePoint) =>
      pointInPolygon(candidatePoint, geometry.coordinates),
    );
  }

  if (geometry.type === "MultiPolygon") {
    return candidatePoints.some((candidatePoint) =>
      geometry.coordinates.some((polygonCoordinates) =>
        pointInPolygon(candidatePoint, polygonCoordinates),
      ),
    );
  }

  return false;
}

function findFeatureForLatLng(latlng, features) {
  for (const feature of features) {
    if (pointInFeature(latlng.lat, latlng.lng, feature)) return feature;
  }
  return null;
}

function haversineDistanceKm(a, b) {
  const earthRadiusKm = 6371;
  const toRadians = (value) => (value * Math.PI) / 180;
  const dLat = toRadians(b.lat - a.lat);
  const dLng = toRadians(b.lng - a.lng);
  const lat1 = toRadians(a.lat);
  const lat2 = toRadians(b.lat);

  const h =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  return 2 * earthRadiusKm * Math.asin(Math.sqrt(h));
}

function formatDistanceKm(distanceKm) {
  if (!Number.isFinite(distanceKm)) return "No guess submitted.";
  if (distanceKm < 10) return `${distanceKm.toFixed(2)} km`;
  if (distanceKm < 100) return `${distanceKm.toFixed(1)} km`;
  return `${Math.round(distanceKm).toLocaleString()} km`;
}

function formatTimer(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60);
  const remainingSeconds = safeSeconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

async function initPlayPage() {
  const bootstrap = window.__playBootstrap || null;
  const shell = document.getElementById("play-shell");
  const mapRoot = document.getElementById("play-map");
  const timerValue = document.getElementById("play-timer-value");
  const timeCard = document.getElementById("play-time-card");
  const submitBtn = document.getElementById("play-submit-btn");
  const expandBtn = document.getElementById("play-map-expand-btn");
  const mapPanel = document.getElementById("play-map-panel");
  const roundCard = document.getElementById("play-round-card");
  const scoreValue = document.getElementById("play-score-value");

  if (
    !bootstrap ||
    !shell ||
    !mapRoot ||
    !timerValue ||
    !submitBtn ||
    !expandBtn ||
    !mapPanel ||
    !roundCard ||
    !scoreValue
  ) {
    return;
  }

  if (bootstrap.backgroundImageUrl) {
    const safeUrl = String(bootstrap.backgroundImageUrl).replaceAll('"', "%22");
    shell.style.setProperty("--play-bg-image", `url("${safeUrl}")`);
  }

  const state = {
    map: null,
    features: [],
    guessMarker: null,
    solutionMarker: null,
    linkLine: null,
    guess: null,
    timerId: null,
    remainingSeconds: Number(bootstrap.timerSeconds) || 30,
    roundEnded: false,
    submitted: false,
    submitting: false,
    scoreRequested: false,
  };

  function updateSubmitButton() {
    if (state.roundEnded) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitted";
      return;
    }
    submitBtn.disabled = !state.guess || state.submitting;
    submitBtn.textContent = state.submitting ? "Submitting..." : "Submit";
  }

  function updateTimer() {
    timerValue.textContent = formatTimer(state.remainingSeconds);
    if (timeCard) {
      timeCard.classList.toggle(
        "play-timer-urgent",
        state.remainingSeconds <= 20 && !state.roundEnded,
      );
    }
  }

  function stopTimer() {
    if (!state.timerId) return;
    clearInterval(state.timerId);
    state.timerId = null;
  }

  function setMapExpanded(expanded) {
    mapPanel.classList.toggle("is-expanded", expanded);
    expandBtn.classList.toggle("is-expanded", expanded);
    expandBtn.setAttribute("aria-pressed", expanded ? "true" : "false");
    expandBtn.setAttribute(
      "aria-label",
      expanded ? "Collapse map" : "Expand map",
    );

    if (!state.map) return;
    const refresh = () => {
      state.map.invalidateSize({ pan: false, debounceMoveend: true });
    };
    refresh();
    setTimeout(refresh, 120);
    setTimeout(refresh, 260);
  }

  async function requestScore() {
    if (state.scoreRequested) return;
    state.scoreRequested = true;

    try {
      const response = await fetch(bootstrap.scoreGuessUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          round_index: Number(bootstrap.currentRoundIndex) || 0,
          guess_latitude: state.guess ? state.guess.lat : null,
          guess_longitude: state.guess ? state.guess.lng : null,
          solution_latitude: Number(bootstrap.solution.latitude),
          solution_longitude: Number(bootstrap.solution.longitude),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error || `Score request failed (${response.status})`,
        );
      }

      if (payload.status === "pending") {
        scoreValue.textContent = "Pending";
      } else if (payload.score !== null && payload.score !== undefined) {
        scoreValue.textContent = String(payload.score);
      } else {
        scoreValue.textContent = "Pending";
      }
    } catch (error) {
      console.error(error);
      scoreValue.textContent = "Pending";
    }
  }

  async function revealRound() {
    if (state.roundEnded || !state.map) return;
    state.roundEnded = true;
    stopTimer();
    setMapExpanded(true);

    const solutionLatLng = L.latLng(
      Number(bootstrap.solution.latitude),
      Number(bootstrap.solution.longitude),
    );

    const distanceText = state.guess
      ? formatDistanceKm(
          haversineDistanceKm(
            L.latLng(state.guess.lat, state.guess.lng),
            solutionLatLng,
          ),
        )
      : "No guess submitted.";

    state.solutionMarker = L.circleMarker(solutionLatLng, {
      radius: 9,
      color: "#fff0f0",
      weight: 2,
      fillColor: "#db6060",
      fillOpacity: 0.95,
    }).addTo(state.map);

    state.solutionMarker.bindPopup(`
      <div class="play-solution-popup">
        <div class="play-solution-title">Solution</div>
        <div class="play-solution-country">${escapeHtml(bootstrap.solution.country)}</div>
        <div class="play-solution-distance">Distance: ${escapeHtml(distanceText)}</div>
      </div>
    `);

    if (state.guess) {
      const guessLatLng = L.latLng(state.guess.lat, state.guess.lng);
      state.linkLine = L.polyline([guessLatLng, solutionLatLng], {
        color: "#f4dd7f",
        weight: 2,
        opacity: 0.75,
        dashArray: "6 6",
      }).addTo(state.map);
    }

    state.map.setView(solutionLatLng, 3, { animate: true });
    setTimeout(() => {
      state.solutionMarker?.openPopup();
    }, 300);

    roundCard.classList.remove("is-hidden");
    await requestScore();
    updateSubmitButton();
  }

  async function submitGuess() {
    if (!state.guess || state.roundEnded || state.submitting) return;
    state.submitting = true;
    updateSubmitButton();

    try {
      const response = await fetch(bootstrap.submitGuessUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latitude: state.guess.lat,
          longitude: state.guess.lng,
          round_index: Number(bootstrap.currentRoundIndex) || 0,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || `Request failed (${response.status})`);
      }

      state.submitted = true;
      await revealRound();
    } catch (error) {
      console.error(error);
      state.submitting = false;
      updateSubmitButton();
    }
  }

  function resolveGuessContext(latlng) {
    const feature = findFeatureForLatLng(latlng, state.features);
    if (!feature) {
      return {
        country: "Open Ocean",
        continent: "Ocean",
      };
    }

    const props = feature.properties || {};
    const country = getCountryNameFromProps(props);
    const continent =
      getContinentFromProps(props, bootstrap.continentNamesByIsoCode || {}) ||
      "Unknown continent";
    return { country, continent };
  }

  function placeGuess(latlng) {
    if (!state.map || state.roundEnded) return;

    if (state.guessMarker) state.map.removeLayer(state.guessMarker);
    state.guessMarker = L.marker(latlng, { title: "Your guess" }).addTo(
      state.map,
    );
    const guessContext = resolveGuessContext(latlng);

    state.guess = {
      lat: latlng.lat,
      lng: latlng.lng,
      country: guessContext.country,
      continent: guessContext.continent,
    };
    updateSubmitButton();
  }

  function startTimer() {
    stopTimer();
    updateTimer();
    state.timerId = setInterval(() => {
      state.remainingSeconds -= 1;
      updateTimer();
      if (state.remainingSeconds <= 0) {
        stopTimer();
        void revealRound();
      }
    }, 1000);
  }

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

  state.map = L.map(mapRoot, {
    worldCopyJump: true,
    zoomControl: true,
  }).setView(MAP_CENTER, MAP_ZOOM);
  state.map.setMaxBounds(WORLD_BOUNDS);
  state.map.options.maxBoundsViscosity = 0.8;

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 15,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(state.map);

  try {
    const response = await fetch(bootstrap.geojsonUrl, {
      cache: "force-cache",
    });
    if (!response.ok) throw new Error(`GeoJSON failed (${response.status})`);
    const geojson = await response.json();
    state.features = Array.isArray(geojson?.features) ? geojson.features : [];
    const scopeStyle = getScopeStyleFactory(
      bootstrap.scope || {},
      bootstrap.continentNamesByIsoCode || {},
    );

    L.geoJSON(geojson, {
      style: scopeStyle,
      interactive: false,
    }).addTo(state.map);
  } catch (error) {
    console.error(error);
    mapRoot.innerHTML =
      '<p class="play-map-error">Map data failed to load.</p>';
  }

  state.map.on("click", (event) => {
    placeGuess(event.latlng);
  });

  submitBtn.addEventListener("click", () => {
    void submitGuess();
  });

  expandBtn.addEventListener("click", () => {
    const isExpanded = !mapPanel.classList.contains("is-expanded");
    setMapExpanded(isExpanded);
  });

  updateSubmitButton();
  startTimer();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPlayPage, { once: true });
} else {
  initPlayPage();
}
