"""Windows integration smoke tests.

GUI tests run only when a Win32 window station is available in the test runner.
No real user files are read, scanned or exported.
"""
import os
import threading
import unittest
import queue

import main


@unittest.skipUnless(os.name == "nt", "Windows-only integration tests")
class WindowsNativeIntegrationTests(unittest.TestCase):
    def test_powershell_optout_does_not_enumerate_installed_software(self):
        script = main.PS_SCRIPT.replace("__COLLECT_SOFTWARE__", "$false")
        result = main.run_powershell_json(script, timeout=90)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("Software", []), [])

    def test_tk_app_starts_with_minimal_scope(self):
        try:
            root = main.Tk()
        except Exception as exc:
            self.skipTest("No interactive Tk window station on CI runner: " + type(exc).__name__)
        try:
            root.withdraw()
            app = main.App(root)
            root.update_idletasks()
            self.assertFalse(app.collection_scope["installed_software"])
            self.assertFalse(app.collection_scope["filesystem_metadata"])
            self.assertEqual(str(app.export_cancel_btn["state"]), "disabled")
        finally:
            root.destroy()

    def test_drive_selector_requires_explicit_optin(self):
        try:
            root = main.Tk()
        except Exception as exc:
            self.skipTest("No interactive Tk window station: " + type(exc).__name__)
        try:
            root.withdraw()
            dialog = main.DriveSelection(root, ["C:\\"])
            self.assertFalse(dialog.include_software.get())
            self.assertFalse(dialog.include_filesystem.get())
            dialog._accept()
            self.assertEqual(dialog.result, ["C:\\"])
            self.assertEqual(dialog.scope["filesystem_metadata"], False)
        finally:
            root.destroy()

    def test_review_window_constructs_without_file_scan(self):
        try:
            root = main.Tk()
        except Exception as exc:
            self.skipTest("No interactive Tk window station: " + type(exc).__name__)
        try:
            root.withdraw()
            fake = {
                "system": {"os": {}, "hardware": {}, "software": [],
                           "drives": [], "python_environments": [],
                           "browser_summary": []},
                "files": [], "folders": [], "warnings": [], "exclusions": [],
                "scan_warnings": [],
                "filesystem_status": "not_collected",
                "filesystem_counts": {"files": 0, "folders": 0, "skipped": 0, "errors": 0,
                                      "warnings": 0, "exclusions": 0},
            }
            window = main.ReviewWindow(root, fake, lambda *_: False)
            root.update_idletasks()
            self.assertTrue(window.winfo_exists())
            self.assertFalse(window.categories["software"].get())
            self.assertFalse(window.categories["files"].get())
            window._close_review()
        finally:
            root.destroy()
