import unittest

from ai_modules.llm import guards
from ai_modules.llm.action_context import get_guard_hits, reset_guards
from ai_modules.llm.guards import (
    correct_reply, fix_stt, has_remove_intent, is_noise, is_question_only, mentions_single,
    quantity_in, wants_reduce_one,
)


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

    def test_corrects_gyeolje_misspelling(self):
        cases = {
            "결재할게요": "결제할게요",
            "결재 할게요": "결제 할게요",
            "카드로 결재할게요": "카드로 결제할게요",
            "간편결재로 할게요": "간편결제로 할게요",
            "결제할게요": "결제할게요",   # 이미 맞는 말은 그대로
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), want)

    def test_corrects_jwo_misheard_as_jyo(self):
        """"~(으)로 줘"가 "~(으)로죠"로 들어온다(실제 로그: "단품으로죠", "생수로죠. 생수로죠.", "탄품으로죠")."""
        cases = {
            "단품으로죠.": "단품으로 줘.",
            "단품으로죠": "단품으로 줘",
            "탄품으로죠.": "단품으로 줘.",
            "세트로죠": "세트로 줘",
            "치즈버거 단품으로 죠": "치즈버거 단품으로 줘",
            "생수로죠. 생수로죠.": "생수로 줘. 생수로 줘.",
            "콜라로죠": "콜라로 줘",
            "양념감자튀김으로죠.": "양념감자튀김으로 줘.",
            "포장으로죠": "포장으로 줘",
            "카드로죠": "카드로 줘",
            "그걸로죠": "그걸로 줘",
            "설치할게.": "결제할게.",
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), want)
        for keep in ("단품으로 줘", "세트로 줄까요", "단품으로죠스바", "어디로죠?"):   # 맞는 말·의문사·다른 낱말은 그대로
            self.assertEqual(fix_stt(keep), keep, keep)

    def test_corrects_dampum_mul_misrecognition(self):
        """"단품으로 줘" → "단풍물을 줘"(2026-10-04 실험)."""
        cases = {
            "단풍물을 줘.": "단품으로 줘.",
            "단풍물을 줘": "단품으로 줘",
            "단풍물 주세요": "단품으로 주세요",
            "치즈버거 탐풍물로 줘": "치즈버거 단품으로 줘",
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), want)
        for keep in ("단풍물감을 샀어요", "단풍물이 들었어요"):   # 다른 낱말은 그대로
            self.assertEqual(fix_stt(keep), keep, keep)

    def test_corrects_dampum_misrecognition(self):
        """"단품"의 실제 오인식(2026-10-04 로그). 단품/세트를 묻는 말에 이렇게 답하면 노이즈로 걸러져 주문이 안 됐다."""
        cases = {
            "탐풍.": "단품.",
            "단풍": "단품",
            "단풍으로 줘": "단품으로 줘",
            "잔툼으로 쏘옥": "단품으로 쏘옥",
            "그냥 단푼이요": "그냥 단품이요",
            "단품으로 줘": "단품으로 줘",   # 이미 맞는 말은 그대로
        }
        for src, want in cases.items():
            with self.subTest(src=src):
                self.assertEqual(fix_stt(src), want)

    def test_leaves_other_sentences_untouched(self):
        for src in [
            "단풍잎이 예쁘네요",      # 다른 낱말의 일부는 건드리지 않는다
            "가을 단풍 구경 가고 싶어요",
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


class QuantityTests(unittest.TestCase):
    def test_single_quantity(self):
        cases = {
            "치즈버거 단품 세 개 주세요": 3, "콜라 두 잔": 2, "치즈버거 하나 줘": 1, "더블치즈버거 단품 5개로 바꿔줘": 5,
            "불고기버거 세트 하나, 사이드는 감자튀김": 1, "치즈버거 한 개": 1, "콜라 네 잔 주세요": 4,
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(quantity_in(text), want)

    def test_ambiguous_or_none(self):
        for text in ["치즈버거 세 개랑 콜라 두 잔", "치즈버거 단품 줘", "인터넷 되나요", "문 열어줘", "세트로 줘"]:
            with self.subTest(text=text):
                self.assertIsNone(quantity_in(text))


class IntentRuleTests(unittest.TestCase):
    def test_remove_intent(self):
        for t in ["치즈버거 빼줘", "콜라 취소해줘", "아니 그거 말고 새우버거", "세트 말고 단품으로", "방금 거 지워줘"]:
            self.assertTrue(has_remove_intent(t), t)
        for t in ["치즈버거 하나 줘", "콜라 주세요", "결제할게요"]:
            self.assertFalse(has_remove_intent(t), t)

    def test_reduce_one(self):
        for t in ["데리버거 단품 하나만 빼줘", "너겟 한 개 줄여줘", "콜라 하나 빼줘"]:
            self.assertTrue(wants_reduce_one(t), t)
        for t in ["데리버거 빼줘", "데리버거 단품 전부 빼줘", "치즈버거 하나 줘"]:
            self.assertFalse(wants_reduce_one(t), t)

    def test_question_only(self):
        self.assertTrue(is_question_only("콜라는 얼마예요?"))
        self.assertTrue(is_question_only("가장 저렴한 버거가 뭐예요?"))
        self.assertFalse(is_question_only("콜라 하나 줘"))
        self.assertFalse(is_question_only("콜라 얼마예요? 하나 주세요"))

    def test_single_word(self):
        self.assertTrue(mentions_single("치즈버거 단품으로 줘"))
        self.assertFalse(mentions_single("치즈버거 하나 줘"))


class CorrectReplyTests(unittest.TestCase):
    def test_claim_without_action_is_replaced(self):
        self.assertIn("담지 못했", correct_reply("모짜렐라 버거 단품 1개 담았습니다. 다른 메뉴를 더 주문하시겠어요?", []))
        self.assertIn("빼지 못했", correct_reply("데리버거를 삭제했습니다.", ["add_item"]))
        self.assertIn("변경하지 못했", correct_reply("음료를 생수로 변경했습니다.", []))
        self.assertIn("결제를 도와드릴까요", correct_reply("주문이 완료되었습니다. 다른 메뉴가 필요하시면 말씀해 주세요.", []))

    def test_claim_with_action_is_kept(self):
        self.assertIsNone(correct_reply("치즈 버거 단품 1개 담았습니다.", ["add_item"]))
        self.assertIsNone(correct_reply("너겟을 삭제했습니다.", ["remove_item"]))
        self.assertIsNone(correct_reply("음료를 생수로 변경했습니다.", ["update_item"]))

    def test_change_claim_is_fulfilled_by_any_action(self):
        # 결제수단·주문유형 선택도 "변경했습니다"의 근거가 되는 액션이다(실제 오탐 사례)
        self.assertIsNone(correct_reply("결제 수단이 카드로 변경되었습니다. 카드를 삽입해 주세요.", ["payment_method"]))
        self.assertIsNone(correct_reply("주문 유형을 포장으로 변경했습니다.", ["order_type"]))
        self.assertIn("변경하지 못했", correct_reply("결제 수단이 카드로 변경되었습니다.", []))

    def test_questions_and_status_are_kept(self):
        for out in ["단품으로 드릴까요, 세트로 드릴까요?", "현재 장바구니에는 치즈 버거 2개가 담겨 있습니다.",
                    "삭제하시겠어요?", "Added one burger."]:
            self.assertIsNone(correct_reply(out, []), out)


class NoiseTests(unittest.TestCase):
    def test_noise_music_and_lyrics(self):
        """배경 음악 가사(한국어 발라드·댄스곡·영어 팝송, 40자 초과 포함)는 모두 노이즈로 차단한다."""
        lyrics = [
            "사랑 전하다 고향을 찾는 철도에",
            "그대 곁에 하늘.",
            "음 음 으으",
            "오늘 밤 주인공은 나야 나 너만을 기다려 왔어",
            "눈물이 차올라서 고개를 들어 흐르지 못하게 또 살짝 웃어",
            "바람이 불어오는 곳 그곳으로 가네 그대의 머릿결같은 나무 아래로",
            "사랑은 늘 도망가 내 가슴에 내리는 비처럼 어제도 오늘도 그대 생각에 잠 못 이루네",  # 40자 초과 긴 가사
            "콘서트 티켓 예매 성공했어 너무 신난다",
            "Dancing in the moonlight everybody is feeling warm and bright",
            "Never gonna give you up never gonna let you down",
            "Baby shark doo doo doo doo doo doo",
        ]
        for t in lyrics:
            with self.subTest(t=t):
                self.assertTrue(is_noise(t), t)

    def test_noise_side_conversations(self):
        """기존 정규식에서 '어', '네', '예', '응', '좋', '물', '개', '잔' 1글자 매칭 때문에 통과하던 주변 테이블 일상 대화 차단."""
        side_chats = [
            "어제 영화 봤어? 진짜 재미없더라",
            "응 그래서 내가 어제 팀장님한테 말했잖아",
            "오늘 날씨 진짜 좋다 산책 갈래?",
            "야 너 이번 주말에 시간 있어?",
            "내일 시험 끝나고 어디 갈까",
            "아 진짜 피곤해서 집에 빨리 가고 싶다",
            "선물 뭐 살지 아직도 고민 중이야",
            "이번 학기 과제 너무 많은 것 같네",
            "개인적으로 그 드라마 결말이 별로였어",
            "잔소리 좀 그만해 알았다니까",
            "담배 피우러 밖에 잠깐 나갔다 올게",
            "비 맞아서 옷이 다 젖었네",
            "예전에 거기 갔을 때는 사람이 별로 없었는데",
            "가을 단풍 구경 가고 싶어요",
        ]
        for t in side_chats:
            with self.subTest(t=t):
                self.assertTrue(is_noise(t), t)

    def test_start_screen_blocks_bare_backchannel(self):
        """대기 화면(start)에서는 지나가는 행인의 짧은 추임새('응', '어', '그거')로 화면이 넘어가면 안 된다."""
        for t in ["응", "어", "음", "그거", "이거", "저거", "아까", "방금"]:
            with self.subTest(t=t):
                self.assertTrue(is_noise(t, screen="start"), t)
        # 반면 주문 화면(menu/cart)에서는 키오스크 질문에 대한 대답이므로 통과해야 한다
        for t in ["응", "어", "그거", "이거"]:
            with self.subTest(t=t):
                self.assertFalse(is_noise(t, screen="menu"), t)
        # 대기 화면에서도 명확한 시작/인사/주문 발화는 통과해야 한다
        for t in ["주문 시작", "안녕하세요", "치즈버거 하나 줘", "매장에서 먹을게요", "메뉴 보여줘"]:
            with self.subTest(t=t):
                self.assertFalse(is_noise(t, screen="start"), t)

    def test_real_utterances_pass(self):
        real_utterances = [
            "치즈버거 하나 줘", "어, 그래 맞아.", "나 뭐 해?", "카메라 꺼줘", "영어로 해줘", "불고기버거 세트",
            "안녕하세요", "화장실 어디예요", "Hello", "포장할게요", "네", "공일공 일이삼사 오육칠팔",
            "010-8251-0345", "01012345678",
            "나는 갑상선 알레르기가 있어서 그런 거 못 먹을 것 같은데.",
            "물 하나 주세요", "물 두 병 줘", "생수로 바꿔줘", "콘샐러드 하나 추가해줘",
            "그걸로 줘", "첫 번째 걸로 하나 줘", "어 그렇게 줘", "아니 괜찮아 결제할게",
            "더블 불고기 버거 단품 두 개 주세요", "사이드 치즈스틱으로 변경해줘",
            "양파 빼줘", "하나만 빼줘", "장바구니 보여줘", "가장 인기 있는 메뉴 추천해줘",
            "I'd like a cheeseburger set please", "Can I pay by card?", "For here please",
            "チーズバーガーをください", "店内で食べます",
            "我要一个芝士汉堡套餐", "打包带走",
        ]
        for t in real_utterances:
            with self.subTest(t=t):
                self.assertFalse(is_noise(t), t)


class BlockBudgetTests(unittest.TestCase):
    def setUp(self):
        reset_guards()

    def test_enforce_blocks_then_budget_message(self):
        import os
        os.environ["GUARD_MODE"] = "enforce"
        msgs = [guards.block("r", f"d{i}", "거절") for i in range(4)]
        self.assertEqual(msgs[0], "거절")
        self.assertEqual(msgs[1], "거절")
        self.assertIn("여러 번 거절", msgs[2])
        self.assertEqual(len(get_guard_hits()), 4)
        self.assertTrue(all(h["blocked"] for h in get_guard_hits()))

    def test_shadow_records_without_blocking(self):
        import os
        os.environ["GUARD_MODE"] = "shadow"
        try:
            self.assertIsNone(guards.block("r", "d", "거절"))
            self.assertFalse(get_guard_hits()[0]["blocked"])
        finally:
            os.environ["GUARD_MODE"] = "enforce"


if __name__ == "__main__":
    unittest.main()
