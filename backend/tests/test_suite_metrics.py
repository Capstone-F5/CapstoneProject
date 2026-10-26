"""suite_metrics: 연쇄 실패를 걷어내는 집계 로직을 검사한다. 서버·LLM 없음."""
import unittest

from tools import suite_metrics as m


def cart(*lines):
    return [{"name": n, "qty": q, "opts": list(o)} for n, q, o in lines]


class DiscrepancyTests(unittest.TestCase):
    def test_diff_and_new_discrepancy(self):
        want = m.counts_from_expected([{"name": "치즈 버거", "opts": [], "qty": 1}, {"name": "콜라", "opts": [], "qty": 2}])
        got = m.counts_from_cart(cart(("치즈 버거", 1, []), ("콜라", 2, [])))
        self.assertEqual(m.diff(got, want), {})
        got2 = m.counts_from_cart(cart(("치즈 버거", 1, [])))   # 콜라 누락
        d = m.diff(got2, want)
        self.assertEqual(sum(d.values()), -2)
        self.assertTrue(m.new_discrepancy(d, {}))

    def test_same_discrepancy_carried_forward_is_not_new(self):
        d = {("콜라", ()): -2}
        self.assertFalse(m.new_discrepancy(dict(d), dict(d)))

    def test_growing_or_flipping_discrepancy_is_new(self):
        self.assertTrue(m.new_discrepancy({("콜라", ()): -3}, {("콜라", ()): -2}))
        self.assertTrue(m.new_discrepancy({("콜라", ()): 1}, {("콜라", ()): -1}))
        self.assertTrue(m.new_discrepancy({("사이다", ()): 1}, {("콜라", ()): -1}))

    def test_resolved_discrepancy_is_not_new(self):
        self.assertFalse(m.new_discrepancy({}, {("콜라", ()): -2}))
        self.assertFalse(m.new_discrepancy({("콜라", ()): -1}, {("콜라", ()): -2}))


class SoftReplaceTests(unittest.TestCase):
    BEFORE = m.counts_from_cart(cart(("데리버거", 1, [])))

    def test_remove_then_ask_is_soft(self):
        after = m.counts_from_cart([])
        self.assertTrue(m.is_soft_replace(self.BEFORE, after, ["remove_item"], "데리버거 단품을 취소했습니다. 새우 버거는 4,800원입니다. 담아드릴까요?"))

    def test_remove_without_question_or_with_add_is_not_soft(self):
        after = m.counts_from_cart([])
        self.assertFalse(m.is_soft_replace(self.BEFORE, after, ["remove_item"], "취소했습니다."))
        self.assertFalse(m.is_soft_replace(self.BEFORE, after, ["remove_item", "add_item"], "담아드릴까요?"))
        self.assertFalse(m.is_soft_replace(self.BEFORE, self.BEFORE, ["update_item"], "담아드릴까요?"))
        wrong_add = m.counts_from_cart(cart(("불고기 버거", 1, [])))
        self.assertFalse(m.is_soft_replace(self.BEFORE, wrong_add, ["remove_item"], "담아드릴까요?"))


class StatusAndSummaryTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(m.scenario_status([{"real_fail": False, "soft_fail": False}]), "PASS")
        self.assertEqual(m.scenario_status([{"soft_fail": True}, {}]), "SOFT")
        self.assertEqual(m.scenario_status([{"soft_fail": True}, {"real_fail": True}]), "FAIL")

    def test_wilson(self):
        lo, hi = m.wilson(3, 6)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertEqual(m.wilson(0, 0), (0.0, 0.0))
        lo, hi = m.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.2)

    def test_summary_separates_cascade_from_new_failures(self):
        # 시나리오 A: 4턴 중 2번째 턴에서 새 실패, 3·4턴은 연쇄(엄격 실패이지만 새 실패 아님)
        a = {"ok": False, "status": "FAIL", "turns": [
            {"op": "add_single", "fails": [], "ms": 1000},
            {"op": "change_mind", "fails": ["x"], "real_fail": True, "ms": 2000},
            {"op": "set_qty", "fails": ["x"], "real_fail": False, "ms": 3000},
            {"op": "query", "fails": ["x"], "real_fail": False, "ms": 4000}]}
        b = {"ok": True, "status": "PASS", "turns": [{"op": "add_single", "fails": [], "ms": 1000}, {"op": "set_qty", "fails": [], "ms": 1000}]}
        c = {"ok": False, "status": "SOFT", "turns": [{"op": "change_mind", "fails": ["x"], "soft_fail": True, "ms": 1000}]}
        s = m.summarize([a, b, c])
        self.assertEqual(s["strict_pass"], 1)
        self.assertEqual(s["status"], {"PASS": 1, "SOFT": 1, "FAIL": 1})
        self.assertEqual(s["resync_new_fail"], (2, 7))        # 새 실패 2건 / 전체 7턴
        self.assertEqual(s["strict_first_fail"], (2, 5))      # 엄격 첫 실패 2건(A, C) / 첫 실패까지의 턴 5개(A 2 + B 2 + C 1)
        cm = s["per_op"]["change_mind"]
        self.assertEqual((cm["n"], cm["fail"], cm["soft"]), (2, 1, 1))
        self.assertEqual(s["per_op"]["set_qty"]["fail"], 0)   # 연쇄는 set_qty 실패로 세지 않는다
        text = m.format_summary(s)
        self.assertIn("PASS 1 / SOFT 1 / FAIL 1", text)
        self.assertIn("change_mind", text)


if __name__ == "__main__":
    unittest.main()
