const API = "/api";

function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => e[k] = v);
  children.forEach(c => {
    if (typeof c === 'string') e.appendChild(document.createTextNode(c));
    else e.appendChild(c);
  });
  return e;
}

// Helper to show/hide loading state
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

// Helper to display errors
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
    const [modelsRes, mappingsRes] = await Promise.all([
      fetch(`${API}/models`),
      fetch(`${API}/mappings`)
    ]);

    if (!modelsRes.ok) throw new Error("Failed to load models");

    // Mappings might not exist or fail, treat as optional but recommended
    const mappings = mappingsRes.ok ? await mappingsRes.json() : {};

    // transform Hub_x_Dest from list [[k1, k2, v], ...] to object "k1_k2": v
    if (Array.isArray(mappings["Hub_x_Dest"])) {
      const hxdMap = {};
      mappings["Hub_x_Dest"].forEach(item => {
        // item is [HubKey, Dest, Value]
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

    // auto-build input form
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

    data.feature_columns.forEach(c => {
      const wrapper = el("div", { className: "feature-input" });

      // Determine display label
      let labelText = c;
      if (c === "Month_cos") labelText = "Month";
      if (c === "DayofMonth_cos") labelText = "Day of Month";

      wrapper.appendChild(el("label", { textContent: labelText, htmlFor: `f_${c}` }));

      // Add description if available (now inserted BETWEEN label and input)
      if (descriptions[c]) {
        const desc = el("small", {
          textContent: descriptions[c],
          style: "display:block; color:#666; margin-bottom:4px; font-size:0.85em;"
        });
        wrapper.appendChild(desc);
      }

      // Check if we have a mapping for this feature
      if (c === "Is_Winter") {
        // Special Yes/No toggle for Is_Winter
        const select = el("select", { id: `f_${c}` });
        select.appendChild(el("option", { value: "1", textContent: "Yes" }));
        select.appendChild(el("option", { value: "0", textContent: "No", selected: true }));
        wrapper.appendChild(select);
      } else if (c === "Month_cos") {
        // Special Month Dropdown
        const select = el("select", { id: "raw_Month" });
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        months.forEach((m, i) => {
          // Default to current month or Jan, let's pick Jan
          select.appendChild(el("option", { value: i + 1, textContent: m }));
        });
        wrapper.appendChild(select);
      } else if (c === "DayofMonth_cos") {
        // Special Day Input (1-31)
        wrapper.appendChild(el("input", { id: "raw_DayofMonth", type: "number", min: "1", max: "31", placeholder: "1-31", value: "1" }));
      } else if (mappings[c]) {
        // Create Select Dropdown
        const select = el("select", { id: `f_${c}` });

        // Add default/placeholder option
        select.appendChild(el("option", { value: "", textContent: `-- Select ${c} --`, disabled: true, selected: true }));

        // Sort keys alphabetically for better UX
        const options = Object.entries(mappings[c]).sort((a, b) => a[0].localeCompare(b[0]));

        options.forEach(([label, value]) => {
          select.appendChild(el("option", { value: value, textContent: label }));
        });

        wrapper.appendChild(select);
      } else {
        // Standard Text/Number Input
        wrapper.appendChild(el("input", { id: `f_${c}`, placeholder: `Enter ${c}`, type: "text" }));
      }

      form.appendChild(wrapper);
    });

    // --- Auto-Feature Logic ---
    // Hide auto-calculated inputs
    ["f_Route", "f_Is_Winter", "f_Hub_Airline", "f_Hub_x_Dest"].forEach(id => {
      const el = document.getElementById(id); // select or input
      if (el) {
        // Find the wrapper div (class="feature-input")
        const wrapper = el.closest(".feature-input");
        if (wrapper) wrapper.style.display = "none";
      }
    });

    // Function to update all auto-calculated features
    function updateAutoFeatures() {
      // 1. Route (Origin_Dest)
      const originSelect = document.getElementById("f_Origin");
      const destSelect = document.getElementById("f_Dest");
      const routeSelect = document.getElementById("f_Route");

      // Inputs for other features
      const airlineSelect = document.getElementById("f_Airline");
      const monthSelect = document.getElementById("raw_Month");

      const hubAirlineSelect = document.getElementById("f_Hub_Airline");
      const hubXDestSelect = document.getElementById("f_Hub_x_Dest");
      const isWinterSelect = document.getElementById("f_Is_Winter");

      if (!originSelect || !destSelect) return;

      // Get the *text* (Airport Code/Airline Name)
      const originCode = originSelect.options[originSelect.selectedIndex]?.text;
      const destCode = destSelect.options[destSelect.selectedIndex]?.text;
      const airlineName = airlineSelect?.options[airlineSelect.selectedIndex]?.text;
      const monthVal = monthSelect?.value ? parseInt(monthSelect.value) : null;

      // --- Route ---
      if (routeSelect && originCode && destCode && !originCode.includes("--") && !destCode.includes("--")) {
        const key = `${originCode}_${destCode}`;
        const val = mappings["Route"] ? mappings["Route"][key] : undefined;
        routeSelect.value = val !== undefined ? val : "";
      }

      // --- Is_Winter ---
      if (isWinterSelect && monthVal !== null) {
        // Winter = Dec (12), Jan (1), Feb (2)
        const isWinter = [12, 1, 2].includes(monthVal);
        isWinterSelect.value = isWinter ? "1" : "0";
      }

      // --- Hub_Airline (Airline_Origin) ---
      // Mapping key format: "AirlineName_OriginCode"
      // Value: Target Encoded float
      let hubKey = null;
      if (hubAirlineSelect && airlineName && originCode && !originCode.includes("--")) {
        hubKey = `${airlineName}_${originCode}`;
        const val = mappings["Hub_Airline"] ? mappings["Hub_Airline"][hubKey] : undefined;
        hubAirlineSelect.value = val !== undefined ? val : ""; // 0.0 is often default for non-hubs, but let's stick to map
      }

      // --- Hub_x_Dest (HubKey_Dest) ---
      // Mapping key format: "AirlineName_OriginCode_DestCode" (via our transformation earlier)
      if (hubXDestSelect && hubKey && destCode && !destCode.includes("--")) {
        const key = `${hubKey}_${destCode}`;
        const val = mappings["Hub_x_Dest"] ? mappings["Hub_x_Dest"][key] : undefined;
        hubXDestSelect.value = val !== undefined ? val : "";
      }
    }

    // Attach listeners
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

    // Recover DOM if wiped by previous error
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

      // Validation and Collection
      for (const c of featureCols) {
        let val;

        // Handle special transforms
        if (c === "Month_cos") {
          const raw = document.getElementById("raw_Month").value;
          if (!raw) throw new Error("Please select a month");
          // cos(2 * pi * month / 12)
          val = Math.cos(2 * Math.PI * parseFloat(raw) / 12);
        } else if (c === "DayofMonth_cos") {
          const raw = document.getElementById("raw_DayofMonth").value;
          if (!raw) throw new Error("Please enter day of month");
          const d = parseFloat(raw);
          if (d < 1 || d > 31) throw new Error("Day of month must be between 1 and 31");
          // cos(2 * pi * day / 31)
          val = Math.cos(2 * Math.PI * d / 31);
        } else {
          const input = document.getElementById(`f_${c}`);
          val = input.value;
          // Basic validation: ensure something is selected or typed
          if (val === "" || val === null) {
            if (val === "" || val === null) {
              if (["Route", "Hub_Airline", "Hub_x_Dest"].includes(c)) {
                throw new Error(`The combination of inputs (Airline, Origin, Dest) is not supported (Missing ${c}).`);
              }
              throw new Error(`Please provide a value for ${c}`);
            }
          }
        }

        // Convert to number if valid (since models expect numbers)
        // If it's a dropdown, val is already the numeric string from mapping
        // If it's text input, user might type number or string. Model expects number.
        // If it was transformed above, it is already a number.
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

      // improved display
      let label = result.prediction;
      let colorClass = "";
      // label comes as string "0" or "1" usually
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

  // Recover DOM if wiped by previous error
  if (!container) {
    const parent = document.getElementById("evalOutContainer");
    if (parent) {
      parent.innerHTML = '<h3>Evaluation Metrics</h3><div id="evalOutTable"></div>';
      container = document.getElementById("evalOutTable");
    }
  }

  if (!container) return; // Should not happen

  container.innerHTML = "";

  if (!results || results.length === 0) {
    container.textContent = "No results returned.";
    return;
  }

  const table = el("table", { className: "results-table" });

  // Header
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

  // Body
  const tbody = el("tbody");
  results.forEach(r => {
    // Optimized metrics are now in 'metrics' by default
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