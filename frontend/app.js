const API = "http://localhost:8000/api";

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

async function loadModels() {
  try {
    const res = await fetch(`${API}/models`);
    if (!res.ok) throw new Error("Failed to load models");
    const data = await res.json();

    const modelSelect = document.getElementById("modelSelect");
    const evalModelSelect = document.getElementById("evalModelSelect");
    modelSelect.innerHTML = "";
    evalModelSelect.innerHTML = "<option value=''>ALL (default)</option>";

    data.models.forEach(m => {
      const text = `${m.technique} (${m.id})`;
      modelSelect.appendChild(el("option", { value: m.id, textContent: text }));
      evalModelSelect.appendChild(el("option", { value: m.id, textContent: text }));
    });

    modelSelect.value = data.default_model;

    // auto-build one input per feature column
    const form = document.getElementById("featureForm");
    form.innerHTML = "";
    data.feature_columns.forEach(c => {
      const wrapper = el("div", { className: "feature-input" });
      wrapper.appendChild(el("label", { textContent: c, htmlFor: `f_${c}` }));
      wrapper.appendChild(el("input", { id: `f_${c}`, placeholder: `Enter ${c}`, type: "text" }));
      form.appendChild(wrapper);
    });

    return data;
  } catch (err) {
    alert("Error loading models: " + err.message);
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
    const outPre = document.getElementById("predictOut");

    outContainer.classList.add("hidden");
    outPre.textContent = "";
    setLoading("predictBtn", true);

    try {
      const model_id = document.getElementById("modelSelect").value;
      const features = {};
      featureCols.forEach(c => features[c] = document.getElementById(`f_${c}`).value);

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
      if (label === "1") {
        label = "Cancelled";
        colorClass = "text-danger"; // You might need to add this class to CSS or use inline style
      } else if (label === "0") {
        label = "Not Cancelled";
        colorClass = "text-success"; // You might need to add this class to CSS
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
  const container = document.getElementById("evalOutTable");
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
  const data = await loadModels();
  if (data) {
    await setupPredict(data.feature_columns);
    await setupEval();
  }
})();