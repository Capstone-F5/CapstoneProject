import unittest
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from core.pricing import calculate_cart_item_price, calculate_final_price, calculate_menu_price


def discount(value, kind="PERCENT", active=True, start=None, end=None):
    return SimpleNamespace(
        id="discount-id",
        name_ko="test",
        discount_type=kind,
        discount_value=Decimal(str(value)),
        is_active=active,
        applicable_tier="ALL",
        valid_from=start,
        valid_until=end,
        target_type="ALL",
        menu_item_id=None,
        category_id=None,
    )


class PricingTests(unittest.TestCase):
    def test_sequential_percentage_discounts(self):
        result = calculate_final_price(10000, [discount(10), discount(20)])
        self.assertEqual(result["final_price"], Decimal("7200.00"))

    def test_three_sequential_percentage_discounts(self):
        result = calculate_final_price(10000, [discount(10), discount(20), discount(10)])
        self.assertEqual(result["final_price"], Decimal("6480.00"))

    def test_no_discounts_returns_original_price(self):
        self.assertEqual(calculate_final_price(10000, [])["final_price"], Decimal("10000.00"))

    def test_null_like_discount_list_returns_original_price(self):
        self.assertEqual(calculate_final_price(10000, None)["final_price"], Decimal("10000.00"))

    def test_inactive_and_expired_discounts_are_not_applied(self):
        item = SimpleNamespace(id="item-id", category_id="category-id", base_price=Decimal("10000"))
        yesterday = date.today() - timedelta(days=1)
        result = calculate_menu_price(
            item,
            [discount(10, active=False), discount(20, end=yesterday)],
        )
        self.assertEqual(result["final_price"], Decimal("10000.00"))

    def test_selected_option_price_is_included_before_discount(self):
        item = SimpleNamespace(
            id="item-id",
            category_id="category-id",
            base_price=Decimal("10000"),
            options=[SimpleNamespace(id="upgrade-id", additional_price=Decimal("2000"))],
        )
        result = calculate_cart_item_price(item, [{"option_id": "upgrade-id"}], [])
        self.assertEqual(result["final_price"], Decimal("12000.00"))


if __name__ == "__main__":
    unittest.main()