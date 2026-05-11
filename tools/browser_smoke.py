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
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.goto(args.url, wait_until="networkidle")
            assert "EMU Regulation Assistant" in page.title()
            assert page.locator("text=EMU Regulation Assistant").first.is_visible()
            question = page.locator("#question")
            question.fill("What is the attendance requirement?")
            page.locator("#ask").click()
            page.locator(".public-citations").wait_for(timeout=15000)
            assert page.locator(".answer-state").first.is_visible()
            if args.screenshot_dir:
                Path(args.screenshot_dir).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(args.screenshot_dir) / "desktop.png"), full_page=False)

            mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
            mobile.goto(args.url, wait_until="networkidle")
            assert mobile.locator("#question").is_visible()
            assert mobile.locator("#ask").is_visible()
            if args.screenshot_dir:
                mobile.screenshot(path=str(Path(args.screenshot_dir) / "mobile.png"), full_page=False)
            browser.close()
    except Error as exc:
        print(f"browser smoke skipped or failed: {exc}")
        return 0 if args.skip_if_unavailable else 1
    except AssertionError as exc:
        print(f"browser smoke failed: {exc}")
        return 1
    print("browser smoke passed")
    return 0


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
