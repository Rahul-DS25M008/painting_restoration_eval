"""Small browser fixtures; no notebook execution or scientific data loading."""

import importlib.util
import os
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/check_streamlit_availability.py"
spec = importlib.util.spec_from_file_location("availability", SCRIPT)
availability = importlib.util.module_from_spec(spec)
spec.loader.exec_module(availability)

READY_HTML = '''
<h3>What the evidence supports</h3>
<p>Validated thesis-level benchmark summary</p>
<div data-testid="stImage"><img src="data:image/svg+xml,%3Csvg
xmlns='http://www.w3.org/2000/svg' width='400' height='200'%3E%3C/svg%3E"></div>
'''


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

    def wait(self, timeout=3):
        return availability.wait_for_dashboard(
            self.page, timeout_seconds=timeout, settle_seconds=0, poll_ms=50
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
        self.page.set_content(READY_HTML.split('<div data-testid=')[0])
        with self.assertRaises(TimeoutError):
            self.wait(timeout=0.2)

    def test_visible_streamlit_exception_fails(self):
        self.page.set_content(READY_HTML + '<div data-testid="stException">Error</div>')
        with self.assertRaises(RuntimeError):
            self.wait()


if __name__ == "__main__":
    unittest.main()
