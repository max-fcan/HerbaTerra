(function () {
  "use strict";

  /* ======================================================================
     Species gallery (only runs on species detail page)
     ====================================================================== */
  const pageBootstrap = window.__speciesPageBootstrap || {};
  const bootstrap =
    pageBootstrap.gallery || window.__speciesGalleryBootstrap || null;
  const mapBootstrap =
    pageBootstrap.map || window.__speciesMapBootstrap || null;
  if (!bootstrap) return;

  const mapRoot = document.getElementById("speciesSummaryMap");
  const galleryRoot = document.getElementById("speciesGalleryRoot");
  const carousel = document.getElementById("speciesCarousel");
  const prevBtn = document.getElementById("speciesPrevBtn");
  const nextBtn = document.getElementById("speciesNextBtn");
  const playPauseBtn = document.getElementById("speciesPlayPauseBtn");
  const locationChipRow = document.getElementById("speciesLocationChips");
  const locationSummary = document.getElementById("speciesLocationSummary");
  const locationShowMoreBtn = document.getElementById(
    "speciesLocationShowMoreBtn",
  );
  const locationShowLessBtn = document.getElementById(
    "speciesLocationShowLessBtn",
  );
  const visibleCountInput = document.getElementById("speciesVisibleCount");
  const visibleCountValue = document.getElementById("speciesVisibleCountValue");

  const lightbox = document.getElementById("speciesLightbox");
  const lightboxImg = document.getElementById("speciesLightboxImage");
  const lightboxCaption = document.getElementById("speciesLightboxCaption");
  const lightboxLoading = document.getElementById("speciesLightboxLoading");
  const lightboxClose = document.getElementById("speciesLightboxClose");
  const lightboxPrev = document.getElementById("speciesLightboxPrev");
  const lightboxNext = document.getElementById("speciesLightboxNext");

  if (!galleryRoot || !carousel || !locationChipRow) return;

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  );
  const MAX_VISIBLE_IMAGES = 25;
  const AUTOPLAY_RESUME_DELAY_MS = 500;
  const FETCH_PAGE_LIMIT = 25;
  const REWIND_MIN_DURATION_MS = 900;
  const REWIND_MAX_DURATION_MS = 2600;
  const REWIND_BASE_PX_PER_SEC = 1800;
  const MAX_FETCH_ROUNDS_PER_SELECTION = 120;
  const LOCATION_CHIP_BATCH_SIZE = 10;
  const ALL_LOCATION_KEY = "__ALL__";
  const LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  const LEAFLET_CSS_INTEGRITY =
    "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
  const LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  const LEAFLET_JS_INTEGRITY =
    "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
  const compactCountFormatter = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  });
  let leafletAssetsPromise = null;

  function getCssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  }

  const mapPalette = {
    emptyFill: getCssVar("--color-species-map-fill-empty", "#efe9e9"),
    stroke: getCssVar("--color-species-map-stroke", "#544949"),
    hoverStroke: getCssVar("--color-species-map-hover-stroke", "#3b2a2a"),
    activeStroke: getCssVar("--color-species-map-active-stroke", "#2d1616"),
  };

  function loadStylesheetOnce({ id, href, integrity }) {
    return new Promise((resolve, reject) => {
      let linkEl = document.getElementById(id);
      if (linkEl) {
        if (linkEl.dataset.loaded === "true") {
          resolve();
          return;
        }
        linkEl.addEventListener("load", () => resolve(), { once: true });
        linkEl.addEventListener(
          "error",
          () => reject(new Error(`Failed to load stylesheet: ${href}`)),
          { once: true },
        );
        return;
      }

      linkEl = document.createElement("link");
      linkEl.id = id;
      linkEl.rel = "stylesheet";
      linkEl.href = href;
      linkEl.crossOrigin = "anonymous";
      if (integrity) linkEl.integrity = integrity;
      linkEl.addEventListener(
        "load",
        () => {
          linkEl.dataset.loaded = "true";
          resolve();
        },
        { once: true },
      );
      linkEl.addEventListener(
        "error",
        () => reject(new Error(`Failed to load stylesheet: ${href}`)),
        { once: true },
      );
      document.head.appendChild(linkEl);
    });
  }

  function loadScriptOnce({ id, src, integrity }) {
    return new Promise((resolve, reject) => {
      let scriptEl = document.getElementById(id);
      if (scriptEl) {
        if (scriptEl.dataset.loaded === "true") {
          resolve();
          return;
        }
        scriptEl.addEventListener("load", () => resolve(), { once: true });
        scriptEl.addEventListener(
          "error",
          () => reject(new Error(`Failed to load script: ${src}`)),
          { once: true },
        );
        return;
      }

      scriptEl = document.createElement("script");
      scriptEl.id = id;
      scriptEl.src = src;
      scriptEl.async = true;
      scriptEl.crossOrigin = "anonymous";
      if (integrity) scriptEl.integrity = integrity;
      scriptEl.addEventListener(
        "load",
        () => {
          scriptEl.dataset.loaded = "true";
          resolve();
        },
        { once: true },
      );
      scriptEl.addEventListener(
        "error",
        () => reject(new Error(`Failed to load script: ${src}`)),
        { once: true },
      );
      document.head.appendChild(scriptEl);
    });
  }

  async function loadLeafletAssets() {
    if (typeof window.L !== "undefined") return;
    if (!leafletAssetsPromise) {
      leafletAssetsPromise = Promise.all([
        loadStylesheetOnce({
          id: "speciesLeafletCss",
          href: LEAFLET_CSS_URL,
          integrity: LEAFLET_CSS_INTEGRITY,
        }),
        loadScriptOnce({
          id: "speciesLeafletScript",
          src: LEAFLET_JS_URL,
          integrity: LEAFLET_JS_INTEGRITY,
        }),
      ]).catch((error) => {
        leafletAssetsPromise = null;
        throw error;
      });
    }
    await leafletAssetsPromise;
  }

  function clamp(value, min, max) {
    if (!Number.isFinite(value)) return min;
    return Math.min(max, Math.max(min, Math.round(value)));
  }

  function normalizeCode(value) {
    return String(value || "")
      .trim()
      .toUpperCase();
  }

  function parseOptionalInt(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) ? parsed : null;
  }

  function getLocationKey(countryCode, continentCode) {
    const normalizedCountry = normalizeCode(countryCode);
    const normalizedContinent = normalizeCode(continentCode);
    if (!normalizedCountry && !normalizedContinent) return ALL_LOCATION_KEY;
    return `${normalizedCountry}|${normalizedContinent}`;
  }

  function parseLocationKey(key) {
    if (!key || key === ALL_LOCATION_KEY) {
      return { countryCode: "", continentCode: "" };
    }
    const [countryCode = "", continentCode = ""] = String(key).split("|", 2);
    return {
      countryCode: normalizeCode(countryCode),
      continentCode: normalizeCode(continentCode),
    };
  }

  function createFetchState(overrides = {}) {
    return {
      hasMore: true,
      nextCursorGbifid: null,
      nextCursorRowid: null,
      fetchPromise: null,
      ...overrides,
    };
  }

  const state = {
    speciesName: bootstrap.speciesName || "",
    apiUrl: bootstrap.apiUrl || "",
    images: Array.isArray(bootstrap.images) ? bootstrap.images.slice() : [],
    loadedImageKeys: new Set(),
    isPlaying: !prefersReducedMotion.matches,
    autoplayRafId: null,
    autoplayResumeTimeoutId: null,
    lastFrameTs: null,
    autoplaySpeedPxPerSec: prefersReducedMotion.matches ? 0 : 26,
    isRewinding: false,
    rewindStartTs: null,
    rewindFromPx: 0,
    rewindDurationMs: 0,
    activeCountryCode: "",
    activeContinentCode: "",
    visibleLocationChipCount: LOCATION_CHIP_BATCH_SIZE,
    visibleCount: clamp(
      Number(visibleCountInput?.value ?? 12),
      1,
      MAX_VISIBLE_IMAGES,
    ),
    fetchStates: new Map([
      [
        ALL_LOCATION_KEY,
        createFetchState({
          hasMore: bootstrap.hasMore === false ? false : true,
          nextCursorGbifid: parseOptionalInt(bootstrap.nextCursorGbifid),
          nextCursorRowid: parseOptionalInt(bootstrap.nextCursorRowid),
        }),
      ],
    ]),
    lightboxVisiblePos: 0,
    lightboxLoadRequestId: 0,
    touchStartX: 0,
  };

  function setLightboxLoading(isLoading) {
    if (lightboxLoading) {
      lightboxLoading.hidden = !isLoading;
    }
    if (lightbox) {
      lightbox.setAttribute("aria-busy", String(isLoading));
    }
  }

  function getImageKey(image) {
    const gbifID = image?.gbifID;
    const rowid = image?.rowid;
    if (
      gbifID === null ||
      gbifID === undefined ||
      rowid === null ||
      rowid === undefined
    ) {
      return "";
    }
    return `${gbifID}|${rowid}`;
  }

  function getActiveLocationKey() {
    return getLocationKey(state.activeCountryCode, state.activeContinentCode);
  }

  function getOrCreateFetchState(locationKey) {
    let fetchState = state.fetchStates.get(locationKey);
    if (!fetchState) {
      fetchState = createFetchState();
      state.fetchStates.set(locationKey, fetchState);
    }
    return fetchState;
  }

  state.images.forEach((image) => {
    const key = getImageKey(image);
    if (key) state.loadedImageKeys.add(key);
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatCompactCount(value) {
    const normalizedValue = Number(value);
    if (!Number.isFinite(normalizedValue)) return "0";
    return compactCountFormatter.format(normalizedValue);
  }

  function mixRgb(start, end, t) {
    const ratio = Math.min(1, Math.max(0, t));
    const channels = start.map((channel, index) =>
      Math.round(channel + (end[index] - channel) * ratio),
    );
    return `rgb(${channels[0]}, ${channels[1]}, ${channels[2]})`;
  }

  function normalizeIsoCode(rawCode) {
    if (!rawCode) return "";
    const code = String(rawCode).trim().toUpperCase();
    if (!code || code === "-99" || code === "--") return "";
    if (code.includes("-")) {
      const parts = code.split("-");
      const suffix = parts[parts.length - 1];
      if (suffix.length === 2 || suffix.length === 3) return suffix;
    }
    return code;
  }

  function getCountryCodeA2FromProps(props, codeMap) {
    const codeCandidates = [
      props.iso_a2,
      props.iso_a2_eh,
      props.wb_a2,
      props.iso_a3,
      props.adm0_a3,
      props.sov_a3,
      props.wb_a3,
    ];

    for (const rawCode of codeCandidates) {
      const normalizedCode = normalizeIsoCode(rawCode);
      if (!normalizedCode) continue;
      const a2Code =
        codeMap[normalizedCode] ||
        (normalizedCode.length === 2 ? normalizedCode : "");
      if (a2Code) return a2Code;
    }
    return "";
  }

  function getCountryNameFromProps(props) {
    return (
      String(props.name || props.ADMIN || props.admin || "").trim() ||
      "Unknown country"
    );
  }

  function getLocationChips({ includeAll = false } = {}) {
    const chips = Array.from(
      locationChipRow.querySelectorAll(".species-location-chip"),
    );
    if (includeAll) return chips;
    return chips.filter(
      (chip) => !chip.classList.contains("species-location-chip--all"),
    );
  }

  function updateLocationChipPaginationUI() {
    const locationChips = getLocationChips();
    const total = locationChips.length;
    const visible = Math.max(
      0,
      Math.min(total, Number(state.visibleLocationChipCount) || 0),
    );

    locationChips.forEach((chip, index) => {
      chip.hidden = index >= visible;
    });

    if (locationSummary) {
      if (total <= 0) {
        locationSummary.textContent = "No location filters available.";
      } else if (visible < total) {
        locationSummary.textContent = `Showing top ${visible} of ${total} locations.`;
      } else {
        locationSummary.textContent = `Showing all ${total} locations.`;
      }
    }

    if (locationShowMoreBtn) {
      const remaining = Math.max(0, total - visible);
      if (remaining <= 0) {
        locationShowMoreBtn.hidden = true;
      } else {
        const step = Math.min(LOCATION_CHIP_BATCH_SIZE, remaining);
        locationShowMoreBtn.hidden = false;
        locationShowMoreBtn.textContent = `Show ${step} more`;
      }
    }

    if (locationShowLessBtn) {
      locationShowLessBtn.hidden = visible <= LOCATION_CHIP_BATCH_SIZE;
    }
  }

  function initLocationChipPagination() {
    const locationChips = getLocationChips();
    locationChips.forEach((chip, index) => {
      chip.dataset.locationIndex = String(index);
    });

    state.visibleLocationChipCount = Math.min(
      LOCATION_CHIP_BATCH_SIZE,
      locationChips.length,
    );
    updateLocationChipPaginationUI();
  }

  function showMoreLocationChips() {
    const locationChips = getLocationChips();
    state.visibleLocationChipCount = Math.min(
      locationChips.length,
      (Number(state.visibleLocationChipCount) || 0) + LOCATION_CHIP_BATCH_SIZE,
    );
    updateLocationChipPaginationUI();
  }

  function showLessLocationChips() {
    const locationChips = getLocationChips();
    state.visibleLocationChipCount = Math.min(
      LOCATION_CHIP_BATCH_SIZE,
      locationChips.length,
    );
    updateLocationChipPaginationUI();
  }

  function ensureLocationChipIsVisible(chip) {
    if (!chip || !chip.hidden) return;
    const locationIndex = Number(chip.dataset.locationIndex);
    if (!Number.isInteger(locationIndex) || locationIndex < 0) return;
    state.visibleLocationChipCount = Math.max(
      Number(state.visibleLocationChipCount) || 0,
      locationIndex + 1,
    );
    updateLocationChipPaginationUI();
  }

  function wrapLongitude(lng) {
    if (!Number.isFinite(lng)) return 0;
    return ((((lng + 180) % 360) + 360) % 360) - 180;
  }

  function unwrapRingLongitudes(ring) {
    const normalized = [];
    let previousLng = null;
    for (const point of ring) {
      if (!Array.isArray(point) || point.length < 2) continue;
      const rawLng = Number(point[0]);
      const lat = Number(point[1]);
      if (!Number.isFinite(rawLng) || !Number.isFinite(lat)) continue;

      if (previousLng === null) {
        previousLng = rawLng;
      } else {
        let candidate = rawLng;
        while (candidate - previousLng > 180) candidate -= 360;
        while (candidate - previousLng < -180) candidate += 360;
        previousLng = candidate;
      }

      normalized.push([previousLng, lat]);
    }
    return normalized;
  }

  function getRingArea(ring) {
    if (!Array.isArray(ring) || ring.length < 3) return 0;
    let area = 0;
    for (let index = 0; index < ring.length; index += 1) {
      const current = ring[index];
      const next = ring[(index + 1) % ring.length];
      area += current[0] * next[1] - next[0] * current[1];
    }
    return area / 2;
  }

  function getLargestOuterRing(geometry) {
    if (!geometry || !geometry.type || !Array.isArray(geometry.coordinates)) {
      return null;
    }

    const candidates = [];
    if (geometry.type === "Polygon") {
      if (Array.isArray(geometry.coordinates[0])) {
        candidates.push(geometry.coordinates[0]);
      }
    } else if (geometry.type === "MultiPolygon") {
      for (const polygon of geometry.coordinates) {
        if (Array.isArray(polygon) && Array.isArray(polygon[0])) {
          candidates.push(polygon[0]);
        }
      }
    }

    let bestRing = null;
    let bestArea = -1;
    for (const ring of candidates) {
      const unwrapped = unwrapRingLongitudes(ring);
      const area = Math.abs(getRingArea(unwrapped));
      if (area > bestArea) {
        bestArea = area;
        bestRing = unwrapped;
      }
    }
    return bestRing;
  }

  function getPolygonCentroid(ring) {
    if (!Array.isArray(ring) || ring.length < 3) return null;
    let signedAreaSum = 0;
    let centroidX = 0;
    let centroidY = 0;

    for (let index = 0; index < ring.length; index += 1) {
      const current = ring[index];
      const next = ring[(index + 1) % ring.length];
      const cross = current[0] * next[1] - next[0] * current[1];
      signedAreaSum += cross;
      centroidX += (current[0] + next[0]) * cross;
      centroidY += (current[1] + next[1]) * cross;
    }

    const area = signedAreaSum / 2;
    if (!Number.isFinite(area) || Math.abs(area) < 1e-8) return null;
    return [centroidY / (6 * area), wrapLongitude(centroidX / (6 * area))];
  }

  function findLocationChipByCountryCode(countryCode) {
    const normalizedCode = normalizeCode(countryCode);
    if (!normalizedCode) return null;
    const chips = Array.from(
      locationChipRow.querySelectorAll(".species-location-chip"),
    );
    return (
      chips.find(
        (chip) => normalizeCode(chip.dataset.countryCode) === normalizedCode,
      ) || null
    );
  }

  async function selectCountryFromMapAndScroll(countryCode) {
    const normalizedCode = normalizeCode(countryCode);
    if (!normalizedCode) return;

    const matchingChip = findLocationChipByCountryCode(normalizedCode);
    if (matchingChip) {
      await handleChipSelection(matchingChip);
    } else {
      const chips = locationChipRow.querySelectorAll(".species-location-chip");
      chips.forEach((chip) => chip.classList.remove("is-active"));
      state.activeCountryCode = normalizedCode;
      state.activeContinentCode = "";
      await ensureImagesForCurrentSelection(state.visibleCount);
      applyVisibleFilters(true);
    }

    galleryRoot.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function getSlides() {
    return Array.from(carousel.querySelectorAll(".species-slide"));
  }

  function assignSlideIndices() {
    getSlides().forEach((slide, index) => {
      slide.dataset.imageIndex = String(index);
      const openBtn = slide.querySelector(".species-slide-open");
      if (openBtn) openBtn.dataset.openLightbox = String(index);
    });
  }

  function updateVisibleCountUI() {
    if (visibleCountInput) visibleCountInput.value = String(state.visibleCount);
    if (visibleCountValue) {
      visibleCountValue.value = String(state.visibleCount);
      visibleCountValue.textContent = String(state.visibleCount);
    }
  }

  function matchesLocationFilter(slide) {
    return matchesLocationCodes(
      normalizeCode(slide.dataset.countryCode),
      normalizeCode(slide.dataset.continentCode),
    );
  }

  function matchesLocationCodes(countryCode, continentCode) {
    if (!state.activeCountryCode && !state.activeContinentCode) return true;
    if (state.activeCountryCode && countryCode !== state.activeCountryCode) {
      return false;
    }
    if (
      state.activeContinentCode &&
      continentCode !== state.activeContinentCode
    ) {
      return false;
    }
    return true;
  }

  function matchesLocationFilterForImage(image) {
    return matchesLocationCodes(
      normalizeCode(image?.country_code),
      normalizeCode(image?.continent_code),
    );
  }

  function applyVisibleFilters(resetScroll = false) {
    let shown = 0;
    getSlides().forEach((slide) => {
      const shouldShow =
        matchesLocationFilter(slide) && shown < state.visibleCount;
      slide.hidden = !shouldShow;
      if (shouldShow) shown += 1;
    });

    if (resetScroll) {
      carousel.scrollTo({ left: 0, behavior: "auto" });
    }
  }

  function getVisibleImageIndices() {
    return getSlides()
      .filter((slide) => !slide.hidden)
      .map((slide) => Number(slide.dataset.imageIndex))
      .filter((v) => Number.isInteger(v));
  }

  function getFormattedObservationDate(image) {
    const year = parseOptionalInt(image?.year);
    const month = parseOptionalInt(image?.month);
    if (!year) return "Unknown date";
    if (!month || month < 1 || month > 12) return String(year);

    const monthNames = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return `${monthNames[month - 1]} ${year}`;
  }

  function createCaptionChip(label, value) {
    const chip = document.createElement("span");
    chip.className = "species-lightbox-caption-chip";

    const labelEl = document.createElement("span");
    labelEl.className = "species-lightbox-caption-chip-label";
    labelEl.textContent = label;

    const valueEl = document.createElement("span");
    valueEl.className = "species-lightbox-caption-chip-value";
    valueEl.textContent = value;

    chip.appendChild(labelEl);
    chip.appendChild(valueEl);
    return chip;
  }

  function renderLightboxCaption(image) {
    if (!lightboxCaption) return;

    lightboxCaption.replaceChildren();

    const locationText = [
      image?.country || "Unknown location",
      image?.state_province,
    ]
      .filter(Boolean)
      .join(", ");
    const locationEl = document.createElement("p");
    locationEl.className = "species-lightbox-caption-location";
    locationEl.textContent = locationText;
    lightboxCaption.appendChild(locationEl);

    const metaRow = document.createElement("div");
    metaRow.className = "species-lightbox-caption-meta";
    metaRow.appendChild(
      createCaptionChip("Date", getFormattedObservationDate(image)),
    );

    const creator = String(image?.creator || "").trim();
    if (creator) {
      metaRow.appendChild(createCaptionChip("Credit", creator));
    }

    const license = String(image?.license || "").trim();
    if (license) {
      metaRow.appendChild(createCaptionChip("License", license));
    }

    lightboxCaption.appendChild(metaRow);
  }

  function syncLightboxCaptionWidth() {
    if (!lightboxCaption || !lightboxImg) return;
    const imageWidth = Math.round(
      lightboxImg.getBoundingClientRect().width || 0,
    );
    const cssWidth = imageWidth > 0 ? `${imageWidth}px` : "0px";
    lightboxCaption.style.setProperty(
      "--species-lightbox-image-width",
      cssWidth,
    );
  }

  function createSlideElement(image, imageIndex) {
    const slide = document.createElement("article");
    slide.className = "species-slide";
    slide.dataset.gbifid = String(image.gbifID ?? "");
    slide.dataset.rowid = String(image.rowid ?? "");
    slide.dataset.countryCode = String(image.country_code ?? "");
    slide.dataset.continentCode = String(image.continent_code ?? "");
    slide.dataset.imageIndex = String(imageIndex);

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "species-slide-open";
    openButton.dataset.openLightbox = String(imageIndex);
    openButton.setAttribute("aria-label", "Open image in lightbox");

    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = image.url_medium || image.url_original || "";
    img.dataset.originalSrc = image.url_original || "";
    img.alt = `${state.speciesName} image ${imageIndex + 1}`;

    openButton.appendChild(img);
    slide.appendChild(openButton);

    const meta = document.createElement("div");
    meta.className = "species-slide-meta";

    const location = document.createElement("p");
    const locationParts = [
      image.country || "Unknown country",
      image.state_province,
    ]
      .filter(Boolean)
      .join(", ");
    location.textContent = locationParts || "Unknown country";
    meta.appendChild(location);

    const date = document.createElement("p");
    date.textContent = image.year
      ? `${image.year}${image.month ? `-${String(image.month).padStart(2, "0")}` : ""}`
      : "Unknown date";
    meta.appendChild(date);

    const credit = document.createElement("p");
    credit.className = "species-slide-credit";
    credit.textContent = [image.creator, image.license]
      .filter(Boolean)
      .join(" | ");
    meta.appendChild(credit);

    slide.appendChild(meta);
    return slide;
  }

  function appendImagesToCarousel(images) {
    if (!Array.isArray(images) || !images.length) return 0;
    const fragment = document.createDocumentFragment();
    let imageIndex = state.images.length;
    let added = 0;
    for (const image of images) {
      const imageKey = getImageKey(image);
      if (imageKey && state.loadedImageKeys.has(imageKey)) continue;
      if (imageKey) state.loadedImageKeys.add(imageKey);
      fragment.appendChild(createSlideElement(image, imageIndex));
      state.images.push(image);
      imageIndex += 1;
      added += 1;
    }
    if (added > 0) carousel.appendChild(fragment);
    return added;
  }

  function countMatchingLoadedImages() {
    let count = 0;
    for (const image of state.images) {
      if (matchesLocationFilterForImage(image)) count += 1;
    }
    return count;
  }

  function buildImagesApiUrl(limit, locationKey, fetchState) {
    if (!state.apiUrl) return null;
    try {
      const url = new URL(state.apiUrl, window.location.origin);
      if (fetchState.nextCursorGbifid !== null) {
        url.searchParams.set(
          "cursor_gbifid",
          String(fetchState.nextCursorGbifid),
        );
      }
      if (fetchState.nextCursorRowid !== null) {
        url.searchParams.set(
          "cursor_rowid",
          String(fetchState.nextCursorRowid),
        );
      }

      const { countryCode, continentCode } = parseLocationKey(locationKey);
      if (countryCode) {
        url.searchParams.set("country_code", countryCode);
      }
      if (continentCode) {
        url.searchParams.set("continent_code", continentCode);
      }

      url.searchParams.set("limit", String(limit));
      return url.toString();
    } catch (_error) {
      return null;
    }
  }

  async function fetchNextImagesPage(
    locationKey = getActiveLocationKey(),
    limit = FETCH_PAGE_LIMIT,
  ) {
    const fetchState = getOrCreateFetchState(locationKey);
    if (!fetchState.hasMore || !state.apiUrl) return { fetched: 0, added: 0 };
    if (fetchState.fetchPromise) return fetchState.fetchPromise;

    const requestUrl = buildImagesApiUrl(limit, locationKey, fetchState);
    if (!requestUrl) {
      fetchState.hasMore = false;
      return { fetched: 0, added: 0 };
    }

    const requestPromise = (async () => {
      try {
        const response = await window.fetch(requestUrl, {
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const page = await response.json();
        const items = Array.isArray(page.items) ? page.items : [];

        fetchState.hasMore = Boolean(page.has_more);
        fetchState.nextCursorGbifid = parseOptionalInt(page.next_cursor_gbifid);
        fetchState.nextCursorRowid = parseOptionalInt(page.next_cursor_rowid);
        const added = appendImagesToCarousel(items);
        return { fetched: items.length, added };
      } catch (error) {
        console.error("Failed to load additional species images.", error);
        fetchState.hasMore = false;
        return { fetched: 0, added: 0 };
      }
    })();

    fetchState.fetchPromise = requestPromise;
    try {
      return await requestPromise;
    } finally {
      if (fetchState.fetchPromise === requestPromise) {
        fetchState.fetchPromise = null;
      }
    }
  }

  async function ensureImagesForCurrentSelection(minMatches) {
    const minimum = clamp(
      Number(minMatches || state.visibleCount),
      1,
      MAX_VISIBLE_IMAGES,
    );
    const activeLocationKey = getActiveLocationKey();
    const fetchState = getOrCreateFetchState(activeLocationKey);
    let matches = countMatchingLoadedImages();
    let rounds = 0;
    while (
      fetchState.hasMore &&
      matches < minimum &&
      rounds < MAX_FETCH_ROUNDS_PER_SELECTION
    ) {
      rounds += 1;
      const result = await fetchNextImagesPage(
        activeLocationKey,
        FETCH_PAGE_LIMIT,
      );
      if (result.fetched <= 0) break;
      matches = countMatchingLoadedImages();
    }
  }

  async function loadSpeciesMapCountryStats() {
    const inlineStats = Array.isArray(mapBootstrap?.countryStats)
      ? mapBootstrap.countryStats
      : [];
    if (inlineStats.length) return inlineStats;

    const statsApiUrl = String(mapBootstrap?.mapStatsApiUrl || "").trim();
    if (!statsApiUrl) return [];

    try {
      const response = await window.fetch(statsApiUrl, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Failed to load map stats (${response.status})`);
      }
      const payload = await response.json();
      if (Array.isArray(payload)) return payload;
      if (Array.isArray(payload?.items)) return payload.items;
      return [];
    } catch (error) {
      console.error("Failed to load species map stats.", error);
      return [];
    }
  }

  async function initSpeciesSummaryMap() {
    if (!mapRoot || !mapBootstrap) return;
    if (typeof L === "undefined" || !mapBootstrap.geojsonUrl) {
      mapRoot.setAttribute("aria-busy", "false");
      mapRoot.innerHTML =
        '<p class="species-summary-map-error">Map data is unavailable.</p>';
      return;
    }

    mapRoot.setAttribute("aria-busy", "true");

    const DEFAULT_MAP_CENTER = [45, 5];
    const DEFAULT_MAP_ZOOM = 2;
    const countryCodeA2ByIsoCode = mapBootstrap.countryCodeA2ByIsoCode || {};
    const speciesLabel = (
      mapBootstrap.commonName ||
      mapBootstrap.scientificName ||
      state.speciesName ||
      "this species"
    ).trim();

    const statsByCountryCode = new Map();
    const rawCountryStats = await loadSpeciesMapCountryStats();
    const preferredCountryCode =
      rawCountryStats
        .map((entry) => normalizeCode(entry?.country_code))
        .find(Boolean) || "";

    rawCountryStats.forEach((entry) => {
      const code = normalizeCode(entry?.country_code);
      if (!code) return;

      const previous = statsByCountryCode.get(code) || {
        country: "",
        occurrenceCount: 0,
        imageCount: 0,
      };

      const countryName = String(entry?.country || "").trim();
      previous.country = previous.country || countryName;
      previous.occurrenceCount += Math.max(
        0,
        Number(entry?.occurrence_count) || 0,
      );
      previous.imageCount += Math.max(0, Number(entry?.image_count) || 0);
      statsByCountryCode.set(code, previous);
    });

    mapRoot.innerHTML = "";

    const maxObservationCount = Math.max(
      0,
      ...Array.from(statsByCountryCode.values()).map(
        (entry) => entry.occurrenceCount,
      ),
    );

    function getFillColor(observationCount) {
      if (observationCount <= 0 || maxObservationCount <= 0) {
        return mapPalette.emptyFill;
      }
      const normalized = Math.min(1, observationCount / maxObservationCount);
      const weighted = Math.pow(normalized, 0.58);
      return mixRgb([247, 194, 194], [127, 12, 12], weighted);
    }

    function getFeatureStyle(feature, mode = "base") {
      const props = feature?.properties || {};
      const countryCode = getCountryCodeA2FromProps(
        props,
        countryCodeA2ByIsoCode,
      );
      const stats = countryCode ? statsByCountryCode.get(countryCode) : null;
      const hasData = Boolean(stats && stats.occurrenceCount > 0);

      if (mode === "active") {
        return {
          weight: 1.35,
          color: mapPalette.activeStroke,
          fillColor: getFillColor(stats?.occurrenceCount || 0),
          fillOpacity: hasData ? 0.86 : 0.48,
        };
      }

      if (mode === "hover") {
        return {
          weight: 1.05,
          color: mapPalette.hoverStroke,
          fillColor: getFillColor(stats?.occurrenceCount || 0),
          fillOpacity: hasData ? 0.78 : 0.4,
        };
      }

      return {
        weight: 0.55,
        color: mapPalette.stroke,
        fillColor: getFillColor(stats?.occurrenceCount || 0),
        fillOpacity: hasData ? 0.68 : 0.28,
      };
    }

    function renderPopupHtml(countryName, countryCode, stats) {
      if (stats && stats.occurrenceCount > 0) {
        const isTopLocation = Boolean(
          findLocationChipByCountryCode(countryCode),
        );
        const actionLabel = isTopLocation
          ? "View Images"
          : "View Images (Filter)";
        return `
            <div class="species-map-popup">
              <div class="species-map-popup-title"><strong>${escapeHtml(countryName)}</strong></div>
            <div class="species-map-popup-stat">${escapeHtml(formatCompactCount(stats.occurrenceCount))} observations</div>
            <div class="species-map-popup-stat">${escapeHtml(formatCompactCount(stats.imageCount))} images</div>
            <button
              type="button"
              class="species-map-popup-action"
              data-country-code="${escapeHtml(countryCode)}"
            >
              ${escapeHtml(actionLabel)}
            </button>
          </div>
        `;
      }

      return `
        <div class="species-map-popup">
          <div class="species-map-popup-title"><strong>${escapeHtml(countryName)}</strong></div>
          <div class="species-map-popup-empty">
            <em>There are no observations of ${escapeHtml(speciesLabel)} available here.</em>
          </div>
        </div>
      `;
    }

    function wirePopupAction(popupElement, mapInstance) {
      if (!popupElement) return;
      const actionButton = popupElement.querySelector(
        ".species-map-popup-action",
      );
      if (!actionButton) return;

      actionButton.addEventListener("click", async (event) => {
        event.preventDefault();
        const countryCode = actionButton.dataset.countryCode || "";
        actionButton.disabled = true;
        try {
          await selectCountryFromMapAndScroll(countryCode);
          mapInstance.closePopup();
        } finally {
          actionButton.disabled = false;
        }
      });
    }

    const map = L.map(mapRoot, {
      worldCopyJump: true,
      zoomControl: true,
      maxZoom: 11,
    }).setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 11,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    try {
      const response = await window.fetch(mapBootstrap.geojsonUrl, {
        cache: "force-cache",
      });
      if (!response.ok) {
        throw new Error(`Failed to load GeoJSON (${response.status})`);
      }

      const countriesGeoJson = await response.json();
      let selectedLayer = null;
      let preferredLayer = null;

      const countriesLayer = L.geoJSON(countriesGeoJson, {
        style: (feature) => getFeatureStyle(feature, "base"),
        onEachFeature(feature, layer) {
          if (!preferredLayer && preferredCountryCode) {
            const props = feature?.properties || {};
            const countryCode = getCountryCodeA2FromProps(
              props,
              countryCodeA2ByIsoCode,
            );
            if (countryCode === preferredCountryCode) {
              preferredLayer = layer;
            }
          }

          layer.on("click", (event) => {
            if (selectedLayer && selectedLayer !== layer) {
              selectedLayer.setStyle(
                getFeatureStyle(selectedLayer.feature, "base"),
              );
            }

            selectedLayer = layer;
            layer.setStyle(getFeatureStyle(feature, "active"));

            const props = feature?.properties || {};
            const countryCode = getCountryCodeA2FromProps(
              props,
              countryCodeA2ByIsoCode,
            );
            const countryName = getCountryNameFromProps(props);
            const stats = countryCode
              ? statsByCountryCode.get(countryCode)
              : null;
            const popupHtml = renderPopupHtml(countryName, countryCode, stats);
            const popup = L.popup({ closeButton: true, autoPan: true })
              .setLatLng(event.latlng)
              .setContent(popupHtml)
              .openOn(map);

            const popupElement = popup.getElement();
            if (popupElement) {
              wirePopupAction(popupElement, map);
            } else {
              map.once("popupopen", ({ popup: openedPopup }) => {
                wirePopupAction(openedPopup.getElement(), map);
              });
            }
          });

          layer.on("mouseover", () => {
            if (layer !== selectedLayer) {
              layer.setStyle(getFeatureStyle(feature, "hover"));
            }
          });

          layer.on("mouseout", () => {
            if (layer !== selectedLayer) {
              layer.setStyle(getFeatureStyle(feature, "base"));
            }
          });
        },
      }).addTo(map);

      if (preferredLayer) {
        const preferredBounds = preferredLayer.getBounds();
        if (preferredBounds?.isValid()) {
          const longitudeSpan = Math.abs(
            preferredBounds.getEast() - preferredBounds.getWest(),
          );
          if (longitudeSpan <= 220) {
            map.fitBounds(preferredBounds.pad(0.3), {
              animate: false,
              maxZoom: 5,
            });
          } else {
            const largestRing = getLargestOuterRing(
              preferredLayer.feature?.geometry,
            );
            const centroid = getPolygonCentroid(largestRing);
            if (centroid) {
              map.setView(centroid, 3, { animate: false });
            } else {
              map.fitBounds(preferredBounds.pad(0.3), {
                animate: false,
                maxZoom: 4,
              });
            }
          }
        }
      }

      const constraintBounds = countriesLayer.getBounds().pad(0.05);
      map.setMaxBounds(constraintBounds);
      map.options.maxBoundsViscosity = 0.9;

      function applyViewportMinZoom() {
        const minZoom = Math.max(
          0,
          map.getBoundsZoom(constraintBounds, true) - 1,
        );
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
        if (resizeTimer) window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(() => {
          map.invalidateSize({ pan: false, debounceMoveend: true });
          applyViewportMinZoom();
        }, 120);
      });

      mapRoot.setAttribute("aria-busy", "false");
    } catch (error) {
      console.error(error);
      mapRoot.setAttribute("aria-busy", "false");
      mapRoot.innerHTML =
        '<p class="species-summary-map-error">Map data failed to load.</p>';
    }
  }

  function setSpeciesSummaryMapLoadingState() {
    if (!mapRoot || !mapBootstrap || !mapBootstrap.geojsonUrl) return;
    mapRoot.setAttribute("aria-busy", "true");
    mapRoot.innerHTML =
      '<p class="species-summary-map-loading" role="status" aria-live="polite">Loading map...</p>';
  }

  function scheduleSpeciesSummaryMapInit() {
    if (!mapRoot || !mapBootstrap || !mapBootstrap.geojsonUrl) return;
    setSpeciesSummaryMapLoadingState();

    const startMapLoad = () => {
      loadLeafletAssets()
        .then(() => initSpeciesSummaryMap())
        .catch((error) => {
          console.error("Failed to load map library.", error);
          mapRoot.setAttribute("aria-busy", "false");
          mapRoot.innerHTML =
            '<p class="species-summary-map-error">Map library failed to load.</p>';
        });
    };

    const initializeMap = () => {
      if (typeof window.requestIdleCallback === "function") {
        window.requestIdleCallback(
          () => {
            startMapLoad();
          },
          { timeout: 1500 },
        );
      } else {
        window.setTimeout(() => {
          startMapLoad();
        }, 180);
      }
    };

    if (document.readyState === "complete") {
      initializeMap();
    } else {
      window.addEventListener("load", initializeMap, { once: true });
    }
  }

  function openLightboxByImageIndex(imageIndex) {
    if (!lightbox || !lightboxImg || !lightboxCaption) return;

    const visible = getVisibleImageIndices();
    if (!visible.length) return;

    const position = Math.max(0, visible.indexOf(imageIndex));
    state.lightboxVisiblePos = position >= 0 ? position : 0;

    renderLightbox();
    lightbox.hidden = false;
    document.body.classList.add("lightbox-open");
    window.requestAnimationFrame(syncLightboxCaptionWidth);
  }

  function closeLightbox() {
    if (!lightbox) return;
    state.lightboxLoadRequestId += 1;
    setLightboxLoading(false);
    lightbox.hidden = true;
    document.body.classList.remove("lightbox-open");
  }

  function renderLightbox() {
    const visible = getVisibleImageIndices();
    if (!visible.length) return;

    if (state.lightboxVisiblePos >= visible.length)
      state.lightboxVisiblePos = 0;
    if (state.lightboxVisiblePos < 0)
      state.lightboxVisiblePos = visible.length - 1;

    const imageIndex = visible[state.lightboxVisiblePos];
    const image = state.images[imageIndex];
    if (!image) return;

    const nextSrc = image.url_original || image.url_medium || "";
    const nextAlt = `${state.speciesName} image ${imageIndex + 1}`;
    const currentSrc = lightboxImg.getAttribute("src") || "";

    if (!nextSrc) {
      lightboxImg.removeAttribute("src");
      lightboxImg.alt = nextAlt;
      renderLightboxCaption(image);
      setLightboxLoading(false);
      syncLightboxCaptionWidth();
      return;
    }

    if (currentSrc === nextSrc) {
      lightboxImg.alt = nextAlt;
      renderLightboxCaption(image);
      setLightboxLoading(false);
      window.requestAnimationFrame(syncLightboxCaptionWidth);
      return;
    }

    const shouldShowLoadingOverlay = Boolean(currentSrc);
    setLightboxLoading(shouldShowLoadingOverlay);
    const requestId = state.lightboxLoadRequestId + 1;
    state.lightboxLoadRequestId = requestId;

    const preloadedImage = new Image();
    let settled = false;
    const commitLoadedImage = () => {
      if (settled) return;
      settled = true;
      if (requestId !== state.lightboxLoadRequestId) return;

      lightboxImg.src = nextSrc;
      lightboxImg.alt = nextAlt;
      renderLightboxCaption(image);
      setLightboxLoading(false);
      window.requestAnimationFrame(syncLightboxCaptionWidth);
    };

    preloadedImage.onload = commitLoadedImage;
    preloadedImage.onerror = commitLoadedImage;
    preloadedImage.src = nextSrc;

    if (preloadedImage.complete) {
      commitLoadedImage();
    }
  }

  function shiftLightbox(direction) {
    const visible = getVisibleImageIndices();
    if (!visible.length) return;
    state.lightboxVisiblePos += direction;
    if (state.lightboxVisiblePos >= visible.length)
      state.lightboxVisiblePos = 0;
    if (state.lightboxVisiblePos < 0)
      state.lightboxVisiblePos = visible.length - 1;
    renderLightbox();
  }

  function getNavScrollDistance() {
    return Math.max(220, carousel.clientWidth * 0.82);
  }

  function scrollCarousel(direction) {
    const maxScroll = Math.max(0, carousel.scrollWidth - carousel.clientWidth);
    let target = carousel.scrollLeft + direction * getNavScrollDistance();
    if (target < 0) target = 0;
    if (target > maxScroll) target = maxScroll;
    carousel.scrollTo({ left: target, behavior: "smooth" });
  }

  function syncPlayPauseUI() {
    if (!playPauseBtn) return;
    playPauseBtn.classList.toggle("is-paused", !state.isPlaying);
    playPauseBtn.setAttribute(
      "aria-label",
      state.isPlaying ? "Pause autoplay" : "Resume autoplay",
    );
  }

  function easeInOutCubic(progress) {
    const p = Math.min(1, Math.max(0, progress));
    if (p < 0.5) return 4 * p * p * p;
    return 1 - Math.pow(-2 * p + 2, 3) / 2;
  }

  function getRewindDurationMs(distancePx) {
    const rawMs = (Math.max(0, distancePx) / REWIND_BASE_PX_PER_SEC) * 1000;
    return clamp(rawMs, REWIND_MIN_DURATION_MS, REWIND_MAX_DURATION_MS);
  }

  function beginAutoplayRewind(maxScroll, timestamp) {
    if (maxScroll <= 0) return;

    state.isRewinding = true;
    state.rewindStartTs = timestamp;
    state.rewindFromPx = Math.min(maxScroll, Math.max(0, carousel.scrollLeft));
    state.rewindDurationMs = getRewindDurationMs(state.rewindFromPx);

    if (state.rewindDurationMs <= 0 || state.rewindFromPx <= 0) {
      carousel.scrollLeft = 0;
      state.isRewinding = false;
      state.rewindStartTs = null;
      state.rewindFromPx = 0;
      state.rewindDurationMs = 0;
    }
  }

  function stopAutoplay() {
    if (state.autoplayResumeTimeoutId !== null) {
      window.clearTimeout(state.autoplayResumeTimeoutId);
      state.autoplayResumeTimeoutId = null;
    }
    if (state.autoplayRafId !== null) {
      window.cancelAnimationFrame(state.autoplayRafId);
      state.autoplayRafId = null;
    }
    state.lastFrameTs = null;
    state.isRewinding = false;
    state.rewindStartTs = null;
    state.rewindFromPx = 0;
    state.rewindDurationMs = 0;
  }

  function tickAutoplay(timestamp) {
    if (!state.isPlaying) return;

    const maxScroll = Math.max(0, carousel.scrollWidth - carousel.clientWidth);
    if (state.isRewinding) {
      if (
        maxScroll <= 0 ||
        state.rewindStartTs === null ||
        state.rewindDurationMs <= 0
      ) {
        carousel.scrollLeft = 0;
        state.isRewinding = false;
        state.rewindStartTs = null;
        state.rewindFromPx = 0;
        state.rewindDurationMs = 0;
        state.lastFrameTs = timestamp;
      } else {
        const elapsed = Math.max(0, timestamp - state.rewindStartTs);
        const progress = Math.min(1, elapsed / state.rewindDurationMs);
        const eased = easeInOutCubic(progress);
        carousel.scrollLeft = state.rewindFromPx * (1 - eased);

        if (progress >= 1) {
          carousel.scrollLeft = 0;
          state.isRewinding = false;
          state.rewindStartTs = null;
          state.rewindFromPx = 0;
          state.rewindDurationMs = 0;
          state.lastFrameTs = timestamp;
        }
      }

      state.autoplayRafId = window.requestAnimationFrame(tickAutoplay);
      return;
    }

    if (state.lastFrameTs == null) {
      state.lastFrameTs = timestamp;
    }

    const deltaMs = Math.max(0, timestamp - state.lastFrameTs);
    state.lastFrameTs = timestamp;

    if (maxScroll > 0 && state.autoplaySpeedPxPerSec > 0) {
      const deltaPx = (state.autoplaySpeedPxPerSec * deltaMs) / 1000;
      const next = carousel.scrollLeft + deltaPx;
      if (next >= maxScroll) {
        carousel.scrollLeft = maxScroll;
        beginAutoplayRewind(maxScroll, timestamp);
      } else {
        carousel.scrollLeft = next;
      }
    }

    state.autoplayRafId = window.requestAnimationFrame(tickAutoplay);
  }

  function startAutoplay() {
    stopAutoplay();
    if (!state.isPlaying) return;
    state.autoplayRafId = window.requestAnimationFrame(tickAutoplay);
  }

  function resumeAutoplayAfterDelay(delayMs) {
    if (!state.isPlaying) return;
    stopAutoplay();
    state.autoplayResumeTimeoutId = window.setTimeout(
      () => {
        state.autoplayResumeTimeoutId = null;
        if (state.isPlaying) startAutoplay();
      },
      Math.max(0, Number(delayMs) || 0),
    );
  }

  function pauseAutoplayTemporarily() {
    if (!state.isPlaying) return;
    stopAutoplay();
  }

  function resumeAutoplayIfEnabled() {
    if (state.isPlaying) startAutoplay();
  }

  function pauseAutoplayFromNavigation() {
    if (!state.isPlaying) return;
    state.isPlaying = false;
    syncPlayPauseUI();
    stopAutoplay();
  }

  async function handleChipSelection(button) {
    ensureLocationChipIsVisible(button);

    const chips = locationChipRow.querySelectorAll(".species-location-chip");
    chips.forEach((chip) => chip.classList.remove("is-active"));
    button.classList.add("is-active");

    state.activeCountryCode = normalizeCode(button.dataset.countryCode);
    state.activeContinentCode = normalizeCode(button.dataset.continentCode);

    await ensureImagesForCurrentSelection(state.visibleCount);
    applyVisibleFilters(true);
  }

  async function handleVisibleCountChange() {
    state.visibleCount = clamp(
      Number(visibleCountInput?.value),
      1,
      MAX_VISIBLE_IMAGES,
    );
    updateVisibleCountUI();
    await ensureImagesForCurrentSelection(state.visibleCount);
    applyVisibleFilters(true);
    resumeAutoplayAfterDelay(AUTOPLAY_RESUME_DELAY_MS);
  }

  function wireEvents() {
    assignSlideIndices();

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        pauseAutoplayFromNavigation();
        scrollCarousel(-1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        pauseAutoplayFromNavigation();
        scrollCarousel(1);
      });
    }

    if (playPauseBtn) {
      playPauseBtn.addEventListener("click", () => {
        state.isPlaying = !state.isPlaying;
        syncPlayPauseUI();
        if (state.isPlaying) {
          startAutoplay();
        } else {
          stopAutoplay();
        }
      });
    }

    carousel.addEventListener("click", (event) => {
      const openButton = event.target.closest(".species-slide-open");
      if (!openButton) return;
      const imageIndex = Number(openButton.dataset.openLightbox);
      if (!Number.isInteger(imageIndex)) return;
      openLightboxByImageIndex(imageIndex);
    });

    locationChipRow.addEventListener("click", (event) => {
      const chip = event.target.closest(".species-location-chip");
      if (!chip) return;
      handleChipSelection(chip);
    });

    if (locationShowMoreBtn) {
      locationShowMoreBtn.addEventListener("click", () => {
        showMoreLocationChips();
      });
    }

    if (locationShowLessBtn) {
      locationShowLessBtn.addEventListener("click", () => {
        showLessLocationChips();
      });
    }

    if (visibleCountInput) {
      visibleCountInput.addEventListener("input", handleVisibleCountChange);
      visibleCountInput.addEventListener("change", handleVisibleCountChange);
    }

    carousel.addEventListener("focusin", pauseAutoplayTemporarily);
    carousel.addEventListener("focusout", resumeAutoplayIfEnabled);
    carousel.addEventListener("touchstart", pauseAutoplayTemporarily, {
      passive: true,
    });
    carousel.addEventListener("touchend", resumeAutoplayIfEnabled, {
      passive: true,
    });

    if (lightbox && lightboxClose && lightboxPrev && lightboxNext) {
      lightboxClose.addEventListener("click", closeLightbox);
      lightboxPrev.addEventListener("click", () => shiftLightbox(-1));
      lightboxNext.addEventListener("click", () => shiftLightbox(1));
      if (lightboxImg) {
        lightboxImg.addEventListener("load", () => {
          if (lightbox.hidden) return;
          syncLightboxCaptionWidth();
        });
      }

      lightbox.addEventListener("click", (event) => {
        if (event.target === lightbox) closeLightbox();
      });

      lightbox.addEventListener(
        "touchstart",
        (event) => {
          state.touchStartX = event.changedTouches[0]?.screenX || 0;
        },
        { passive: true },
      );

      lightbox.addEventListener(
        "touchend",
        (event) => {
          const endX = event.changedTouches[0]?.screenX || 0;
          const delta = state.touchStartX - endX;
          if (Math.abs(delta) < 45) return;
          shiftLightbox(delta > 0 ? 1 : -1);
        },
        { passive: true },
      );
    }

    window.addEventListener("resize", () => {
      if (!lightbox || lightbox.hidden) return;
      window.requestAnimationFrame(syncLightboxCaptionWidth);
    });

    document.addEventListener("keydown", (event) => {
      if (!lightbox || lightbox.hidden) return;
      if (event.key === "Escape") closeLightbox();
      if (event.key === "ArrowLeft") shiftLightbox(-1);
      if (event.key === "ArrowRight") shiftLightbox(1);
    });
  }

  function init() {
    initLocationChipPagination();
    updateVisibleCountUI();
    syncPlayPauseUI();
    applyVisibleFilters(true);
    wireEvents();
    scheduleSpeciesSummaryMapInit();
    startAutoplay();
  }

  init();
})();
