/* ═══════════════════════════════════════════════════════════════════════════
   catalogue.js — Autocomplete, gallery slider, lightbox, infinite scroll, lazy load
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ── Register Service Worker for caching & offline support ──────────────
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/js/sw.js").catch(() => {
      // Silently fail if SW registration fails
    });
  }

  // ── Image Lazy Loading with Intersection Observer ────────────────────
  function initLazyLoading() {
    const images = document.querySelectorAll('img[loading="lazy"]');

    if ("IntersectionObserver" in window) {
      const imageObserver = new IntersectionObserver(
        (entries, observer) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = entry.target;
              // Load native srcset/src attributes
              if (img.dataset.src) {
                img.src = img.dataset.src;
              }
              if (img.dataset.srcset) {
                img.srcset = img.dataset.srcset;
              }
              img.removeAttribute("data-src");
              img.removeAttribute("data-srcset");
              observer.unobserve(img);
            }
          });
        },
        { rootMargin: "50px 0px", threshold: 0.01 },
      );

      images.forEach((img) => imageObserver.observe(img));
    }
  }

  // Initialize lazy loading on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLazyLoading);
  } else {
    initLazyLoading();
  }

  // ── Dynamic Filter Management ──────────────────────────────────────────
  const catalogueForm = document.getElementById("catalogueForm");
  const filterSelects = document.querySelectorAll(".filter-select");
  const searchInput = document.getElementById("catalogueSearch");
  const clearFiltersBtn = document.getElementById("clearFiltersBtn");
  const subtitleEl = document.getElementById("catalogueSubtitle");
  const countEl = document.getElementById("catalogueCount");

  const apiPageUrl = catalogueForm?.dataset.apiPageUrl || "/catalogue/api/page";
  const apiFiltersUrl =
    catalogueForm?.dataset.apiFiltersUrl || "/catalogue/api/filters";
  const apiAutocompleteUrl =
    catalogueForm?.dataset.apiAutocompleteUrl || "/catalogue/api/autocomplete";
  const speciesBaseUrl =
    catalogueForm?.dataset.speciesBaseUrl || "/catalogue/species/__SPECIES__";

  let filterDebounceTimer = null;

  function getCurrentFilters() {
    return {
      q: searchInput.value.trim(),
      per_page: document.getElementById("perPageSelect")?.value || "24",
      family: document.getElementById("filterFamily")?.value || "",
      genus: document.getElementById("filterGenus")?.value || "",
      continent: document.getElementById("filterContinent")?.value || "",
      country: document.getElementById("filterCountry")?.value || "",
    };
  }

  function buildQueryString(filters) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val) params.set(key, val);
    });
    return params.toString();
  }

  function updateURL(filters) {
    const query = buildQueryString(filters);
    const newURL = query ? `/catalogue?${query}` : "/catalogue";
    window.history.replaceState({ filters }, "", newURL);
  }

  function updateSubtitleRange(endCount, totalSpecies) {
    if (countEl) {
      countEl.textContent = `1-${Math.max(0, endCount)}`;
    }
    if (subtitleEl && totalSpecies != null) {
      subtitleEl.dataset.totalSpecies = String(totalSpecies);
      subtitleEl.dataset.end = String(endCount);
    }
  }

  async function fetchDynamicFilters(filters) {
    try {
      const query = buildQueryString(filters);
      const response = await fetch(`${apiFiltersUrl}?${query}`);
      if (!response.ok) throw new Error("Failed to fetch filters");

      const data = await response.json();

      // Update each filter select with new options
      const filterMap = {
        family_options: "filterFamily",
        genus_options: "filterGenus",
        continent_options: "filterContinent",
        country_options: "filterCountry",
      };

      Object.entries(filterMap).forEach(([dataKey, selectId]) => {
        const select = document.getElementById(selectId);
        if (!select) return;

        const currentValue = select.value;
        const newOptions = data[dataKey] || [];

        // Get the filter type label for the default option
        const filterType = dataKey.replace("_options", "");
        const filterLabel =
          filterType.charAt(0).toUpperCase() + filterType.slice(1);
        const pluralMap = {
          family: "Families",
          genus: "Genera",
          continent: "Continents",
          country: "Countries",
        };
        const defaultLabel = pluralMap[filterType] || filterLabel + "s";

        // Rebuild select options
        select.innerHTML = `<option value="">All ${defaultLabel}</option>`;
        newOptions.forEach((opt) => {
          const option = document.createElement("option");
          option.value = opt;
          option.textContent = opt;
          if (opt === currentValue) option.selected = true;
          select.appendChild(option);
        });
      });
    } catch (error) {
      console.error("Error fetching dynamic filters:", error);
    }
  }

  async function loadCatalogueWithFilters(filters, page = 1) {
    try {
      filters.q = filters.q || "";
      const query = buildQueryString({ ...filters, page });
      const response = await fetch(`${apiPageUrl}?${query}`);

      if (!response.ok) throw new Error("Failed to fetch catalogue");

      const data = await response.json();

      // Clear grid if first page
      if (page === 1) {
        const grid = document.getElementById("catalogueGrid");
        grid.innerHTML = "";

        if (!data.species_list || !data.species_list.length) {
          grid.innerHTML =
            '<div class="catalogue-empty"><p>No species found matching your filters.</p></div>';
          updateSubtitleRange(0, data.total_species || 0);
          return data;
        }

        updateSubtitleRange(
          data.species_list.length,
          data.total_species || data.species_list.length,
        );

        // Add species cards
        data.species_list.forEach((item) => {
          const card = document.createElement("a");
          card.href = speciesBaseUrl.replace(
            "__SPECIES__",
            encodeURIComponent(item.species),
          );
          card.className = "species-card";
          card.innerHTML = `
            <div class="card-image-wrap">
              <img
                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'%3E%3Crect fill='%23f0f0f0' width='400' height='300'/%3E%3C/svg%3E"
                data-src="${escapeHtml(item.image_url)}"
                alt="${escapeHtml(item.species)}"
                loading="lazy"
              />
              <span class="card-count-badge">${item.observation_count}</span>
            </div>
            <div class="card-body">
              <h3 class="card-species">${escapeHtml(item.species)}</h3>
              <p class="card-taxonomy">${escapeHtml(item.family)} · ${escapeHtml(item.genus)}</p>
              <div class="card-meta">
                <span class="card-location" title="${escapeHtml(item.location)}">📍 ${escapeHtml(item.location)}</span>
                <span class="card-date">📅 ${escapeHtml(item.date_display)}</span>
              </div>
            </div>
          `;
          grid.appendChild(card);
        });

        // Reinitialize lazy loading
        initLazyLoading();
      }

      return data;
    } catch (error) {
      console.error("Error loading catalogue:", error);
    }
  }

  function handleFilterChange() {
    clearTimeout(filterDebounceTimer);

    filterDebounceTimer = setTimeout(async () => {
      const filters = getCurrentFilters();
      updateURL(filters);

      // Load new catalogue results
      await loadCatalogueWithFilters(filters, 1);

      // Update available filters dynamically
      await fetchDynamicFilters(filters);

      // Update clear button visibility
      updateClearButtonVisibility();
    }, 300);
  }

  function updateClearButtonVisibility() {
    const filters = getCurrentFilters();
    const hasFilters =
      filters.q ||
      filters.family ||
      filters.genus ||
      filters.continent ||
      filters.country;

    if (clearFiltersBtn) {
      clearFiltersBtn.style.display = hasFilters ? "inline-block" : "none";
    }
  }

  // Attach change listeners to filter selects
  filterSelects.forEach((select) => {
    select.addEventListener("change", handleFilterChange);
  });

  // Search input changes (only on catalogue listing page)
  if (searchInput) {
    searchInput.addEventListener("input", handleFilterChange);
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(filterDebounceTimer);
        handleFilterChange();
      }
    });
  }

  // Clear filters button
  if (clearFiltersBtn && searchInput) {
    clearFiltersBtn.addEventListener("click", (e) => {
      e.preventDefault();
      searchInput.value = "";
      const perPageSelect = document.getElementById("perPageSelect");
      if (perPageSelect) perPageSelect.value = "24";
      document.getElementById("filterFamily").value = "";
      document.getElementById("filterGenus").value = "";
      document.getElementById("filterContinent").value = "";
      document.getElementById("filterCountry").value = "";

      const filters = {
        q: "",
        per_page: "24",
        family: "",
        genus: "",
        continent: "",
        country: "",
      };
      updateURL(filters);
      loadCatalogueWithFilters(filters, 1);
      fetchDynamicFilters(filters);
      updateClearButtonVisibility();
    });
  }

  // Prevent form submission
  if (catalogueForm) {
    catalogueForm.addEventListener("submit", (e) => {
      e.preventDefault();
    });
  }

  // ── Autocomplete ────────────────────────────────────────────────────────
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
    fetch(`${apiAutocompleteUrl}?q=${encodeURIComponent(query)}`)
      .then((r) => r.json())
      .then((results) => {
        acIndex = -1;
        if (!results.length) {
          dropdown.classList.remove("show");
          dropdown.innerHTML = "";
          return;
        }

        // Group results by type for better visual organization
        const grouped = {};
        results.forEach((r) => {
          if (!grouped[r.type]) grouped[r.type] = [];
          grouped[r.type].push(r);
        });

        // Build HTML with type grouping
        let html = "";
        const typeOrder = [
          "species",
          "genus",
          "family",
          "country",
          "continent",
        ];
        const typeLabels = {
          species: "Species",
          genus: "Genus",
          family: "Family",
          country: "Country",
          continent: "Continent",
        };

        typeOrder.forEach((type) => {
          if (grouped[type] && grouped[type].length > 0) {
            // Only show section header if we have multiple types
            const showHeader = Object.keys(grouped).length > 1;
            if (showHeader) {
              html += `<div class="ac-section-header">${typeLabels[type]}</div>`;
            }
            grouped[type].forEach((r) => {
              html += `<div class="ac-item" data-value="${escapeHtml(r.value)}" data-type="${r.type}">
                <span class="ac-label">${escapeHtml(r.label)}</span>
                <span class="ac-type">${r.type}</span>
              </div>`;
            });
          }
        });

        dropdown.innerHTML = html;
        dropdown.classList.add("show");

        // Click handler for suggestions
        dropdown.querySelectorAll(".ac-item").forEach((el) => {
          el.addEventListener("click", function () {
            const val = this.dataset.value;
            const type = this.dataset.type;

            // Apply as a specific filter when possible
            if (
              type === "family" ||
              type === "genus" ||
              type === "country" ||
              type === "continent"
            ) {
              // Set the specific filter
              const filterId = `filter${type.charAt(0).toUpperCase() + type.slice(1)}`;
              const filterEl = document.getElementById(filterId);
              if (filterEl) {
                filterEl.value = val;
                searchInput.value = "";
                dropdown.classList.remove("show");
                handleFilterChange();
              }
            } else {
              // For species or other types, use text search
              searchInput.value = val;
              dropdown.classList.remove("show");
              handleFilterChange();
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

  // ── Enhanced Gallery System ─────────────────────────────────────────────

  // Initialize gallery when DOM is ready
  function initGallery() {
    // Gallery state (exposed globally for filtering integration)
    window.galleryState = {
      currentView: "carousel", // 'carousel' or 'grid'
      currentLightboxIndex: 0,
      images: window.__speciesImages || [],
      allImages: window.__allImages || [],
    };

    const galleryState = window.galleryState;

    // DOM elements
    const viewToggle = document.getElementById("viewToggle");
    const carouselView = document.getElementById("carouselView");
    const gridView = document.getElementById("gridView");
    const slider = document.getElementById("gallerySlider");
    const leftBtn = document.getElementById("sliderLeft");
    const rightBtn = document.getElementById("sliderRight");

    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightboxImg");
    const lightboxCaption = document.getElementById("lightboxCaption");
    const lightboxCounter = document.getElementById("lightboxCounter");
    const lightboxClose = document.getElementById("lightboxClose");
    const lightboxPrev = document.getElementById("lightboxPrev");
    const lightboxNext = document.getElementById("lightboxNext");
    const lightboxThumbnails = document.getElementById("lightboxThumbnails");
    const lightboxLoader = document.getElementById("lightboxLoader");

    // ── View Toggle ──────────────────────────────────────────────────────────
    function toggleView() {
      if (!viewToggle || !carouselView || !gridView) return;

      const iconGrid = viewToggle.querySelector(".icon-grid");
      const iconCarousel = viewToggle.querySelector(".icon-carousel");

      if (galleryState.currentView === "carousel") {
        galleryState.currentView = "grid";
        carouselView.classList.remove("active");
        gridView.classList.add("active");
        if (iconGrid) iconGrid.style.display = "none";
        if (iconCarousel) iconCarousel.style.display = "block";
      } else {
        galleryState.currentView = "carousel";
        carouselView.classList.add("active");
        gridView.classList.remove("active");
        if (iconGrid) iconGrid.style.display = "block";
        if (iconCarousel) iconCarousel.style.display = "none";
      }
    }

    if (viewToggle) {
      viewToggle.addEventListener("click", toggleView);
    }

    // ── Carousel Navigation ──────────────────────────────────────────────────
    if (slider && leftBtn && rightBtn) {
      // Scale scroll amount proportionally (300px at 1905px viewport)
      const scrollAmount = Math.max(200, Math.round(window.innerWidth * 0.157));

      leftBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        slider.scrollBy({ left: -scrollAmount, behavior: "smooth" });
      });

      rightBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        slider.scrollBy({ left: scrollAmount, behavior: "smooth" });
      });

      // Drag scroll support
      let isDragging = false;
      let startX = 0;
      let scrollLeft = 0;
      let hasMoved = false;

      slider.addEventListener("mousedown", (e) => {
        const isCard = e.target.closest(".slider-card");
        if (!isCard) return;

        isDragging = true;
        hasMoved = false;
        startX = e.pageX - slider.offsetLeft;
        scrollLeft = slider.scrollLeft;
        slider.style.cursor = "grabbing";
        slider.style.userSelect = "none";
      });

      slider.addEventListener("mouseleave", () => {
        isDragging = false;
        slider.style.cursor = "";
        slider.style.userSelect = "";
      });

      slider.addEventListener("mouseup", () => {
        isDragging = false;
        slider.style.cursor = "";
        slider.style.userSelect = "";
        setTimeout(() => {
          hasMoved = false;
        }, 10);
      });

      slider.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        e.preventDefault();
        const x = e.pageX - slider.offsetLeft;
        const walk = x - startX;

        if (Math.abs(walk) > 3) {
          hasMoved = true;
          slider.scrollLeft = scrollLeft - walk;
        }
      });

      // Click to open lightbox
      slider.addEventListener("click", (e) => {
        if (hasMoved) return;

        const card = e.target.closest(".slider-card");
        if (!card) return;

        const index = parseInt(card.getAttribute("data-index"), 10);
        if (!isNaN(index)) {
          openLightbox(index);
        }
      });
    }

    // ── Grid View Click Handler ─────────────────────────────────────────────
    if (gridView) {
      gridView.addEventListener("click", (e) => {
        const gridItem = e.target.closest(".grid-item");
        if (!gridItem) return;

        const index = parseInt(gridItem.getAttribute("data-index"), 10);
        if (!isNaN(index)) {
          openLightbox(index);
        }
      });
    }

    // ── Lightbox Functions ───────────────────────────────────────────────────
    function openLightbox(index) {
      const images = galleryState.images;
      if (!images.length || !lightbox) return;

      galleryState.currentLightboxIndex = index;
      updateLightboxContent();

      lightbox.classList.add("open");
      document.body.style.overflow = "hidden";

      // Generate thumbnails if not already done
      if (lightboxThumbnails && lightboxThumbnails.children.length === 0) {
        generateThumbnails();
      }
      updateActiveThumbnail();
    }

    function closeLightbox() {
      if (!lightbox) return;
      lightbox.classList.remove("open");
      document.body.style.overflow = "";
    }

    function updateLightboxContent() {
      const images = galleryState.images;
      const index = galleryState.currentLightboxIndex;
      const img = images[index];

      if (!img || !lightboxImg) return;

      // Show loader
      if (lightboxLoader) {
        lightboxLoader.classList.add("loading");
      }

      // Update image
      const tempImg = new Image();
      tempImg.onload = () => {
        lightboxImg.src = img.image_url;
        lightboxImg.alt = img.species || "";
        if (lightboxLoader) {
          lightboxLoader.classList.remove("loading");
        }
      };
      tempImg.onerror = () => {
        if (lightboxLoader) {
          lightboxLoader.classList.remove("loading");
        }
      };
      tempImg.src = img.image_url;

      // Update caption
      if (lightboxCaption) {
        const parts = [
          img.location_str ||
            [img.city, img.country].filter(Boolean).join(", "),
          img.eventDate ? img.eventDate.slice(0, 10) : "",
        ].filter(Boolean);
        lightboxCaption.textContent = parts.join(" · ");
      }

      // Update counter
      if (lightboxCounter) {
        lightboxCounter.textContent = `${index + 1} / ${images.length}`;
      }

      updateActiveThumbnail();
    }

    function generateThumbnails() {
      if (!lightboxThumbnails) return;

      const images = galleryState.images;
      lightboxThumbnails.innerHTML = "";

      images.forEach((img, idx) => {
        const thumb = document.createElement("div");
        thumb.className = "thumbnail-item";
        thumb.dataset.index = idx;

        const thumbImg = document.createElement("img");
        thumbImg.src = img.image_url;
        thumbImg.alt = `Thumbnail ${idx + 1}`;
        thumbImg.loading = "lazy";

        thumb.appendChild(thumbImg);
        thumb.addEventListener("click", () => {
          galleryState.currentLightboxIndex = idx;
          updateLightboxContent();
        });

        lightboxThumbnails.appendChild(thumb);
      });
    }

    function updateActiveThumbnail() {
      if (!lightboxThumbnails) return;

      const thumbnails = lightboxThumbnails.querySelectorAll(".thumbnail-item");
      thumbnails.forEach((thumb, idx) => {
        if (idx === galleryState.currentLightboxIndex) {
          thumb.classList.add("active");
          thumb.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "center",
          });
        } else {
          thumb.classList.remove("active");
        }
      });
    }

    function navigateLightbox(direction) {
      const images = galleryState.images;
      if (!images.length) return;

      if (direction === "prev") {
        galleryState.currentLightboxIndex =
          (galleryState.currentLightboxIndex - 1 + images.length) %
          images.length;
      } else {
        galleryState.currentLightboxIndex =
          (galleryState.currentLightboxIndex + 1) % images.length;
      }

      updateLightboxContent();
    }

    // ── Lightbox Event Handlers ──────────────────────────────────────────────
    if (lightbox) {
      if (lightboxClose) {
        lightboxClose.addEventListener("click", closeLightbox);
      }

      if (lightboxPrev) {
        lightboxPrev.addEventListener("click", () => navigateLightbox("prev"));
      }

      if (lightboxNext) {
        lightboxNext.addEventListener("click", () => navigateLightbox("next"));
      }

      // Close on background click
      lightbox.addEventListener("click", (e) => {
        if (e.target === lightbox) closeLightbox();
      });

      // Keyboard navigation
      document.addEventListener("keydown", (e) => {
        if (!lightbox.classList.contains("open")) return;

        if (e.key === "Escape") {
          closeLightbox();
        } else if (e.key === "ArrowLeft") {
          navigateLightbox("prev");
        } else if (e.key === "ArrowRight") {
          navigateLightbox("next");
        }
      });

      // Touch swipe support for mobile
      let touchStartX = 0;
      let touchEndX = 0;

      lightbox.addEventListener(
        "touchstart",
        (e) => {
          touchStartX = e.changedTouches[0].screenX;
        },
        { passive: true },
      );

      lightbox.addEventListener(
        "touchend",
        (e) => {
          touchEndX = e.changedTouches[0].screenX;
          handleSwipe();
        },
        { passive: true },
      );

      function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;

        if (Math.abs(diff) > swipeThreshold) {
          if (diff > 0) {
            navigateLightbox("next");
          } else {
            navigateLightbox("prev");
          }
        }
      }
    }

    // ── Update gallery state when filtering ─────────────────────────────────
    const originalUpdateSpeciesImages = window.updateSpeciesImages;
    window.updateSpeciesImages = function (filteredImages) {
      galleryState.images = filteredImages || galleryState.allImages;
      if (originalUpdateSpeciesImages) {
        originalUpdateSpeciesImages(filteredImages);
      }
    };
  }

  // Initialize gallery when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGallery);
  } else {
    initGallery();
  }
})();

// ── Infinite Scroll Pagination ──────────────────────────────────────────────
(function () {
  "use strict";

  const grid = document.getElementById("catalogueGrid");
  const paginationNav = document.querySelector(".catalogue-pagination");
  const catalogueForm = document.getElementById("catalogueForm");

  const apiPageUrl = catalogueForm?.dataset.apiPageUrl || "/catalogue/api/page";
  const speciesBaseUrl =
    catalogueForm?.dataset.speciesBaseUrl || "/catalogue/species/__SPECIES__";

  if (!grid || !paginationNav) return;

  let isLoading = false;
  let currentPage = Math.max(
    1,
    parseInt(
      new URLSearchParams(window.location.search).get("page") || "1",
      10,
    ),
  );
  let totalPages = parseInt(paginationNav.dataset.totalPages || "1", 10);
  let hasNextPage = currentPage < totalPages;

  // Get current filter parameters from URL
  const urlParams = new URLSearchParams(window.location.search);
  const subtitleEl = document.getElementById("catalogueSubtitle");
  const countEl = document.getElementById("catalogueCount");
  const filters = {
    q: urlParams.get("q") || "",
    per_page: urlParams.get("per_page") || "24",
    family: urlParams.get("family") || "",
    genus: urlParams.get("genus") || "",
    continent: urlParams.get("continent") || "",
    country: urlParams.get("country") || "",
  };

  let currentLoadedCount = parseInt(subtitleEl?.dataset.end || "0", 10);
  const totalSpecies = parseInt(subtitleEl?.dataset.totalSpecies || "0", 10);

  function updateInfiniteCount(addedCount) {
    currentLoadedCount += addedCount;
    if (countEl && totalSpecies > 0) {
      countEl.textContent = `1-${Math.min(currentLoadedCount, totalSpecies)}`;
    }
  }

  // Hide pagination nav, enable infinite scroll instead
  paginationNav.style.display = "none";

  // Create sentinel element for intersection observer
  const sentinel = document.createElement("div");
  sentinel.className = "infinite-scroll-sentinel";
  sentinel.setAttribute("aria-hidden", "true");
  grid.parentElement.appendChild(sentinel);

  // Add loading indicator
  const loadingIndicator = document.createElement("div");
  loadingIndicator.className = "infinite-scroll-loading";
  loadingIndicator.innerHTML = "<p>Loading more species...</p>";
  grid.parentElement.appendChild(loadingIndicator);

  function buildQueryString(page) {
    const params = new URLSearchParams();
    params.set("page", page);
    Object.entries(filters).forEach(([key, val]) => {
      if (val) params.set(key, val);
    });
    return params.toString();
  }

  function loadNextPage() {
    if (isLoading || !hasNextPage) return;

    isLoading = true;
    loadingIndicator.style.display = "block";

    const nextPage = currentPage + 1;
    const query = buildQueryString(nextPage);

    fetch(`${apiPageUrl}?${query}`)
      .then((response) => {
        if (!response.ok) throw new Error("Network response failed");
        return response.json();
      })
      .then((data) => {
        if (!data.species_list || !data.species_list.length) {
          hasNextPage = false;
          loadingIndicator.style.display = "none";
          isLoading = false;
          return;
        }

        // Append new cards to grid
        data.species_list.forEach((item) => {
          const card = createSpeciesCard(item);
          grid.appendChild(card);
        });

        updateInfiniteCount(data.species_list.length);

        // Re-initialize lazy loading for new images
        if (window.IntersectionObserver) {
          const newImages = grid.querySelectorAll("img[data-src]");
          const imageObserver = new IntersectionObserver(
            (entries, observer) => {
              entries.forEach((entry) => {
                if (entry.isIntersecting) {
                  const img = entry.target;
                  if (img.dataset.src) {
                    img.src = img.dataset.src;
                  }
                  if (img.dataset.srcset) {
                    img.srcset = img.dataset.srcset;
                  }
                  img.removeAttribute("data-src");
                  img.removeAttribute("data-srcset");
                  observer.unobserve(img);
                }
              });
            },
            { rootMargin: "50px 0px", threshold: 0.01 },
          );

          newImages.forEach((img) => imageObserver.observe(img));
        }

        currentPage = nextPage;
        hasNextPage = nextPage < data.total_pages;
        loadingIndicator.style.display = "none";
        isLoading = false;
      })
      .catch((error) => {
        console.error("Error loading next page:", error);
        loadingIndicator.innerHTML =
          '<p>Failed to load more. <a href="#">Retry</a></p>';
        isLoading = false;
      });
  }

  function createSpeciesCard(item) {
    const card = document.createElement("a");
    card.href = speciesBaseUrl.replace(
      "__SPECIES__",
      encodeURIComponent(item.species),
    );
    card.className = "species-card";
    card.innerHTML = `
      <div class="card-image-wrap">
        <img
          src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'%3E%3Crect fill='%23f0f0f0' width='400' height='300'/%3E%3C/svg%3E"
          data-src="${escapeHtml(item.image_url)}"
          alt="${escapeHtml(item.species)}"
          loading="lazy"
          onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 400 300%22%3E%3Crect fill=%22%23111%22 width=%22400%22 height=%22300%22/%3E%3Ctext x=%22200%22 y=%22150%22 fill=%22%23555%22 text-anchor=%22middle%22 font-size=%2218%22%3ENo image%3C/text%3E%3C/svg%3E'"
        />
        <span class="card-count-badge">${item.observation_count}</span>
      </div>
      <div class="card-body">
        <h3 class="card-species">${escapeHtml(item.species)}</h3>
        <p class="card-taxonomy">${escapeHtml(item.family)} · ${escapeHtml(item.genus)}</p>
        <div class="card-meta">
          <span class="card-location" title="${escapeHtml(item.location)}">📍 ${escapeHtml(item.location)}</span>
          <span class="card-date">📅 ${escapeHtml(item.date_display)}</span>
        </div>
      </div>
    `;
    return card;
  }

  function escapeHtml(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  // Intersection Observer for infinite scroll
  if ("IntersectionObserver" in window) {
    const scrollObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadNextPage();
          }
        });
      },
      { rootMargin: "200px" },
    );

    scrollObserver.observe(sentinel);
  }
})();
