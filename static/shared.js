/** Shared helpers for EMU Regulation Assistant UI. */
(function (global) {
  const THEME_KEY = "emu_theme";
  const ADMIN_TOKEN_KEY = "emu_admin_token";
  const THEMES = new Set(["light", "dark"]);

  function getAdminToken() {
    return window.sessionStorage.getItem(ADMIN_TOKEN_KEY) || "";
  }

  function setAdminToken(token) {
    const normalized = String(token || "").trim();
    if (normalized) {
      window.sessionStorage.setItem(ADMIN_TOKEN_KEY, normalized);
    } else {
      window.sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    }
    return normalized;
  }

  function clearAdminToken() {
    window.sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  }

  function authedFetch(url, options = {}) {
    const token = getAdminToken();
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return fetch(url, { ...options, headers });
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

  function systemTheme() {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function normalizeTheme(theme) {
    return THEMES.has(theme) ? theme : systemTheme();
  }

  function getTheme() {
    return normalizeTheme(window.localStorage.getItem(THEME_KEY));
  }

  function updateThemeToggle(theme) {
    const toggle = document.querySelector("#theme-toggle");
    if (!toggle) {
      return;
    }
    const isDark = theme === "dark";
    toggle.setAttribute("aria-pressed", isDark ? "true" : "false");
    toggle.setAttribute("title", isDark ? "Switch to light mode" : "Switch to dark mode");
    const label = toggle.querySelector(".theme-toggle-text");
    if (label) {
      label.textContent = isDark ? "Light mode" : "Dark mode";
    }
  }

  function setTheme(theme) {
    const normalized = normalizeTheme(theme);
    window.localStorage.setItem(THEME_KEY, normalized);
    document.documentElement.dataset.theme = normalized;
    updateThemeToggle(normalized);
    return normalized;
  }

  function applyTheme() {
    const theme = getTheme();
    document.documentElement.dataset.theme = theme;
    updateThemeToggle(theme);
    return theme;
  }

  function toggleTheme() {
    return setTheme(getTheme() === "dark" ? "light" : "dark");
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

  function formatPercent(value) {
    return value == null ? "-" : `${Math.round(value * 100)}%`;
  }

  function getViewMode() {
    const params = new URLSearchParams(window.location.search);
    const view = params.get("view");
    if (view === "diagnostics" || view === "user") {
      return view;
    }
    const stored = window.sessionStorage.getItem("emu_admin_view");
    if (stored === "diagnostics" || stored === "user") {
      return stored;
    }
    return "user";
  }

  function setViewMode(mode) {
    window.sessionStorage.setItem("emu_admin_view", mode);
    const url = new URL(window.location.href);
    url.searchParams.set("view", mode);
    window.history.replaceState({}, document.title, url.pathname + url.search);
    document.body.classList.remove("mode-user", "mode-diagnostics");
    document.body.classList.add(mode === "diagnostics" ? "mode-diagnostics" : "mode-user");
    document.querySelectorAll("[data-view-tab]").forEach((tab) => {
      const active = tab.dataset.viewTab === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    const userPanel = document.querySelector("#user-panel");
    const diagPanel = document.querySelector("#diagnostics-panel");
    if (userPanel) {
      userPanel.hidden = mode !== "user";
    }
    if (diagPanel) {
      diagPanel.hidden = mode !== "diagnostics";
    }
  }

  applyTheme();

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme();
    document.querySelector("#theme-toggle")?.addEventListener("click", toggleTheme);
  });

  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (!window.localStorage.getItem(THEME_KEY)) {
      applyTheme();
    }
  });

  global.EmuShared = {
    authedFetch,
    readableError,
    escapeHtml,
    escapeAttr,
    formatPercent,
    getAdminToken,
    setAdminToken,
    clearAdminToken,
    getTheme,
    getViewMode,
    setTheme,
    setViewMode,
    toggleTheme,
  };
})(window);
fetch("/health")
  .then((response) => response.json())
  .then((status) => {
    const banner = document.querySelector("#fixture-banner");
    if (banner && status.fixture === true) {
      banner.hidden = false;
    }
  })
  .catch(() => {});
