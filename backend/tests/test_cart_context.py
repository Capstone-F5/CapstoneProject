import unittest
from types import SimpleNamespace

from core.cart_context import (
    cart_lines_from_db,
    cart_status_text,
    cart_summary,
    format_cart_status_reply,
    is_cart_status_query,
    resolve_cart_item,
    selected_options_with_groups,
)


def option(option_id, group, name, name_en):
    return SimpleNamespace(
        id=option_id,
        option_group=group,
        name_ko=name,
        name_en=name_en,
        additional_price=0,
    )


class CartContextTests(unittest.TestCase):
    def test_db_cart_keeps_set_type_all_exclusions_and_special_note(self):
        options = [
            option("upgrade", "SET_UPGRADE", "세트 업그레이드", "Set upgrade"),
            option("side", "SET_SIDE", "치즈스틱", "Cheese sticks"),
            option("drink", "SET_DRINK", "콜라", "Cola"),
            option("no-lettuce", "EXCLUDE", "양상추 제외", "No lettuce"),
            option("no-onion", "EXCLUDE", "양파 제외", "No onion"),
        ]
        item = SimpleNamespace(
            id="line-1",
            menu_item_id="burger-1",
            menu_item=SimpleNamespace(name_ko="F버거", options=options),
            quantity=2,
            unit_price=9500,
            selected_options=[
                {"option_id": "upgrade", "name": "세트 업그레이드"},
                {"option_id": "side", "name": "치즈스틱"},
                {"option_id": "drink", "name": "콜라"},
                {"option_id": "no-lettuce", "name": "양상추 제외"},
                {"option_id": "no-onion", "name": "양파 제외"},
            ],
            special_note="반으로 잘라주세요",
        )

        [line] = cart_lines_from_db(SimpleNamespace(items=[item]), [])

        self.assertEqual(line["item_type"], "set")
        self.assertEqual(line["cart_item_id"], "line-1")
        self.assertEqual(line["side"], "치즈스틱")
        self.assertEqual(line["drink"], "콜라")
        self.assertEqual(line["exclusions"], ["양상추 제외", "양파 제외"])
        self.assertEqual(line["special_note"], "반으로 잘라주세요")

        summary = cart_summary([line])
        self.assertIn("F버거(세트)", summary)
        self.assertIn("양상추 제외, 양파 제외", summary)
        self.assertIn("사이드:치즈스틱 / 음료:콜라", summary)
        self.assertIn("요청사항:반으로 잘라주세요", summary)

    def test_missing_db_cart_uses_request_snapshot(self):
        fallback = [{"name": "불고기버거", "quantity": 1}]
        self.assertIs(cart_lines_from_db(None, fallback), fallback)

    def test_cart_api_exposes_option_group_and_english_name(self):
        selected = [{"option_id": "upgrade", "name": "세트 업그레이드"}]
        options = [option("upgrade", "SET_UPGRADE", "세트 업그레이드", "Set upgrade")]

        result = selected_options_with_groups(selected, options)

        self.assertEqual(result[0]["option_group"], "SET_UPGRADE")
        self.assertEqual(result[0]["name_en"], "Set upgrade")
        self.assertEqual(result[0]["additional_price"], 0.0)

    def test_cart_status_explicitly_says_set_or_single(self):
        cart = {
            "items": [
                {
                    "name_ko": "F버거",
                    "quantity": 1,
                    "unit_price": 9500,
                    "selected_options": [
                        {"name": "세트 업그레이드", "option_group": "SET_UPGRADE"},
                        {"name": "감자튀김", "option_group": "SET_SIDE"},
                    ],
                    "cart_item_id": "line-1",
                },
                {
                    "name_ko": "콜라",
                    "quantity": 1,
                    "unit_price": 2000,
                    "selected_options": [],
                    "cart_item_id": "line-2",
                },
            ],
            "total": 11500,
        }

        response = cart_status_text(cart)

        self.assertIn("F버거 세트 x1", response)
        self.assertIn("콜라 단품 x1", response)

    def test_cart_status_questions_are_answered_from_authoritative_snapshot(self):
        self.assertTrue(is_cart_status_query("지금 담겨있는 메뉴가 뭐야?"))
        self.assertTrue(is_cart_status_query("장바구니 비었어"))
        self.assertTrue(is_cart_status_query("뭐 메뉴 뺀거 있어?"))
        self.assertTrue(is_cart_status_query("제외옵션 어떤 게 돼 있어?"))
        self.assertTrue(is_cart_status_query("What's in my cart?"))
        self.assertFalse(is_cart_status_query("장바구니에 뭐 담으면 좋아?"))
        self.assertFalse(is_cart_status_query("제외 없는 걸로 해줘."))
        self.assertFalse(is_cart_status_query("양파 제외하지 말아줘."))
        self.assertFalse(is_cart_status_query("Remove the onion, please."))

    def test_deterministic_cart_reply_reports_set_options_and_total(self):
        reply = format_cart_status_reply(
            [{
                "cart_item_id": "line-1",
                "name": "F버거",
                "item_type": "set",
                "quantity": 1,
                "unit_price": 6650,
                "exclusions": ["양파 제외"],
                "side": "치킨너겟",
                "drink": "제로사이다",
            }],
            "ko",
        )
        self.assertIn("F버거 세트 x1", reply)
        self.assertIn("제외: 양파 제외", reply)
        self.assertIn("사이드: 치킨너겟", reply)
        self.assertIn("음료: 제로사이다", reply)
        self.assertIn("6,650원", reply)
        self.assertEqual(format_cart_status_reply([], "ko"), "현재 장바구니가 비어 있습니다.")
        self.assertTrue(
            format_cart_status_reply([], "en", "장바구니 비었어?").startswith("현재 장바구니")
        )

    def test_cart_item_resolution_only_infers_when_unambiguous(self):
        one_item = {"items": [{"cart_item_id": "line-1"}]}
        item, error = resolve_cart_item(one_item, None)
        self.assertEqual(item["cart_item_id"], "line-1")
        self.assertIsNone(error)

        multiple_items = {"items": [{"cart_item_id": "line-1"}, {"cart_item_id": "line-2"}]}
        item, error = resolve_cart_item(multiple_items, None)
        self.assertIsNone(item)
        self.assertIn("여러 개", error)

        item, error = resolve_cart_item(multiple_items, "line-2")
        self.assertEqual(item["cart_item_id"], "line-2")
        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()
