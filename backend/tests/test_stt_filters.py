"""STT 환각 및 세그먼트 신뢰도 필터 검증(API 호출 없음). 기준 수치는 2026-10-04 whisper-1 실험: 환각 구간 no_speech_prob 0.85~0.97, 실제 말소리 0.00~0.40."""
import unittest
from types import SimpleNamespace as NS

from core.stt_service import (
    COMPRESSION_DROP,
    LOGPROB_DROP,
    NO_SPEECH_DROP,
    _drop_no_speech,
    _filter_segments,
    _is_hallucination,
    _is_unsupported_language,
    _postprocess_transcription,
)


def seg(text, p=0.1, avg_logprob=-0.25, compression_ratio=1.2):
    return NS(text=text, no_speech_prob=p, avg_logprob=avg_logprob, compression_ratio=compression_ratio)


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

    def test_low_avg_logprob_segment_is_dropped(self):
        """배경 음악이나 먼 거리 소음을 억지로 전사해 avg_logprob가 낮은 구간(-1.25)은 제거한다."""
        res = _filter_segments([seg("오늘 밤 주인공은 나야 나", p=0.2, avg_logprob=-1.25)])
        self.assertEqual(res["kept_text"], "")
        self.assertIn("low_logprob", res["drop_reasons"])

    def test_short_core_word_allows_relaxed_logprob(self):
        """"네", "단품", "매장" 등 1~2음절 핵심 단답은 avg_logprob가 -1.15 수준이어도 보존한다."""
        for word in ("네.", "단품", "매장", "포장", "카드", "yes"):
            res = _filter_segments([seg(word, p=0.25, avg_logprob=-1.18)])
            self.assertIsNone(res["kept_text"], word)   # 버려지지 않음

    def test_high_compression_ratio_loop_is_dropped(self):
        """배경 리듬이나 잡음으로 인해 동일 구절이 반복되는 세그먼트(compression_ratio > 2.4)를 제거한다."""
        res = _filter_segments([seg("아 아 아 아 아 아 아 아 아 아", p=0.15, avg_logprob=-0.4, compression_ratio=3.1)])
        self.assertEqual(res["kept_text"], "")
        self.assertIn("high_compression", res["drop_reasons"])


class HallucinationPhrases(unittest.TestCase):
    def test_known_hallucinations(self):
        for t in [
            "Thank you for watching.", "thank you for watching!", "Thanks for watching",   # 실험에서 나온 영어 환각
            "you", "You.", "bye", ".", "...", "…",
            "시청해주셔서 감사합니다.", "시청해 주셔서 감사합니다", "한글자막 by 한효정", "자막 제공 배달의민족",
            "다음 영상에서 만나요", "구독과 좋아요 부탁드립니다",
            "ご視聴ありがとうございました", "感谢您的观看", "Субтитры сделал DimaTorzok",
            "♪ 사랑은 늘 도망가 ♪", "[음악]", "(박수)", "[Music]",
            "음 음 으으", "아 아 아", "하하하", "흠...", "어...",
        ]:
            self.assertTrue(_is_hallucination(t), t)

    def test_real_utterances_are_not_flagged(self):
        for t in ["치즈버거 하나 줘", "네", "좋아요", "감사합니다", "Thank you", "I'd like a cheese burger", "one coke please",
                  "你好", "チーズバーガーをください", "결제할게요", "주문 시작", "영상 틀어줘 말고 메뉴 알려줘"]:
            self.assertFalse(_is_hallucination(t), t)

    def test_unsupported_language_detection(self):
        """whisper-1이 무음·배경 음악에서 nynorsk, welsh, russian 등 미지원 언어를 반환하면 차단한다."""
        for bad_lang in ("nynorsk", "welsh", "russian", "arabic", "spanish", "tagalog", "latin"):
            self.assertTrue(_is_unsupported_language(bad_lang), bad_lang)
            post = _postprocess_transcription("Some random noise text", use_verbose=True, raw_language=bad_lang)
            self.assertEqual(post["text"], "")
            self.assertTrue(post["filtered"])

        for ok_lang in ("korean", "ko", "english", "en", "japanese", "ja", "chinese", "zh", None):
            self.assertFalse(_is_unsupported_language(ok_lang), ok_lang)


if __name__ == "__main__":
    unittest.main()
