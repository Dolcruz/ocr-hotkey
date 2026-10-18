import ctypes
import json
import unittest
from ctypes import wintypes
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ocr_hotkey as app


class HotkeyTests(unittest.TestCase):
    def test_default_hotkey(self):
        self.assertEqual(app.parse_windows_hotkey(app.DEFAULT_HOTKEY), (0x4007, ord("O")))

    def test_function_key_and_modifier_aliases(self):
        self.assertEqual(app.parse_windows_hotkey("control+windows+F24"), (0x400A, 0x87))

    def test_navigation_key(self):
        self.assertEqual(app.parse_windows_hotkey("<alt>+page_down"), (0x4001, 0x22))

    def test_invalid_keys(self):
        for hotkey in ("ctrl", "ctrl+a+b", "ctrl+f25", "ctrl+", "ctrl+é", "ctrl+ß"):
            with self.subTest(hotkey=hotkey), self.assertRaises(ValueError):
                app.parse_windows_hotkey(hotkey)


class MutexTests(unittest.TestCase):
    def test_handle_uses_pointer_sized_windows_type(self):
        create_mutex = Mock(return_value=0x123456789)
        kernel = SimpleNamespace(CreateMutexW=create_mutex)
        with patch.object(ctypes, "WinDLL", return_value=kernel), patch.object(ctypes, "get_last_error", return_value=0):
            self.assertEqual(app.ensure_single_instance(), 0x123456789)
        self.assertIs(create_mutex.restype, wintypes.HANDLE)
        self.assertEqual(create_mutex.argtypes, [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR])

    def test_duplicate_instance_exits_successfully(self):
        kernel = SimpleNamespace(CreateMutexW=Mock(return_value=123))
        with patch.object(ctypes, "WinDLL", return_value=kernel), patch.object(ctypes, "get_last_error", return_value=183):
            with self.assertRaises(SystemExit) as result:
                app.ensure_single_instance()
        self.assertEqual(result.exception.code, 0)


class TextTests(unittest.TestCase):
    def test_text_order_whitespace_and_empty_lines(self):
        self.assertEqual(app.extract_text([{"rec_texts": [" Hello ", "", "World"]}, {"text": "Next"}]), "Hello\nWorld\nNext")

    def test_json_result_object(self):
        result = SimpleNamespace(json=json.dumps({"rec_texts": ["Sample"]}))
        self.assertEqual(app.extract_text(result), "Sample")

    def test_no_text(self):
        self.assertEqual(app.extract_text([{}, {"rec_texts": []}]), "")


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.overlay = app.SelectionOverlay.__new__(app.SelectionOverlay)
        self.overlay.overlays = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": -1280, "top": -200, "width": 1280, "height": 1024},
        ]

    def test_cross_monitor_capture_is_clipped_and_sorted(self):
        self.assertEqual(self.overlay._selected_regions(-100, -100, 200, 100), [(-100, -100, 100, 200), (0, 0, 200, 100)])

    def test_small_and_outside_regions_are_rejected(self):
        self.assertEqual(self.overlay._selected_regions(0, 0, 5, 100), [])
        self.assertEqual(self.overlay._selected_regions(3000, 0, 3100, 100), [])

    def test_minimum_region_is_accepted(self):
        self.assertEqual(self.overlay._selected_regions(0, 0, 6, 6), [(0, 0, 6, 6)])


if __name__ == "__main__":
    unittest.main()
