"""직접 명령 파서·직전 기록·세트 옵션 근거 범위 검증. 고정 시나리오의 실제 발화로 비용 없이 확인한다(API·LLM 호출 없음)."""
import unittest

from ai_modules.llm import action_tools, cart_history, checkout_progress
from core import cart_commands as C
from tests.test_order_parser import MENU
from tools import flow_scenarios_gen as gen


def with_options(item):
    """세트 옵션이 있는 버거로 만든다(파서는 SET_UPGRADE·SET_SIDE·SET_DRINK 옵션 이름으로 매칭한다)."""
    if not any(o.get("option_group") == "SET_UPGRADE" for o in item["options"]):
        return item
    opts = [{"id": "u", "option_group": "SET_UPGRADE", "name_ko": "세트 업그레이드"}]
    opts += [{"id": f"s{i}", "option_group": "SET_SIDE", "name_ko": n}
             for i, n in enumerate(["감자튀김", "치즈스틱", "치킨너겟", "양념감자튀김"])]
    opts += [{"id": f"d{i}", "option_group": "SET_DRINK", "name_ko": n}
             for i, n in enumerate(["콜라", "제로콜라", "사이다", "제로사이다", "생수", "뽀로로 음료수", "오렌지주스"])]
    return {**item, "options": opts}


MENU2 = [with_options(i) for i in MENU]


def kind(text):
    c = C.parse_command(text, MENU2)
    return c["kind"] if c else None


class ParseCommands(unittest.TestCase):
    def test_grammar(self):
        cases = {
            "방금 담은 거 취소해줘": "undo",
            "아까 뺀 코울슬로 다시 담아줘": "readd",
            "아까 뺀 치즈버거 세트 같은 구성으로 다시 담아줘": "readd",
            "데리버거 세트 두 개, 사이드는 치킨너겟 음료는 콜라로 줘": "set_order",
            "새우버거 세트 하나 더, 이번엔 사이드는 치즈스틱 음료는 사이다로 줘": "set_order",
            "치즈버거 단품을 세트로 바꿔줘. 사이드는 양념감자튀김 음료는 오렌지주스": "to_set",
            "새우버거 세트 말고 단품으로 바꿔줘": "to_single",
            "불고기버거 세트 사이드는 치즈스틱 음료는 생수로 바꿔줘": "set_options",
            "불고기버거 세트 음료를 사이다로 바꿔줘": "set_options",
            "치즈버거 단품 하나만 빼줘": "reduce_one",
            "치즈버거 한 개 줄여줘": "reduce_one",
            "치즈버거 하나만 남겨줘": "keep_n",
            "치즈버거 세트로 하나, 사이드는 너겟 음료는 오렌지주스": "set_order",   # 짧은 사이드 이름("너겟" ← 치킨너겟)
            "치즈버거 단품 전부 지워줘": "remove_line",
            "코울슬로 취소해줘": "remove_line",
        }
        for text, want in cases.items():
            self.assertEqual(kind(text), want, text)

    def test_not_commands(self):
        for text in ["치즈버거 세트로 하나 줘", "사이드는 치킨너겟", "치즈버거 양파 빼줘", "치즈버거 단품 빼고 결제할게요", "콜라는 얼마예요?",
                     "결제할게요", "치즈버거 단품으로 줘", "치즈버거 세트 사이드는 치즈스틱 음료는 콜라가 뭐예요?"]:
            self.assertIsNone(kind(text), text)

    def test_all_fixed_scenarios_have_no_false_positive(self):
        """고정 100개 중 명령 문법인 조작만 분류되고, 다른 조작(담기·삭제·수량 지정·결제 등)은 걸리지 않는다."""
        grammar = {"undo_last": "undo", "readd_removed": "readd", "add_set_oneshot": "set_order",
                   "add_second_set": "set_order", "convert_to_set": "to_set", "convert_to_single": "to_single",
                   "change_side": "set_options", "change_drink": "set_options", "change_both": "set_options",
                   "reduce_qty": "reduce_one", "remove_line": "remove_line"}
        for sc in gen.load_fixed():
            for st in sc["steps"]:
                if st["kind"] == "say":
                    got = kind(st["text"])
                    # 시험용 메뉴에 없는 이름(게살버거 등)은 분류되지 않을 수 있다. 문법이 아닌 조작이 걸리면 안 된다.
                    if st.get("op") in grammar:
                        self.assertIn(got, (None, grammar[st["op"]]), f"{sc['id']} {st['text']}")
                    else:
                        self.assertIsNone(got, f"{sc['id']} {st['text']}")


class SetFollowup(unittest.TestCase):
    def test_multi_turn_set(self):
        recent = "새우버거 단품으로 두 개 줘 ¦ 불고기버거 세트로 하나 줘 ¦ 사이드는 양념감자튀김"
        c = C.parse_set_followup("음료는 오렌지주스", recent, MENU2)
        self.assertEqual((c["item"]["name_ko"], c["qty"], c["side"], c["drink"]), ("불고기 버거", 1, "양념감자튀김", "오렌지주스"))
        # 드링크 하나만 말한 상태(사이드 아직 없음) → 담지 않는다
        self.assertIsNone(C.parse_set_followup("음료는 오렌지주스", "불고기버거 세트로 하나 줘", MENU2))
        # 가장 최근 버거 발화가 단품 주문이면 세트가 아니다
        self.assertIsNone(C.parse_set_followup("음료는 오렌지주스", "불고기버거 단품 하나 줘 ¦ 사이드는 치즈스틱", MENU2))
        # 이번 발화가 옵션 이야기가 아니면 건드리지 않는다
        self.assertIsNone(C.parse_set_followup("네", "불고기버거 세트로 하나 줘 ¦ 사이드는 치즈스틱 음료는 콜라", MENU2))


class History(unittest.TestCase):
    def test_undo_covers_whole_turn_and_new_add_resets_checkout(self):
        sid = "t-hist"
        cart_history.reset(sid)
        checkout_progress.mark_done(sid, "start_checkout")
        cart_history.begin_turn(sid)
        cart_history.record_added(sid, "a", "치즈 버거", 1)
        cart_history.record_added(sid, "b", "콜라", 2)
        self.assertEqual([e["cart_item_id"] for e in cart_history.peek_added(sid)], ["a", "b"])
        self.assertNotIn("start_checkout", checkout_progress.snapshot(sid))   # 품목이 늘면 결제 단계가 처음으로
        cart_history.begin_turn(sid)
        cart_history.record_added(sid, "c", "생수", 1)
        self.assertEqual([e["cart_item_id"] for e in cart_history.peek_added(sid)], ["c"])   # 새 턴은 그 턴만

    def test_this_turn_only(self):
        sid = "t-turn"
        cart_history.reset(sid)
        cart_history.begin_turn(sid)
        cart_history.record_added(sid, "a", "생수", 1)
        self.assertEqual(len(cart_history.peek_added(sid, this_turn_only=True)), 1)
        cart_history.begin_turn(sid)
        self.assertEqual(cart_history.peek_added(sid, this_turn_only=True), [])   # 지난 턴 기록은 undo용으로만
        self.assertEqual(len(cart_history.peek_added(sid)), 1)

    def test_removed_lines_of_one_turn_are_all_kept(self):
        sid = "t-rm"
        cart_history.reset(sid)
        cart_history.begin_turn(sid)
        line = {"menu_item_id": "m", "name_ko": "F 버거", "quantity": 1, "selected_options": [{"option_id": "o", "name": "x"}]}
        cart_history.record_removed(sid, line)
        cart_history.record_removed(sid, {**line, "menu_item_id": "n", "quantity": 3})   # "전부 빼줘"가 remove_item 두 번
        got = cart_history.pop_removed(sid)
        self.assertEqual([(l["menu_item_id"], l["quantity"]) for l in got], [("m", 1), ("n", 3)])
        self.assertEqual(got[0]["selected_options"][0]["option_id"], "o")
        self.assertEqual(cart_history.pop_removed(sid), [])
        cart_history.begin_turn(sid)
        cart_history.record_removed(sid, line)
        cart_history.begin_turn(sid)
        cart_history.record_removed(sid, {**line, "menu_item_id": "z"})
        self.assertEqual([l["menu_item_id"] for l in cart_history.peek_removed(sid)], ["z"])   # 새 턴은 그 턴만


class FailureSignals(unittest.TestCase):
    def test_signals(self):
        from ai_modules.llm import order_parser as P
        for out, want in {
            "더블 불고기 버거는 현재 주문할 수 없습니다. 다른 메뉴를 선택하시겠어요?": "claimed_unavailable",
            "오렌지주스를 추가하는 데 문제가 발생했습니다. 다시 시도해 보시겠어요?": "claimed_unavailable",
            "모짜렐라 버거 단품은 7200원입니다. 단품으로 두 개 담아드릴까요?": "asked_single_set",
            "불고기버거 단품 1개를 추가로 담겠습니다. 다른 메뉴를 더 주문하시겠어요?": "asked_single_set",
            "치즈 버거 단품 1개 담았습니다.": "claimed_add",
            "매장 식사로 선택했습니다. 메뉴를 읽어 드릴까요?": None,
        }.items():
            self.assertEqual(P.reply_failed_to_act(out), want, out)


class BurgerOnly(unittest.TestCase):
    def test_burger_only_order(self):
        from ai_modules.llm import order_parser as P
        self.assertEqual(P.burger_only_order("데리버거 하나 줘", MENU2), "데리버거")
        self.assertEqual(P.burger_only_order("치즈버거 주세요", MENU2), "치즈 버거")
        for t in ["데리버거 단품 하나 줘", "데리버거 세트로 줘", "데리버거 하나 더 줘", "데리버거 얼마예요?",
                  "데리버거랑 콜라 줘", "데리버거 빼줘", "콜라 하나 줘"]:
            self.assertIsNone(P.burger_only_order(t, MENU2), t)

    def test_every_burger_ask_in_fixed_scenarios(self):
        """고정 시나리오의 "X 하나 줘"(단품/세트 되묻기 대상)는 모두 걸리고, 다른 조작의 발화는 걸리지 않는다."""
        from ai_modules.llm import order_parser as P
        for sc in gen.load_fixed():
            for st in sc["steps"]:
                if st["kind"] == "say":
                    got = P.burger_only_order(st["text"], MENU2)
                    if st.get("op") not in ("add_burger_ask",) or "단품으로 줘" == st["text"]:
                        self.assertIsNone(got, f"{sc['id']} {st['text']}")


class MenuMatch(unittest.TestCase):
    def test_substring_name_is_not_a_match(self):
        """"양념감자튀김"을 말했는데 "감자튀김"이 넘어오면 어긋난 것이다(부분 문자열이라 맞다고 보던 결함)."""
        menu = MENU2
        by = {i["name_ko"]: i for i in menu}
        wrong = action_tools._mentions_other_menu("양념감자튀김 세 개 그리고 콜라 세 잔 줘", by["감자튀김(M)"], menu=menu)
        self.assertEqual(wrong[0], "양념감자튀김")
        self.assertIsNone(action_tools._mentions_other_menu("양념감자튀김 세 개 줘", by["양념감자튀김"], menu=menu))
        self.assertIsNone(action_tools._mentions_other_menu("감자튀김 두 개 줘", by["감자튀김(M)"], menu=menu))
        self.assertIsNone(action_tools._mentions_other_menu("치즈스틱 세 개 줘", by["치즈스틱(2개)"], menu=menu))


class Hints(unittest.TestCase):
    def test_hint_carries_ids_and_quantities(self):
        from core import order_hints as H
        h = H.build_hint("오렌지주스 세 잔 그리고 F버거 단품 두 개 줘", MENU2)
        by = {i["name_ko"]: i["id"] for i in MENU2}
        self.assertEqual(sorted((n, q) for _, n, q in h["expected"]), [("F 버거", 2), ("오렌지 주스", 3)])
        self.assertIn(by["F 버거"], h["text"])
        self.assertIn('quantity=3', h["text"])

    def test_no_hint_when_unsure(self):
        from core import order_hints as H
        for t in ["F버거 하나 줘", "F버거 세트 하나 줘", "콜라는 얼마예요?", "치즈버거 빼줘", "네"]:
            self.assertIsNone(H.build_hint(t, MENU2), t)
        # 세트의 사이드·음료를 고르는 중이면 "콜라로 주세요"는 단품 주문이 아니다
        self.assertIsNone(H.build_hint("콜라로 주세요", MENU2, "음료는 어떤 걸로 드릴까요?"))

    def test_missing_and_retry(self):
        from core import order_hints as H
        h = H.build_hint("콜라 두 잔 그리고 생수 한 잔 줘", MENU2)
        ids = {n: m for m, n, _ in h["expected"]}
        miss = H.missing_items(h, [{"type": "add_item", "menu_item_id": ids["생수"]}])
        self.assertEqual([n for _, n, _ in miss], ["콜라(M)"])
        txt = H.retry_text(miss, "담았습니다")
        self.assertIn(ids["콜라(M)"], txt)
        self.assertNotIn(ids["생수"], txt)   # 이미 담긴 품목은 다시 시키지 않는다
        self.assertEqual(H.missing_items(h, [{"type": "add_item", "menu_item_id": m} for m in ids.values()]), [])


class AwaitingOption(unittest.TestCase):
    def test_only_a_trailing_question_counts(self):
        from ai_modules.llm import order_parser as P
        self.assertTrue(P.awaiting_set_option("치킨 가슴살 버거 세트로 드릴까요? 사이드는 어떤 걸로 드릴까요?"))
        self.assertTrue(P.awaiting_set_option("사이드는 감자튀김으로 선택했습니다. 음료는 무엇으로 드릴까요?"))
        self.assertTrue(P.awaiting_set_option("음료는 어떤 걸로 드릴까요? 콜라, 제로콜라, 생수 중에서 선택해 주세요."))
        self.assertFalse(P.awaiting_set_option("치킨 가슴살 버거 세트 1개, 사이드 감자튀김, 음료 오렌지주스 담았습니다. 다른 메뉴를 더 주문하시겠어요?"))
        self.assertFalse(P.awaiting_set_option(""))


class OptionContext(unittest.TestCase):
    def test_previous_sets_options_do_not_count(self):
        recent = "불고기버거 단품으로 세 개 줘 ¦ 더블치즈버거 세트 두 개, 사이드는 감자튀김 음료는 제로콜라로 줘"
        ctx = action_tools._option_context("불고기버거 세트로 하나 줘", recent, "불고기 버거", MENU2)
        self.assertNotIn("제로콜라", ctx)   # 이번 발화에 버거 이름이 있으면 이번 발화만
        ctx = action_tools._option_context("음료는 제로사이다", recent + " ¦ 불고기버거 세트로 하나 줘 ¦ 사이드는 치킨너겟",
                                           "불고기 버거", MENU2)
        self.assertIn("치킨너겟", ctx)      # 같은 세트를 여러 턴에 걸쳐 주문하는 중
        self.assertNotIn("제로콜라", ctx)
        ctx = action_tools._option_context("음료는 콜라", "더블치즈버거 세트로 줘 ¦ 사이드는 치즈스틱", "불고기 버거", MENU2)
        self.assertNotIn("치즈스틱", ctx)   # 다른 버거의 세트를 말하던 중


if __name__ == "__main__":
    unittest.main()
