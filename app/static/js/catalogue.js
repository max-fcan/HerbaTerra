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

  let filterDebounceTimer = null;

  function getCurrentFilters() {
    return {
      q: searchInput.value.trim(),
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
    const newURL = query ? `/play/catalogue?${query}` : "/play/catalogue";
    window.history.replaceState({ filters }, "", newURL);
  }

  async function fetchDynamicFilters(filters) {
    try {
      const query = buildQueryString(filters);
      const response = await fetch(`/play/catalogue/api/filters?${query}`);
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
      const response = await fetch(`/play/catalogue/api/page?${query}`);

      if (!response.ok) throw new Error("Failed to fetch catalogue");

      const data = await response.json();

      // Clear grid if first page
      if (page === 1) {
        const grid = document.getElementById("catalogueGrid");
        grid.innerHTML = "";

        if (!data.species_list || !data.species_list.length) {
          grid.innerHTML =
            '<div class="catalogue-empty"><p>No species found matching your filters.</p></div>';
          return data;
        }

        // Add species cards
        data.species_list.forEach((item) => {
          const card = document.createElement("a");
          card.href = `/play/catalogue/species/${encodeURIComponent(item.species)}`;
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

  // Search input changes
  searchInput.addEventListener("input", handleFilterChange);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      clearTimeout(filterDebounceTimer);
      handleFilterChange();
    }
  });

  // Clear filters button
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", (e) => {
      e.preventDefault();
      searchInput.value = "";
      document.getElementById("filterFamily").value = "";
      document.getElementById("filterGenus").value = "";
      document.getElementById("filterContinent").value = "";
      document.getElementById("filterCountry").value = "";

      const filters = {
        q: "",
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
  catalogueForm.addEventListener("submit", (e) => {
    e.preventDefault();
  });

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
    fetch("/play/api/catalogue/autocomplete?q=" + encodeURIComponent(query))
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
    const parts = [
      img.city,
      img.country,
      img.eventDate ? img.eventDate.slice(0, 10) : "",
    ].filter(Boolean);
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
        openLightbox(
          (currentLightboxIndex - 1 + images.length) % images.length,
        );
      if (e.key === "ArrowRight")
        openLightbox((currentLightboxIndex + 1) % images.length);
    });
  }
})();

// ── Infinite Scroll Pagination ──────────────────────────────────────────────
(function () {
  "use strict";

  const grid = document.getElementById("catalogueGrid");
  const paginationNav = document.querySelector(".catalogue-pagination");

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
  const filters = {
    q: urlParams.get("q") || "",
    family: urlParams.get("family") || "",
    genus: urlParams.get("genus") || "",
    continent: urlParams.get("continent") || "",
    country: urlParams.get("country") || "",
  };

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

    fetch(`/play/catalogue/api/page?${query}`)
      .then((response) => {
        if (!response.ok) throw new Error("Network response failed");
        return response.json();
      })
      .then((data) => {
        if (!data.species_list || !data.species_list.length) {
          hasNextPage = false;
          loadingIndicator.style.display = "none";
          return;
        }

        // Append new cards to grid
        data.species_list.forEach((item) => {
          const card = createSpeciesCard(item);
          grid.appendChild(card);
        });

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
    card.href = `/play/catalogue/species/${encodeURIComponent(item.species)}`;
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
