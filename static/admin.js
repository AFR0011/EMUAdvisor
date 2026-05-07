const askButton = document.querySelector("#ask");
const question = document.querySelector("#question");
const mode = document.querySelector("#mode");
const answerStyle = document.querySelector("#answer-style");
const cross = document.querySelector("#cross");
const statusEl = document.querySelector("#status");
const answerEl = document.querySelector("#answer");
const evidenceGroupsEl = document.querySelector("#evidence-groups");
const generatedEl = document.querySelector("#generated");
const citationsEl = document.querySelector("#citations");
const diagnosticJson = document.querySelector("#diagnostic-json");
const corpusCount = document.querySelector("#corpus-count");
const top5 = document.querySelector("#top5");
const reject = document.querySelector("#reject");
const latency = document.querySelector("#latency");
const llmStatus = document.querySelector("#llm-status");
const corpusDetails = document.querySelector("#corpus-details");
const modeDetails = document.querySelector("#mode-details");

loadMetrics();

askButton.addEventListener("click", async () => {
  statusEl.textContent = "Retrieving cited evidence...";
  answerEl.textContent = "";
  evidenceGroupsEl.innerHTML = "";
  generatedEl.textContent = "";
  citationsEl.innerHTML = "";
  diagnosticJson.textContent = "";
  askButton.disabled = true;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question.value,
        mode: mode.value,
        answer_style: answerStyle.value,
        cross_corpus: cross.checked,
        session_id: "admin-ui",
      }),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = await response.json();
    statusEl.textContent = `${payload.mode} / ${payload.answer_type || "direct"} - ${payload.route.query_language.toUpperCase()} - ${payload.latency_ms}ms`;
    answerEl.textContent = payload.extractive_answer || payload.answer;
    evidenceGroupsEl.innerHTML = renderEvidenceGroups(payload.evidence_groups || []);
    if (payload.generated_answer) {
      generatedEl.textContent = `Generated (${payload.timings.generation_ms}ms):\n${payload.generated_answer}`;
    } else if (payload.generated_error) {
      generatedEl.textContent = `Generated answer unavailable: ${payload.generated_error}`;
    }
    citationsEl.innerHTML = payload.citations
      .map((citation) => `<div class="citation">${escapeHtml(citation.label)}</div>`)
      .join("");
    diagnosticJson.textContent = JSON.stringify(
      {
        route: payload.route,
        timings: payload.timings,
        hit_count: payload.hits.length,
        top_hits: payload.hits.slice(0, 5).map((hit) => ({
          score: hit.score,
          dense_score: hit.dense_score,
          lexical_score: hit.lexical_score,
          source_title: hit.source_title,
          section_path: hit.section_path,
          source_url: hit.source_url,
        })),
      },
      null,
      2
    );
  } catch (error) {
    statusEl.textContent = "Error";
    answerEl.textContent = error.message;
  } finally {
    askButton.disabled = false;
  }
});

async function loadMetrics() {
  llmStatus.textContent = "checking";
  try {
    const [corpusResponse, metricsResponse, modesResponse] = await Promise.all([
      fetch("/corpus/status"),
      fetch("/metrics"),
      fetch("/metrics/modes"),
    ]);
    const corpus = await corpusResponse.json();
    const metrics = await metricsResponse.json();
    const modes = await modesResponse.json();
    corpusCount.textContent = corpus.chunk_count ?? "-";
    top5.textContent = formatPercent(metrics.retrieval_top5);
    reject.textContent = formatPercent(metrics.rejection_accuracy);
    latency.textContent = metrics.extractive_latency_p50_ms == null ? "-" : `${metrics.extractive_latency_p50_ms}ms`;
    corpusDetails.innerHTML = renderDetails({
      source: corpus.source,
      runtime_profile: corpus.runtime_profile,
      vector_backend: corpus.vector_backend,
      embedding_model: corpus.embedding_model,
      documents: corpus.document_count,
      sources: corpus.source_count,
      languages: JSON.stringify(corpus.languages || {}),
      source_types: JSON.stringify(corpus.source_types || {}),
    });
    modeDetails.innerHTML = renderModes(modes);
  } catch {
    corpusCount.textContent = "-";
  }

  try {
    const llmResponse = await fetch("/llm/status");
    const llm = await llmResponse.json();
    llmStatus.textContent = llm.model_available ? "available" : "fallback";
    llmStatus.classList.toggle("warn", !llm.model_available);
  } catch {
    llmStatus.textContent = "fallback";
    llmStatus.classList.add("warn");
  }
}

function renderEvidenceGroups(groups) {
  if (!groups.length) {
    return "";
  }
  return groups
    .map(
      (group) => `
        <article class="evidence-group">
          <h3>${escapeHtml(group.title)}</h3>
          <p>${escapeHtml(group.summary)}</p>
        </article>
      `
    )
    .join("");
}

function renderDetails(values) {
  return Object.entries(values)
    .map(([key, value]) => `<div><dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${escapeHtml(value ?? "-")}</dd></div>`)
    .join("");
}

function renderModes(payload) {
  const modes = payload.modes || {};
  return Object.entries(modes)
    .map(([name, preset]) => {
      const latest = payload.results?.[name] || {};
      const score = latest.total_score == null ? "-" : Number(latest.total_score).toFixed(2);
      return `
        <article class="mode-card">
          <h3>${escapeHtml(name)}</h3>
          <p>${escapeHtml(preset.local_llm_label || "")}</p>
          <dl>
            <div><dt>fanout</dt><dd>${escapeHtml(preset.retrieval_fanout)}</dd></div>
            <div><dt>rerank</dt><dd>${preset.rerank_enabled ? "on" : "off"}</dd></div>
            <div><dt>context</dt><dd>${escapeHtml(preset.max_context_chunks)}</dd></div>
            <div><dt>score</dt><dd>${score}</dd></div>
          </dl>
        </article>
      `;
    })
    .join("");
}

function formatPercent(value) {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
