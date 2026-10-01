"""Small browser fixtures; no notebook execution or scientific data loading."""

import importlib.util
import os
import unittest
from pathlib import Path

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

    def test_late_streamlit_error_during_settle_fails(self):
        self.page.set_content(READY_HTML)
        self.page.evaluate("setTimeout(() => {const e=document.createElement('div');e.dataset.testid='stException';e.textContent='late error';document.body.append(e);},100)")
        with self.assertRaises(RuntimeError):
            availability.wait_for_dashboard(self.page,timeout_seconds=2,settle_seconds=0.5,poll_ms=50)


class TargetTests(unittest.TestCase):
    def test_full_version_target(self):
        self.assertEqual(availability.APP_URL, 'https://fhtw-painting-restoration-main.streamlit.app/')


if __name__ == "__main__":
    unittest.main()
