"""action_tools 안의 규칙 가드(메뉴 해석·직전 id 재사용·수량)를 가짜 메뉴로 검사한다. API·LLM 호출 없음."""
import os
import unittest

os.environ.setdefault("GUARD_MODE", "enforce")

from ai_modules.llm import action_tools as T
from ai_modules.llm import action_context as C

UP = [{"option_group": "SET_UPGRADE"}]


def it(i, name, burger=True):
    return {"id": f"{i:08d}-0000-0000-0000-000000000000", "name_ko": name, "options": UP if burger else []}


MENU = [
    it(1, "치즈 버거"), it(2, "더블 치즈 버거"), it(3, "비건 버거"), it(4, "F 버거"),
    it(5, "더블 불고기 버거"), it(6, "불고기 버거"), it(7, "그릴드 비프 버거"), it(8, "치킨 다릿살 버거"),
    it(20, "너겟(4조각)", False), it(21, "치즈스틱(2개)", False), it(22, "콜라(M)", False),
    it(23, "제로 콜라(M)", False), it(24, "뽀로로 음료수", False), it(25, "생수", False), it(26, "오렌지 주스", False),
]
BY = {m["name_ko"]: m for m in MENU}


class ResolveByNameTests(unittest.TestCase):
    def test_name_in_id_slot(self):
        cases = {"치킨너겟": "너겟(4조각)", "너겟": "너겟(4조각)", "치즈스틱": "치즈스틱(2개)", "오렌지주스": "오렌지 주스",
                 "뽀로로음료수": "뽀로로 음료수", "F버거": "F 버거", "그릴드비프버거": "그릴드 비프 버거"}
        for name, want in cases.items():
            with self.subTest(name=name):
                self.assertEqual(T._resolve_menu_by_name(name, MENU)["name_ko"], want)

    def test_ambiguous_or_unknown_is_not_guessed(self):
        self.assertIsNone(T._resolve_menu_by_name("피자", MENU))
        self.assertIsNone(T._resolve_menu_by_name("버", MENU))

    def test_longer_name_wins(self):
        self.assertEqual(T._resolve_menu_by_name("더블치즈버거", MENU)["name_ko"], "더블 치즈 버거")
        self.assertEqual(T._resolve_menu_by_name("치즈버거", MENU)["name_ko"], "치즈 버거")


class MismatchTests(unittest.TestCase):
    def check(self, user, item, last_bot="", set_=False, recent=""):
        T._run = lambda x: MENU
        T.api_client.fetch_menu_items = lambda: None
        found = T._mentions_other_menu(user, BY[item], last_bot, set_, MENU, recent)
        return found

    def test_user_names_other_burger_is_unique(self):
        self.assertEqual(self.check("비건버거 하나 세트로 줘. 콜라에다가 치즈스틱.", "더블 불고기 버거", set_=True), ("비건 버거", True))

    def test_confirmation_uses_last_bot(self):
        self.assertEqual(self.check("어, 그래 맞아.", "더블 불고기 버거", "F 버거 세트로 드릴까요?", True), ("F 버거", True))
        self.assertIsNone(self.check("어, 그래 맞아.", "F 버거", "F 버거 세트로 드릴까요?", True))

    def test_falls_back_to_recent_user_turn_when_bot_names_nothing(self):
        # "치킨다릿살버거 세트로 하나 줘" → … → "콜라로 주세요"(이름 없음) 인데 모델이 다른 버거 id를 쓴 사례(W057)
        recent = "그릴드비프버거 단품 하나 줘 ¦ 치킨다릿살버거 세트로 하나 줘 ¦ 사이드는 양념감자튀김"
        self.assertEqual(self.check("콜라로 주세요", "그릴드 비프 버거", "음료는 무엇으로 드릴까요?", True, recent),
                         ("치킨 다릿살 버거", True))
        self.assertIsNone(self.check("콜라로 주세요", "치킨 다릿살 버거", "음료는 무엇으로 드릴까요?", True, recent))

    def test_non_burger_added_with_stale_burger_id(self):
        self.assertEqual(self.check("아 잠깐 뽀로로음료수도 한 잔 추가할게요", "치즈 버거"), ("뽀로로 음료수", True))
        self.assertEqual(self.check("콜라도 하나 추가해줘", "치즈 버거"), ("콜라(M)", True))

    def test_two_burgers_named_and_wrong_third_is_not_unique(self):
        found = self.check("치즈버거 단품 하나랑 비건버거 단품 하나", "F 버거")
        self.assertEqual(found[1], False)

    def test_correct_items_pass(self):
        self.assertIsNone(self.check("치즈버거 단품 하나랑 비건버거 단품 하나", "비건 버거"))
        self.assertIsNone(self.check("콜라 하나 줘", "콜라(M)"))
        self.assertIsNone(self.check("단품으로 줘", "불고기 버거", "불고기 버거는 단품으로 드릴까요?"))
        self.assertIsNone(self.check("One cheese burger please", "치즈 버거"))


class TargetMismatchTests(unittest.TestCase):
    def test_wrong_line(self):
        self.assertEqual(T._target_mismatch("모짜렐라버거 단품 3개로 바꿔줘", "치즈 버거", MENU + [it(9, "모짜렐라 버거")]), "모짜렐라 버거")
        self.assertIsNone(T._target_mismatch("치즈버거 단품 3개로 바꿔줘", "치즈 버거", MENU))


class FixAndAddSemanticsTests(unittest.TestCase):
    def setUp(self):
        C.reset_guards()
        os.environ["GUARD_MODE"] = "enforce"

    def test_fix_records_and_allows_in_enforce(self):
        from ai_modules.llm import guards
        self.assertTrue(guards.fix("r", "d"))
        self.assertTrue(C.get_guard_hits()[0]["fixed"])

    def test_fix_only_records_in_shadow(self):
        from ai_modules.llm import guards
        os.environ["GUARD_MODE"] = "shadow"
        try:
            self.assertFalse(guards.fix("r", "d"))
            self.assertFalse(C.get_guard_hits()[0]["fixed"])
        finally:
            os.environ["GUARD_MODE"] = "enforce"

    def test_add_vs_change_verbs(self):
        from ai_modules.llm import guards
        for t in ["게살버거 단품 두 개 담아줘", "데리버거 단품 두 개 더 줘", "그릴드비프버거 단품 세 개 주세요"]:
            self.assertTrue(guards.has_add_verb(t) and not guards.has_change_verb(t), t)
        for t in ["모짜렐라버거 단품 3개로 바꿔줘", "치즈버거 2개로 해줘", "콜라 세 잔으로 변경해줘"]:
            self.assertTrue(guards.has_change_verb(t), t)


if __name__ == "__main__":
    unittest.main()
