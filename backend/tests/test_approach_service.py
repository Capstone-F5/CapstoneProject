"""접근 감지 상태 머신 검증(모델·API 없음): 연속 프레임 확정, 모드 선택, 재시작 잠금."""
import unittest

from core import approach_service as svc
from core.approach_service import ApproachSession, process_frame_result


def frame(session, cane=False, wheel=False):
    return process_frame_result(session, cane, 0.9 if cane else 0.0, wheel, 0.9 if wheel else 0.0)


class ApproachConfirm(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
