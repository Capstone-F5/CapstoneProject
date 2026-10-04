"""STT 환각 필터 검증(API 호출 없음). 기준 수치는 2026-10-04 whisper-1 실험: 환각 구간 no_speech_prob 0.85~0.97, 실제 말소리 0.00~0.40."""
import unittest
from types import SimpleNamespace as NS

from core.stt_service import NO_SPEECH_DROP, _drop_no_speech, _is_hallucination


def seg(text, p):
    return NS(text=text, no_speech_prob=p)


class DropNoSpeech(unittest.TestCase):
    def test_threshold_default_sits_between_real_speech_and_hallucination(self):
        self.assertGreater(NO_SPEECH_DROP, 0.40)   # 실험에서 정상 발화의 최댓값(짧은 "네", 언어 자동)
        self.assertLess(NO_SPEECH_DROP, 0.85)      # 환각 구간의 최솟값

    def test_pure_hallucination_is_dropped(self):
        text, peak = _drop_no_speech([seg("Thank you for watching.", 0.9)], 0.7)
        self.assertEqual((text, peak), ("", 0.9))

    def test_real_speech_is_untouched(self):
        for p in (0.0, 0.1, 0.4):
            self.assertEqual(_drop_no_speech([seg("치즈버거 하나 줘.", p)], 0.7)[0], None, p)   # None = 원문 그대로

    def test_mixed_keeps_only_real_part(self):
        """말 뒤에 이어 붙은 환각 구간(예: 말 끝에 "시청해주셔서 감사합니다")만 제거한다."""
        text, _ = _drop_no_speech([seg("치즈버거 하나 줘.", 0.05), seg("시청해주셔서 감사합니다.", 0.95)], 0.7)
        self.assertEqual(text, "치즈버거 하나 줘.")

    def test_works_for_any_language(self):
        for t in ("ありがとうございました", "感谢观看", "Спасибо за просмотр"):
            self.assertEqual(_drop_no_speech([seg(t, 0.93)], 0.7)[0], "", t)

    def test_no_segments_or_missing_probability(self):
        self.assertEqual(_drop_no_speech(None, 0.7), (None, None))
        self.assertEqual(_drop_no_speech([], 0.7), (None, None))
        self.assertEqual(_drop_no_speech([NS(text="네")], 0.7)[0], None)   # 확률이 없으면 건드리지 않는다
        self.assertEqual(_drop_no_speech([{"text": "x", "no_speech_prob": 0.9}], 0.7)[0], "")   # 딕셔너리 구간도 처리


class HallucinationPhrases(unittest.TestCase):
    def test_known_hallucinations(self):
        for t in [
            "Thank you for watching.", "thank you for watching!", "Thanks for watching",   # 실험에서 나온 영어 환각
            "you", "You.", "bye", ".", "...", "…",
            "시청해주셔서 감사합니다.", "시청해 주셔서 감사합니다", "한글자막 by 한효정", "자막 제공 배달의민족",
            "다음 영상에서 만나요", "구독과 좋아요 부탁드립니다",
            "ご視聴ありがとうございました", "感谢您的观看", "Субтитры сделал DimaTorzok",
        ]:
            self.assertTrue(_is_hallucination(t), t)

    def test_real_utterances_are_not_flagged(self):
        for t in ["치즈버거 하나 줘", "네", "좋아요", "감사합니다", "Thank you", "I'd like a cheese burger", "one coke please",
                  "你好", "チーズバーガーをください", "결제할게요", "주문 시작", "영상 틀어줘 말고 메뉴 알려줘"]:
            self.assertFalse(_is_hallucination(t), t)


if __name__ == "__main__":
    unittest.main()
