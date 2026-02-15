/* game.js — plant guessing game logic (game/play.html) */
(function () {
  "use strict";

  console.log("[Game] Script loaded - TIMESTAMP:", new Date().toISOString());

  // Read configuration from the script tag's data attributes
  var scriptTag = document.currentScript;
  if (!scriptTag) {
    console.error("[Game] Error: document.currentScript is null");
    alert("ERROR: document.currentScript is null");
    return;
  }

  var nextChallengeUrl = scriptTag.getAttribute("data-next-url");
  var speciesBase = scriptTag.getAttribute("data-species-base"); // contains __SPECIES__ placeholder

  // Read challenge data from a dedicated JSON script block (safe from HTML attribute escaping issues)
  var challengeDataEl = document.getElementById("challenge-data");
  var challengeJSON = challengeDataEl ? challengeDataEl.textContent : null;

  console.log("[Game] Script tag data attributes:", {
    nextChallengeUrl: nextChallengeUrl,
    speciesBase: speciesBase,
    challengeJSON: challengeJSON ? "present" : "missing",
  });

  if (!challengeJSON) {
    console.error("[Game] Error: challenge-data script block is missing");
    return;
  }

  var currentChallenge;
  try {
    currentChallenge = JSON.parse(challengeJSON);
  } catch (e) {
    console.error("[Game] Error parsing challenge JSON:", e);
    return;
  }

  function init() {
    console.log("[Game] ========== INIT CALLED ==========");
    console.log("[Game] Initializing game.js");
    console.log("[Game] Challenge data:", currentChallenge);
    console.log("[Game] document.readyState:", document.readyState);

    var optionsList = document.getElementById("options-list");
    var nextButton = document.getElementById("next-button");
    var challengeImage = document.getElementById("challenge-image");
    var imageContainer = document.getElementById("image-container");
    var speciesInfoCard = document.getElementById("species-info-card");
    var imageAttribution = document.getElementById("image-attribution");
    var answered = false;
    var loadingNext = false;
    var defaultButtonText = "Next Challenge →";

    console.log("[Game] Found elements:", {
      optionsList: !!optionsList,
      nextButton: !!nextButton,
      challengeImage: !!challengeImage,
      imageContainer: !!imageContainer,
    });

    if (!optionsList) {
      console.error("[Game] CRITICAL: options-list element not found!");
      alert("ERROR: options-list element not found!");
      return;
    }

    function setLoadingState(isLoading) {
      loadingNext = isLoading;
      nextButton.disabled = isLoading;
      imageContainer.classList.toggle("is-loading", isLoading);
      nextButton.classList.toggle("is-loading", isLoading);
      nextButton.textContent = isLoading ? "Loading" : defaultButtonText;
    }

    function bindOptionClickHandlers() {
      var options = document.querySelectorAll(".option-card");
      console.log(
        "[Game] Binding click handlers to",
        options.length,
        "option cards",
      );

      if (options.length === 0) {
        console.error("[Game] ERROR: No option cards found!");
        alert("ERROR: No option cards found in DOM!");
        return;
      }

      options.forEach(function (card, index) {
        console.log("[Game] Attaching listener to card", index, card);

        // Test if the element is clickable
        var rect = card.getBoundingClientRect();
        console.log("[Game] Card", index, "position:", rect);

        card.addEventListener("click", function (event) {
          console.log("[Game] ==> CLICK EVENT FIRED for card:", index);
          console.log("[Game] Event:", event);
          console.log("[Game] Target:", event.target);
          console.log("[Game] CurrentTarget:", event.currentTarget);
          if (answered) {
            console.log("[Game] Already answered, ignoring click");
            return;
          }
          answered = true;

          var solutionLat = Number(currentChallenge.solution.coordinates.lat);
          var solutionLon = Number(currentChallenge.solution.coordinates.lon);

          options.forEach(function (o) {
            o.classList.add("answered");
          });

          var lat = Number(this.getAttribute("data-lat"));
          var lon = Number(this.getAttribute("data-lon"));

          if (lat === solutionLat && lon === solutionLon) {
            this.classList.add("correct");
          } else {
            this.classList.add("wrong");
            options.forEach(function (c) {
              var cLat = Number(c.getAttribute("data-lat"));
              var cLon = Number(c.getAttribute("data-lon"));
              if (cLat === solutionLat && cLon === solutionLon) {
                c.classList.add("correct");
              }
            });
          }

          if (speciesInfoCard) {
            speciesInfoCard.classList.add("show");
          }

          // Show attribution after answering
          if (imageAttribution) {
            imageAttribution.classList.add("show");
          }

          nextButton.style.display = "block";
        });
      });
    }

    function createOptionCard(option) {
      var card = document.createElement("div");
      card.className = "option-card";
      card.dataset.lat = option.coordinates.lat;
      card.dataset.lon = option.coordinates.lon;

      var continent = document.createElement("div");
      continent.className = "continent-label";
      continent.textContent = "continent: " + option.continent;
      card.appendChild(continent);

      if (option.details) {
        var details = document.createElement("div");
        details.className = "details-label";
        details.textContent = option.details;
        card.appendChild(details);
      }

      return card;
    }

    function speciesDetailUrl(speciesName, locationDetails) {
      var url = speciesBase.replace(
        "__SPECIES__",
        encodeURIComponent(speciesName),
      );
      if (locationDetails) {
        url += "?location=" + encodeURIComponent(locationDetails);
      }
      return url;
    }

    function renderChallenge(challenge) {
      currentChallenge = challenge;
      answered = false;
      nextButton.style.display = "none";

      // Update species info card
      if (speciesInfoCard) {
        speciesInfoCard.classList.remove("show");
        if (challenge.species_info && challenge.species_info.species) {
          var speciesName = challenge.species_info.species;
          var family = challenge.species_info.family || "Unknown";
          var genus = challenge.species_info.genus || "Unknown";
          var locationDetails =
            challenge.solution && challenge.solution.details
              ? challenge.solution.details
              : "";
          var detailUrl = speciesDetailUrl(speciesName, locationDetails);

          speciesInfoCard.innerHTML =
            "<h3>" +
            speciesName +
            "</h3>" +
            '<div class="taxonomy">' +
            "<span>Family:</span> " +
            family +
            " | " +
            "<span>Genus:</span> " +
            genus +
            "</div>" +
            '<a href="' +
            detailUrl +
            '" class="view-detail-link">View Species Details →</a>';
        }
      }

      // Update attribution
      if (imageAttribution) {
        if (challenge.species_info) {
          var license = challenge.species_info.license || "";
          var holder = challenge.species_info.rightsHolder || "";
          var occurrenceUrl = challenge.species_info.occurrence_url || "";

          var attrHTML = "";
          if (license) attrHTML += "License: " + license;
          if (holder) attrHTML += (attrHTML ? " | " : "") + "© " + holder;
          if (occurrenceUrl)
            attrHTML +=
              (attrHTML ? " | " : "") +
              '<a href="' +
              occurrenceUrl +
              '" target="_blank" rel="noopener">Source</a>';

          imageAttribution.innerHTML = attrHTML;
        }
        imageAttribution.classList.remove("show");
      }

      // Update plant image
      challengeImage.src = challenge.url;

      optionsList.innerHTML = "";
      challenge.proposed_locations.forEach(function (option) {
        optionsList.appendChild(createOptionCard(option));
      });

      bindOptionClickHandlers();
    }

    nextButton.addEventListener("click", async function () {
      if (loadingNext) return;

      setLoadingState(true);

      try {
        var response = await fetch(nextChallengeUrl, { method: "GET" });
        if (!response.ok) {
          throw new Error("Could not load next challenge.");
        }

        var payload = await response.json();
        if (!payload.challenge) {
          throw new Error("No challenge returned.");
        }

        renderChallenge(payload.challenge);
      } catch (error) {
        console.error(error);
        nextButton.textContent = "Try Again";
      } finally {
        if (nextButton.textContent === "Try Again") {
          loadingNext = false;
          nextButton.disabled = false;
          nextButton.classList.remove("is-loading");
          imageContainer.classList.remove("is-loading");
        } else {
          setLoadingState(false);
        }
      }
    });

    console.log("[Game] Attaching initial click handlers");
    bindOptionClickHandlers();
    console.log("[Game] ========== INIT COMPLETE ==========");
  }

  // Call init when DOM is ready
  console.log("[Game] Current readyState:", document.readyState);
  if (document.readyState === "loading") {
    console.log("[Game] DOM still loading, adding DOMContentLoaded listener");
    document.addEventListener("DOMContentLoaded", function () {
      console.log("[Game] DOMContentLoaded event fired");
      init();
    });
  } else {
    console.log("[Game] DOM already ready, calling init immediately");
    init();
  }
})();
