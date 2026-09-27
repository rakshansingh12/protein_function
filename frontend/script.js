// Protein Function Classifier -- frontend logic. Vanilla JS, no dependencies.

const EXAMPLE_SEQUENCE = `>sp|P00918|CAH2_HUMAN Carbonic anhydrase 2
MSHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAKYDPSLKPLSVSYDQATSLRI
LNNGHAFNVEFDDSQDKAVLKGGPLDGTYRLIQFHFHWGSLDGQGSEHTVDKKKYAAEL
HLVHWNTKYGDFGKAVQQPDGLAVLGIFLKVGSAKPGLQKVVDVLDSIKTKGKSADFTN
FDPRGLLPESLDYWTYPGSLTTPPLLECVTWIVLKEPISVSSEQVLKFRKLNFNGEGEP
EELMVDNWRPAQPLKNRQIKASFK`;

const STANDARD_AMINO_ACIDS = new Set("ACDEFGHIKLMNPQRSTVWY".split(""));

const els = {
  sequenceInput: document.getElementById("sequence-input"),
  inputError: document.getElementById("input-error"),
  predictBtn: document.getElementById("predict-btn"),
  clearBtn: document.getElementById("clear-btn"),
  exampleBtn: document.getElementById("example-btn"),
  predictionSection: document.getElementById("prediction-section"),
  predictionResult: document.getElementById("prediction-result"),
  datasetBanner: document.getElementById("dataset-match-banner"),
  notesList: document.getElementById("notes-list"),
  modelPerformanceTable: document.getElementById("model-performance-table"),
  modelPerformanceCaption: document.getElementById("model-performance-caption"),
  similarSection: document.getElementById("similar-proteins-section"),
  similarTable: document.getElementById("similar-proteins-table"),
  comparisonSection: document.getElementById("comparison-section"),
  comparisonTable: document.getElementById("comparison-table"),
  instabilityNote: document.getElementById("instability-note"),
  motifSection: document.getElementById("motif-section"),
  motifDisclaimer: document.getElementById("motif-disclaimer"),
  motifResults: document.getElementById("motif-results"),
  serineNote: document.getElementById("serine-note"),
  sequenceDisplay: document.getElementById("sequence-display"),
  enrichmentSection: document.getElementById("enrichment-section"),
  enrichmentResults: document.getElementById("enrichment-results"),
};

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function cleanSequence(raw) {
  const lines = raw.split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => !line.startsWith(">"));
  return lines.join("").toUpperCase().replace(/[^A-Z]/g, "");
}

function validateSequence(cleaned) {
  if (!cleaned) {
    return "Sequence is empty.";
  }
  if (cleaned.length < 50) {
    return `Sequence is too short (${cleaned.length} residues). Minimum is 50.`;
  }
  const invalid = [...new Set(cleaned.split(""))].filter((ch) => !STANDARD_AMINO_ACIDS.has(ch));
  if (invalid.length) {
    return `Sequence contains non-standard residues: ${invalid.join(", ")}.`;
  }
  return null;
}

function setBusy(busy) {
  els.predictBtn.disabled = busy;
  els.clearBtn.disabled = busy;
  els.exampleBtn.disabled = busy;
  els.predictBtn.textContent = busy ? "Predicting..." : "Predict";
}

function showInputError(message) {
  if (message) {
    els.inputError.textContent = message;
    els.inputError.hidden = false;
  } else {
    els.inputError.hidden = true;
    els.inputError.textContent = "";
  }
}

async function loadModelInfo() {
  try {
    const response = await fetch("/api/model-info");
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }
    const data = await response.json();
    renderModelInfo(data);
  } catch (err) {
    els.modelPerformanceTable.textContent = `Could not load model info: ${err.message}`;
  }
}

function renderModelInfo(data) {
  const rows = Object.entries(data.models).map(([name, m]) => {
    const randomCol = m.random_split_roc_auc !== undefined
      ? m.random_split_roc_auc.toFixed(4)
      : "n/a";
    const highlight = name === data.best_model ? " highlight" : "";
    return `<tr class="${highlight.trim()}">
      <td>${escapeHtml(name)}</td>
      <td>${m.roc_auc.toFixed(4)}</td>
      <td>${m.f1.toFixed(4)}</td>
      <td>${randomCol}</td>
    </tr>`;
  }).join("");

  els.modelPerformanceTable.innerHTML = `
    <table>
      <thead><tr><th>Model</th><th>ROC-AUC</th><th>F1</th><th>ROC-AUC (random split)</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  els.modelPerformanceCaption.textContent =
    `Homology-aware split (split_mode: ${data.split_mode}). ` +
    `Size-only baseline (molecular weight + length) test ROC-AUC ` +
    `${data.size_baseline.test_roc_auc.toFixed(4)}, lift of the full model ` +
    `+${data.size_baseline.lift_of_full_model.toFixed(4)}.`;
}

function renderPrediction(data) {
  els.predictionSection.hidden = false;

  const cls = data.prediction === "ENZYME" ? "enzyme" : "non-enzyme";
  const pct = (data.probability_enzyme * 100).toFixed(1);
  els.predictionResult.innerHTML = `
    <div class="result-banner ${cls}">${data.prediction}</div>
    <p>Probability of enzyme: <strong>${pct}%</strong>
       (confidence ${(data.confidence * 100).toFixed(1)}%)</p>
    <p>Model: ${escapeHtml(data.model_name)}</p>`;

  if (data.dataset_match) {
    const m = data.dataset_match;
    els.datasetBanner.hidden = false;
    const splitNote = m.in_training_split
      ? "This protein was in the model's training split."
      : "This protein was in the test split, not used to fit the model.";
    els.datasetBanner.innerHTML = `
      <div class="dataset-banner">
        Matches a known protein:
        <a href="https://www.uniprot.org/uniprotkb/${encodeURIComponent(m.accession)}/entry" target="_blank" rel="noopener">${escapeHtml(m.accession)}</a>
        (${escapeHtml(m.evidence_class)}). ${splitNote}
      </div>`;
  } else {
    els.datasetBanner.hidden = true;
    els.datasetBanner.innerHTML = "";
  }

  els.notesList.innerHTML = data.notes.map((n) => `<li>${escapeHtml(n)}</li>`).join("");

  renderSimilarProteins(data.similar_proteins);
  renderComparison(data.comparison);
  renderMotifs(data.motifs, data.cleaned_sequence);
  renderEnrichment(data.dataset_match);
}

function renderSimilarProteins(rows) {
  if (!rows || !rows.length) {
    els.similarSection.hidden = true;
    return;
  }
  els.similarSection.hidden = false;
  const body = rows.map((r) => `
    <tr>
      <td><a href="https://www.uniprot.org/uniprotkb/${encodeURIComponent(r.accession)}/entry" target="_blank" rel="noopener">${escapeHtml(r.accession)}</a></td>
      <td>${escapeHtml(r.class)}</td>
      <td>${r.distance.toFixed(3)}</td>
      <td>${r.similarity.toFixed(1)}%</td>
    </tr>`).join("");
  els.similarTable.innerHTML = `
    <table>
      <thead><tr><th>Accession</th><th>Class</th><th>Distance</th><th>Similarity</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

function renderComparison(rows) {
  if (!rows || !rows.length) {
    els.comparisonSection.hidden = true;
    return;
  }
  els.comparisonSection.hidden = false;

  const blocks = rows.map((row) => {
    const isGravy = row.property === "gravy";
    const values = [row.input, row.enzyme_mean, row.non_enzyme_mean];
    const maxAbs = Math.max(...values.map((v) => Math.abs(v)), 1e-9);

    function barHtml(label, value, cssClass) {
      if (isGravy) {
        const pct = (Math.abs(value) / maxAbs) * 50;
        const side = value >= 0 ? `left: 50%; width: ${pct}%;` : `right: 50%; width: ${pct}%;`;
        return `
          <div class="bar-row">
            <div class="bar-label">${label}: ${value.toFixed(3)}</div>
            <div class="bar-track centered"><div class="bar-fill ${cssClass}" style="${side}"></div></div>
          </div>`;
      }
      const pct = (Math.abs(value) / maxAbs) * 100;
      return `
        <div class="bar-row">
          <div class="bar-label">${label}: ${value.toFixed(3)}</div>
          <div class="bar-track"><div class="bar-fill ${cssClass}" style="left: 0; width: ${pct}%;"></div></div>
        </div>`;
    }

    return `
      <div class="comparison-block">
        <h3>${escapeHtml(row.property)}</h3>
        ${barHtml("Input", row.input, "input")}
        ${barHtml(`Enzyme avg (±${row.enzyme_std.toFixed(3)})`, row.enzyme_mean, "enzyme")}
        ${barHtml(`Non-enzyme avg (±${row.non_enzyme_std.toFixed(3)})`, row.non_enzyme_mean, "non-enzyme")}
      </div>`;
  }).join("");

  els.comparisonTable.innerHTML = blocks;

  const instabilityRow = rows.find((r) => r.property === "instability_index");
  if (instabilityRow) {
    const status = instabilityRow.input > 40 ? "above 40 (conventionally \"unstable\")" : "at or below 40 (conventionally stable)";
    els.instabilityNote.textContent = `Instability index for this input is ${status}.`;
  } else {
    els.instabilityNote.textContent = "";
  }
}

function renderMotifs(motifResult, cleanedSequence) {
  els.motifSection.hidden = false;
  els.motifDisclaimer.textContent = motifResult.disclaimer;

  const allNames = new Set([
    ...motifResult.matches.map((m) => m.name),
    ...motifResult.not_found,
  ]);

  const matchesByName = {};
  for (const m of motifResult.matches) {
    matchesByName[m.name] = matchesByName[m.name] || [];
    matchesByName[m.name].push(m);
  }

  const blocks = [...allNames].map((name) => {
    const hits = matchesByName[name];
    if (!hits) {
      return `<p class="motif-match">No ${escapeHtml(name)} motif detected.</p>`;
    }
    return hits.map((hit) => {
      const rateText = hit.class_rates
        ? ` Class match rate: enzymes ${(hit.class_rates.enzyme_pct * 100).toFixed(1)}%, ` +
          `non-enzymes ${(hit.class_rates.non_enzyme_pct * 100).toFixed(1)}% ` +
          `(ratio ${hit.class_rates.ratio_enzyme_over_non_enzyme.toFixed(3)}).`
        : "";
      return `<p class="motif-match">
        <span class="name">&#10003; ${escapeHtml(hit.name)}</span>
        position ${hit.start}&ndash;${hit.end}, matched "${escapeHtml(hit.match)}".
        ${escapeHtml(hit.explanation)}${rateText}
      </p>`;
    }).join("");
  }).join("");

  els.motifResults.innerHTML = blocks;

  const serineMotif = motifResult.matches.concat(
    motifResult.not_found.map((name) => ({ name }))
  ).find((m) => m.name === "Serine protease-related (simplified)");
  els.serineNote.textContent = serineMotif
    ? "Note: the serine-protease pattern is a low-specificity placeholder (4 residues) and matches many proteins by chance; it is not the official PROSITE pattern."
    : "";

  renderSequenceWithHighlights(cleanedSequence, motifResult.matches);
}

function renderSequenceWithHighlights(sequence, matches) {
  // Wrap at 60 residues; wrap matched ranges in spans. Positions from the
  // API are 1-based inclusive; built here from plain text, never server HTML.
  const highlightMask = new Array(sequence.length).fill(false);
  for (const m of matches) {
    for (let i = m.start - 1; i < m.end; i++) {
      if (i >= 0 && i < highlightMask.length) highlightMask[i] = true;
    }
  }

  let html = "";
  for (let i = 0; i < sequence.length; i++) {
    if (i > 0 && i % 60 === 0) html += "\n";
    const ch = escapeHtml(sequence[i]);
    html += highlightMask[i] ? `<span class="motif">${ch}</span>` : ch;
  }
  els.sequenceDisplay.innerHTML = html;
}

async function renderEnrichment(datasetMatch) {
  if (!datasetMatch) {
    els.enrichmentSection.hidden = false;
    els.enrichmentResults.innerHTML =
      "<p>Enrichment runs only for sequences that exactly match a known UniProt " +
      "entry. Predicting structures for novel sequences is out of scope.</p>";
    return;
  }

  els.enrichmentSection.hidden = false;
  els.enrichmentResults.innerHTML = "<p>Loading database records&hellip;</p>";

  try {
    const response = await fetch(`/api/enrich/${encodeURIComponent(datasetMatch.accession)}`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    renderEnrichmentData(data);
  } catch (err) {
    els.enrichmentResults.innerHTML = `<p>Could not load database records: ${escapeHtml(err.message)}</p>`;
  }
}

function renderEnrichmentData(data) {
  if (data.message) {
    els.enrichmentResults.innerHTML = `<p>${escapeHtml(data.message)}</p>`;
    return;
  }

  let html = "";

  if (data.uniprot) {
    html += `<div class="enrichment-block">
      <h3>UniProt</h3>
      <p>${escapeHtml(data.uniprot.protein_name || "n/a")} &mdash; ${escapeHtml(data.uniprot.organism || "n/a")}</p>
      ${data.uniprot.subcellular_locations.length
        ? `<p>Subcellular location: ${data.uniprot.subcellular_locations.map(escapeHtml).join(", ")}</p>`
        : ""}
    </div>`;
  }

  if (data.pdb && data.pdb.length) {
    const items = data.pdb.map((p) => `<li><a href="${p.url}" target="_blank" rel="noopener">${escapeHtml(p.id)}</a> (${escapeHtml(p.method || "n/a")}, ${escapeHtml(p.resolution || "n/a")})</li>`).join("");
    html += `<div class="enrichment-block"><h3>PDB structures</h3><ul>${items}</ul></div>`;
  }

  if (data.kegg) {
    const pathways = data.kegg.pathways.map((p) => `<li><a href="${p.url}" target="_blank" rel="noopener">${escapeHtml(p.name)}</a></li>`).join("");
    html += `<div class="enrichment-block">
      <h3>KEGG</h3>
      ${data.kegg.ec.length ? `<p>EC: ${data.kegg.ec.map(escapeHtml).join(", ")}</p>` : ""}
      ${pathways ? `<ul>${pathways}</ul>` : "<p>No pathway membership recorded.</p>"}
    </div>`;
  }

  if (data.alphafold) {
    html += `<div class="enrichment-block">
      <h3>AlphaFold</h3>
      <p>Mean pLDDT: ${data.alphafold.mean_plddt.toFixed(2)}, fraction pLDDT &lt; 50: ${(data.alphafold.fraction_plddt_very_low * 100).toFixed(1)}%</p>
      <p>Structures are retrieved from AlphaFold DB, not predicted here.
         <a href="${data.alphafold.url}" target="_blank" rel="noopener">View predicted 3D structure at AlphaFold DB</a></p>
    </div>`;
  }

  els.enrichmentResults.innerHTML = html || "<p>No additional database records found.</p>";
}

async function handlePredict() {
  const raw = els.sequenceInput.value;
  const cleaned = cleanSequence(raw);
  const error = validateSequence(cleaned);
  if (error) {
    showInputError(error);
    return;
  }
  showInputError(null);
  setBusy(true);

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sequence: raw }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `Server returned ${response.status}`);
    }
    renderPrediction(data);
  } catch (err) {
    showInputError(err.message);
  } finally {
    setBusy(false);
  }
}

function handleClear() {
  els.sequenceInput.value = "";
  showInputError(null);
  els.predictionSection.hidden = true;
  els.similarSection.hidden = true;
  els.comparisonSection.hidden = true;
  els.motifSection.hidden = true;
  els.enrichmentSection.hidden = true;
}

function handleExample() {
  els.sequenceInput.value = EXAMPLE_SEQUENCE;
  showInputError(null);
}

els.predictBtn.addEventListener("click", handlePredict);
els.clearBtn.addEventListener("click", handleClear);
els.exampleBtn.addEventListener("click", handleExample);

loadModelInfo();
