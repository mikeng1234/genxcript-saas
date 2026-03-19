"""
browser_tools.py
================
Synchronous Playwright browser tools for LangChain agents.
Uses playwright.sync_api — no async, no event loop issues.
"""

import time
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, Playwright

log = logging.getLogger("browser-tools")

# ── Singleton state ────────────────────────────────────────────────────────────
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None


def start_browser(headless: bool = False) -> Page:
    global _playwright, _browser, _page
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=headless)
    ctx = _browser.new_context(viewport={"width": 1280, "height": 900})
    _page = ctx.new_page()
    log.info(f"Browser started (headless={headless})")
    return _page


def stop_browser():
    global _playwright, _browser, _page
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _playwright = _browser = _page = None
    log.info("Browser stopped")


def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Browser not started. Call start_browser() first.")
    return _page


# ── Tool implementations ───────────────────────────────────────────────────────

def tool_navigate(url: str) -> str:
    page = get_page()
    # Strip accidental /login or other paths when agent targets the root app URL
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.path.strip("/").lower() in ("login", "register", "signin"):
        url = urlunparse(parsed._replace(path="/", query="", fragment=""))
        log.info(f"Corrected URL path → {url}")
    page.goto(url, wait_until="networkidle", timeout=30_000)
    time.sleep(1)
    title = page.title()
    return f"Navigated to {url} — page title: '{title}'"


def tool_get_text() -> str:
    page = get_page()
    text = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('body *'))
            .filter(el => el.offsetParent !== null && el.children.length === 0)
            .map(el => el.innerText?.trim())
            .filter(t => t && t.length > 0)
            .join('\\n');
    }""")
    return (text[:4000] if text else "(no visible text)")


def tool_click(text_or_selector: str) -> str:
    page = get_page()
    # Try by text
    try:
        page.get_by_text(text_or_selector, exact=False).first.click(timeout=5_000)
        time.sleep(1.5)
        return f"Clicked text: '{text_or_selector}'"
    except Exception:
        pass
    # Try by role button
    try:
        page.get_by_role("button", name=text_or_selector).first.click(timeout=5_000)
        time.sleep(1.5)
        return f"Clicked button: '{text_or_selector}'"
    except Exception:
        pass
    # Try as CSS selector
    try:
        page.click(text_or_selector, timeout=5_000)
        time.sleep(1.5)
        return f"Clicked selector: '{text_or_selector}'"
    except Exception as e:
        return f"ERROR: Could not click '{text_or_selector}': {e}"


def tool_fill(label_or_placeholder: str, value: str) -> str:
    page = get_page()
    # Try placeholder
    try:
        page.get_by_placeholder(label_or_placeholder).first.fill(value, timeout=5_000)
        return f"Filled '{label_or_placeholder}' = '{value}'"
    except Exception:
        pass
    # Try label
    try:
        page.get_by_label(label_or_placeholder).first.fill(value, timeout=5_000)
        return f"Filled label '{label_or_placeholder}' = '{value}'"
    except Exception:
        pass
    return f"ERROR: Could not find input '{label_or_placeholder}'"


def tool_wait(seconds: float) -> str:
    time.sleep(float(seconds))
    return f"Waited {seconds}s"


def tool_get_url() -> str:
    return get_page().url


def tool_scroll(direction: str = "down") -> str:
    page = get_page()
    key = "PageDown" if direction == "down" else "PageUp"
    page.keyboard.press(key)
    time.sleep(0.5)
    return f"Scrolled {direction}"
