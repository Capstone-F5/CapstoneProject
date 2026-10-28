"""LLM 손님 시뮬레이터(층 C)의 순수 로직을 가짜 손님·가짜 키오스크로 검사한다. LLM·서버 호출 없음."""
import random
import unittest

from tests.test_flow_gen import FAKE_MENU
from tools import flow_scenarios_gen as gen
from tools import persona_sim as ps


class FakeKiosk:
    """손님이 한 말을 그대로 장바구니에 반영하지는 않는다 — 테스트가 장바구니와 응답을 직접 정한다."""

    def __init__(self, replies, cart):
        self.replies, self._cart, self.heard = list(replies), cart, []

    def say(self, text):
        self.heard.append(text)
        return self.replies.pop(0)

    def cart(self):
        return self._cart


def cart_of(goal):
    return [{"name": e["name"], "qty": e["qty"], "set": "세트 업그레이드" in e["opts"],
             "opts": [o if o != "세트 업그레이드" else "세트 업그레이드" for o in e["opts"]]} for e in goal.expected]


class GoalTests(unittest.TestCase):
    def setUp(self):
        self.menu = gen.MenuData(FAKE_MENU)

    def test_goals_are_valid_and_reproducible(self):
        for name, persona in ps.PERSONAS.items():
            for i in range(25):
                g = ps.make_goal(self.menu, random.Random(f"{name}-{i}"), persona)
                self.assertTrue(g.lines and g.expected, name)
                self.assertEqual(g.expected, ps.make_goal(self.menu, random.Random(f"{name}-{i}"), persona).expected)
                burgers = [l["name"] for l in g.lines if l["kind"] == "burger"]
                for a in burgers:   # 이름이 서로 포함되는 버거는 한 주문에 없다
                    for b in burgers:
                        if a != b:
                            self.assertNotIn(gen._compact(a), gen._compact(b))

    def test_allergy_goal_avoids_the_allergen(self):
        by_name = {b["name"]: b for b in self.menu.burgers}
        for i in range(30):
            g = ps.make_goal(self.menu, random.Random(i), ps.PERSONAS["알레르기부모"])
            self.assertIsNotNone(g.allergy_name)
            for l in g.lines:
                if l["kind"] == "burger":
                    self.assertNotIn(g.allergy_name, by_name[l["name"]]["allergens"].values())
            self.assertIn(g.allergy_name, ps.build_customer_prompt(ps.PERSONAS["알레르기부모"], g))

    def test_changes_mind_first_pick_is_not_in_goal(self):
        for i in range(30):
            g = ps.make_goal(self.menu, random.Random(i), ps.PERSONAS["마음바꾸는손님"])
            self.assertIsNotNone(g.first_pick)
            self.assertNotIn(g.first_pick, {l["name"] for l in g.lines})

    def test_prompt_has_goal_persona_and_rules_but_english_for_foreigner(self):
        g = ps.make_goal(self.menu, random.Random(1), ps.PERSONAS["외국인"])
        prompt = ps.build_customer_prompt(ps.PERSONAS["외국인"], g)
        self.assertIn(ps.describe_goal(g), prompt)
        self.assertIn("English", prompt)
        self.assertIn(ps.END, prompt)
        self.assertIn("한국어 구어체", ps.build_customer_prompt(ps.PERSONAS["할머니"], g))


class AnomalyTests(unittest.TestCase):
    def test_empty_reply_repeats_and_stuck_customer(self):
        turns = [{"say": "치즈버거 줘", "output": "", "ms": 100},
                 {"say": "치즈버거 줘", "output": "잘 못 들었어요.", "ms": 100},
                 {"say": "치즈버거 하나요", "output": "잘 못 들었어요.", "ms": 100},
                 {"say": "음", "output": "잘 못 들었어요.", "ms": 20000}]
        found = ps.detect_anomalies(turns)
        self.assertTrue(any("비어 있음" in f for f in found))
        self.assertTrue(any("같은 응답 3회" in f for f in found))
        self.assertTrue(any("같은 말을 반복" in f for f in found))
        self.assertTrue(any("지연" in f for f in found))

    def test_clean_conversation_has_none(self):
        turns = [{"say": "안녕", "output": "매장에서 드실 건가요?", "ms": 900}, {"say": "매장", "output": "메뉴를 읽어 드릴까요?", "ms": 900}]
        self.assertEqual(ps.detect_anomalies(turns), [])


class SimulateTests(unittest.TestCase):
    def setUp(self):
        self.menu = gen.MenuData(FAKE_MENU)
        self.persona = ps.PERSONAS["급한직장인"]
        self.goal = ps.make_goal(self.menu, random.Random(5), self.persona)

    def _customer(self, lines):
        it = iter(lines)
        return lambda system, history: next(it, ps.END)

    def test_pass_when_cart_matches_goal_and_payment_reached(self):
        kiosk = FakeKiosk([{"output": "매장에서 드실 건가요?", "actions": []},
                           {"output": "결제 수단은요?", "actions": ["start_checkout"]},
                           {"output": "카드 단말기에 카드를 넣어 주세요.", "actions": ["payment_method"]}], cart_of(self.goal))
        r = ps.simulate(self.persona, self.goal, self._customer(["안녕", "결제할게", "카드로 할게요"]), kiosk, None)
        self.assertTrue(r.ok, (r.cart_msg, r.error))
        self.assertEqual(len(r.turns), 3)

    def test_fail_when_cart_differs_or_never_paid(self):
        wrong = cart_of(self.goal)[:-1] or [{"name": "엉뚱", "qty": 1, "set": False, "opts": []}]
        kiosk = FakeKiosk([{"output": "네", "actions": []}], wrong)
        r = ps.simulate(self.persona, self.goal, self._customer(["안녕"]), kiosk, None)
        self.assertFalse(r.ok)
        self.assertFalse(r.paid)
        self.assertIsNotNone(r.cart_msg)

    def test_customer_end_token_stops_and_conversation_is_fed_back(self):
        seen = []

        def customer(system, history):
            seen.append(list(history))
            return ps.END if len(seen) > 1 else "안녕"
        kiosk = FakeKiosk([{"output": "어서 오세요", "actions": []}], cart_of(self.goal))
        ps.simulate(self.persona, self.goal, customer, kiosk, None)
        self.assertEqual(seen[1][-2:], [{"role": "assistant", "content": "안녕"}, {"role": "user", "content": "키오스크: 어서 오세요"}])

    def test_exception_is_reported_not_raised(self):
        def boom(system, history):
            raise TimeoutError("llm down")
        r = ps.simulate(self.persona, self.goal, boom, FakeKiosk([], []), None)
        self.assertIn("TimeoutError", r.error)
        self.assertFalse(r.ok)

    def test_customer_speech_is_humanized_with_persona_level(self):
        persona = ps.PERSONAS["말많은손님"]
        goal = ps.make_goal(self.menu, random.Random(2), persona)
        heard = []
        for seed in range(40):
            kiosk = FakeKiosk([{"output": "네", "actions": []}], cart_of(goal))
            ps.simulate(persona, goal, self._customer(["치즈버거 단품으로 줘"]), kiosk, random.Random(seed))
            heard += kiosk.heard
        self.assertGreater(len({h for h in heard}), 1)   # 같은 말도 변형이 들어간다


if __name__ == "__main__":
    unittest.main()
