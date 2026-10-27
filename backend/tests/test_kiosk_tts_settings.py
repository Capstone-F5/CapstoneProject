"""음성 배속 설정(tts 섹션)의 검증·저장 왕복. 파일·서버 없이 모듈 함수만 쓴다(저장 파일은 임시 경로로 돌린다)."""
import json
import tempfile
import unittest
from pathlib import Path

from core import kiosk_settings as K


class SanitizeTts(unittest.TestCase):
    def tts(self, **kw):
        return K._sanitize({"tts": kw})["tts"]

    def test_defaults(self):
        self.assertEqual(K._sanitize({})["tts"], {"default_speed": 1.0, "min_speed": 0.7, "max_speed": 1.5})

    def test_values_inside_range_are_kept(self):
        self.assertEqual(self.tts(default_speed=1.2, min_speed=0.6, max_speed=1.8),
                         {"default_speed": 1.2, "min_speed": 0.6, "max_speed": 1.8})

    def test_out_of_range_is_clamped(self):
        t = self.tts(default_speed=9, min_speed=0.1, max_speed=9)
        self.assertEqual((t["min_speed"], t["max_speed"], t["default_speed"]), (0.5, 2.0, 2.0))
        t = self.tts(default_speed=0.01, min_speed=5, max_speed=0.2)
        self.assertEqual((t["min_speed"], t["max_speed"], t["default_speed"]), (1.0, 1.0, 1.0))   # 최소는 1.0까지, 최대는 1.0부터

    def test_default_always_between_min_and_max(self):
        for d in (0.5, 0.8, 1.0, 1.4, 2.0):
            t = self.tts(default_speed=d, min_speed=0.9, max_speed=1.3)
            self.assertLessEqual(t["min_speed"], t["default_speed"])
            self.assertLessEqual(t["default_speed"], t["max_speed"])
        self.assertEqual(self.tts(default_speed=1.8, min_speed=0.9, max_speed=1.3)["default_speed"], 1.3)
        self.assertEqual(self.tts(default_speed=0.6, min_speed=0.9, max_speed=1.3)["default_speed"], 0.9)

    def test_min_never_exceeds_max(self):
        for lo in (0.5, 0.8, 1.0):
            for hi in (1.0, 1.4, 2.0):
                t = self.tts(min_speed=lo, max_speed=hi)
                self.assertLessEqual(t["min_speed"], t["max_speed"])

    def test_bad_types_fall_back(self):
        for bad in ("fast", None, float("nan"), float("inf"), [], {}):
            t = self.tts(default_speed=bad, min_speed=bad, max_speed=bad)
            self.assertEqual(t, {"default_speed": 1.0, "min_speed": 0.7, "max_speed": 1.5}, repr(bad))
        self.assertEqual(K._sanitize({"tts": "garbage"})["tts"], {"default_speed": 1.0, "min_speed": 0.7, "max_speed": 1.5})

    def test_rounded_to_two_decimals_and_numeric_strings_accepted(self):
        t = self.tts(default_speed="1.234", min_speed=0.7, max_speed=1.5)
        self.assertEqual(t["default_speed"], 1.23)

    def test_other_sections_unaffected(self):
        s = K._sanitize({"tts": {"default_speed": 1.2}})
        self.assertEqual(s["mic"]["min_active_ms"], 120)
        self.assertEqual(s["gesture"]["target_fps"], 15)


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = (K._LOG_DIR, K._SETTINGS_FILE, K._cached_settings)
        K._LOG_DIR = Path(self.tmp.name)
        K._SETTINGS_FILE = K._LOG_DIR / "kiosk_dev_settings.json"
        K._cached_settings = None

    def tearDown(self):
        K._LOG_DIR, K._SETTINGS_FILE, K._cached_settings = self._saved
        self.tmp.cleanup()

    def test_update_persists_and_survives_reload(self):
        out = K.update_kiosk_settings({"tts": {"default_speed": 1.3, "min_speed": 0.8, "max_speed": 1.6}})
        self.assertEqual(out["tts"], {"default_speed": 1.3, "min_speed": 0.8, "max_speed": 1.6})
        on_disk = json.loads(K._SETTINGS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["tts"]["default_speed"], 1.3)
        K._cached_settings = None   # 서버 재시작과 같다
        self.assertEqual(K.get_kiosk_settings()["tts"]["max_speed"], 1.6)

    def test_partial_update_keeps_other_tts_fields_and_rechecks_range(self):
        K.update_kiosk_settings({"tts": {"default_speed": 1.4, "max_speed": 1.5}})
        out = K.update_kiosk_settings({"tts": {"max_speed": 1.2}})   # 최대를 낮추면 기본도 따라 내려온다
        self.assertEqual((out["tts"]["default_speed"], out["tts"]["max_speed"]), (1.2, 1.2))

    def test_old_file_without_tts_gets_defaults(self):
        K._SETTINGS_FILE.write_text(json.dumps({"debug_mode": True, "mic": {"min_active_ms": 200}}), encoding="utf-8")
        s = K.get_kiosk_settings()
        self.assertEqual(s["tts"], {"default_speed": 1.0, "min_speed": 0.7, "max_speed": 1.5})
        self.assertEqual(s["mic"]["min_active_ms"], 200)

    def test_reset_restores_defaults(self):
        K.update_kiosk_settings({"tts": {"default_speed": 1.4}})
        self.assertEqual(K.reset_kiosk_settings()["tts"]["default_speed"], 1.0)
        self.assertFalse(K._SETTINGS_FILE.exists())


if __name__ == "__main__":
    unittest.main()
