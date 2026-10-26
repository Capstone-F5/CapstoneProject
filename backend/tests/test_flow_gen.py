import unittest

from tools import flow_scenarios_gen as gen
from tools.voice_scenario_suite import cart_exact_fail


_ALLERGENS = {"SOY": "대두", "SHRIMP": "새우", "MILK": "우유", "WHEAT": "밀"}
_BURGER_ALLERGENS = {"치즈 버거": ["WHEAT", "MILK"], "더블 치즈 버거": ["WHEAT", "MILK"], "새우 버거": ["WHEAT", "SHRIMP"],
                     "불고기 버거": ["WHEAT", "SOY"], "데리버거": ["WHEAT", "SOY"], "F 버거": ["WHEAT", "SOY"]}


def _burger(name, excls):
    opts = [{"option_group": "SET_UPGRADE", "name_ko": "세트 업그레이드"}]
    opts += [{"option_group": "SET_SIDE", "name_ko": n} for n in ("감자튀김", "치즈스틱", "치킨너겟", "양념감자튀김")]
    opts += [{"option_group": "SET_DRINK", "name_ko": n} for n in ("콜라", "제로콜라", "사이다", "제로사이다", "생수")]
    opts += [{"option_group": "EXCLUDE", "name_ko": n} for n in excls]
    return {"name_ko": name, "options": opts,
            "allergens": [{"code": c, "name_ko": _ALLERGENS[c]} for c in _BURGER_ALLERGENS.get(name, [])]}


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

    def _all_human(self):
        out = []
        for seed in range(1, 41):
            out += gen.generate_random(self.menu, 10, seed, human=2, tiers=["사람처럼"])
        return out

    def test_expected_carts_are_always_valid(self):
        self._assert_carts_valid(self._all())

    def test_expected_carts_are_valid_in_human_tier(self):
        self._assert_carts_valid(self._all_human())

    def _assert_carts_valid(self, scenarios):
        burgers = {b["name"]: b for b in self.menu.burgers}
        singles = set(self.menu.sides) | set(self.menu.drinks)
        for sc in scenarios:
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

    def test_default_generation_is_unchanged_by_new_features(self):
        """사람처럼 티어·말투 변형을 넣어도 human=0 기본 생성(고정 100개 포함)의 시나리오는 그대로여야 한다."""
        base = gen.generate_random(self.menu, 20, 9)
        self.assertEqual(base, gen.generate_random(self.menu, 20, 9, human=0, tiers=None))
        self.assertTrue(all("사람처럼" not in s["title"] for s in base))
        self.assertTrue(all(" · H" not in s["title"] for s in base))

    def test_human_levels_keep_the_skeleton(self):
        """말투 변형은 문장만 바꾼다: 같은 시드에서 조작·액션 검사·기대 장바구니·숫자와 메뉴 이름은 human 0/1/2에서 같다."""
        import re
        for seed in range(1, 15):
            a = gen.generate_random(self.menu, 6, seed, human=0)
            for level in (1, 2):
                b = gen.generate_random(self.menu, 6, seed, human=level)
                for x, y in zip(a, b):
                    self.assertEqual(len(x["steps"]), len(y["steps"]))
                    for sx, sy in zip(x["steps"], y["steps"]):
                        self.assertEqual(sx["kind"], sy["kind"])
                        self.assertEqual(sx.get("checks"), sy.get("checks"))
                        if sx["kind"] == "say":
                            self.assertEqual(re.findall(r"\d+", sx["text"]), re.findall(r"\d+", sy["text"]))
        changed = sum(1 for seed in range(1, 15) for x, y in zip(gen.generate_random(self.menu, 6, seed),
                                                                 gen.generate_random(self.menu, 6, seed, human=2))
                      for sx, sy in zip(x["steps"], y["steps"]) if sx["kind"] == "say" and sx["text"] != sy["text"])
        self.assertGreater(changed, 20)   # 변형이 실제로 일어난다

    def test_injected_stt_errors_are_ones_the_server_corrects(self):
        """오인식을 넣은 발화는 서버 교정(fix_stt)을 거치면 원래 말이 돼야 한다 — 교정 못 하는 오인식을 넣으면 거짓 실패가 난다."""
        from ai_modules.llm.guards import fix_stt
        seen = 0
        for seed in range(1, 60):
            for sc in gen.generate_random(self.menu, 8, seed, human=2):
                for st in sc["steps"]:
                    if st["kind"] == "say" and any(w in st["text"] for w in ("단풍", "결재")):
                        seen += 1
                        fixed = fix_stt(st["text"])
                        self.assertNotIn("단풍", fixed, st["text"])
                        self.assertNotIn("결재", fixed, st["text"])
        self.assertGreater(seen, 3)

    def test_human_tier_covers_new_behaviours(self):
        ops = set()
        titles = []
        for sc in self._all_human():
            ops |= {s["op"] for s in sc["steps"] if s.get("op")}
            titles.append(sc["title"])
        for needed in ("noise_turn", "ask_mid_order", "change_mind", "allergy_have", "pay_accident"):
            self.assertIn(needed, ops)
        self.assertTrue(all(t.startswith("[사람처럼]") and t.endswith(" · H2") for t in titles))

    def test_noise_and_questions_never_expect_cart_changes(self):
        for sc in self._all_human():
            prev = None
            for st in sc["steps"]:
                if st["kind"] != "say":
                    prev = None
                    continue
                exp = st["checks"].get("cart_exact")
                if st["op"] in ("noise_turn", "ask_mid_order") and prev is not None:
                    self.assertEqual(exp, prev, sc["id"])
                    self.assertIn("add_item", st["checks"]["no_actions"])
                if exp is not None:
                    prev = exp

    def test_allergy_steps_use_the_menu_allergens(self):
        """allergy_have: 말한 성분이 없는 버거를 주문 / allergy_none: 그 성분이 든 버거를 주문."""
        by_name = {b["name"]: b for b in self.menu.burgers}
        checked = {"allergy_have": 0, "allergy_none": 0}
        for sc in self._all_human():
            steps = sc["steps"]
            for i, st in enumerate(steps):
                if st.get("op") in checked and st["kind"] == "say" and "알레르기" in st["text"]:
                    nxt = steps[i + 1]
                    ordered = nxt["checks"]["cart_exact"]
                    names = [n for n in sorted({n for b in by_name.values() for n in b["allergens"].values()}) if n in st["text"]]
                    self.assertEqual(len(names), 1, st["text"])
                    last_line = next(e for e in reversed(ordered) if e["name"] in nxt["text"].replace(" ", "") or e["name"].replace(" ", "") in nxt["text"].replace(" ", ""))
                    has = names[0] in by_name[last_line["name"]]["allergens"].values()
                    self.assertEqual(has, st["op"] == "allergy_none", f"{st['text']} → {nxt['text']}")
                    checked[st["op"]] += 1
        self.assertGreater(checked["allergy_have"], 0)
        self.assertGreater(checked["allergy_none"], 0)

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
