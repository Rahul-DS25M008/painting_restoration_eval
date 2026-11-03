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
from pathlib import Path
from urllib.parse import urlsplit

APP_URL = "https://fhtw-painting-restoration-main.streamlit.app/"
FALLBACK_URL = APP_URL + "~/+/"
PRIMARY_TIMEOUT_SECONDS = 120
TOTAL_TIMEOUT_SECONDS = 600
READY_HEADING = "How should we judge an AI-restored painting?"
ROOM_LINKS = ("Exhibition Foyer", "Study Design", "Metric Framework", "Model Gallery",
              "Stability Lab", "Trustworthiness", "Case Explorer", "Research Archive")
WAKE_BUTTON = re.compile(r"^Yes, get this app back up!?$", re.IGNORECASE)


def inspect_frame(frame, room="foyer") -> bool:
    """Require real Controlled-300 content, navigation and decoded evidence."""
    for error in frame.locator('[data-testid="stException"]').all():
        if error.is_visible():
            raise RuntimeError("The deployed app displays a Streamlit exception.")
    if room not in {"foyer", "case"}:
        raise ValueError("Unsupported availability room")
    heading = READY_HEADING if room == "foyer" else "Case Explorer"
    if not frame.get_by_role("heading", name=heading, exact=True).is_visible():
        return False
    if not all(frame.get_by_role("link", name=name, exact=True).is_visible() for name in ROOM_LINKS):
        return False
    if room == "foyer":
        if not frame.get_by_role("link", name="Take the guided tour about 6 min", exact=True).is_visible():
            return False
        images = frame.get_by_role("img", name="Juan de Pareja clean controlled reference.", exact=True)
        minimum = 1
    else:
        if not frame.get_by_role("button", name="Select model", exact=True).is_visible():
            return False
        if not frame.get_by_role("button", name="Inspect exact saved metric rows", exact=True).is_visible():
            return False
        images = frame.locator('main[aria-label="Case Explorer evidence room"] button img')
        minimum = 5
    return images.evaluate_all(
        "(images, minimum) => images.filter(img => img.complete && img.naturalWidth >= 50 "
        "&& img.naturalHeight >= 50 && img.getClientRects().length > 0).length >= minimum",
        minimum,
    )


def describe_loading_state(page):
    """Report small DOM facts, without page HTML, data URLs or query strings."""
    from playwright.sync_api import Error as BrowserError

    states = []
    for frame in list(page.frames)[:8]:
        try:
            url = urlsplit(frame.url)
            states.append({
                "frame": ((url.netloc + url.path)[:180]
                          if url.scheme in {"http", "https"} else url.scheme),
                "headings": [text[:120] for text in
                             frame.locator("h1, h2").all_text_contents()[:3]],
                "images": frame.locator("img").evaluate_all(
                    "images => ({total: images.length, decoded: images.filter("
                    "i => i.complete && i.naturalWidth >= 50 && i.naturalHeight >= 50 "
                    "&& i.getClientRects().length > 0).length})"
                ),
            })
        except BrowserError:
            states.append({"frame": "changed during inspection"})
    return states


def wait_for_dashboard(page, *, room="foyer", timeout_seconds=600, settle_seconds=15, poll_ms=2000):
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
                if inspect_frame(frame, room):
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
            print("Loading state: " + json.dumps(describe_loading_state(page)), flush=True)
            next_progress = now + 30
        page.wait_for_timeout(poll_ms)
    print("Final loading state: " + json.dumps(describe_loading_state(page)), flush=True)
    raise TimeoutError(
        "Dashboard did not become ready before the deadline. "
        f"Wake button clicked: {wake_requested}. "
        "Inspect the public app and Streamlit logs; an HTTP response is not enough."
    )


def check_visitor_dialog(frame):
    """One small browser-only interaction; never start the full tour."""
    frame.get_by_role("link", name="Take the guided tour about 6 min", exact=True).click()
    title = frame.get_by_role("heading", name="From a convincing image to a defensible conclusion", exact=True)
    title.wait_for(state="visible", timeout=15000)
    close = frame.get_by_role("button", name="Close visitor guide", exact=True)
    close.press("Escape")
    title.wait_for(state="hidden", timeout=15000)


def open_dashboard(page, *, timeout_seconds=TOTAL_TIMEOUT_SECONDS,
                   primary_timeout_seconds=PRIMARY_TIMEOUT_SECONDS,
                   settle_seconds=15, poll_ms=2000):
    """Try the public entry for two minutes, then the same app's direct route.

    Navigation and rendered readiness share each route's budget. Both attempts
    share the total deadline. Visible application exceptions remain hard failures;
    only loading/transport failures can select the temporary fallback.
    """
    from playwright.sync_api import Error as BrowserError

    deadline = time.monotonic() + timeout_seconds
    primary_error = None
    for url, fallback in ((APP_URL, False), (FALLBACK_URL, True)):
        route_deadline = deadline if fallback else min(
            deadline, time.monotonic() + primary_timeout_seconds
        )

        def remaining():
            seconds = route_deadline - time.monotonic()
            if seconds <= 0:
                raise TimeoutError("Entry-route loading budget exhausted.")
            return seconds

        print(f"Visiting {'fallback' if fallback else 'primary'} entry: {url}", flush=True)
        try:
            page.goto(url, wait_until="domcontentloaded",
                      timeout=max(1, int(min(120, remaining()) * 1000)))
            result = wait_for_dashboard(
                page, timeout_seconds=remaining(), settle_seconds=settle_seconds,
                poll_ms=poll_ms,
            )
        except (TimeoutError, BrowserError) as error:
            # Keep diagnostics short; never dump page HTML or embedded image data.
            reason = f"{type(error).__name__}: {' '.join(str(error).split())[:400]}"
            if fallback:
                raise RuntimeError(
                    f"Neither entry route became ready. Primary: {primary_error}; "
                    f"fallback: {reason}"
                ) from error
            primary_error = reason
            print(f"Primary entry unavailable: {reason}", flush=True)
            print("Public entry did not become ready. Trying the temporary "
                  "direct route; fallback success does not prove the public URL recovered.",
                  flush=True)
            continue
        result.update(
            url=url, primary_url=APP_URL, fallback_used=fallback,
            primary_status="unavailable" if fallback else "ready",
            primary_error=primary_error,
        )
        return result


def write_summary(result):
    """Make degraded public access visible even when fallback checks pass."""
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        return
    mode = ("PASS via temporary fallback — public entry unavailable"
            if result["fallback_used"] else "PASS via public entry")
    with Path(destination).open("a", encoding="utf-8") as output:
        output.write(
            f"## Streamlit availability\n\n**{mode}**\n\n"
            f"- Checked entry: {result['url']}\n"
            f"- Public entry: {result['primary_url']}\n"
            "- Verified: foyer navigation and image, visitor dialog, "
            "Case Explorer's five images and metric control.\n"
            f"- Browser check duration: {result['elapsed_seconds']} seconds.\n\n"
            "The public entry is tried first on every run. Fallback use does not "
            "confirm that the normal public link has recovered.\n"
        )


def main() -> int:
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
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
                result = open_dashboard(
                    page, timeout_seconds=max(1, TOTAL_TIMEOUT_SECONDS - (time.monotonic() - started))
                )
                frame = next(frame for frame in page.frames if inspect_frame(frame))
                check_visitor_dialog(frame)
                # One representative evidence room, not a full regression sweep.
                frame.get_by_role("link", name="Case Explorer", exact=True).click()
                case_result = wait_for_dashboard(page, room="case",
                    timeout_seconds=max(1, TOTAL_TIMEOUT_SECONDS - (time.monotonic() - started)))
                result.update(
                    checked_at_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=round(time.monotonic() - started, 1),
                    checks=["foyer_navigation_and_image", "visitor_dialog_open_and_escape",
                            "case_explorer_five_images_and_metric_control"],
                    case_status=case_result["status"],
                    scope="Lightweight availability smoke; not N35 certification or an uptime guarantee",
                )
                if result["fallback_used"]:
                    print("::warning::Museum checks passed via the temporary direct route. "
                          "The normal public entry did not become ready within its budget.",
                          flush=True)
                write_summary(result)
                print(json.dumps(result, indent=2), flush=True)
                return 0
            finally:
                browser.close()
    except Exception as error:
        print(f"Availability check FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
