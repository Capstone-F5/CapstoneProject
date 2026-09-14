from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


def is_discount_applicable(discount, today: date | None = None) -> bool:
    today = today or date.today()
    return (
        bool(discount.is_active)
        and discount.applicable_tier == "ALL"
        and (discount.valid_from is None or discount.valid_from <= today)
        and (discount.valid_until is None or discount.valid_until >= today)
    )


def discount_matches_item(discount, *, menu_item_id: str, category_id: str) -> bool:
    return (
        discount.target_type == "ALL"
        or (discount.target_type == "MENU" and discount.menu_item_id == menu_item_id)
        or (discount.target_type == "CATEGORY" and discount.category_id == category_id)
    )


def calculate_final_price(
    original_price: Decimal | int | str,
    discounts: Iterable | None,
) -> dict:
    """Apply each eligible discount to the current price in sequence."""
    original = Decimal(str(original_price))
    current = original
    applied = []

    for discount in discounts or ():
        if discount.discount_type == "PERCENT":
            current = (current * (Decimal("1") - Decimal(str(discount.discount_value)) / Decimal("100"))).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        else:
            current = max(Decimal("0"), current - Decimal(str(discount.discount_value)))
        applied.append(
            {
                "id": discount.id,
                "name": discount.name_ko,
                "discount_type": discount.discount_type,
                "discount_value": Decimal(str(discount.discount_value)),
            }
        )

    final = max(Decimal("0"), current).quantize(Decimal("0.01"))
    return {
        "original_price": original,
        "discount_amount": original - final,
        "final_price": final,
        "applied_discounts": applied,
    }


def calculate_menu_price(menu_item, discounts: Iterable) -> dict:
    applicable = (
        discount
        for discount in discounts
        if is_discount_applicable(discount)
        and discount_matches_item(
            discount, menu_item_id=menu_item.id, category_id=menu_item.category_id
        )
    )
    return calculate_final_price(menu_item.base_price, applicable)


def calculate_cart_item_price(menu_item, selected_options: list[dict], discounts: Iterable) -> dict:
    option_prices = {option.id: option.additional_price for option in menu_item.options}
    original = Decimal(str(menu_item.base_price)) + sum(
        (
            Decimal(str(option.get("additional_price", option_prices.get(option.get("option_id"), 0))))
            for option in selected_options
        ),
        Decimal("0"),
    )
    applicable = (
        discount
        for discount in discounts
        if is_discount_applicable(discount)
        and discount_matches_item(
            discount, menu_item_id=menu_item.id, category_id=menu_item.category_id
        )
    )
    return calculate_final_price(original, applicable)