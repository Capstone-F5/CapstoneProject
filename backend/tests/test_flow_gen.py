import unittest

from tools import flow_scenarios_gen as gen
from tools.voice_scenario_suite import cart_exact_fail


def _burger(name, excls):
    opts = [{"option_group": "SET_UPGRADE", "name_ko": "세트 업그레이드"}]
    opts += [{"option_group": "SET_SIDE", "name_ko": n} for n in ("감자튀김", "치즈스틱", "치킨너겟", "양념감자튀김")]
    opts += [{"option_group": "SET_DRINK", "name_ko": n} for n in ("콜라", "제로콜라", "사이다", "제로사이다", "생수")]
    opts += [{"option_group": "EXCLUDE", "name_ko": n} for n in excls]
    return {"name_ko": name, "options": opts}


FAKE_MENU = {"menu_items": {
    "burger": [
        _burger("치즈 버거", ["다진 양파 제외", "피클 제외"]),
        _burger("더블 치즈 버거", ["다진 양파 제외", "피클 제외"]),
        _burger("새우 버거", ["채썬 양배추 제외"]),
        _burger("불고기 버거", ["양상추 제외", "양파 제외"]),
        _burger("데리버거", ["양상추 제외", "양파 제외"]),
        _burger("F 버거", ["양상추 제외", "양파 제외", "양배추(또는 양상추) 제외"]),
    ],
    "side": [{"name_ko": n} for n in ("코울슬로", "양념감자튀김", "감자튀김(M)", "너겟(4조각)", "치즈스틱(2개)")],
    "beverage": [{"name_ko": n} for n in ("제로 콜라(M)", "콜라(M)", "사이다(M)", "오렌지 주스", "생수")],
}}


class FlowGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.menu = gen.MenuData(FAKE_MENU)

    def _all(self):
        out = []
        for seed in range(1, 41):
            out += gen.generate_random(self.menu, 10, seed)
        return out

    def test_same_seed_same_scenarios(self):
        a = gen.generate_random(self.menu, 12, 5)
        b = gen.generate_random(self.menu, 12, 5)
        self.assertEqual(a, b)
        self.assertNotEqual(a, gen.generate_random(self.menu, 12, 6))

    def test_fixed_set_is_100_and_stable(self):
        a = gen.generate_fixed(self.menu)
        self.assertEqual(len(a), 100)
        self.assertEqual([s["id"] for s in a][:2], ["W001", "W002"])
        self.assertEqual(a, gen.generate_fixed(self.menu))

    def test_expected_carts_are_always_valid(self):
        burgers = {b["name"]: b for b in self.menu.burgers}
        singles = set(self.menu.sides) | set(self.menu.drinks)
        for sc in self._all():
            prev = None
            for st in sc["steps"]:
                if st["kind"].startswith("touch"):
                    prev = None   # 터치 조작은 말 없이 장바구니를 바꾸므로 직전 기대값과 비교하지 않는다
                    continue
                if st["kind"] != "say":
                    continue
                exp = st["checks"].get("cart_exact")
                if exp is None:
                    continue
                for e in exp:
                    with self.subTest(sc=sc["id"], text=st["text"]):
                        self.assertGreaterEqual(e["qty"], 1)
                        if e["name"] in burgers:
                            b = burgers[e["name"]]
                            opts = e["opts"]
                            if "세트 업그레이드" in opts:
                                self.assertEqual(opts[0], "세트 업그레이드")
                                self.assertIn(opts[1], b["sides"])
                                self.assertIn(opts[2], b["drinks"])
                                rest = opts[3:]
                            else:
                                rest = opts
                            for r in rest:
                                self.assertIn(r, b["excls"])
                        else:
                            self.assertIn(e["name"], singles)
                            self.assertEqual(e["opts"], [])
                if st["checks"].get("no_actions") == ["add_item"] and prev is not None:
                    # 담지 않아야 하는 턴(되묻기·질문)은 직전 기대 장바구니와 같아야 한다
                    self.assertEqual(exp, prev, msg=f"{sc['id']} {st['text']}")
                prev = exp

    def test_checkout_always_has_items(self):
        for sc in self._all():
            start = next(s for s in sc["steps"] if s["kind"] == "say" and s["op"] == "pay_start" and "cart_exact" in s["checks"])
            self.assertTrue(start["checks"]["cart_exact"], msg=sc["id"])

    def test_no_burger_names_that_contain_each_other_in_one_scenario(self):
        for sc in self._all():
            names = set()
            for st in sc["steps"]:
                for e in st.get("checks", {}).get("cart_exact", []) or []:
                    if e["name"] in {b["name"] for b in self.menu.burgers}:
                        names.add(e["name"].replace(" ", ""))
            for a in names:
                for b in names:
                    if a != b:
                        self.assertNotIn(a, b, msg=f"{sc['id']}: {a} ⊂ {b}")

    def test_tiers_cover_edit_and_set_operations(self):
        ops = set()
        for sc in self._all():
            ops |= {s["op"] for s in sc["steps"] if s.get("op")}
        for needed in ("remove_line", "undo_last", "readd_removed", "change_side", "change_drink",
                       "convert_to_set", "convert_to_single", "add_exclusion", "add_second_set", "reduce_qty",
                       "set_qty", "add_more", "touch_add", "pay_back_add", "pay_method_change"):
            self.assertIn(needed, ops)


class CartExactTests(unittest.TestCase):
    CART = [
        {"name": "불고기 버거", "qty": 1, "set": True, "opts": ["세트 업그레이드", "감자튀김", "콜라"]},
        {"name": "불고기 버거", "qty": 1, "set": True, "opts": ["세트 업그레이드", "감자튀김", "콜라"]},
        {"name": "콜라(M)", "qty": 2, "set": False, "opts": []},
    ]

    def test_equal_even_if_lines_are_split(self):
        exp = [{"name": "불고기 버거", "opts": ["세트 업그레이드", "감자튀김", "콜라"], "qty": 2},
               {"name": "콜라(M)", "opts": [], "qty": 2}]
        self.assertIsNone(cart_exact_fail(self.CART, exp))

    def test_reports_wrong_option_and_quantity(self):
        exp = [{"name": "불고기 버거", "opts": ["세트 업그레이드", "치즈스틱", "콜라"], "qty": 2},
               {"name": "콜라(M)", "opts": [], "qty": 3}]
        self.assertIn("불일치", cart_exact_fail(self.CART, exp))

    def test_extra_line_is_a_failure(self):
        exp = [{"name": "콜라(M)", "opts": [], "qty": 2}]
        self.assertIn("불일치", cart_exact_fail(self.CART, exp))


if __name__ == "__main__":
    unittest.main()
