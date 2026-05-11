const form = document.querySelector("#chat-form");
const askButton = document.querySelector("#ask");
const question = document.querySelector("#question");
const cross = document.querySelector("#cross");
const messages = document.querySelector("#messages");
const sessionIdInput = document.querySelector("#session-id");
const newSessionBtn = document.querySelector("#new-session-btn");

// Use sessionStorage to persist session across page refreshes
let currentSessionId = sessionStorage.getItem("emuSessionId") || "public-ui";

// Initialize session on load
if (!sessionStorage.getItem("emuSessionId")) {
  sessionStorage.setItem("emuSessionId", currentSessionId);
}

// Function to generate a random session ID
function generateSessionId() {
  return 'session-' + Math.random().toString(36).substr(2, 9);
}

// Function to create a new session
function createNewSession() {
  const newSessionId = generateSessionId();
  sessionIdInput.value = newSessionId;
  currentSessionId = newSessionId;
  sessionStorage.setItem("emuSessionId", newSessionId);
  // Clear the chat history when creating a new session
  messages.innerHTML = '';
  addMessage("assistant", "New session created. You can now ask questions.");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = question.value.trim();
  if (!value) {
    question.focus();
    return;
  }

  addMessage("user", value);
  question.value = "";
  const pending = addMessageWithTyping("assistant");
  askButton.disabled = true;
  form.setAttribute("aria-busy", "true");

  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: value,
        cross_corpus: cross.checked,
        session_id: currentSessionId,
      }),
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(readableError(errorPayload, response.status));
    }

    // Process streaming response
    let fullText = "";
    let citations = null;
    let sessionReceived = false;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const payload = JSON.parse(line);

          if (payload.type === "session") {
            currentSessionId = payload.session_id;
            sessionIdInput.value = currentSessionId;
            sessionStorage.setItem("emuSessionId", currentSessionId);
            sessionReceived = true;
          } else if (payload.type === "citations") {
            citations = payload.citations;
          } else if (payload.type === "casual") {
            // Handle casual greeting response
            removeTypingIndicator(pending);
            pending.classList.add(stateClass("casual"));
            pending.innerHTML = renderCasualAnswer(payload);
          } else if (payload.type === "refusal") {
            removeTypingIndicator(pending);
            pending.classList.add("error");
            pending.textContent = payload.text;
          } else if (payload.type === "generated_delta") {
            // Append streaming text
            fullText += payload.text;
            updateMessageText(pending, fullText, citations);
          } else if (payload.type === "generation_done") {
            removeTypingIndicator(pending);
            pending.classList.add(stateClass("answer"));
            // Ensure citations are rendered
            if (citations) {
              pending.innerHTML = renderAnswer({
                answer: fullText,
                citations: citations,
                state: "answer",
                language: pending.dataset.lang || "en"
              });
            }
          }
        } catch (e) {
          console.error("Failed to parse NDJSON line:", line, e);
        }
      }
    }
  } catch (error) {
    removeTypingIndicator(pending);
    pending.classList.add("error");
    pending.textContent = `I could not complete the request: ${error.message}`;
  } finally {
    askButton.disabled = false;
    form.removeAttribute("aria-busy");
  }
});

// Event listener for the new session button
newSessionBtn.addEventListener("click", createNewSession);

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.textContent = text;
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function addMessageWithTyping(role) {
  const article = document.createElement("article");
  article.className = `message ${role} typing`;
  article.innerHTML = '<span class="typing-text"></span><span class="typing-indicator"><span></span><span></span><span></span></span>';
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function updateMessageText(element, text, citations) {
  const textSpan = element.querySelector(".typing-text");
  if (textSpan) {
    textSpan.textContent = text;
  }
  // Keep typing indicator visible while streaming
  const indicator = element.querySelector(".typing-indicator");
  if (indicator) {
    element.classList.add("streaming");
  }
}

function removeTypingIndicator(element) {
  element.classList.remove("typing", "streaming");
  const indicator = element.querySelector(".typing-indicator");
  if (indicator) {
    indicator.remove();
  }
}

function renderCasualAnswer(payload) {
  return `
    <div class="answer-state">Casual <span>${escapeHtml(payload.category || "greeting").toUpperCase()}</span></div>
    <p>${escapeHtml(payload.text || "")}</p>
  `;
}

function renderAnswer(payload) {
  const citations = (payload.citations || [])
    .map((citation) => `<li><a href="${escapeAttr(citation.source_url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(citation.label || citation.source_title || "Source")}</a><span>${escapeHtml(citation.section_path || citation.article_number || "")}</span></li>`)
    .join("");
  const groups = (payload.evidence_groups || [])
    .map((group) => `<section class="mini-group"><strong>${escapeHtml(group.title || "")}</strong><p>${escapeHtml(group.summary || "")}</p></section>`)
    .join("");
  return `
    <div class="answer-state">${formatState(payload.state)} <span>${escapeHtml((payload.language || "").toUpperCase())}</span></div>
    <p>${escapeHtml(payload.answer || "")}</p>
    ${groups ? `<div class="mini-groups">${groups}</div>` : ""}
    ${citations ? `<div class="public-citations"><strong>Citations</strong><ol>${citations}</ol></div>` : ""}
  `;
}

function formatState(state) {
  const labels = {
    answer: "Answered",
    answer_uncertain: "Answered with uncertainty",
    clarify: "Clarification needed",
    refuse: "Outside demo scope",
    show_conflict: "Source conflict",
  };
  return escapeHtml(labels[state] || state || "Answered");
}

function stateClass(state) {
  return `state-${String(state || "answer").replace(/[^a-z0-9_-]/gi, "")}`;
}

function readableError(payload, status) {
  const details = Array.isArray(payload.detail) ? payload.detail : [];
  if (details.length && details[0].msg) {
    return details[0].msg;
  }
  if (payload.detail) {
    return String(payload.detail);
  }
  return `Request failed: ${status}`;
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
