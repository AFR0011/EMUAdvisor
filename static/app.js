const form = document.querySelector("#chat-form");
const askButton = document.querySelector("#ask");
const question = document.querySelector("#question");
const cross = document.querySelector("#cross");
const messages = document.querySelector("#messages");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = question.value.trim();
  if (!value) {
    question.focus();
    return;
  }

  addMessage("user", value);
  const pending = addMessage("assistant", "Retrieving cited regulation evidence...");
  askButton.disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: value,
        cross_corpus: cross.checked,
        session_id: "public-ui",
      }),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const payload = await response.json();
    pending.innerHTML = renderAnswer(payload);
  } catch (error) {
    pending.textContent = `I could not complete the request: ${error.message}`;
  } finally {
    askButton.disabled = false;
  }
});

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.textContent = text;
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function renderAnswer(payload) {
  const citations = (payload.citations || [])
    .map((citation) => `<li><a href="${escapeAttr(citation.source_url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(citation.label || citation.source_title || "Source")}</a></li>`)
    .join("");
  const groups = (payload.evidence_groups || [])
    .map((group) => `<section class="mini-group"><strong>${escapeHtml(group.title || "")}</strong><p>${escapeHtml(group.summary || "")}</p></section>`)
    .join("");
  return `
    <div class="answer-state">${escapeHtml(payload.state || "answer")} / ${escapeHtml((payload.language || "").toUpperCase())}</div>
    <p>${escapeHtml(payload.answer || "")}</p>
    ${groups ? `<div class="mini-groups">${groups}</div>` : ""}
    ${citations ? `<div class="public-citations"><strong>Citations</strong><ol>${citations}</ol></div>` : ""}
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
