export const LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
export const LEAFLET_CSS_INTEGRITY =
  "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
export const LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
export const LEAFLET_JS_INTEGRITY =
  "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";

let leafletAssetsPromise = null;

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

export async function loadLeafletAssets() {
  if (typeof window.L !== "undefined") return;

  if (!leafletAssetsPromise) {
    leafletAssetsPromise = Promise.all([
      loadStylesheetOnce({
        id: "leafletCss",
        href: LEAFLET_CSS_URL,
        integrity: LEAFLET_CSS_INTEGRITY,
      }),
      loadScriptOnce({
        id: "leafletScript",
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
