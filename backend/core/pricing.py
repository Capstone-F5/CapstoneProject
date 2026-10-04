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


def _discount_amount(original: Decimal, discount) -> Decimal:
    """단일 할인의 할인 금액을 계산한다."""
    if discount.discount_type == "PERCENT":
        return (original * Decimal(str(discount.discount_value)) / Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    return min(original, Decimal(str(discount.discount_value)))


def calculate_final_price(
    original_price: Decimal | int | str,
    discounts: Iterable | None,
) -> dict:
    """중복 할인이 있을 때 가장 높은 할인 하나만 적용한다."""
    original = Decimal(str(original_price))
    discount_list = list(discounts or ())

    if not discount_list:
        return {
            "original_price": original,
            "discount_amount": Decimal("0"),
            "final_price": original,
            "applied_discounts": [],
        }

    # 할인 금액이 가장 큰 것 하나만 적용
    best = max(discount_list, key=lambda d: _discount_amount(original, d))
    amount = _discount_amount(original, best)
    final = max(Decimal("0"), original - amount).quantize(Decimal("0.01"))

    return {
        "original_price": original,
        "discount_amount": original - final,
        "final_price": final,
        "applied_discounts": [
            {
                "id": best.id,
                "name": best.name_ko,
                "discount_type": best.discount_type,
                "discount_value": Decimal(str(best.discount_value)),
            }
        ],
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