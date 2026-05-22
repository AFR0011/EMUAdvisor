/** User-mode regulation chat (streaming /chat). */
(function () {
  const { escapeHtml, escapeAttr, readableError } = window.EmuShared;

  const form = document.querySelector("#chat-form");
  const sendButton = document.querySelector("#user-send");
  const question = document.querySelector("#user-question");
  const messages = document.querySelector("#messages");
  const sessionIdInput = document.querySelector("#session-id");
  const newSessionBtn = document.querySelector("#new-session-btn");
  const historyBtn = document.querySelector("#history-btn");
  const exportBtn = document.querySelector("#export-btn");
  const exportFormat = document.querySelector("#export-format");
  const advancedToggle = document.querySelector("#advanced-toggle");
  const advancedPanel = document.querySelector("#advanced-panel");

  if (!form || !messages) {
    return;
  }

  let currentSessionId = sessionStorage.getItem("emuSessionId") || "user-ui";
  let messageCounter = 0;
  const stickyScrollThreshold = 96;

  if (!sessionStorage.getItem("emuSessionId")) {
    sessionStorage.setItem("emuSessionId", currentSessionId);
  }
  if (sessionIdInput) {
    sessionIdInput.value = currentSessionId;
  }

  function restoreCurrentSessionIfAvailable() {
    fetch(`/chat/session/${encodeURIComponent(currentSessionId)}`)
      .then((r) => r.json())
      .then((payload) => {
        if (payload.messages && payload.messages.length > 0) {
          renderSessionMessages(payload);
        }
      })
      .catch(() => {});
  }

  function generateSessionId() {
    return `session-${Math.random().toString(36).slice(2, 11)}`;
  }

  function createNewSession() {
    const newSessionId = generateSessionId();
    if (sessionIdInput) {
      sessionIdInput.value = newSessionId;
    }
    currentSessionId = newSessionId;
    sessionStorage.setItem("emuSessionId", newSessionId);
    messages.innerHTML = "";
    addMessage("assistant", "New session created. Ask a question about EMU regulations.");
    showHistoryPanel(false);
  }

  function showHistoryPanel(show) {
    const panel = document.querySelector("#history-panel");
    if (panel) {
      panel.hidden = !show;
    }
  }

  function renderSessionMessages(payload) {
    const transcript = payload.messages || [];
    messages.innerHTML = "";
    if (!transcript.length) {
      addMessage("assistant", "New session created. Ask a question about EMU regulations.");
      return;
    }
    transcript.forEach((msg) => {
      addMessage(msg.role === "user" ? "user" : "assistant", msg.text || "");
    });
  }

  function loadSessionFromHistory(sessionId) {
    currentSessionId = sessionId;
    if (sessionIdInput) {
      sessionIdInput.value = sessionId;
    }
    sessionStorage.setItem("emuSessionId", sessionId);
    showHistoryPanel(false);
    fetch(`/chat/session/${encodeURIComponent(sessionId)}`)
      .then((r) => r.json())
      .then(renderSessionMessages)
      .catch(() => {
        messages.innerHTML = "";
        addMessage("assistant", `Session ${sessionId} loaded. Continue the conversation below.`);
      });
  }

  function addMessage(role, text) {
    const stickToBottom = shouldStickToBottom();
    const article = document.createElement("article");
    article.className = `message ${role}`;
    article.innerHTML = `<p>${escapeHtml(text)}</p>`;
    messages.appendChild(article);
    scrollMessagesToBottom(stickToBottom);
    return article;
  }

  function addMessageWithTyping(role) {
    const stickToBottom = shouldStickToBottom();
    const article = document.createElement("article");
    article.className = `message ${role} typing`;
    article.dataset.msgId = `msg-${messageCounter++}`;
    article.innerHTML = `
      <div class="answer-body"></div>
      <span class="typing-indicator"><span></span><span></span><span></span></span>
    `;
    messages.appendChild(article);
    scrollMessagesToBottom(stickToBottom);
    return article;
  }

  function shouldStickToBottom() {
    return messages.scrollHeight - messages.scrollTop - messages.clientHeight <= stickyScrollThreshold;
  }

  function scrollMessagesToBottom(enabled) {
    if (!enabled) {
      return;
    }
    window.requestAnimationFrame(() => {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function answerBody(element) {
    return element.querySelector(".answer-body");
  }

  function formatState(state) {
    const labels = {
      answer: "Answered",
      answer_uncertain: "Answered with uncertainty",
      clarify: "Clarification needed",
      refuse: "Outside scope",
      show_conflict: "Source conflict",
      casual: "Casual",
      retrieving: "Searching",
      generating: "Thinking",
    };
    return escapeHtml(labels[state] || state || "Answered");
  }

  function stateClass(state) {
    return `state-${String(state || "answer").replace(/[^a-z0-9_-]/gi, "")}`;
  }

  function renderAnswer(payload) {
    const answerText = payload.text || payload.answer || "";
    const extractiveText = payload.extractive_answer || payload.extractive_text || "";
    const showExtractive = extractiveText && extractiveText !== answerText;
    const citations = (payload.citations || [])
      .map(
        (citation) => `
      <li>
        <a href="${escapeAttr(citation.source_url || "#")}" target="_blank" rel="noreferrer">
          ${escapeHtml(citation.label || citation.source_title || "Source")}
        </a>
        <span>${escapeHtml(citation.section_path || citation.article_number || "")}</span>
      </li>
    `
      )
      .join("");
    const groups = (payload.evidence_groups || [])
      .map(
        (group) => `
      <section class="mini-group">
        <strong>${escapeHtml(group.title || "")}</strong>
        <p>${escapeHtml(group.summary || "")}</p>
      </section>
    `
      )
      .join("");
    const suggestions = payload.suggestions?.questions || payload.questions || [];
    const suggestionsHtml =
      suggestions.length > 0
        ? `<div class="suggestion-chips">
        <span class="eyebrow">Try asking:</span>
        ${suggestions
          .map(
            (q) =>
              `<button type="button" class="suggestion-chip" data-question="${escapeAttr(q)}">${escapeHtml(q)}</button>`
          )
          .join("")}
      </div>`
        : "";
    const supportingId = `supporting-${messageCounter++}`;
    const supportingHtml = [
      showExtractive
        ? `<section class="extractive-result"><h3>Extractive result</h3><p>${escapeHtml(extractiveText)}</p></section>`
        : "",
      groups ? `<section><h3>Evidence groups</h3><div class="mini-groups">${groups}</div></section>` : "",
      citations ? `<section><h3>Citations</h3><ol class="citations-list">${citations}</ol></section>` : "",
    ].join("");

    return `
    <div class="answer-state">${formatState(payload.mode || payload.state)} <span>${escapeHtml(
      (payload.language || payload.query_language || "").toUpperCase()
    )}</span></div>
    ${
      answerText
        ? `<p class="answer-text">${escapeHtml(answerText)}</p>`
        : ""
    }
    ${
      supportingHtml
        ? `<div class="public-supporting-results"><button type="button" class="toggle-supporting-results" aria-expanded="false" aria-controls="${supportingId}">Show evidence</button><div id="${supportingId}" class="supporting-results is-collapsed" hidden>${supportingHtml}</div></div>`
        : ""
    }
    ${suggestionsHtml}
  `;
  }

  function renderCasualAnswer(payload) {
    return `
    <div class="answer-state">Casual <span>${escapeHtml((payload.category || "message").toUpperCase())}</span></div>
    <p class="answer-text">${escapeHtml(payload.text || "")}</p>
  `;
  }

  function setAnswerHtml(element, html, state) {
    const stickToBottom = shouldStickToBottom();
    const body = answerBody(element);
    if (body) {
      body.innerHTML = html;
    } else {
      element.innerHTML = html;
    }
    element.classList.remove("typing", "streaming");
    const indicator = element.querySelector(".typing-indicator");
    if (indicator) {
      indicator.remove();
    }
    if (state) {
      element.classList.add(stateClass(state));
    }
    scrollMessagesToBottom(stickToBottom);
  }

  function setStreamingText(element, text) {
    const stickToBottom = shouldStickToBottom();
    let body = answerBody(element);
    if (!body) {
      element.innerHTML = `<div class="answer-body"><p class="answer-text"></p></div>`;
      body = answerBody(element);
    }
    let textNode = body.querySelector(".answer-text");
    if (!textNode) {
      textNode = document.createElement("p");
      textNode.className = "answer-text";
      body.appendChild(textNode);
    }
    textNode.textContent = text;
    element.classList.add("streaming");
    scrollMessagesToBottom(stickToBottom);
  }

  function finalizeAssistantMessage(element, payload) {
    setAnswerHtml(element, renderAnswer(payload), payload.mode || payload.state || "answer");
  }

  function exportSession(format = "markdown") {
    fetch("/chat/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, format }),
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `emu-chat-${currentSessionId}.${format === "html" ? "html" : "md"}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
  }

  restoreCurrentSessionIfAvailable();

  function toggleSupportingResults(button) {
    const panel = button.nextElementSibling;
    if (panel && panel.classList.contains("supporting-results")) {
      const shouldShow = panel.hidden;
      panel.hidden = !shouldShow;
      panel.classList.toggle("is-collapsed", !shouldShow);
      button.setAttribute("aria-expanded", shouldShow ? "true" : "false");
      button.textContent = shouldShow ? "Hide evidence" : "Show evidence";
    }
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
    sendButton.disabled = true;
    form.setAttribute("aria-busy", "true");

    let extractivePayload = null;
    let generatedText = "";
    let suggestions = [];
    let terminalRendered = false;

    try {
      const response = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: value,
          session_id: currentSessionId,
        }),
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(readableError(errorPayload, response.status));
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }
          let payload;
          try {
            payload = JSON.parse(line);
          } catch (err) {
            console.error("NDJSON parse error", line, err);
            continue;
          }

          if (payload.type === "session") {
            currentSessionId = payload.session_id;
            sessionStorage.setItem("emuSessionId", currentSessionId);
            if (sessionIdInput) {
              sessionIdInput.value = currentSessionId;
            }
          } else if (payload.type === "retrieving") {
            setStreamingText(pending, "Searching regulation sources...");
          } else if (payload.type === "extractive_answer") {
            extractivePayload = {
              ...payload,
              extractive_answer: payload.text || "",
            };
          } else if (payload.type === "generating") {
            setStreamingText(pending, "Preparing answer...");
          } else if (payload.type === "generated_delta" && payload.text) {
            generatedText += payload.text;
            setStreamingText(pending, generatedText);
          } else if (payload.type === "generated_done") {
            const finalText = payload.text || generatedText || extractivePayload?.text || "";
            if (finalText) {
              generatedText = finalText;
            }
          } else if (payload.type === "suggestions") {
            suggestions = payload.questions || [];
          } else if (payload.type === "casual") {
            setAnswerHtml(pending, renderCasualAnswer(payload), "casual");
            extractivePayload = { state: "casual" };
            terminalRendered = true;
          } else if (payload.type === "refusal") {
            pending.classList.add("error");
            setAnswerHtml(pending, `<p class="answer-text">${escapeHtml(payload.text || "")}</p>`, "refuse");
            terminalRendered = true;
          } else if (payload.type === "done") {
            if (extractivePayload && !terminalRendered) {
              finalizeAssistantMessage(pending, {
                ...extractivePayload,
                text: generatedText || extractivePayload.text,
                extractive_answer: extractivePayload.extractive_answer || extractivePayload.text,
                suggestions: { questions: suggestions },
              });
            }
          }
        }
      }
    } catch (error) {
      pending.classList.add("error");
      setAnswerHtml(pending, `<p class="answer-text">${escapeHtml(error.message)}</p>`, "refuse");
    } finally {
      sendButton.disabled = false;
      form.removeAttribute("aria-busy");
      question.focus({ preventScroll: true });
    }
  });

  newSessionBtn?.addEventListener("click", createNewSession);

  historyBtn?.addEventListener("click", () => {
    fetch("/chat/sessions")
      .then((r) => r.json())
      .then((sessions) => {
        const list = document.querySelector("#history-list");
        if (list) {
          list.innerHTML = sessions
            .map(
              (s) => `
            <li>
              <button type="button" class="history-item" data-session="${escapeAttr(s.session_id)}">
                <strong>${escapeHtml(s.session_id)}</strong>
                <small>${s.message_count} messages</small>
              </button>
            </li>
          `
            )
            .join("");
        }
        showHistoryPanel(true);
      });
  });

  exportBtn?.addEventListener("click", () => {
    exportSession(exportFormat?.value || "markdown");
  });

  advancedToggle?.addEventListener("click", () => {
    const open = advancedPanel?.hidden !== false;
    if (advancedPanel) {
      advancedPanel.hidden = !open;
    }
    advancedToggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  messages.addEventListener("click", (event) => {
    if (event.target.classList.contains("suggestion-chip")) {
      const questionText = event.target.dataset.question;
      if (questionText) {
        question.value = questionText;
        question.focus();
      }
    }
    if (event.target.classList.contains("toggle-supporting-results")) {
      toggleSupportingResults(event.target);
    }
    if (event.target.id === "close-history-btn" || event.target.closest("#close-history-btn")) {
      showHistoryPanel(false);
    }
    const historyItem = event.target.closest(".history-item");
    if (historyItem?.dataset.session) {
      loadSessionFromHistory(historyItem.dataset.session);
    }
  });

  document.querySelectorAll("[data-view-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      window.EmuShared.setViewMode(tab.dataset.viewTab);
    });
  });

  window.EmuShared.setViewMode(window.EmuShared.getViewMode());
})();
