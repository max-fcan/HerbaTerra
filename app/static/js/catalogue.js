/* ═══════════════════════════════════════════════════════════════════════════
   catalogue.js — Autocomplete, gallery slider, lightbox
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ── Autocomplete ────────────────────────────────────────────────────────
  const searchInput = document.getElementById("catalogueSearch");
  const dropdown = document.getElementById("autocompleteDropdown");
  let debounceTimer = null;
  let acIndex = -1;

  if (searchInput && dropdown) {
    searchInput.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      const q = this.value.trim();
      if (q.length < 2) {
        dropdown.classList.remove("show");
        dropdown.innerHTML = "";
        return;
      }
      debounceTimer = setTimeout(() => fetchSuggestions(q), 220);
    });

    searchInput.addEventListener("keydown", function (e) {
      const items = dropdown.querySelectorAll(".ac-item");
      if (!items.length) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        acIndex = Math.min(acIndex + 1, items.length - 1);
        highlightItem(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        acIndex = Math.max(acIndex - 1, 0);
        highlightItem(items);
      } else if (e.key === "Enter" && acIndex >= 0) {
        e.preventDefault();
        items[acIndex].click();
      } else if (e.key === "Escape") {
        dropdown.classList.remove("show");
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", function (e) {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove("show");
      }
    });
  }

  function highlightItem(items) {
    items.forEach((el, i) => el.classList.toggle("ac-active", i === acIndex));
    if (items[acIndex]) {
      items[acIndex].scrollIntoView({ block: "nearest" });
    }
  }

  function fetchSuggestions(query) {
    fetch("/play/api/catalogue/autocomplete?q=" + encodeURIComponent(query))
      .then((r) => r.json())
      .then((results) => {
        acIndex = -1;
        if (!results.length) {
          dropdown.classList.remove("show");
          dropdown.innerHTML = "";
          return;
        }
        dropdown.innerHTML = results
          .map(
            (r) =>
              `<div class="ac-item" data-value="${escapeHtml(r.value)}" data-type="${r.type}">
                <span class="ac-label">${escapeHtml(r.label)}</span>
                <span class="ac-type">${r.type}</span>
              </div>`
          )
          .join("");
        dropdown.classList.add("show");

        // Click handler for suggestions
        dropdown.querySelectorAll(".ac-item").forEach((el) => {
          el.addEventListener("click", function () {
            const val = this.dataset.value;
            const type = this.dataset.type;
            // Apply as a filter or search
            if (type === "family" || type === "genus" || type === "country" || type === "continent") {
              const form = document.getElementById("catalogueForm");
              // Set the corresponding select value if available
              const sel = form.querySelector(`select[name="${type}"]`);
              if (sel) {
                sel.value = val;
              }
              searchInput.value = "";
              form.submit();
            } else {
              // species or location → text search
              searchInput.value = val;
              dropdown.classList.remove("show");
              document.getElementById("catalogueForm").submit();
            }
          });
        });
      })
      .catch(() => {
        dropdown.classList.remove("show");
      });
  }

  function escapeHtml(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  // ── Gallery Slider (species detail page) ────────────────────────────────
  const slider = document.getElementById("gallerySlider");
  const leftBtn = document.getElementById("sliderLeft");
  const rightBtn = document.getElementById("sliderRight");

  if (slider) {
    const scrollAmount = 260;

    if (leftBtn) {
      leftBtn.addEventListener("click", () => {
        slider.scrollBy({ left: -scrollAmount, behavior: "smooth" });
      });
    }
    if (rightBtn) {
      rightBtn.addEventListener("click", () => {
        slider.scrollBy({ left: scrollAmount, behavior: "smooth" });
      });
    }

    // Touch / drag scroll support
    let isDown = false;
    let startX, scrollLeft;

    slider.addEventListener("mousedown", (e) => {
      isDown = true;
      slider.style.cursor = "grabbing";
      startX = e.pageX - slider.offsetLeft;
      scrollLeft = slider.scrollLeft;
    });
    slider.addEventListener("mouseleave", () => {
      isDown = false;
      slider.style.cursor = "";
    });
    slider.addEventListener("mouseup", () => {
      isDown = false;
      slider.style.cursor = "";
    });
    slider.addEventListener("mousemove", (e) => {
      if (!isDown) return;
      e.preventDefault();
      const x = e.pageX - slider.offsetLeft;
      slider.scrollLeft = scrollLeft - (x - startX);
    });
  }

  // ── Lightbox (species detail page) ──────────────────────────────────────
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxCaption = document.getElementById("lightboxCaption");
  const lightboxClose = document.getElementById("lightboxClose");
  const lightboxPrev = document.getElementById("lightboxPrev");
  const lightboxNext = document.getElementById("lightboxNext");

  let currentLightboxIndex = 0;
  const images = window.__speciesImages || [];

  function openLightbox(index) {
    if (!images.length || !lightbox) return;
    currentLightboxIndex = index;
    const img = images[index];
    lightboxImg.src = img.image_url;
    lightboxImg.alt = img.species || "";
    const parts = [img.city, img.country, img.eventDate ? img.eventDate.slice(0, 10) : ""].filter(Boolean);
    lightboxCaption.textContent = parts.join(" · ");
    lightbox.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove("open");
    document.body.style.overflow = "";
  }

  if (lightbox) {
    // Open from slider card click
    document.querySelectorAll(".slider-card").forEach((card) => {
      card.addEventListener("click", function () {
        openLightbox(parseInt(this.dataset.index, 10));
      });
    });

    lightboxClose.addEventListener("click", closeLightbox);

    lightboxPrev.addEventListener("click", () => {
      openLightbox((currentLightboxIndex - 1 + images.length) % images.length);
    });

    lightboxNext.addEventListener("click", () => {
      openLightbox((currentLightboxIndex + 1) % images.length);
    });

    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) closeLightbox();
    });

    document.addEventListener("keydown", (e) => {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") closeLightbox();
      if (e.key === "ArrowLeft")
        openLightbox((currentLightboxIndex - 1 + images.length) % images.length);
      if (e.key === "ArrowRight")
        openLightbox((currentLightboxIndex + 1) % images.length);
    });
  }
})();
