(function () {
  "use strict";

  const filterForm = document.querySelector(".catalogue-filters");
  const submitBtn = filterForm?.querySelector(".catalogue-submit");
  const resetBtn = filterForm?.querySelector(".catalogue-reset");

  if (!filterForm || !submitBtn || !resetBtn) return;

  const initialMap = Object.fromEntries(new FormData(filterForm));
  const defaultMap = {
    q: "",
    family: "",
    genus: "",
    country_code: "",
    continent_code: "",
    sort: filterForm.dataset.defaultSort || "popular",
    per_page: filterForm.dataset.defaultPerPage || "25",
  };

  function currentMap() {
    return Object.fromEntries(new FormData(filterForm));
  }

  function mapEquals(left, right) {
    const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
    for (const key of keys) {
      if ((left[key] ?? "") !== (right[key] ?? "")) return false;
    }
    return true;
  }

  function updateButtons() {
    const current = currentMap();
    const hasChanges = !mapEquals(current, initialMap);
    const isDefault = mapEquals(current, defaultMap);

    submitBtn.classList.toggle("has-changes", hasChanges);
    submitBtn.disabled = !hasChanges;
    submitBtn.setAttribute("aria-disabled", String(!hasChanges));

    resetBtn.classList.toggle("is-disabled", isDefault);
    resetBtn.setAttribute("aria-disabled", String(isDefault));
    if (isDefault) {
      resetBtn.setAttribute("tabindex", "-1");
    } else {
      resetBtn.removeAttribute("tabindex");
    }
  }

  filterForm.addEventListener("input", updateButtons);
  filterForm.addEventListener("change", updateButtons);

  filterForm.addEventListener("submit", (event) => {
    if (mapEquals(currentMap(), initialMap)) {
      event.preventDefault();
    }
  });

  resetBtn.addEventListener("click", (event) => {
    if (resetBtn.classList.contains("is-disabled")) {
      event.preventDefault();
    }
  });

  updateButtons();
})();
