"""규칙 기반 단순 주문 파서 검증. 생성기가 만든 실제 발화로 비용 없이 확인한다(API·LLM 호출 없음)."""
import unittest

from ai_modules.llm import order_parser as P
from tools import flow_scenarios_gen as gen
from tests.test_flow_gen import FAKE_MENU

UP = [{"option_group": "SET_UPGRADE"}]


def build_menu():
    items, n = [], 0
    for b in FAKE_MENU["menu_items"]["burger"]:
        n += 1
        items.append({"id": f"{n:08d}-0000-0000-0000-000000000000", "name_ko": b["name_ko"], "options": UP})
    for k in ("side", "beverage"):
        for s in FAKE_MENU["menu_items"][k]:
            n += 1
            items.append({"id": f"{n:08d}-0000-0000-0000-000000000000", "name_ko": s["name_ko"], "options": []})
    return items


MENU = build_menu()


def names(parsed):
    return sorted((i["name_ko"], q) for i, q in parsed) if parsed else None


class ParseCases(unittest.TestCase):
    def test_items_spoken_without_separators(self):
        """구분어 없이 이어 말한 다품목 주문(2026-10-04 시나리오 H03): 수량 표현 뒤에 다른 메뉴 이름이 이어지면 나눈다."""
        cases = {
            "치즈 버거 단품 한개 콜라 한잔": [("치즈 버거", 1), ("콜라(M)", 1)],
            "치즈버거 단품 두 개 콜라 한 잔 생수 하나": [("생수", 1), ("치즈 버거", 2), ("콜라(M)", 1)],
            "치즈버거 단품 하나 줘": [("치즈 버거", 1)],          # "하나 줘"의 "줘"는 메뉴가 아니므로 나누지 않는다
            "콜라 한 잔 줘": [("콜라(M)", 1)],
        }
        for text, want in cases.items():
            self.assertEqual(sorted(names(P.parse_simple_order(text, MENU)) or []), sorted(want), text)

    def test_simple_orders(self):
        cases = {
            "치즈버거 단품 세 개 주세요": [("치즈 버거", 3)],
            "콜라 두 잔 줘": [("콜라(M)", 2)],
            "치즈버거 단품 하나랑 감자튀김 하나": [("감자튀김(M)", 1), ("치즈 버거", 1)],
            "오렌지주스 한 잔 그리고 데리버거 단품 하나 줘": [("데리버거", 1), ("오렌지 주스", 1)],
            "생수 세 잔 그리고 새우버거 단품 하나 그리고 너겟": [("너겟(4조각)", 1), ("새우 버거", 1), ("생수", 3)],
            "콘샐러드 세 개 그리고 생수 두 잔 그리고 F버거 단품 하나 주세요": None,   # 콘샐러드는 FAKE 메뉴에 없다
            "F버거 단품 하나 담아줘": [("F 버거", 1)],
            "아 잠깐 뽀로로음료수도 한 잔 추가할게요": None,   # 뽀로로는 FAKE 메뉴에 없다
            "더블치즈버거 단품 두 개 주세요": [("더블 치즈 버거", 2)],
            "콜라 하나 추가해줘": [("콜라(M)", 1)],
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                got = names(P.parse_simple_order(text, MENU))
                self.assertEqual(got, sorted(want) if want else None)

    def test_not_simple_returns_none(self):
        for text in [
            "치즈버거 하나 줘",                       # 버거에 단품 표시 없음 → 되묻는 것이 설계
            "불고기버거 세트로 하나 줘",              # 세트
            "콜라는 얼마예요?",                       # 질문
            "치즈버거 빼줘",                          # 삭제
            "치즈버거 단품 하나 그리고 사이드 추천해줘",   # 모르는 말이 남음
            "치즈버거 단품 하나 그리고 불고기버거 하나",  # 두 번째 버거에 단품 없음
            "안녕하세요", "", "Hello",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(P.parse_simple_order(text, MENU))

    def test_set_option_question_is_not_a_new_order(self):
        # 세트 음료를 묻는 중에 나온 "콜라로 주세요"를 단품 주문으로 담으면 안 된다(실제 오탐 사례 W057)
        self.assertTrue(P.awaiting_set_option("음료는 콜라, 제로콜라, 사이다 중 어떤 걸로 드릴까요?"))
        self.assertTrue(P.awaiting_set_option("사이드는 감자튀김, 치즈스틱 중 뭐로 드릴까요?"))
        self.assertFalse(P.awaiting_set_option("치즈 버거 단품 1개 담았습니다. 다른 메뉴를 더 주문하시겠어요?"))
        self.assertFalse(P.awaiting_set_option(""))

    def test_reply_signals(self):
        self.assertEqual(P.reply_failed_to_act("모짜렐라 버거 단품 1개 담았습니다."), "claimed_add")
        self.assertEqual(P.reply_failed_to_act("콘샐러드는 메뉴에 없습니다."), "claimed_unavailable")
        self.assertEqual(P.reply_failed_to_act("치킨너겟은 현재 품절입니다."), "claimed_unavailable")
        self.assertEqual(P.reply_failed_to_act("그릴드 비프 버거 단품으로 드릴까요?"), "asked_single_set")
        self.assertIsNone(P.reply_failed_to_act("가격은 4,000원입니다."))


class AgainstGeneratedScenarios(unittest.TestCase):
    """생성기가 만든 단순 담기 발화(add_single/add_multi)는 기대 장바구니 증가분과 정확히 같게 풀려야 한다."""

    def test_parser_matches_expected_additions(self):
        menu = gen.MenuData(FAKE_MENU)
        checked = 0
        for seed in range(1, 31):
            for sc in gen.generate_random(menu, 12, seed):
                prev: dict = {}
                for st in sc["steps"]:
                    if st["kind"] != "say":
                        if st["kind"].startswith("touch"):
                            prev = None
                        continue
                    exp = st["checks"].get("cart_exact")
                    cur = None
                    if exp is not None:
                        cur = {}
                        for e in exp:
                            k = (e["name"], tuple(e["opts"]))
                            cur[k] = cur.get(k, 0) + e["qty"]
                    if st.get("op") in ("add_single", "add_multi") and prev is not None and cur is not None:
                        delta = {k: v - prev.get(k, 0) for k, v in cur.items() if v != prev.get(k, 0)}
                        parsed = P.parse_simple_order(st["text"], MENU)
                        if parsed is not None:
                            # 파서가 풀었다면 증가분과 정확히 같아야 한다(틀리게 푸는 것이 가장 위험하다)
                            got = {(i["name_ko"], ()): q for i, q in parsed}
                            self.assertEqual(got, delta, msg=f"{sc['id']} {st['text']}")
                            checked += 1
                    if cur is not None:
                        prev = cur
        self.assertGreater(checked, 50)   # 충분히 많은 발화가 실제로 검증되었는지


if __name__ == "__main__":
    unittest.main()
