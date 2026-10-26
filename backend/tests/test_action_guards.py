"""action_tools 안의 규칙 가드(메뉴 해석·직전 id 재사용·수량)를 가짜 메뉴로 검사한다. API·LLM 호출 없음."""
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

    def test_refusal_blocks_duplicate_add_item(self):
        """2026-10-23 실제 로그 재현: 직전 턴에 세트를 담고 '다른 메뉴를 추가하시겠어요?'라고 물었는데
        손님이 '아니.'라고 답한 턴에 모델이 같은 세트를 또 담으려 하면 차단한다."""
        T._run = lambda x: MENU
        T.api_client.fetch_menu_items = lambda: None
        C.set_user_input("아니.")
        C.set_recent_user_text("세트로 줘. ¦ 양념감자튀김으로 줘. ¦ 생수로 줘.")
        C.set_last_bot_text("그릴드 비프 버거 세트를 양념감자튀김과 생수로 장바구니에 담았습니다. 다른 메뉴를 추가하시겠어요?")
        blocked, _, _ = T._check_add_item(BY["그릴드 비프 버거"], 1, True, "양념감자튀김", "생수")
        self.assertIsNotNone(blocked)
        self.assertEqual(C.get_guard_hits()[0]["rule"], "refusal_add")

    def test_decline_more_menu_triggers_checkout_actions(self):
        """'다른 메뉴를 추가하시겠어요?' → '아니.' 응답 시 장바구니 이동 + start_checkout 액션이 생성된다."""
        from core.intent_fallback import ensure_actions, is_decline_more_menu
        from ai_modules.llm import checkout_progress
        C.reset_actions()
        checkout_progress.reset("test-session-decline")
        last_bot = "그릴드 비프 버거 세트를 양념감자튀김과 생수로 장바구니에 담았습니다. 다른 메뉴를 추가하시겠어요?"
        C.set_last_bot_text(last_bot)
        self.assertTrue(is_decline_more_menu("아니.", last_bot))
        self.assertFalse(is_decline_more_menu("아니.", "단품으로 드릴까요, 세트로 드릴까요?"))
        added = ensure_actions(
            session_id="test-session-decline",
            user_input="아니.",
            screen="menu",
            cart=[{"name": "그릴드 비프 버거", "qty": 1}],
            snapshot_before=frozenset(),
            has_items=True,
        )
        self.assertEqual(added, [{"type": "navigate", "screen": "cart"}, {"type": "start_checkout"}])


class PaymentAndPointsFlowTests(unittest.TestCase):
    """2026-10-13·10-26 로그: 전화번호 없이 포인트 적립이 선택된 채 결제 수단으로 넘어감 / "결제페이지"가 간편결제로 읽힘."""

    def setUp(self):
        C.reset_actions()
        os.environ["GUARD_MODE"] = "enforce"

    def test_payment_page_is_not_easy_pay(self):
        from core.intent_fallback import _method_from
        for text in ["결제페이지 이동해줘", "결제 페이지로 가줘", "go to the payment page"]:
            with self.subTest(text=text):
                self.assertIsNone(_method_from(text))
                C.set_user_input(text)
                self.assertFalse(T._payment_method_supported_by_input("pay"))
        self.assertEqual(_method_from("카카오페이로 할게요"), "pay")
        self.assertEqual(_method_from("페이로 할게요"), "pay")

    def test_awaiting_points_phone(self):
        from ai_modules.llm import checkout_progress as P
        self.assertTrue(P.awaiting_points_phone(frozenset({"start_checkout", "points", "points_yes"})))
        self.assertFalse(P.awaiting_points_phone(frozenset({"start_checkout", "points", "points_yes", "points_phone"})))
        self.assertFalse(P.awaiting_points_phone(frozenset({"start_checkout", "points"})))   # 적립 안 함
        self.assertFalse(P.awaiting_points_phone(frozenset({"start_checkout", "points", "points_yes"}), True))

    def test_fallback_does_not_pick_payment_before_phone(self):
        from core.intent_fallback import ensure_actions
        from ai_modules.llm import checkout_progress
        sid = "test-session-points-phone"
        checkout_progress.reset(sid)
        added = ensure_actions(sid, "카드로 결제할게", "cart", [{"name": "버거", "qty": 1}],
                               frozenset({"start_checkout", "points", "points_yes"}), True)
        self.assertEqual(added, [])
        C.reset_actions()
        added = ensure_actions(sid, "카드로 결제할게", "cart", [{"name": "버거", "qty": 1}],
                               frozenset({"start_checkout", "points", "points_yes", "points_phone"}), True)
        self.assertEqual(added, [{"type": "payment_method", "value": "card"}])

    def test_fallback_records_points_yes(self):
        from core.intent_fallback import ensure_actions
        from ai_modules.llm import checkout_progress
        sid = "test-session-points-yes"
        checkout_progress.reset(sid)
        ensure_actions(sid, "적립할게", "cart", [{"name": "버거", "qty": 1}], frozenset({"start_checkout"}), True)
        self.assertIn("points_yes", checkout_progress.snapshot(sid))


class ServerCartFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_request_cart_uses_server_cart(self):
        """2026-09-28: 방금 F 버거 세트를 안내했는데 요청 cart가 비어 와서 "담긴 메뉴가 없습니다"라고 답했다."""
        from core import llm_service
        from core.cart_context import format_cart_status_reply

        async def fake_get_cart(session_id):
            return {"items": [{"name_ko": "F 버거", "quantity": 1, "unit_price": 6650, "selected_options": [
                {"name": "세트", "option_group": "SET_UPGRADE"}, {"name": "치킨너겟", "option_group": "SET_SIDE"},
                {"name": "제로사이다", "option_group": "SET_DRINK"}, {"name": "양파 제외", "option_group": "EXCLUDE"}]}]}

        orig = llm_service.__dict__.get("api_client")
        from ai_modules.llm import api_client
        saved = api_client.get_cart
        api_client.get_cart = fake_get_cart
        try:
            cart = await llm_service._cart_for_status_reply("s1", [])
            self.assertEqual(
                format_cart_status_reply(cart, "ko"),
                "현재 장바구니에는 F 버거 세트 하나가 담겨 있어요. 사이드는 치킨너겟, 음료는 제로사이다, 양파 빼고. 합계는 6,650원이에요.")
            keep = [{"name": "콜라", "quantity": 1}]
            self.assertIs(await llm_service._cart_for_status_reply("s1", keep), keep)   # 요청 cart가 있으면 그대로
            async def boom(session_id):
                raise RuntimeError("down")
            api_client.get_cart = boom
            self.assertEqual(await llm_service._cart_for_status_reply("s1", []), [])   # 조회 실패 시 기존 동작
        finally:
            api_client.get_cart = saved


class NavigateTests(unittest.TestCase):
    def setUp(self):
        C.reset_actions()

    def test_same_screen_navigate_is_not_emitted(self):
        C.set_screen("cart")
        out = T.navigate("cart")
        self.assertEqual(C.get_actions(), [])
        self.assertIn("이미", out)

    def test_other_screen_navigate_is_emitted(self):
        C.set_screen("menu")
        T.navigate("cart")
        self.assertEqual(C.get_actions(), [{"type": "navigate", "screen": "cart"}])


class NoiseRepromptTests(unittest.TestCase):
    def test_short_utterance_on_waiting_screen_is_reprompted(self):
        from core.llm_service import _should_reprompt_noise
        self.assertTrue(_should_reprompt_noise("갑자기 왜 이게 떠?", "cart"))
        self.assertTrue(_should_reprompt_noise("철제.", "orderType"))

    def test_start_screen_long_or_empty_stay_silent(self):
        from core.llm_service import _should_reprompt_noise
        self.assertFalse(_should_reprompt_noise("철제.", "start"))
        self.assertFalse(_should_reprompt_noise("", "cart"))
        self.assertFalse(_should_reprompt_noise("그래서 내가 어제 말했잖아 그 친구가 그러는데 진짜 웃기더라", "menu"))
        self.assertFalse(_should_reprompt_noise("철제.", None))


class CompleteMissingOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkout_utterance_does_not_add_item(self):
        """2026-10-13: 세트를 담은 뒤 "아니, 그냥 결제해줘"에 비건 버거 단품이 또 담겼다(15,600원)."""
        from core import llm_service
        C.reset_actions()
        C.reset_guards()
        C.set_last_bot_text("비건버거 세트, 사이드 치즈스틱, 음료 콜라로 담았습니다. 다른 메뉴를 더 주문하시겠어요?")
        C.set_recent_user_text("비건버거 하나 해줘 ¦ 세트로 해줘 ¦ 치즈스틱 ¦ 콜라")
        for text in ["아니, 그냥 결제해줘.", "그냥 결제할게요"]:
            with self.subTest(text=text):
                self.assertIsNone(await llm_service._complete_missing_order(text, "담긴 메뉴는 비건 버거 세트 1개입니다."))
        self.assertEqual(C.get_actions(), [])


if __name__ == "__main__":
    unittest.main()
