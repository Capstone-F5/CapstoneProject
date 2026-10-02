import unittest

from ai_modules.llm.guards import fix_stt


class FixSttTests(unittest.TestCase):
    def test_corrects_known_misrecognition_only_in_dine_in_context(self):
        cases = {
            "내장에서 먹을게.": "매장에서 먹을게.",
            "내장에서 먹을게요": "매장에서 먹을게요",
            "내장에서 드실게요": "매장에서 드실게요",
            "내장 식사로 할게요": "매장 식사로 할게요",
            "내장이요": "매장이요",
            "내장으로 할게요": "매장으로 할게요",
            "네 내장에서 먹고 치즈버거 하나 줘": "네 매장에서 먹고 치즈버거 하나 줘",
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), want)

    def test_leaves_other_sentences_untouched(self):
        for src in [
            "내장이 뭐야",
            "내장 알레르기가 있어요",
            "매장에서 먹을게요",
            "포장할게요",
            "치즈버거 하나 줘",
            "",
        ]:
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), src)

    def test_none_safe(self):
        self.assertIsNone(fix_stt(None))


if __name__ == "__main__":
    unittest.main()
