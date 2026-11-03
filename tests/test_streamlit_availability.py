"""Small browser fixtures; no notebook execution or scientific data loading."""

import importlib.util
import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tools/check_streamlit_availability.py"
spec = importlib.util.spec_from_file_location("availability", SCRIPT)
availability = importlib.util.module_from_spec(spec)
spec.loader.exec_module(availability)

IMAGE = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='200'%3E%3C/svg%3E"
NAV = '<nav>' + ''.join(f'<a href="?room={i}">{name}</a>' for i,name in enumerate(availability.ROOM_LINKS)) + '</nav>'
READY_HTML = NAV + f'''
<h1>{availability.READY_HEADING}</h1>
<a href="#tour" onclick="document.querySelector('dialog').showModal();return false;">Take the guided tour about 6 min</a>
<img alt="Juan de Pareja clean controlled reference." src="{IMAGE}">
<dialog><h2>From a convincing image to a defensible conclusion</h2><button>Close visitor guide</button></dialog>
'''
CASE_HTML = NAV + '<main aria-label="Case Explorer evidence room"><h1>Case Explorer</h1>' + \
    '<button>Select model</button><button>Inspect exact saved metric rows</button>' + \
    ''.join(f'<button><img src="{IMAGE}" alt="Evidence {i}"></button>' for i in range(5)) + '</main>'


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Playwright not installed")
class AvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright

        cls.playwright = sync_playwright().start()
        options = {"headless": True}
        channel = os.environ.get("AVAILABILITY_BROWSER_CHANNEL")
        if channel:
            options["channel"] = channel
        cls.browser = cls.playwright.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def wait(self, timeout=3, room="foyer"):
        return availability.wait_for_dashboard(
            self.page, room=room, timeout_seconds=timeout, settle_seconds=0, poll_ms=50
        )

    def test_ready_direct_page(self):
        self.page.set_content(READY_HTML)
        self.assertEqual(self.wait(), {"status": "ready", "wake_requested": False})

    def test_iframe_and_public_wake_button(self):
        self.page.set_content('<iframe title="app"></iframe>')
        frame = self.page.frames[1]
        frame.set_content('<button>Yes, get this app back up!</button>')
        frame.evaluate(
            "html => document.querySelector('button').onclick = () => "
            "{ document.body.innerHTML = html; }", READY_HTML
        )
        self.assertTrue(self.wait()["wake_requested"])

    def test_shell_without_wake_button_is_not_success(self):
        self.page.set_content('<div id="root">Loading</div>')
        with self.assertRaises(TimeoutError):
            self.wait(timeout=0.2)

    def test_missing_image_is_not_success(self):
        self.page.set_content(READY_HTML.replace(f'<img alt="Juan de Pareja clean controlled reference." src="{IMAGE}">', ''))
        with self.assertRaises(TimeoutError):
            self.wait(timeout=0.2)

    def test_visible_streamlit_exception_fails(self):
        self.page.set_content(READY_HTML + '<div data-testid="stException">Error</div>')
        with self.assertRaises(RuntimeError):
            self.wait()

    def test_pilot_page_is_not_full_version_readiness(self):
        self.page.set_content('<h3>What the evidence supports</h3><p>Validated thesis-level benchmark summary</p>')
        with self.assertRaises(TimeoutError): self.wait(timeout=0.2)

    def test_missing_room_link_is_not_success(self):
        self.page.set_content(READY_HTML.replace('Research Archive', 'Missing room'))
        with self.assertRaises(TimeoutError): self.wait(timeout=0.2)

    def test_broken_image_is_not_success(self):
        self.page.set_content(READY_HTML.replace(IMAGE, 'data:image/png;base64,broken'))
        with self.assertRaises(TimeoutError): self.wait(timeout=0.2)

    def test_visitor_dialog_opens_and_escape_closes(self):
        self.page.set_content(READY_HTML)
        self.wait()
        availability.check_visitor_dialog(self.page.main_frame)
        self.assertFalse(self.page.locator('dialog').is_visible())

    def test_case_evidence_ready(self):
        self.page.set_content(CASE_HTML)
        self.assertEqual(self.wait(room="case")["status"], "ready")

    def test_case_incomplete_images_fail(self):
        self.page.set_content(CASE_HTML.replace(f'<button><img src="{IMAGE}" alt="Evidence 4"></button>', ''))
        with self.assertRaises(TimeoutError): self.wait(timeout=0.2, room="case")

    def test_case_missing_metric_control_fails(self):
        self.page.set_content(CASE_HTML.replace('<button>Inspect exact saved metric rows</button>', ''))
        with self.assertRaises(TimeoutError): self.wait(timeout=0.2, room="case")

    def test_loading_diagnostics_distinguish_broken_images_without_dumping_sources(self):
        self.page.set_content(READY_HTML.replace(IMAGE, 'data:image/png;base64,broken'))
        state = availability.describe_loading_state(self.page)
        self.assertIn(availability.READY_HEADING, state[0]["headings"])
        self.assertEqual(state[0]["images"], {"total": 1, "decoded": 0})
        self.assertNotIn("base64", json.dumps(state))

    def test_late_streamlit_error_during_settle_fails(self):
        self.page.set_content(READY_HTML)
        self.page.evaluate("setTimeout(() => {const e=document.createElement('div');e.dataset.testid='stException';e.textContent='late error';document.body.append(e);},100)")
        with self.assertRaises(RuntimeError):
            availability.wait_for_dashboard(self.page,timeout_seconds=2,settle_seconds=0.5,poll_ms=50)

    def open_entry(self):
        return availability.open_dashboard(
            self.page, timeout_seconds=0.8, primary_timeout_seconds=0.15,
            settle_seconds=0, poll_ms=25,
        )

    def test_ready_primary_never_visits_fallback(self):
        with patch.object(self.page, "goto", side_effect=lambda *a, **kw:
                          self.page.set_content(READY_HTML)) as navigate:
            result = self.open_entry()
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["primary_status"], "ready")
        self.assertEqual(result["url"], availability.APP_URL)
        self.assertIsNone(result["primary_error"])
        self.assertEqual(navigate.call_count, 1)

    def test_stuck_primary_uses_verified_fallback(self):
        def navigate(url, **kwargs):
            self.page.set_content(READY_HTML if url == availability.FALLBACK_URL
                                  else '<div>Loading</div>')
        with patch.object(self.page, "goto", side_effect=navigate) as navigation:
            result = self.open_entry()
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["primary_status"], "unavailable")
        self.assertIn("TimeoutError", result["primary_error"])
        self.assertEqual(result["url"], availability.FALLBACK_URL)
        self.assertEqual([c.args[0] for c in navigation.call_args_list],
                         [availability.APP_URL, availability.FALLBACK_URL])

    def test_navigation_failure_uses_fallback(self):
        from playwright.sync_api import Error as BrowserError

        def navigate(url, **kwargs):
            if url == availability.APP_URL:
                raise BrowserError("net::ERR_CONNECTION_RESET")
            self.page.set_content(READY_HTML)
        with patch.object(self.page, "goto", side_effect=navigate):
            self.assertTrue(self.open_entry()["fallback_used"])

    def test_application_error_is_not_hidden_by_fallback(self):
        with patch.object(self.page, "goto", side_effect=lambda *a, **kw:
                          self.page.set_content('<div data-testid="stException">Error</div>')) as navigate:
            with self.assertRaisesRegex(RuntimeError, "Streamlit exception"):
                self.open_entry()
        self.assertEqual(navigate.call_count, 1)

    def test_both_routes_stuck_fail(self):
        with patch.object(self.page, "goto", side_effect=lambda *a, **kw:
                          self.page.set_content('<div>Loading</div>')) as navigate:
            with self.assertRaisesRegex(RuntimeError, "Neither entry route became ready"):
                self.open_entry()
        self.assertEqual(navigate.call_count, 2)

    def test_fallback_broken_image_is_not_success(self):
        def navigate(url, **kwargs):
            self.page.set_content(
                READY_HTML.replace(IMAGE, 'data:image/png;base64,broken')
                if url == availability.FALLBACK_URL else '<div>Loading</div>'
            )
        with patch.object(self.page, "goto", side_effect=navigate):
            with self.assertRaisesRegex(RuntimeError, "Neither entry route became ready"):
                self.open_entry()


class TargetTests(unittest.TestCase):
    def test_full_version_target(self):
        self.assertEqual(availability.APP_URL, 'https://fhtw-painting-restoration-main.streamlit.app/')

    @unittest.skipUnless(importlib.util.find_spec("playwright"), "Playwright not installed")
    def test_navigation_time_counts_towards_primary_budget(self):
        from unittest.mock import Mock

        clock = [100.0]
        page = Mock()
        page.goto.side_effect = lambda *a, **kw: clock.__setitem__(0, 190.0)
        with patch.object(availability.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(availability, "wait_for_dashboard",
                          return_value={"status": "ready", "wake_requested": False}) as wait:
            availability.open_dashboard(page)
        self.assertEqual(page.goto.call_args.kwargs["timeout"], 120000)
        self.assertEqual(wait.call_args.kwargs["timeout_seconds"], 30)

    def test_fallback_summary_discloses_public_entry_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
                availability.write_summary({
                    "fallback_used": True, "url": availability.FALLBACK_URL,
                    "primary_url": availability.APP_URL, "elapsed_seconds": 160,
                })
            summary = path.read_text(encoding="utf-8")
        self.assertIn("public entry unavailable", summary)
        self.assertIn(availability.FALLBACK_URL, summary)
        self.assertIn("Case Explorer", summary)

    @unittest.skipUnless(importlib.util.find_spec("playwright"), "Playwright not installed")
    def test_fallback_uses_remaining_total_budget(self):
        from unittest.mock import Mock

        clock = [100.0]
        page = Mock()

        def navigate(url, **kwargs):
            clock[0] += 100 if url == availability.APP_URL else 10

        waits = []

        def wait(*args, **kwargs):
            waits.append(kwargs["timeout_seconds"])
            if len(waits) == 1:
                clock[0] += kwargs["timeout_seconds"]
                raise TimeoutError("Primary entry remained loading")
            return {"status": "ready", "wake_requested": False}

        page.goto.side_effect = navigate
        with patch.object(availability.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(availability, "wait_for_dashboard", side_effect=wait):
            result = availability.open_dashboard(page)
        self.assertEqual(waits, [20, 470])
        self.assertTrue(result["fallback_used"])


if __name__ == "__main__":
    unittest.main()
