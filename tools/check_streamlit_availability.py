"""Visit the deployed app as a browser; never equate HTTP 200 with readiness.

Run in a separate environment with Playwright and Chromium installed. This
script neither imports the application nor reads or alters scientific outputs.
It uses Streamlit's ordinary public wake button, not private management APIs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

APP_URL = "https://fhtw-painting-restoration.streamlit.app/"
READY_HEADING = "What the evidence supports"
WAKE_BUTTON = re.compile(r"^Yes, get this app back up!?$", re.IGNORECASE)


def inspect_frame(frame) -> bool:
    """Require rendered overview evidence and a decoded, visible large image."""
    for error in frame.locator('[data-testid="stException"]').all():
        if error.is_visible():
            raise RuntimeError("The deployed app displays a Streamlit exception.")
    if not frame.get_by_role("heading", name=READY_HEADING, exact=True).is_visible():
        return False
    if not frame.get_by_text(
        "Validated thesis-level benchmark summary", exact=True
    ).is_visible():
        return False
    return frame.locator('[data-testid="stImage"] img').evaluate_all(
        "images => images.some(img => img.complete && img.naturalWidth >= 300 "
        "&& img.naturalHeight >= 150 && img.getClientRects().length > 0)"
    )


def wait_for_dashboard(page, *, timeout_seconds=600, settle_seconds=15, poll_ms=2000):
    """Handle direct or iframe-hosted apps, including delayed wake buttons.

    A short stable-ready interval keeps the browser session open and catches
    late application errors. A missing wake button alone never means success.
    """
    from playwright.sync_api import Error as BrowserError

    deadline = time.monotonic() + timeout_seconds
    ready_since = None
    wake_requested = False
    next_progress = time.monotonic() + 30
    while time.monotonic() < deadline:
        ready = False
        for frame in list(page.frames):
            try:
                wake = frame.get_by_role("button", name=WAKE_BUTTON)
                if not wake_requested and wake.is_visible():
                    wake.click(timeout=5000)
                    wake_requested = True
                    print("Sleep screen detected; requested normal public wake-up.", flush=True)
                if inspect_frame(frame):
                    ready = True
            except BrowserError:
                # Cloud navigation can replace/detach an iframe during startup.
                # Retry until the global deadline rather than reporting success.
                continue
        now = time.monotonic()
        if ready:
            if ready_since is None:
                ready_since = now
            if now - ready_since >= settle_seconds:
                return {"status": "ready", "wake_requested": wake_requested}
        else:
            ready_since = None
        if now >= next_progress:
            print("Waiting for rendered dashboard content and a decoded image...", flush=True)
            next_progress = now + 30
        page.wait_for_timeout(poll_ms)
    raise TimeoutError(
        "Dashboard did not become ready before the deadline. "
        f"Wake button clicked: {wake_requested}. "
        "Inspect the public app and Streamlit logs; an HTTP response is not enough."
    )


def main() -> int:
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
    print(f"Visiting {APP_URL}", flush=True)
    try:
        with sync_playwright() as playwright:
            # Optional installed browser channel is for local verification only.
            channel = os.environ.get("AVAILABILITY_BROWSER_CHANNEL")
            launch_options = {"headless": True}
            if channel:
                launch_options["channel"] = channel
            browser = playwright.chromium.launch(**launch_options)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.set_default_timeout(5000)
                page.goto(APP_URL, wait_until="domcontentloaded", timeout=120000)
                result = wait_for_dashboard(
                    page, timeout_seconds=max(1, 600 - (time.monotonic() - started))
                )
                result.update(
                    url=APP_URL,
                    checked_at_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=round(time.monotonic() - started, 1),
                )
                print(json.dumps(result, indent=2), flush=True)
                return 0
            finally:
                browser.close()
    except Exception as error:
        print(f"Availability check FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
