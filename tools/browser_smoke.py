"""Optional Playwright browser smoke for the static EMU Advisor demo UI."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


def main() -> int:
    args = build_parser().parse_args()
    proc: Optional[subprocess.Popen[str]] = None
    try:
        if args.start_server:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "emu_advisor.server:app", "--host", args.host, "--port", str(args.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if not wait_for_health(args.url, timeout_s=args.wait_s):
                print("browser smoke skipped: server did not become healthy")
                return 0 if args.skip_if_unavailable else 1
        return run_playwright_smoke(args)
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def run_playwright_smoke(args) -> int:
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        print("browser smoke skipped: Python Playwright is not installed")
        return 0 if args.skip_if_unavailable else 1

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            screenshot_dir = Path(args.screenshot_dir) if args.screenshot_dir else None
            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            admin_url = args.url.rstrip("/") + "/admin?view=user"
            page.goto(admin_url, wait_until="networkidle")
            assert "EMU Regulation Assistant" in page.title()
            assert page.locator("#user-panel").is_visible()
            set_theme(page, "light")
            exercise_user_chat(page)
            assert_readable_controls(page)
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir / "desktop-light.png"), full_page=False)
            set_theme(page, "dark")
            exercise_user_chat(page)
            assert_readable_controls(page)
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir / "desktop-dark.png"), full_page=False)

            mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
            mobile.goto(admin_url, wait_until="networkidle")
            set_theme(mobile, "light")
            assert mobile.locator("#user-question").is_visible()
            assert mobile.locator("#user-send").is_visible()
            assert_readable_controls(mobile)
            if screenshot_dir:
                mobile.screenshot(path=str(screenshot_dir / "mobile-light.png"), full_page=False)
            set_theme(mobile, "dark")
            assert mobile.locator("#user-question").is_visible()
            assert mobile.locator("#user-send").is_visible()
            assert_readable_controls(mobile)
            if screenshot_dir:
                mobile.screenshot(path=str(screenshot_dir / "mobile-dark.png"), full_page=False)
            browser.close()
    except Error as exc:
        print(f"browser smoke skipped or failed: {exc}")
        return 0 if args.skip_if_unavailable else 1
    except AssertionError as exc:
        print(f"browser smoke failed: {exc}")
        return 1
    print("browser smoke passed")
    return 0


def set_theme(page, theme: str) -> None:
    page.evaluate(
        """theme => {
            window.localStorage.setItem("emu_theme", theme);
            window.EmuShared?.setTheme?.(theme);
        }""",
        theme,
    )
    page.reload(wait_until="networkidle")
    assert page.evaluate("document.documentElement.dataset.theme") == theme


def exercise_user_chat(page) -> None:
    question = page.locator("#user-question")
    question.fill("What is the attendance requirement?")
    send = page.locator("#user-send")
    send.scroll_into_view_if_needed()
    page_y_before = page.evaluate("window.scrollY")
    send.click()
    page.locator(".answer-state").first.wait_for(timeout=15000)
    assert page.locator(".answer-text, .public-citations").first.is_visible()
    wait_for_send_ready(page, timeout_s=15)
    state = page.evaluate(
        """before => {
            const messages = document.querySelector("#messages");
            return {
                activeId: document.activeElement?.id || "",
                pageYBefore: before,
                pageYAfter: window.scrollY,
                messagesClientHeight: messages.clientHeight,
                messagesScrollHeight: messages.scrollHeight,
                messagesOverflowY: getComputedStyle(messages).overflowY,
                viewportHeight: window.innerHeight
            };
        }""",
        page_y_before,
    )
    assert state["activeId"] == "user-question", f"question focus not restored: {state}"
    assert state["messagesOverflowY"] in {"auto", "scroll"}, f"messages area is not scrollable: {state}"
    assert state["messagesClientHeight"] <= state["viewportHeight"] * 0.72, f"messages area is unbounded: {state}"
    assert state["pageYAfter"] - state["pageYBefore"] <= 80, f"page jumped after streaming: {state}"


def wait_for_send_ready(page, *, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.evaluate("!document.querySelector('#user-send')?.disabled"):
            return
        time.sleep(0.1)
    raise AssertionError("send button did not re-enable after streaming")


def assert_readable_controls(page) -> None:
    selectors = [
        "#history-btn",
        "#export-btn",
        "#export-format",
        "#new-session-btn",
        "#advanced-toggle",
        "#theme-toggle",
        ".view-tab.is-active",
        ".view-tab:not(.is-active)",
        ".admin-link",
        "#user-send",
        ".message.assistant",
        ".message.user",
    ]
    checks = page.evaluate(CONTRAST_SCRIPT, selectors)
    failures = [item for item in checks if item["visible"] and item["ratio"] < 4.5]
    assert not failures, "low contrast controls: " + ", ".join(
        f"{item['selector']}={item['ratio']:.2f}" for item in failures
    )


CONTRAST_SCRIPT = """selectors => {
    const rootStyle = getComputedStyle(document.documentElement);
    const bodyStyle = getComputedStyle(document.body);
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");

    function parseColor(color) {
        context.fillStyle = "#000000";
        context.fillStyle = color.trim();
        const normalized = context.fillStyle;
        if (normalized.startsWith("#")) {
            const value = normalized.slice(1);
            const parts = value.length === 3
                ? value.split("").map((ch) => parseInt(ch + ch, 16))
                : [value.slice(0, 2), value.slice(2, 4), value.slice(4, 6)].map((part) => parseInt(part, 16));
            return [parts[0], parts[1], parts[2], 1];
        }
        const match = normalized.match(/rgba?\\(([^)]+)\\)/);
        if (!match) {
            return [0, 0, 0, 0];
        }
        const parts = match[1].split(",").map((part) => Number(part.trim()));
        return [parts[0], parts[1], parts[2], parts.length > 3 ? parts[3] : 1];
    }

    function composite(foreground, background) {
        const alpha = foreground[3] + background[3] * (1 - foreground[3]);
        if (alpha === 0) {
            return [0, 0, 0, 0];
        }
        return [
            (foreground[0] * foreground[3] + background[0] * background[3] * (1 - foreground[3])) / alpha,
            (foreground[1] * foreground[3] + background[1] * background[3] * (1 - foreground[3])) / alpha,
            (foreground[2] * foreground[3] + background[2] * background[3] * (1 - foreground[3])) / alpha,
            alpha,
        ];
    }

    function luminance(color) {
        const values = color.slice(0, 3).map((value) => {
            const channel = value / 255;
            return channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
        });
        return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    }

    function ratio(foreground, background) {
        const light = Math.max(luminance(foreground), luminance(background));
        const dark = Math.min(luminance(foreground), luminance(background));
        return (light + 0.05) / (dark + 0.05);
    }

    function baseBackground(element) {
        const rect = element.getBoundingClientRect();
        const absoluteY = rect.top + window.scrollY + rect.height / 2;
        const band = Number.parseFloat(bodyStyle.getPropertyValue("--admin-header-band")) || 0;
        const token = absoluteY <= band ? "--header-bg" : "--paper";
        return parseColor(bodyStyle.getPropertyValue(token) || rootStyle.getPropertyValue(token));
    }

    function resolvedBackground(element) {
        const layers = [];
        let node = element;
        while (node && node.nodeType === Node.ELEMENT_NODE) {
            layers.push(parseColor(getComputedStyle(node).backgroundColor));
            node = node.parentElement;
        }
        let background = baseBackground(element);
        for (const layer of layers.reverse()) {
            background = composite(layer, background);
        }
        return background;
    }

    return selectors.map((selector) => {
        const element = document.querySelector(selector);
        if (!element) {
            return { selector, visible: false, ratio: 99 };
        }
        const rect = element.getBoundingClientRect();
        const visible = rect.width > 0 && rect.height > 0;
        const foreground = parseColor(getComputedStyle(element).color);
        const background = resolvedBackground(element);
        return { selector, visible, ratio: ratio(foreground, background) };
    });
}"""


def wait_for_health(url: str, *, timeout_s: int) -> bool:
    health_url = url.rstrip("/") + "/health"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an optional Playwright smoke against the EMU Advisor UI.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--wait-s", type=int, default=30)
    parser.add_argument("--skip-if-unavailable", action="store_true")
    parser.add_argument("--screenshot-dir", default=None)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
