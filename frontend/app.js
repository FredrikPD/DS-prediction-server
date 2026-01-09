const API = "/api";

// Map airline names to their backend ID representation
const AIRLINE_MAP = {
  "Southwest Airlines Co.": "1",
  "Comair Inc.": "2",
  "Delta Air Lines Inc.": "3",
  "Frontier Airlines Inc.": "4",
  "Alaska Airlines Inc.": "5",
  "Endeavor Air Inc.": "6",
  "SkyWest Airlines Inc.": "7",
  "Commutair Aka Champlain Enterprises, Inc.": "8",
  "American Airlines Inc.": "9",
  "Spirit Air Lines": "10",
  "Hawaiian Airlines Inc.": "11",
  "Horizon Air": "12",
  "Mesa Airlines Inc.": "13",
  "Envoy Air": "14",
  "Allegiant Air": "15",
  "United Air Lines Inc.": "16",
  "JetBlue Airways": "17",
  "Republic Airlines": "18",
  "GoJet Airlines, LLC d/b/a United Express": "19",
  "Air Wisconsin Airlines Corp": "20",
  "Capital Cargo International": "21"
};

// Helper to create DOM elements with attributes and children
function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => e[k] = v);
  children.forEach(c => {
    if (typeof c === 'string') e.appendChild(document.createTextNode(c));
    else e.appendChild(c);
  });
  return e;
}

// Toggle button loading state to prevent double submissions
function setLoading(btnId, isLoading) {
  const btn = document.getElementById(btnId);
  if (isLoading) {
    btn.dataset.originalText = btn.textContent;
    btn.textContent = "Loading...";
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.originalText || "Submit";
    btn.disabled = false;
  }
}

function showError(containerId, message) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  container.classList.remove("hidden");
  container.appendChild(el("div", {
    style: "color: #EF4444; background: #FEF2F2; padding: 1rem; border-radius: 8px; border: 1px solid #FECACA;"
  }, [message]));
}

async function loadModelsAndMappings() {
  try {
    // Fetch models and mappings in parallel for faster load time
    const [modelsRes, mappingsRes] = await Promise.all([
      fetch(`${API}/models`),
      fetch(`${API}/mappings`)
    ]);

    if (!modelsRes.ok) throw new Error("Failed to load models");

    const mappings = mappingsRes.ok ? await mappingsRes.json() : {};

    // Transform list-based interaction mapping to object for O(1) lookup
    if (Array.isArray(mappings["Hub_x_Dest"])) {
      const hxdMap = {};
      mappings["Hub_x_Dest"].forEach(item => {
        if (item.length === 3) {
          hxdMap[`${item[0]}_${item[1]}`] = item[2];
        }
      });
      mappings["Hub_x_Dest"] = hxdMap;
    }

    const data = await modelsRes.json();

    const modelSelect = document.getElementById("modelSelect");
    const evalModelSelect = document.getElementById("evalModelSelect");
    modelSelect.innerHTML = "";
    evalModelSelect.innerHTML = "<option value=''>ALL (default)</option>";

    data.models.forEach(m => {
      const text = `${m.technique} (${m.id})`;
      modelSelect.appendChild(el("option", { value: m.id, textContent: text }));
      evalModelSelect.appendChild(el("option", { value: m.id, textContent: text }));
    });

    if (data.default_model) {
      modelSelect.value = data.default_model;
    }

    const form = document.getElementById("featureForm");
    form.innerHTML = "";

    const descriptions = {
      "Airline": "The airline company operating the flight.",
      "Origin": "The starting airport code (e.g., JFK, LAX).",
      "Dest": "The destination airport code (e.g., ORD, MIA).",
      "Route": "The specific flight route (Origin-Dest).",
      "Hub_Airline": "Is the airline a major hub carrier? (1=Yes, 0=No)",
      "Month_cos": "The month of the flight.",
      "DayofMonth_cos": "The day of the month (1-31).",
      "Is_Winter": "Is the flight during winter season?",
      "Hub_x_Dest": "Interaction feature: Hub Airline × Destination.",
      "DepDelay": "Departure delay in minutes.",
      "Distance": "Flight distance in miles."
    };

    // Dynamically generate form inputs based on backend feature columns
    data.feature_columns.forEach(c => {
      const wrapper = el("div", { className: "feature-input" });

      let labelText = c;
      if (c === "Month_cos") labelText = "Month";
      if (c === "DayofMonth_cos") labelText = "Day of Month";

      wrapper.appendChild(el("label", { textContent: labelText, htmlFor: `f_${c}` }));

      if (descriptions[c]) {
        const desc = el("small", {
          textContent: descriptions[c],
          style: "display:block; color:#666; margin-bottom:4px; font-size:0.85em;"
        });
        wrapper.appendChild(desc);
      }

      if (c === "Is_Winter") {
        const select = el("select", { id: `f_${c}` });
        select.appendChild(el("option", { value: "1", textContent: "Yes" }));
        select.appendChild(el("option", { value: "0", textContent: "No", selected: true }));
        wrapper.appendChild(select);
      } else if (c === "Month") {
        const select = el("select", { id: "raw_Month" });
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        months.forEach((m, i) => {
          select.appendChild(el("option", { value: i + 1, textContent: m }));
        });
        wrapper.appendChild(select);
      } else if (c === "DayofMonth") {
        wrapper.appendChild(el("input", { id: "raw_DayofMonth", type: "number", min: "1", max: "31", placeholder: "1-31", value: "1" }));
      } else if (c === "Airline") {
        const select = el("select", { id: `f_${c}` });
        const sortedAirlines = Object.keys(AIRLINE_MAP).sort();

        sortedAirlines.forEach(name => {
          select.appendChild(el("option", { value: AIRLINE_MAP[name], textContent: name }));
        });
        wrapper.appendChild(select);

      } else if (["Route", "Hub_Airline", "Hub_x_Dest"].includes(c)) {
        wrapper.appendChild(el("input", { id: `f_${c}`, type: "text", readonly: true }));

      } else if (mappings[c]) {
        const select = el("select", { id: `f_${c}` });
        select.appendChild(el("option", { value: "", textContent: `-- Select ${c} --`, disabled: true, selected: true }));

        const options = Object.entries(mappings[c]).sort((a, b) => a[0].localeCompare(b[0]));

        options.forEach(([label, value]) => {
          select.appendChild(el("option", { value: value, textContent: label }));
        });

        wrapper.appendChild(select);
      } else {
        wrapper.appendChild(el("input", { id: `f_${c}`, placeholder: `Enter ${c}`, type: "text" }));
      }

      form.appendChild(wrapper);
    });

    ["f_Route", "f_Is_Winter", "f_Hub_Airline", "f_Hub_x_Dest"].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        const wrapper = el.closest(".feature-input");
        if (wrapper) wrapper.style.display = "none";
      }
    });

    // Update derived features (Route, Hub_x_Dest, etc.) when base inputs change
    function updateAutoFeatures() {
      const originInput = document.getElementById("f_Origin");
      const destInput = document.getElementById("f_Dest");
      const routeSelect = document.getElementById("f_Route");

      const airlineSelect = document.getElementById("f_Airline");
      const monthSelect = document.getElementById("raw_Month");

      const hubAirlineSelect = document.getElementById("f_Hub_Airline");
      const hubXDestSelect = document.getElementById("f_Hub_x_Dest");
      const isWinterSelect = document.getElementById("f_Is_Winter");

      const valOf = (el) => {
        if (!el) return "";
        if (el.tagName === "SELECT") return el.options[el.selectedIndex]?.text || "";
        return el.value || "";
      };

      const originCode = valOf(originInput);
      const destCode = valOf(destInput);
      const airlineName = valOf(airlineSelect);
      const monthVal = monthSelect?.value ? parseInt(monthSelect.value) : null;

      if (routeSelect) {
        // Construct composite key matching backend expectation (Origin_Dest)
        const key = `${originCode}_${destCode}`;

        let val = mappings["Route"] ? mappings["Route"][key] : undefined;
        if (val === undefined) val = "0.0";

        routeSelect.value = val;
      }

      if (isWinterSelect && monthVal !== null) {
        const isWinter = [12, 1, 2].includes(monthVal);
        isWinterSelect.value = isWinter ? "1" : "0";
      }
      let hubKey = null;
      if (hubAirlineSelect) {
        hubKey = `${airlineName}_${originCode}`;
        let val = mappings["Hub_Airline"] ? mappings["Hub_Airline"][hubKey] : undefined;
        if (val === undefined) val = "0.0";
        hubAirlineSelect.value = val;
      }

      if (hubXDestSelect) {
        const key = `${hubKey}_${destCode}`;
        let val = mappings["Hub_x_Dest"] ? mappings["Hub_x_Dest"][key] : undefined;
        if (val === undefined) val = "0.0";
        hubXDestSelect.value = val;
      }
    }

    const elementsToWatch = ["f_Origin", "f_Dest", "f_Airline", "raw_Month"];
    elementsToWatch.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("change", updateAutoFeatures);
    });

    return data;
  } catch (err) {
    alert("Error loading data: " + err.message);
  }
}

function setupModeToggle() {
  document.querySelectorAll("input[name='mode']").forEach(r => {
    r.addEventListener("change", () => {
      const isSingle = r.value === "single";
      document.getElementById("single").classList.toggle("hidden", !isSingle);
      document.getElementById("eval").classList.toggle("hidden", isSingle);
    });
  });
}

async function setupPredict(featureCols) {
  document.getElementById("predictBtn").onclick = async () => {
    const outContainer = document.getElementById("predictOutContainer");
    let outPre = document.getElementById("predictOut");

    if (!outPre) {
      outContainer.innerHTML = '<h3>Result</h3><pre id="predictOut"></pre>';
      outPre = document.getElementById("predictOut");
    }

    outContainer.classList.add("hidden");
    outPre.textContent = "";
    setLoading("predictBtn", true);

    try {
      const model_id = document.getElementById("modelSelect").value;
      const features = {};

      // Collect and validate all features from the form
      for (const c of featureCols) {
        let val;
        if (c === "Month") {
          const raw = document.getElementById("raw_Month").value;
          if (!raw) throw new Error("Please select a month");
          val = raw;
        } else if (c === "DayofMonth") {
          const raw = document.getElementById("raw_DayofMonth").value;
          if (!raw) throw new Error("Please enter day of month");
          const d = parseFloat(raw);
          if (d < 1 || d > 31) throw new Error("Day of month must be between 1 and 31");
          val = raw;
        } else if (c === "Month_cos" || c === "DayofMonth_cos") {
          val = 0;
        } else {
          const input = document.getElementById(`f_${c}`);
          val = input.value;
          if (val === "" || val === null) {
            if (val === "" || val === null) {
              if (["Route", "Hub_Airline", "Hub_x_Dest"].includes(c)) {
                throw new Error(`The combination of inputs (Airline, Origin, Dest) is not supported (Missing ${c}).`);
              }
              throw new Error(`Please provide a value for ${c}`);
            }
          }
        }
        const numVal = parseFloat(val);
        features[c] = isNaN(numVal) ? val : numVal;
      }

      const res = await fetch(`${API}/predict-single`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id, features })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Prediction failed");
      }

      const result = await res.json();

      let label = result.prediction;
      let colorClass = "";
      if (String(label) === "1") {
        label = "Cancelled";
        colorClass = "text-danger";
      } else if (String(label) === "0") {
        label = "Not Cancelled";
        colorClass = "text-success";
      }

      outPre.innerHTML = `Prediction: <span class="${colorClass}" style="font-weight:bold">${label}</span>\nModel Used: ${result.model_id}`;
      outContainer.classList.remove("hidden");
    } catch (err) {
      showError("predictOutContainer", err.message);
    } finally {
      setLoading("predictBtn", false);
    }
  };
}

function renderEvalTable(results) {
  let container = document.getElementById("evalOutTable");
  if (!container) {
    const parent = document.getElementById("evalOutContainer");
    if (parent) {
      parent.innerHTML = '<h3>Evaluation Metrics</h3><div id="evalOutTable"></div>';
      container = document.getElementById("evalOutTable");
    }
  }

  if (!container) return;

  container.innerHTML = "";

  if (!results || results.length === 0) {
    container.textContent = "No results returned.";
    return;
  }

  const table = el("table", { className: "results-table" });

  const thead = el("thead", {}, [
    el("tr", {}, [
      el("th", { textContent: "Model ID" }),
      el("th", { textContent: "Accuracy" }),
      el("th", { textContent: "Precision" }),
      el("th", { textContent: "Recall" }),
      el("th", { textContent: "F1 Score" })
    ])
  ]);
  table.appendChild(thead);

  const tbody = el("tbody");
  results.forEach(r => {
    tbody.appendChild(el("tr", {}, [
      el("td", { textContent: r.model_id }),
      el("td", { textContent: r.metrics.accuracy.toFixed(4) }),
      el("td", { textContent: r.metrics.precision.toFixed(4) }),
      el("td", { textContent: r.metrics.recall.toFixed(4) }),
      el("td", { textContent: r.metrics.f1.toFixed(4) })
    ]));
  });
  table.appendChild(tbody);

  container.appendChild(table);
}

// Handle batch evaluation via CSV upload
async function setupEval() {
  document.getElementById("evalBtn").onclick = async () => {
    const outContainer = document.getElementById("evalOutContainer");
    const csvInput = document.getElementById("csvFile");

    outContainer.classList.add("hidden");
    setLoading("evalBtn", true);

    try {
      const f = csvInput.files[0];
      const model_id = document.getElementById("evalModelSelect").value;

      if (!f) throw new Error("Please choose a CSV file first.");

      const fd = new FormData();
      fd.append("file", f);
      if (model_id) fd.append("model_id", model_id);

      const res = await fetch(`${API}/evaluate-models`, { method: "POST", body: fd });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Evaluation failed");
      }

      const data = await res.json();
      renderEvalTable(data.results);
      outContainer.classList.remove("hidden");

    } catch (err) {
      showError("evalOutContainer", err.message);
    } finally {
      setLoading("evalBtn", false);
    }
  };
}

(async function main() {
  setupModeToggle();
  const data = await loadModelsAndMappings();
  if (data) {
    await setupPredict(data.feature_columns);
    await setupEval();
  }
})();