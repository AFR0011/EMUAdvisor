const askButton = document.querySelector("#ask");
const question = document.querySelector("#question");
const mode = document.querySelector("#mode");
const answerStyle = document.querySelector("#answer-style");
const cross = document.querySelector("#cross");
const statusEl = document.querySelector("#status");
const answerEl = document.querySelector("#answer");
const generatedEl = document.querySelector("#generated");
const citationsEl = document.querySelector("#citations");
const corpusCount = document.querySelector("#corpus-count");
const top5 = document.querySelector("#top5");
const reject = document.querySelector("#reject");
const latency = document.querySelector("#latency");

loadMetrics();

askButton.addEventListener("click", async () => {
  statusEl.textContent = "Retrieving cited evidence...";
  answerEl.textContent = "";
  generatedEl.textContent = "";
  citationsEl.innerHTML = "";
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
        session_id: "local-ui",
      }),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = await response.json();
    statusEl.textContent = `${payload.mode} · ${payload.route.query_language.toUpperCase()} · ${payload.latency_ms}ms`;
    answerEl.textContent = payload.extractive_answer || payload.answer;
    if (payload.generated_answer) {
      generatedEl.textContent = `Generated (${payload.timings.generation_ms}ms):\n${payload.generated_answer}`;
    } else if (payload.generated_error) {
      generatedEl.textContent = `Generated answer unavailable: ${payload.generated_error}`;
    }
    citationsEl.innerHTML = payload.citations
      .map((citation) => `<div class="citation">${escapeHtml(citation.label)}</div>`)
      .join("");
  } catch (error) {
    statusEl.textContent = "Error";
    answerEl.textContent = error.message;
  } finally {
    askButton.disabled = false;
  }
});

async function loadMetrics() {
  try {
    const [corpusResponse, metricsResponse] = await Promise.all([fetch("/corpus/status"), fetch("/metrics")]);
    const corpus = await corpusResponse.json();
    const metrics = await metricsResponse.json();
    corpusCount.textContent = corpus.chunk_count ?? "-";
    top5.textContent = formatPercent(metrics.retrieval_top5);
    reject.textContent = formatPercent(metrics.rejection_accuracy);
    latency.textContent = metrics.extractive_latency_p50_ms == null ? "-" : `${metrics.extractive_latency_p50_ms}ms`;
  } catch {
    corpusCount.textContent = "-";
  }
}

function formatPercent(value) {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
