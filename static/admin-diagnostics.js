/** Diagnostics mode: /ask, metrics, corpus status. */
(function () {
  const { authedFetch, readableError, escapeHtml, formatPercent } = window.EmuShared;

  const askButton = document.querySelector("#diag-ask");
  const question = document.querySelector("#diag-question");
  const mode = document.querySelector("#diag-mode");
  const answerStyle = document.querySelector("#diag-answer-style");
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
  const auditCount = document.querySelector("#audit-count");
  const corpusDetails = document.querySelector("#corpus-details");
  const modeDetails = document.querySelector("#mode-details");
  const analyticsDetails = document.querySelector("#analytics-details");

  if (!askButton) {
    return;
  }

  document.querySelectorAll("[data-view-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      window.EmuShared.setViewMode(tab.dataset.viewTab);
      if (tab.dataset.viewTab === "diagnostics") {
        loadMetrics();
      }
    });
  });

  if (window.EmuShared.getViewMode() === "diagnostics") {
    loadMetrics();
  }

  askButton.addEventListener("click", async () => {
    statusEl.textContent = "Retrieving cited evidence...";
    answerEl.textContent = "";
    evidenceGroupsEl.innerHTML = "";
    generatedEl.textContent = "";
    citationsEl.innerHTML = "";
    diagnosticJson.textContent = "";
    askButton.disabled = true;

    try {
      const response = await authedFetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.value,
          mode: mode.value,
          answer_style: answerStyle.value,
          session_id: "admin-ui",
        }),
      });
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(readableError(errorPayload, response.status));
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
      const [corpusResponse, metricsResponse, modesResponse, analyticsResponse] = await Promise.all([
        authedFetch("/corpus/status"),
        authedFetch("/metrics"),
        authedFetch("/metrics/modes"),
        authedFetch("/analytics"),
      ]);
      const corpus = await corpusResponse.json();
      const metrics = await metricsResponse.json();
      const modes = await modesResponse.json();
      const analytics = await analyticsResponse.json();
      corpusCount.textContent = corpus.chunk_count ?? "-";
      top5.textContent = formatPercent(metrics.retrieval_top5);
      reject.textContent = formatPercent(metrics.rejection_accuracy);
      latency.textContent =
        metrics.extractive_latency_p50_ms == null ? "-" : `${metrics.extractive_latency_p50_ms}ms`;
      auditCount.textContent = analytics.events ?? "-";
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
      analyticsDetails.innerHTML = renderDetails({
        events: analytics.events,
        event_types: JSON.stringify(analytics.event_types || {}),
        answer_modes: JSON.stringify(analytics.answer_modes || {}),
        languages: JSON.stringify(analytics.languages || {}),
        out_of_scope_routes: analytics.out_of_scope_or_refusal_routes,
        latency_p50_ms: analytics.latency_p50_ms,
        latency_p95_ms: analytics.latency_p95_ms,
      });
      modeDetails.innerHTML = renderModes(modes);
    } catch {
      corpusCount.textContent = "-";
      auditCount.textContent = "-";
    }

    try {
      const llmResponse = await authedFetch("/llm/status");
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
      .map(
        ([key, value]) =>
          `<div><dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${escapeHtml(value ?? "-")}</dd></div>`
      )
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
            <div><dt>fanout</dt><dd>${escapeHtml(String(preset.retrieval_fanout))}</dd></div>
            <div><dt>rerank</dt><dd>${preset.rerank_enabled ? "on" : "off"}</dd></div>
            <div><dt>context</dt><dd>${escapeHtml(String(preset.max_context_chunks))}</dd></div>
            <div><dt>score</dt><dd>${score}</dd></div>
          </dl>
        </article>
      `;
      })
      .join("");
  }
})();
