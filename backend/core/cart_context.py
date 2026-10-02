"""Cart serialization and deterministic status-response helpers."""

import re


def selected_options_with_groups(selected_options, menu_options):
    options_by_id = {option.id: option for option in menu_options}
    return [
        {
            **selected,
            "option_group": (
                options_by_id[selected.get("option_id")].option_group
                if options_by_id.get(selected.get("option_id")) else None
            ),
            "name_en": (
                options_by_id[selected.get("option_id")].name_en
                if options_by_id.get(selected.get("option_id")) else None
            ),
            "additional_price": (
                float(options_by_id[selected.get("option_id")].additional_price)
                if options_by_id.get(selected.get("option_id")) else None
            ),
        }
        for selected in (selected_options or [])
    ]


def cart_lines_from_db(cart, fallback):
    """Convert DB cart rows to LLM lines, retaining the request snapshot if no cart row exists."""
    if cart is None:
        return fallback

    lines = []
    for item in cart.items:
        selected_by_group = {}
        options_by_id = {
            option.id: option
            for option in (item.menu_item.options if item.menu_item else [])
        }
        exclusions = []
        for selected in item.selected_options or []:
            option = options_by_id.get(selected.get("option_id"))
            if not option:
                continue
            name = selected.get("name") or option.name_ko
            if option.option_group == "EXCLUDE":
                exclusions.append(name)
            else:
                selected_by_group[option.option_group] = name

        lines.append({
            "cart_item_id": item.id,
            "menu_id": item.menu_item_id,
            "name": item.menu_item.name_ko if item.menu_item else None,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "item_type": "set" if "SET_UPGRADE" in selected_by_group else "single",
            "exclusion": ", ".join(exclusions) or "없음",
            "exclusions": exclusions,
            "side": selected_by_group.get("SET_SIDE"),
            "drink": selected_by_group.get("SET_DRINK"),
            "special_note": item.special_note,
        })
    return lines


def cart_summary(cart):
    """Render a cart snapshot for the model, including all selected options."""
    if not cart:
        return "현재 장바구니: 비어 있음"

    lines = ["현재 장바구니: (수정/삭제 시 cart_item_id로 정확한 줄을 지정)"]
    total = 0
    for item in cart:
        name = item.get("name") or f"메뉴#{item.get('menu_id')}"
        quantity = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        subtotal = quantity * unit_price
        total += subtotal
        item_type = "세트" if item.get("item_type") == "set" else "단품"
        cart_item_id = item.get("cart_item_id") or item.get("cart_id")
        line = (
            f"  - cart_item_id={cart_item_id} | menu_id={item.get('menu_id')} | "
            f"{name}({item_type}) x{quantity}  소계 {subtotal}원"
        )

        exclusions = item.get("exclusions") or item.get("exclusion") or []
        if isinstance(exclusions, str):
            exclusions = [exclusions]
        exclusions = [value for value in exclusions if value and value != "없음"]
        if exclusions:
            line += f"  [제외:{', '.join(exclusions)}]"

        side = item.get("side")
        drink = item.get("drink")
        if side or drink:
            line += f"  [사이드:{side or '없음'} / 음료:{drink or '없음'}]"
        special_note = item.get("special_note")
        if special_note:
            line += f"  [요청사항:{special_note}]"
        lines.append(line)

    lines.append(f"  합계: {total}원")
    return "\n".join(lines)


def cart_status_text(cart):
    """Format the cart tool response, explicitly identifying set lines."""
    items = cart.get("items", [])
    if not items:
        return "장바구니가 비어있습니다."

    lines = ["[현재 장바구니]"]
    for item in items:
        selected_options = item.get("selected_options", [])
        option_names = ", ".join(option["name"] for option in selected_options)
        item_type = "세트" if any(
            option.get("option_group") == "SET_UPGRADE" for option in selected_options
        ) else "단품"
        line = (
            f"- {item['name_ko']} {item_type} x{item['quantity']} "
            f"({int(float(item['unit_price']))}원)"
        )
        if option_names:
            line += f" [{option_names}]"
        if item.get("special_note"):
            line += f" [{item['special_note']}]"
        line += f" (cart_item_id: {item['cart_item_id']})"
        lines.append(line)
    lines.append(f"합계: {int(float(cart.get('total', 0)))}원")
    return "\n".join(lines)


_CART_MUTATION_RE = re.compile(
    r"(?:빼\s*(?:줘|주세요|주라)|빼지\s*말|제외하지\s*말|제외\s*(?:해줘|해주세요)|"
    r"담아\s*(?:줘|주세요)|추가\s*해|삭제\s*해|바꿔\s*(?:줘|주세요)|변경\s*해|"
    r"수정\s*해|비워\s*(?:줘|주세요)|\b(?:add|remove|delete|change|update|clear)\b)",
    re.IGNORECASE,
)
_CART_RECOMMENDATION_RE = re.compile(
    r"(?:추천|뭐\s*(?:담|추가).*(?:좋|추천)|뭘\s*(?:담|추가).*(?:좋|추천)|"
    r"\bwhat should I (?:add|order)\b|\brecommend\b)",
    re.IGNORECASE,
)
# "장바구니 보여줘/열어줘/가자"는 담긴 내용을 묻는 게 아니라 장바구니 화면을 열어 달라는 명령이다.
# 내용을 묻는 말(뭐/뭘/어떤/담겨…)이 함께 있으면 해당하지 않는다.
_CART_OPEN_RE = re.compile(r"(?:장바구니|카트).{0,6}(?:보여|보자|열어|이동|가줘|가자|갈래)")
_CART_CONTENT_Q_RE = re.compile(r"뭐|뭘|무엇|어떤|뭔|담겨|담겼|담긴|담았|넣은|넣었|비었|비어|\?")


def is_cart_status_query(text: str) -> bool:
    """Return whether a turn asks for current cart state rather than changing it."""
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if (
        not normalized
        or _CART_MUTATION_RE.search(normalized)
        or _CART_RECOMMENDATION_RE.search(normalized)
    ):
        return False
    if _CART_OPEN_RE.search(normalized) and not _CART_CONTENT_Q_RE.search(normalized):
        return False   # 화면 이동 요청 → 에이전트가 navigate 처리

    has_question = bool(re.search(
        r"(?:\?|현재|지금|뭐|뭘|무엇|어떤|뭔|있어|있나요|있습니까|알려|확인|보여|뭐야|"
        r"담겨|담겼|담긴|담았|비었|비어|넣은|넣었|"
        r"what|which|what's|whats|show|tell me|in my cart|购物车|購物車|カート|何|どれ|ある)",
        normalized,
        re.IGNORECASE,
    ))
    has_cart_topic = bool(re.search(
        r"(?:장바구니|카트|담겨|담겼|담긴|담았|넣은|넣었|담아|뺀\s*거|뺀거|제외|\bcart\b|"
        r"\badded\b|\bremoved\b|购物车|購物車|カート|入れた|除外)",
        normalized,
        re.IGNORECASE,
    ))
    # "사이드", "음료"는 메뉴 카테고리 이름이기도 하다. "음료는 어떤 게 있어요?"는 메뉴 질문이지 장바구니
    # 질문이 아니므로, 담기·선택 같은 장바구니 동사가 함께 있을 때만 장바구니 주제로 본다.
    if not has_cart_topic and re.search(r"사이드|음료", normalized):
        has_cart_topic = bool(re.search(r"담|넣|추가|뺐|뺀|선택|고른|주문한|시킨|시켰", normalized))
    return has_question and has_cart_topic


def format_cart_status_reply(
    cart: list[dict], language: str | None = None, user_input: str | None = None
) -> str:
    """Format the authoritative cart snapshot without asking the model to infer it."""
    text = user_input or ""
    script_counts = {
        "ko": len(re.findall(r"[가-힣]", text)),
        "ja": len(re.findall(r"[\u3040-\u30ff]", text)),
        "zh": len(re.findall(r"[\u3400-\u9fff]", text)),
    }
    dominant_script, script_count = max(script_counts.items(), key=lambda pair: pair[1])
    lang = (
        dominant_script
        if script_count >= 2
        else language if language in {"ko", "en", "zh", "ja"} else "en"
    )
    if not cart:
        return {
            "ko": "현재 장바구니가 비어 있습니다.",
            "en": "Your cart is currently empty.",
            "zh": "当前购物车为空。",
            "ja": "現在、カートは空です。",
        }[lang]

    set_label = {"ko": "세트", "en": "set", "zh": "套餐", "ja": "セット"}[lang]
    single_label = {"ko": "단품", "en": "single", "zh": "单品", "ja": "単品"}[lang]
    exclusion_label = {"ko": "제외", "en": "without", "zh": "不加", "ja": "抜き"}[lang]
    side_label = {"ko": "사이드", "en": "side", "zh": "配菜", "ja": "サイド"}[lang]
    drink_label = {"ko": "음료", "en": "drink", "zh": "饮料", "ja": "ドリンク"}[lang]
    note_label = {"ko": "요청사항", "en": "note", "zh": "备注", "ja": "要望"}[lang]

    item_lines = []
    total = 0.0
    for item in cart:
        name = item.get("name") or item.get("name_ko") or f"메뉴 {item.get('menu_id', '')}".strip()
        quantity = int(item.get("quantity", 1) or 1)
        unit_price = float(item.get("unit_price", 0) or 0)
        total += quantity * unit_price
        kind = set_label if item.get("item_type") == "set" else single_label
        line = f"{name} {kind} x{quantity}"

        exclusions = item.get("exclusions") or item.get("exclusion") or []
        if isinstance(exclusions, str):
            exclusions = [] if exclusions in {"", "없음", "none"} else [exclusions]
        if exclusions:
            line += f" ({exclusion_label}: {', '.join(exclusions)})"
        if item.get("side"):
            line += f" ({side_label}: {item['side']})"
        if item.get("drink"):
            line += f" ({drink_label}: {item['drink']})"
        if item.get("special_note"):
            line += f" ({note_label}: {item['special_note']})"
        item_lines.append(line)

    amount = f"{int(round(total)):,}"
    if lang == "ko":
        joined = ", ".join(item_lines)
        return f"현재 장바구니에는 {joined} 담겨 있습니다. 합계는 {amount}원입니다."
    if lang == "zh":
        return f"当前购物车有：{'，'.join(item_lines)}。合计 {amount} 韩元。"
    if lang == "ja":
        return f"現在のカート：{'、'.join(item_lines)}。合計 {amount}ウォンです。"
    return f"Your cart contains: {', '.join(item_lines)}. Total: {amount} won."


def resolve_cart_item(cart: dict, cart_item_id: str | None):
    """Resolve an explicit cart line, or infer it only when exactly one exists."""
    items = cart.get("items", [])
    if cart_item_id:
        match = next((item for item in items if item.get("cart_item_id") == cart_item_id), None)
        if match:
            return match, None
        return None, f"장바구니에서 해당 항목을 찾을 수 없습니다 ({cart_item_id})"
    if len(items) == 1:
        return items[0], None
    if not items:
        return None, "장바구니가 비어 있습니다."
    return None, "수정할 항목이 여러 개입니다. 먼저 장바구니를 확인해 정확한 항목을 지정해 주세요."
