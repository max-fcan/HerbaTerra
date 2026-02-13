/* Service Worker for offline support and intelligent caching */

const CACHE_NAME = "herbaterra-v1";
const STATIC_ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/css/catalogue.css",
  "/static/css/gradient.css",
  "/static/js/catalogue.js",
  "/static/js/main.js",
];

// Install: cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Silently fail if some assets can't be cached
        return Promise.resolve();
      });
    }),
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name)),
      );
    }),
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for assets
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests: network-first, fall back to cache
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/play/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const cache = caches.open(CACHE_NAME);
            cache.then((c) => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => caches.match(request)),
    );
  }
  // Static assets: cache-first, fall back to network
  else {
    event.respondWith(
      caches.match(request).then((response) => {
        return response || fetch(request);
      }),
    );
  }
});
