/* register-sw.js — service worker registration */
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/static/js/sw.js").catch(function (err) {
    console.warn("SW registration failed:", err);
  });
}
