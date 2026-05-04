const askButton = document.querySelector("#ask");
const question = document.querySelector("#question");
const mode = document.querySelector("#mode");
const cross = document.querySelector("#cross");
const statusEl = document.querySelector("#status");
const answerEl = document.querySelector("#answer");
const citationsEl = document.querySelector("#citations");

askButton.addEventListener("click", async () => {
  statusEl.textContent = "Retrieving cited evidence...";
  answerEl.textContent = "";
  citationsEl.innerHTML = "";
  askButton.disabled = true;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question.value,
        mode: mode.value,
        cross_corpus: cross.checked,
        session_id: "local-ui",
      }),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = await response.json();
    statusEl.textContent = `${payload.mode} · ${payload.route.query_language.toUpperCase()} · ${payload.latency_ms}ms`;
    answerEl.textContent = payload.answer;
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

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
