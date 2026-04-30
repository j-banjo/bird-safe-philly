import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
INPUT_GPKG = Path(
    r"C:/Users/16102/Desktop/big_geospatial_data/Final/data/bird_reports.gpkg"
)

OUTPUT_DIR = Path("docs")
DATA_DIR = OUTPUT_DIR / "data"
OUTPUT_GEOJSON = DATA_DIR / "bird_reports_sample.geojson"
OUTPUT_HTML = OUTPUT_DIR / "index.html"

MAX_RECORDS = 5000


# ------------------------------------------------------------
# LOAD AND PREP DATA
# ------------------------------------------------------------
bird_reports = gpd.read_file(INPUT_GPKG)

if bird_reports.crs is None:
    raise ValueError("Input GeoPackage has no CRS. Define the CRS before exporting.")

bird_reports = bird_reports.to_crs(epsg=4326)

bird_reports["lon"] = bird_reports.geometry.x
bird_reports["lat"] = bird_reports.geometry.y

if "time_observed" in bird_reports.columns:
    bird_reports["time_observed"] = pd.to_datetime(
        bird_reports["time_observed"],
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")
else:
    bird_reports["time_observed"] = None

required_columns = [
    "species_name",
    "dead_or_alive",
    "building_name",
    "building_id",
    "time_observed",
    "lat",
    "lon",
    "geometry",
]

available_columns = [col for col in required_columns if col in bird_reports.columns]

export_gdf = bird_reports[available_columns].copy()

if len(export_gdf) > MAX_RECORDS:
    export_gdf = export_gdf.sample(MAX_RECORDS, random_state=42)

DATA_DIR.mkdir(parents=True, exist_ok=True)

export_gdf.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

print(f"Exported {len(export_gdf):,} records to {OUTPUT_GEOJSON}")


# ------------------------------------------------------------
# WRITE STATIC HTML DASHBOARD
# ------------------------------------------------------------
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Bird Collision Analysis Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  />

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    :root {
      --bg: #fcfcfc;
      --panel: #ffffff;
      --border: #e3e8ee;
      --text: #011f3e;
      --muted: #5c6b7a;
      --primary: #034485;
      --secondary: #011f3e;
      --accent: #f7c447;
      --danger: #e94f37;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      height: 100vh;
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      overflow: hidden;
    }

    header {
      padding: 12px 16px;
      background: var(--panel);
      border-bottom: 2px solid var(--primary);
    }

    h1 {
      margin: 0;
      font-size: 26px;
    }

    header p {
      margin: 4px 0 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .filters {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr)) auto;
      gap: 14px;
      align-items: end;
      padding: 12px 14px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }

    label {
      display: block;
      font-size: 12px;
      font-weight: 700;
      color: var(--secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 4px;
    }

    select,
    input,
    button {
      width: 100%;
      height: 38px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0 10px;
      background: #ffffff;
      color: var(--text);
    }

    button {
      border: none;
      background: var(--primary);
      color: #ffffff;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }

    main {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 320px;
      gap: 12px;
      padding: 12px;
      min-height: 0;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
      min-height: 0;
      overflow: hidden;
    }

    .stack {
      display: grid;
      grid-template-rows: 1fr 1fr;
      gap: 12px;
      min-height: 0;
    }

    .panel-header {
      border-top: 4px solid var(--accent);
      padding-top: 6px;
      padding-bottom: 8px;
      margin-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }

    .panel-header h2,
    .card h2 {
      margin: 0;
      font-size: 18px;
    }

    .panel-header p {
      margin: 4px 0 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    #map {
      height: calc(100% - 64px);
      min-height: 300px;
      border-radius: 8px;
    }

    .stat {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      background: #fcfcfc;
      margin-bottom: 10px;
    }

    .stat-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .stat-value {
      font-size: 20px;
      font-weight: 700;
      color: var(--primary);
      margin-top: 4px;
    }

    .muted {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }

    @media (max-width: 900px) {
      body {
        overflow: auto;
        height: auto;
      }

      .filters,
      main {
        grid-template-columns: 1fr;
      }

      main {
        min-height: 900px;
      }

      .stack {
        grid-template-rows: auto auto;
      }

      #map {
        height: 520px;
      }
    }
  </style>
</head>

<body>
  <header>
    <h1>Bird Collision Analysis Dashboard</h1>
    <p>Static GitHub Pages smoke test for bird-building collision observations</p>
  </header>

  <section class="filters">
    <div>
      <label for="species-filter">Species</label>
      <select id="species-filter">
        <option value="">All species</option>
      </select>
    </div>

    <div>
      <label for="status-filter">Status</label>
      <select id="status-filter">
        <option value="">All statuses</option>
      </select>
    </div>

    <div>
      <label for="building-filter">Building</label>
      <select id="building-filter">
        <option value="">All buildings</option>
      </select>
    </div>

    <div>
      <label for="date-filter">Start date</label>
      <input id="date-filter" type="date" />
    </div>

    <button id="clear-filters">Clear filters</button>
  </section>

  <main>
    <section class="stack">
      <div class="card">
        <h2>Dashboard Summary</h2>
        <div id="stats-panel" style="margin-top: 12px;"></div>
      </div>

      <div class="card">
        <h2>Selected Collision</h2>
        <div id="selected-panel" class="muted" style="margin-top: 12px;">
          Click a collision point to inspect details.
        </div>
      </div>
    </section>

    <section class="card">
      <div class="panel-header">
        <h2>Collision Map</h2>
        <p>Filtered bird-building collision observations</p>
      </div>
      <div id="map"></div>
    </section>

    <section class="stack">
      <div class="card">
        <h2>Graph Panel</h2>
        <div id="graph-panel" class="muted" style="margin-top: 12px;">
          Static test panel. Graphs can be added with Plotly.js later.
        </div>
      </div>

      <div class="card">
        <h2>3D Building View</h2>
        <div class="muted" style="margin-top: 12px;">
          Static test panel. Cesium can be added later, but this confirms the GitHub Pages structure first.
        </div>
      </div>
    </section>
  </main>

  <script>
    const map = L.map("map").setView([39.9526, -75.1652], 12);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
    }).addTo(map);

    const markerLayer = L.layerGroup().addTo(map);

    let allFeatures = [];

    const speciesFilter = document.getElementById("species-filter");
    const statusFilter = document.getElementById("status-filter");
    const buildingFilter = document.getElementById("building-filter");
    const dateFilter = document.getElementById("date-filter");
    const clearButton = document.getElementById("clear-filters");
    const statsPanel = document.getElementById("stats-panel");
    const selectedPanel = document.getElementById("selected-panel");

    function cleanValue(value) {
      if (value === null || value === undefined || value === "nan") {
        return "";
      }

      return String(value);
    }

    function getBuildingLabel(properties) {
      return cleanValue(properties.building_name) || cleanValue(properties.building_id) || "Unknown building";
    }

    function uniqueSorted(values) {
      return [...new Set(values.filter(value => value !== ""))].sort();
    }

    function populateSelect(select, values, defaultLabel) {
      const currentValue = select.value;
      select.innerHTML = "";

      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = defaultLabel;
      select.appendChild(defaultOption);

      values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });

      if (values.includes(currentValue)) {
        select.value = currentValue;
      }
    }

    function initializeFilters(features) {
      const speciesValues = uniqueSorted(
        features.map(feature => cleanValue(feature.properties.species_name))
      );

      const statusValues = uniqueSorted(
        features.map(feature => cleanValue(feature.properties.dead_or_alive))
      );

      const buildingValues = uniqueSorted(
        features.map(feature => getBuildingLabel(feature.properties))
      );

      populateSelect(speciesFilter, speciesValues, "All species");
      populateSelect(statusFilter, statusValues, "All statuses");
      populateSelect(buildingFilter, buildingValues, "All buildings");
    }

    function filterFeatures() {
      const species = speciesFilter.value;
      const status = statusFilter.value;
      const building = buildingFilter.value;
      const startDate = dateFilter.value;

      return allFeatures.filter(feature => {
        const properties = feature.properties;

        const featureSpecies = cleanValue(properties.species_name);
        const featureStatus = cleanValue(properties.dead_or_alive);
        const featureBuilding = getBuildingLabel(properties);
        const featureDate = cleanValue(properties.time_observed);

        if (species && featureSpecies !== species) {
          return false;
        }

        if (status && featureStatus !== status) {
          return false;
        }

        if (building && featureBuilding !== building) {
          return false;
        }

        if (startDate && featureDate && featureDate < startDate) {
          return false;
        }

        return true;
      });
    }

    function updateStats(features) {
      const speciesSet = new Set(
        features.map(feature => cleanValue(feature.properties.species_name)).filter(Boolean)
      );

      const buildingSet = new Set(
        features.map(feature => getBuildingLabel(feature.properties)).filter(Boolean)
      );

      const speciesCounts = {};

      features.forEach(feature => {
        const species = cleanValue(feature.properties.species_name);

        if (species) {
          speciesCounts[species] = (speciesCounts[species] || 0) + 1;
        }
      });

      let mostCommonSpecies = "N/A";
      let maxCount = 0;

      Object.entries(speciesCounts).forEach(([species, count]) => {
        if (count > maxCount) {
          mostCommonSpecies = species;
          maxCount = count;
        }
      });

      statsPanel.innerHTML = `
        <div class="stat">
          <div class="stat-label">Filtered records</div>
          <div class="stat-value">${features.length.toLocaleString()}</div>
        </div>

        <div class="stat">
          <div class="stat-label">Unique species</div>
          <div class="stat-value">${speciesSet.size.toLocaleString()}</div>
        </div>

        <div class="stat">
          <div class="stat-label">Unique buildings</div>
          <div class="stat-value">${buildingSet.size.toLocaleString()}</div>
        </div>

        <div class="stat">
          <div class="stat-label">Most common species</div>
          <div class="stat-value">${mostCommonSpecies}</div>
        </div>
      `;
    }

    function renderMarkers(features) {
      markerLayer.clearLayers();

      const bounds = [];

      features.forEach(feature => {
        const coordinates = feature.geometry.coordinates;
        const lon = coordinates[0];
        const lat = coordinates[1];
        const properties = feature.properties;

        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
          return;
        }

        const marker = L.circleMarker([lat, lon], {
          radius: 5,
          color: "#011f3e",
          fillColor: "#e94f37",
          fillOpacity: 0.75,
          weight: 1
        });

        const species = cleanValue(properties.species_name) || "Unknown species";
        const status = cleanValue(properties.dead_or_alive) || "Unknown status";
        const building = getBuildingLabel(properties);
        const date = cleanValue(properties.time_observed) || "Unknown date";

        marker.bindTooltip(species);

        marker.on("click", () => {
          selectedPanel.innerHTML = `
            <strong>Species:</strong> ${species}<br>
            <strong>Status:</strong> ${status}<br>
            <strong>Building:</strong> ${building}<br>
            <strong>Date:</strong> ${date}
          `;
        });

        marker.addTo(markerLayer);
        bounds.push([lat, lon]);
      });

      if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [20, 20], maxZoom: 15 });
      }
    }

    function updateDashboard() {
      const filteredFeatures = filterFeatures();
      updateStats(filteredFeatures);
      renderMarkers(filteredFeatures);
    }

    speciesFilter.addEventListener("change", updateDashboard);
    statusFilter.addEventListener("change", updateDashboard);
    buildingFilter.addEventListener("change", updateDashboard);
    dateFilter.addEventListener("change", updateDashboard);

    clearButton.addEventListener("click", () => {
      speciesFilter.value = "";
      statusFilter.value = "";
      buildingFilter.value = "";
      dateFilter.value = "";
      selectedPanel.textContent = "Click a collision point to inspect details.";
      updateDashboard();
    });

    fetch("data/bird_reports_sample.geojson")
      .then(response => {
        if (!response.ok) {
          throw new Error("Could not load GeoJSON file.");
        }

        return response.json();
      })
      .then(geojson => {
        allFeatures = geojson.features || [];
        initializeFilters(allFeatures);
        updateDashboard();
      })
      .catch(error => {
        statsPanel.innerHTML = `
          <div class="stat">
            <div class="stat-label">Error</div>
            <div class="stat-value">Data failed to load</div>
          </div>
          <p class="muted">${error.message}</p>
        `;
      });
  </script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html_template, encoding="utf-8")

print(f"Wrote static dashboard to {OUTPUT_HTML}")
print("Open docs/index.html locally first, then push the docs folder to GitHub.")
