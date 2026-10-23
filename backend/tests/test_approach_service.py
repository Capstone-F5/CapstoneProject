"""접근 감지 상태 머신 및 키오스크 개발자 설정 연동 검증(모델·API 없음)."""
import unittest

from core import approach_service as svc
from core.approach_service import ApproachSession, process_frame_result
from core.kiosk_settings import get_kiosk_settings, reset_kiosk_settings, update_kiosk_settings


def frame(session, cane=False, wheel=False):
    return process_frame_result(session, cane, 0.9 if cane else 0.0, wheel, 0.9 if wheel else 0.0)


class ApproachConfirm(unittest.TestCase):
    def setUp(self):
        reset_kiosk_settings()

    def tearDown(self):
        reset_kiosk_settings()

    def test_single_frame_does_not_trigger(self):
        self.assertFalse(frame(ApproachSession(), wheel=True)["mode_on"])

    def test_two_of_four_does_not_trigger(self):
        s = ApproachSession()
        for w in (True, False, True, False):
            r = frame(s, wheel=w)
        self.assertFalse(r["mode_on"])

    def test_three_hits_trigger_wheelchair_gesture(self):
        s = ApproachSession()
        for _ in range(svc.CONFIRM_HITS):
            r = frame(s, wheel=True)
        self.assertTrue(r["mode_on"])
        self.assertEqual(r["mode_action"], "gesture")
        self.assertTrue(r["confirmed"]["wheelchair"])

    def test_three_hits_trigger_white_cane_voice(self):
        s = ApproachSession()
        for _ in range(svc.CONFIRM_HITS):
            r = frame(s, cane=True)
        self.assertTrue(r["mode_on"])
        self.assertEqual(r["mode_action"], "voice")

    def test_latch_until_absent_frames(self):
        s = ApproachSession()
        for _ in range(svc.CONFIRM_HITS):
            frame(s, cane=True)
        s.finish()
        self.assertFalse(frame(s, cane=True)["mode_on"])   # 잠금 중에는 다시 발동하지 않는다
        for _ in range(svc.CONFIRM_WINDOW + svc.REARM_ABSENT_FRAMES):
            frame(s)
        self.assertFalse(s.latched)                        # 대상이 사라지면 해제

    def test_developer_settings_override_confirm_hits_and_mic(self):
        """대시보드 개발자 설정에서 confirm_hits=2로 낮추면 2프레임 연속 감지 시 즉시 확정된다."""
        updated = update_kiosk_settings({
            "mic": {"min_speech_rms": 0.025, "snr_margin": 2.6, "auto_gain_control": False},
            "approach": {
                "confirm_window": 3,
                "confirm_hits": 2,
                "min_box_h": 0.22,
                "wheelchair_confidence": 0.45,
                "person_confidence": 0.55,
                "white_cane_confidence": 0.40,
                "motion_gate_enabled": True,
                "motion_threshold": 0.035,
                "motion_keepalive_sec": 3.5,
            },
        })
        self.assertEqual(updated["mic"]["min_speech_rms"], 0.025)
        self.assertEqual(updated["approach"]["min_box_h"], 0.22)
        self.assertEqual(updated["approach"]["wheelchair_confidence"], 0.45)
        self.assertEqual(updated["approach"]["person_confidence"], 0.55)
        self.assertEqual(updated["approach"]["white_cane_confidence"], 0.40)
        self.assertTrue(updated["approach"]["motion_gate_enabled"])
        self.assertEqual(updated["approach"]["motion_threshold"], 0.035)
        self.assertEqual(updated["approach"]["motion_keepalive_sec"], 3.5)
        self.assertEqual(get_kiosk_settings()["approach"]["confirm_hits"], 2)

        s = ApproachSession()
        self.assertFalse(frame(s, wheel=True)["mode_on"])
        r2 = frame(s, wheel=True)
        self.assertTrue(r2["mode_on"])
        self.assertEqual(r2["mode_action"], "gesture")


if __name__ == "__main__":
    unittest.main()
