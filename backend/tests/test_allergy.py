"""알레르기 질의를 메뉴 DB의 allergens로 답하는 순수 함수와 담기 가드를 검사한다. API·LLM 호출 없음."""
import os
import sys
import types
import unittest

os.environ.setdefault("GUARD_MODE", "enforce")

try:
    import langchain_community  # noqa: F401
except ModuleNotFoundError:
    rag_stub = types.ModuleType("ai_modules.llm.rag")
    rag_stub.search_menu = lambda *a, **kw: []
    sys.modules.setdefault("ai_modules.llm.rag", rag_stub)
    lc_core = types.ModuleType("langchain_core")
    lc_tools = types.ModuleType("langchain_core.tools")
    lc_tools.tool = lambda f: f
    sys.modules.setdefault("langchain_core", lc_core)
    sys.modules.setdefault("langchain_core.tools", lc_tools)

from ai_modules.llm import allergy, action_context as C
from ai_modules.llm import action_tools as T


# /api/menu/allergens가 돌려주는 DB 마스터(code → name_ko). 테스트는 이 값만 본다 — 코드에 이름 표가 없다는 것을 확인하기 위해
# 일부러 실제 시드와 다른 이름("갑각류 새우")을 쓴 항목을 하나 둔다.
MASTER = {"SHRIMP": "새우", "CRAB": "게", "SOY": "대두", "WHEAT": "밀", "EGG": "난류", "MILK": "우유", "CHICKEN": "닭고기", "BEEF": "쇠고기",
          "PEANUT": "땅콩"}


def m(i, name, *codes):
    return {"id": f"id-{i}", "name_ko": name, "is_available": True,
            "allergens": [{"code": c, "name_ko": MASTER[c]} for c in codes]}


MENU = [
    m(1, "F 버거", "WHEAT", "SOY", "CHICKEN", "BEEF"),
    m(2, "새우 버거", "WHEAT", "SHRIMP", "EGG"),
    m(3, "게살 버거", "WHEAT", "CRAB", "EGG"),
    m(4, "비건 버거", "WHEAT", "SOY"),
    m(5, "감자튀김(M)"),
    m(6, "콜라(M)"),
]


class ExtractTests(unittest.TestCase):
    def test_crustacean_means_shrimp_and_crab(self):
        self.assertEqual(allergy.extract_codes("갑각류 알레르기 있으면 먹으면 안되는 햄버거가 있어?", MASTER), {"SHRIMP", "CRAB"})

    def test_soy(self):
        self.assertEqual(allergy.extract_codes("난 대두알레르기가 있는데 먹을 수 있는게 뭐야?", MASTER), {"SOY"})

    def test_needs_allergy_keyword(self):
        self.assertEqual(allergy.extract_codes("새우버거 하나 줘", MASTER), set())

    def test_single_syllable_crab_needs_context(self):
        self.assertEqual(allergy.extract_codes("이게 뭐야, 알레르기 정보 알려줘", MASTER), set())
        self.assertEqual(allergy.extract_codes("게 알레르기 있어요", MASTER), {"CRAB"})

    def test_names_come_from_master_not_code(self):
        self.assertEqual(allergy.extract_codes("땅콩 알레르기", MASTER), {"PEANUT"})
        self.assertEqual(allergy.extract_codes("땅콩 알레르기", {"SOY": "대두"}), set())   # 마스터에 없으면 모른다
        self.assertEqual(allergy.extract_codes("땅콩 알레르기", {"PEANUT": "피넛"}), set())   # DB가 다른 이름이면 그 이름을 따른다
        self.assertEqual(allergy.extract_codes("피넛 알레르기", {"PEANUT": "피넛"}), {"PEANUT"})
        self.assertEqual(allergy.extract_codes("갑각류 알레르기", {"SHRIMP": "새우"}), {"SHRIMP"})   # 동의어는 마스터에 있는 코드만

    def test_unknown_ingredient_is_not_guessed(self):
        self.assertEqual(allergy.extract_codes("각광료 알레르기가 있는 사람이 먹으면 안되는 메뉴", MASTER), set())


class DecideTests(unittest.TestCase):
    def test_negated_only_is_not_remembered(self):
        """"갑각류 알레르기 없어"를 있다로 읽으면 없다는 손님의 새우 버거 주문을 막는다."""
        for t in ["갑각류 알레르기 없어", "나 갑각류 알레르기 없어요", "대두 알레르기는 괜찮아", "알레르기 없는 메뉴 알려줘"]:
            with self.subTest(t=t):
                self.assertEqual(allergy.decide(t, MASTER).kind, "none")

    def test_plain_affirmation_is_decided_by_rule(self):
        d = allergy.decide("갑각류 알레르기 있어", MASTER)
        self.assertEqual((d.kind, d.codes), ("have", {"SHRIMP", "CRAB"}))
        d = allergy.decide("난 대두알레르기가 있는데 먹을 수 있는게 뭐야?", MASTER)
        self.assertEqual((d.kind, d.codes), ("have", {"SOY"}))

    def test_mixed_or_unrecognized_goes_to_llm(self):
        self.assertEqual(allergy.decide("갑각류는 없는데 대두 알레르기는 있어요", MASTER).kind, "llm")
        self.assertEqual(allergy.decide("각광료 알레르기가 있는 사람이 먹으면 안되는 메뉴", MASTER).kind, "llm")
        self.assertEqual(allergy.decide("알레르기 때문에 그래요", MASTER).kind, "llm")

    def test_no_keyword_is_ignored(self):
        self.assertEqual(allergy.decide("새우버거 하나 줘", MASTER).kind, "none")


class ResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_rule_cases_never_call_llm(self):
        async def boom(prompt):
            raise AssertionError("LLM을 부르면 안 된다")
        self.assertEqual(await allergy.resolve("갑각류 알레르기 있어", MASTER, boom), {"SHRIMP", "CRAB"})
        self.assertEqual(await allergy.resolve("갑각류 알레르기 없어", MASTER, boom), set())

    async def test_llm_have_only_and_validated_against_master(self):
        async def ask(prompt):
            self.assertIn("SHRIMP: 새우", prompt)   # 마스터 목록이 프롬프트에 실린다
            return '```json\n{"have": ["SOY", "FAKE"], "none": ["SHRIMP", "CRAB"]}\n```'
        got = await allergy.resolve("갑각류는 없는데 대두 알레르기는 있어요", MASTER, ask)
        self.assertEqual(got, {"SOY"})   # none은 기억하지 않고, 마스터에 없는 코드는 버린다

    async def test_llm_failure_means_unknown(self):
        async def timeout(prompt):
            raise TimeoutError()
        async def junk(prompt):
            return "잘 모르겠어요"
        self.assertEqual(await allergy.resolve("각광료 알레르기가 있어요", MASTER, timeout), set())
        self.assertEqual(await allergy.resolve("각광료 알레르기가 있어요", MASTER, junk), set())


class ReplyTests(unittest.TestCase):
    def test_crustacean_reply_lists_shrimp_and_crab_burgers(self):
        text = allergy.build_reply(MENU, {"SHRIMP", "CRAB"}, MASTER)
        self.assertIn("새우 버거, 게살 버거는 드실 수 없어요", text)
        self.assertNotIn("F 버거는", text)
        self.assertIn("F 버거", text.split("나머지로는")[1])

    def test_soy_reply_excludes_f_burger_from_safe_list(self):
        text = allergy.build_reply(MENU, {"SOY"}, MASTER)
        bad, good = text.split("나머지로는")
        self.assertIn("F 버거", bad)
        self.assertIn("비건 버거", bad)
        self.assertNotIn("F 버거", good)

    def test_nothing_unsafe(self):
        self.assertIn("들어간 메뉴는 없어요", allergy.build_reply(MENU, {"PEANUT"}, MASTER))

    def test_unavailable_items_are_ignored(self):
        menu = [dict(MENU[1], is_available=False), MENU[4]]
        self.assertIn("들어간 메뉴는 없어요", allergy.build_reply(menu, {"SHRIMP"}, MASTER))


class AddGuardTests(unittest.TestCase):
    def setUp(self):
        C.reset_guards()
        os.environ["GUARD_MODE"] = "enforce"
        from ai_modules.llm.session_context import set_session_id
        set_session_id("allergy-test")
        allergy.reset("allergy-test")
        T._run = lambda x: MENU
        T.api_client.fetch_menu_items = lambda: None

    def test_blocks_conflicting_item_when_not_named(self):
        allergy.remember("allergy-test", {"SOY"})
        C.set_user_input("그걸로 해줘.")
        C.set_recent_user_text("")
        C.set_last_bot_text("F 버거는 어떠세요?")
        blocked, _, _ = T._check_add_item(MENU[0], 1, False, None, None)
        self.assertIsNotNone(blocked)
        self.assertEqual(C.get_guard_hits()[0]["rule"], "allergy_conflict")

    def test_allows_when_customer_names_it_or_no_conflict(self):
        allergy.remember("allergy-test", {"SOY"})
        C.set_user_input("그래도 F버거 담아줘")
        blocked, _, _ = T._check_add_item(MENU[0], 1, False, None, None)
        self.assertFalse(blocked and C.get_guard_hits() and C.get_guard_hits()[0]["rule"] == "allergy_conflict")
        C.reset_guards()
        C.set_user_input("감자튀김 줘")
        blocked, _, _ = T._check_add_item(MENU[4], 1, False, None, None)
        self.assertFalse(any(h["rule"] == "allergy_conflict" for h in C.get_guard_hits()))


if __name__ == "__main__":
    unittest.main()
