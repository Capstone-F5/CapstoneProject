"""
?뚯꽦 二쇰Ц ?≪뀡 ?꾧뎄 ??DB 誘몄궗?? ?≪뀡 諛쒗뻾 ?꾩슜.

媛??꾧뎄???낅젰 寃利?移댄깉濡쒓렇 ?議? ??push_action() ???щ엺???쎌쓣 ?뺤씤 臾몄옄??諛섑솚.
ACTION_TOOLS 由ъ뒪?몃? agent.py ?먯꽌 import ???ъ슜?쒕떎.
"""
from __future__ import annotations

from langchain_core.tools import tool

from .action_context import get_cart, push_action
from .menu_catalog import (
    SET_DRINKS,
    SET_SIDES,
    SET_SURCHARGE,
    get_menu,
)


@tool
def add_item(
    menu_id: int,
    item_type: str = "single",
    quantity: int = 1,
    exclusion: str = "?놁쓬",
    side: str | None = None,
    drink: str | None = None,
    special_note: str | None = None,
) -> str:
    """?λ컮援щ땲??硫붾돱瑜??대뒗??

    Args:
        menu_id: 移댄깉濡쒓렇 ?レ옄 ID (1~23). 移댄깉濡쒓렇???녿뒗 ID ??嫄곕??쒕떎.
        item_type: 'single'(?⑦뭹) ?먮뒗 'set'(?명듃). ?명듃??has_set=True 硫붾돱留?媛??
        quantity: ?댁쓣 ?섎웾 (1 ?댁긽).
        exclusion: ?쒖쇅 ?듭뀡. 移댄깉濡쒓렇??exclusions 紐⑸줉 以??섎굹. 湲곕낯 '?놁쓬'.
        side: ?명듃 ?ъ씠???대쫫 (媛먯옄?源/移섏쫰?ㅽ떛/移섑궓?덇쿊/?묐뀗媛먯옄?源). 誘몄?????湲곕낯媛?
        drink: ?명듃 ?뚮즺 ?대쫫 (肄쒕씪/?쒕줈肄쒕씪/?ъ씠???쒕줈?ъ씠???앹닔/戮濡쒕줈?뚮즺/?ㅻ젋吏二쇱뒪). 誘몄?????湲곕낯媛?
        special_note: 二쇰갑 ?꾨떖 鍮꾩젙???붽뎄?ы빆 ("諛섏쑝濡??섎씪二쇱꽭?? ??. ?앸왂 媛??
    """
    menu = get_menu(menu_id)
    if menu is None:
        return f"?ㅻ쪟: 移댄깉濡쒓렇??ID {menu_id} 硫붾돱媛 ?놁뒿?덈떎. ?뺥솗??硫붾돱 ID 瑜??ъ슜?섏꽭??"

    if quantity < 1:
        return "?ㅻ쪟: ?섎웾? 1 ?댁긽?댁뼱???⑸땲??"

    if item_type not in ("single", "set"):
        return "?ㅻ쪟: item_type ? 'single' ?먮뒗 'set' ?댁뼱???⑸땲??"

    if item_type == "set" and not menu["has_set"]:
        return f"?ㅻ쪟: {menu['name']}?(?? ?명듃 二쇰Ц??遺덇??ν빀?덈떎."

    # exclusion ?좏슚??寃利???移댄깉濡쒓렇???놁쑝硫?'?놁쓬' ?대갚
    valid_exclusions = menu["exclusions"]
    if exclusion not in valid_exclusions:
        exclusion = "?놁쓬"

    # ?명듃 ?듭뀡 湲곕낯媛?蹂댁젙
    resolved_side: str | None = None
    side_extra: int = 0
    resolved_drink: str | None = None
    drink_extra: int = 0

    if item_type == "set":
        side_names = [s["name"] for s in SET_SIDES]
        if side and side in side_names:
            idx = side_names.index(side)
            resolved_side = SET_SIDES[idx]["name"]
            side_extra = SET_SIDES[idx]["extra"]
        else:
            resolved_side = SET_SIDES[0]["name"]  # 湲곕낯媛? 媛먯옄?源
            side_extra = SET_SIDES[0]["extra"]

        drink_names = [d["name"] for d in SET_DRINKS]
        if drink and drink in drink_names:
            idx = drink_names.index(drink)
            resolved_drink = SET_DRINKS[idx]["name"]
            drink_extra = SET_DRINKS[idx]["extra"]
        else:
            resolved_drink = SET_DRINKS[0]["name"]  # 湲곕낯媛? 肄쒕씪
            drink_extra = SET_DRINKS[0]["extra"]

    action: dict = {
        "type": "add_item",
        "menu_id": menu_id,
        "name": menu["name"],
        "item_type": item_type,
        "quantity": quantity,
        "exclusion": exclusion,
        "side": resolved_side,
        "drink": resolved_drink,
    }
    if special_note:
        action["special_note"] = special_note

    push_action(action)

    type_label = "?⑦뭹" if item_type == "single" else "?명듃"
    msg = f"{menu['name']}({type_label}) {quantity}媛??댁쓬"
    if item_type == "set":
        msg += f" [?ъ씠?? {resolved_side}, ?뚮즺: {resolved_drink}]"
    if exclusion != "?놁쓬":
        msg += f" [{exclusion}]"
    if special_note:
        msg += f" [?뱀씠?ы빆: {special_note}]"
    return msg


@tool
def update_qty(menu_id: int, quantity: int, cart_id: float | None = None) -> str:
    """?λ컮援щ땲???뱀젙 硫붾돱 ?섎웾??蹂寃쏀븳??

    Args:
        menu_id: ?섎웾??諛붽? 硫붾돱??移댄깉濡쒓렇 ID.
        quantity: ???섎웾. 0 ?댄븯?대㈃ ??젣??remove_item ?ъ슜 沅뚯옣).
        cart_id: 媛숈? 硫붾돱媛 ?듭뀡蹂꾨줈 ?щ윭 以꾩씠硫?context??cart_id濡??뺥솗??以?吏??
    """
    menu = get_menu(menu_id)
    if menu is None:
        return f"?ㅻ쪟: 移댄깉濡쒓렇??ID {menu_id} 硫붾돱媛 ?놁뒿?덈떎."

    cart = get_cart()
    exists = any(c.get("menu_id") == menu_id for c in cart)
    if not exists:
        return f"?λ컮援щ땲??{menu['name']}??媛) ?놁뒿?덈떎."

    match = {"cart_id": cart_id} if cart_id is not None else {"menu_id": menu_id}
    push_action({"type": "update_qty", "match": match, "quantity": quantity})
    return f"{menu['name']} ?섎웾??{quantity}媛쒕줈 蹂寃?


@tool
def update_item(
    cart_id: float,
    item_type: str | None = None,
    quantity: int | None = None,
    exclusion: str | None = None,
    side: str | None = None,
    drink: str | None = None,
) -> str:
    """?대? ?닿릿 ?λ컮援щ땲 ??ぉ???듭뀡???쒖옄由ъ뿉??蹂寃쏀븳????젣 ???щ떞湲??꾨떂).

    ?뚮즺/?ъ씠???쒖쇅/?섎웾/?⑦뭹쨌?명듃瑜?諛붽? ???ъ슜. 蹂寃쏀븷 ?꾨뱶留?梨꾩슫??
    諛섎뱶??context??cart_id濡????以꾩쓣 吏?뺥븳??

    Args:
        cart_id: 蹂寃쏀븷 ?λ컮援щ땲 以꾩쓽 cart_id (context???쒖떆??.
        item_type: 'single'|'set' 濡?蹂寃???
        quantity: ?섎웾 蹂寃???
        exclusion: ?쒖쇅 ?듭뀡 蹂寃???(?? '?묒긽異??쒖쇅').
        side: ?명듃 ?ъ씠??蹂寃???(?? '移섑궓?덇쿊').
        drink: ?명듃 ?뚮즺 蹂寃???(?? '?앹닔').
    """
    cart = get_cart()
    target = next((c for c in cart if c.get("cart_id") == cart_id), None)
    if target is None:
        return f"?ㅻ쪟: cart_id {cart_id} ??ぉ???λ컮援щ땲???놁뒿?덈떎."

    action: dict = {"type": "update_item", "match": {"cart_id": cart_id}}
    if item_type in ("single", "set"):
        action["item_type"] = item_type
    if quantity is not None:
        action["quantity"] = quantity
    if exclusion is not None:
        action["exclusion"] = exclusion
    if side is not None:
        action["side"] = side
    if drink is not None:
        action["drink"] = drink

    push_action(action)
    name = target.get("name", "硫붾돱")
    changed = side or drink or exclusion or (f"{quantity}媛? if quantity else None) or item_type or "?듭뀡"
    return f"{name} {changed}(??濡?蹂寃?


@tool
def remove_item(menu_id: int, cart_id: float | None = None) -> str:
    """?λ컮援щ땲?먯꽌 ?뱀젙 硫붾돱瑜???젣?쒕떎.

    Args:
        menu_id: ??젣??硫붾돱??移댄깉濡쒓렇 ID.
        cart_id: 媛숈? 硫붾돱媛 ?듭뀡蹂꾨줈 ?щ윭 以꾩씠硫?context??cart_id濡??뺥솗??以?吏??
                 (?? "F踰꾧굅 ?앹닔 ?명듃"泥섎읆 ?듭뀡?쇰줈 ?뱀젙?섎뒗 寃쎌슦 ?대떦 以꾩쓽 cart_id ?ъ슜)
    """
    menu = get_menu(menu_id)
    if menu is None:
        return f"?ㅻ쪟: 移댄깉濡쒓렇??ID {menu_id} 硫붾돱媛 ?놁뒿?덈떎."

    cart = get_cart()
    exists = any(c.get("menu_id") == menu_id for c in cart)
    if not exists:
        return f"?λ컮援щ땲??{menu['name']}??媛) ?놁뒿?덈떎."

    match = {"cart_id": cart_id} if cart_id is not None else {"menu_id": menu_id}
    push_action({"type": "remove_item", "match": match})
    return f"{menu['name']} ??젣"


@tool
def clear_cart() -> str:
    """?λ컮援щ땲瑜??꾨? 鍮꾩슫??"""
    push_action({"type": "clear_cart"})
    return "?λ컮援щ땲瑜?鍮꾩썱?듬땲??"


@tool
def navigate(screen: str) -> str:
    """?붾㈃???대룞?쒕떎.

    Args:
        screen: ?대룞???붾㈃ ?대쫫. 'menu'(硫붾돱), 'cart'(?λ컮援щ땲) ??
    """
    push_action({"type": "navigate", "screen": screen})
    return f"{screen} ?붾㈃?쇰줈 ?대룞"


@tool
def checkout(method: str | None = None) -> str:
    """寃곗젣瑜?吏꾪뻾?쒕떎. ?λ컮援щ땲媛 鍮꾩뼱?덉쑝硫?嫄곕??쒕떎.

    Args:
        method: 寃곗젣 ?섎떒 ('card'/'cash'/'pay' ??. ?앸왂 媛?? MVP ?먯꽌??李멸퀬??
    """
    cart = get_cart()
    if not cart:
        return "?닿릿 硫붾돱媛 ?놁뼱?? 癒쇱? 硫붾돱瑜??좏깮??二쇱꽭??"

    action: dict = {"type": "checkout"}
    if method:
        action["method"] = method
    push_action(action)
    return "寃곗젣 ?붾㈃(?λ컮援щ땲)?쇰줈 ?대룞?⑸땲??"


# ?? ui_action: ?붾㈃ 議곗옉 踰붿슜 ?꾧뎄 ??????????????????????????????????????????
# action 蹂??덉슜 value ?붿씠?몃━?ㅽ듃. None = value 遺덊븘??
_UI_ACTION_SPEC: dict[str, set[str] | None] = {
    "update_modal": None,    # field + field_value 濡?泥섎━ (?꾨옒 李멸퀬)
    "order_type": {"dine-in", "takeout"},
    "select_category": {"recommended", "burger", "side", "drink"},
    "menu_page": {"next", "prev"},
    "open_item": None,          # value = 硫붾돱 ID (?レ옄 臾몄옄??
    "start_checkout": None,
    "points": {"yes", "no"},
    "points_phone": None,       # value = ?꾪솕踰덊샇
    "payment_method": {"card", "cash", "pay"},
    "set_language": {"ko", "en", "zh", "ja"},
    "set_gesture": {"on", "off"},
    "set_camera": {"on", "off"},
}

# ?щ엺???쎌쓣 ?뺤씤 硫붿떆吏(媛꾨떒)
_UI_ACTION_MSG: dict[str, str] = {
    "update_modal": "?앹뾽 ?좏깮 蹂寃?,
    "order_type": "二쇰Ц ?좏삎 ?좏깮",
    "select_category": "硫붾돱 移댄뀒怨좊━ ?대룞",
    "menu_page": "硫붾돱 ?섏씠吏 ?대룞",
    "open_item": "硫붾돱 ?곸꽭 ?닿린",
    "start_checkout": "寃곗젣 ?쒖옉",
    "points": "?ъ씤???곷┰ ?좏깮",
    "points_phone": "?꾪솕踰덊샇 ?낅젰",
    "payment_method": "寃곗젣 ?섎떒 ?좏깮",
    "set_language": "?몄뼱 蹂寃?,
    "set_gesture": "?쒖뒪泥??ㅼ젙",
    "set_camera": "移대찓??誘몃━蹂닿린 ?ㅼ젙",
}


@tool
def ui_action(action: str, value: str | None = None, item_type: str | None = None,
              field: str | None = None, field_value: str | None = None) -> str:
    """?붾㈃ UI 瑜?議곗옉?섎뒗 踰붿슜 ?꾧뎄. ?꾩옱 ?붾㈃??留욌뒗 action 留??몄텧?쒕떎.

    action 醫낅쪟? ?뚮씪誘명꽣:
      - update_modal (field: qty|exclusion|side|drink, field_value: 蹂寃쎄컪)
                                                         : ?대┛ ?앹뾽???좏깮 蹂寃?                                                           ?? field=side, field_value=?묐뀗媛먯옄?源
      - order_type (value: dine-in | takeout)            : 留ㅼ옣/?ъ옣 ?좏깮 ??硫붾돱濡?      - select_category (value: recommended|burger|side|drink) : 硫붾돱 移댄뀒怨좊━ ?꾪솚 (menu ?붾㈃)
      - menu_page (value: next | prev)                   : 硫붾돱 ?섏씠吏 ?대룞 (menu ?붾㈃)
      - open_item (value: 硫붾돱 ID ?レ옄, item_type: single|set ?좏깮?ы빆)
                                                         : 硫붾돱 ?곸꽭 紐⑤떖 ?쒖떆 (menu ?붾㈃)
      - start_checkout                                   : 寃곗젣 ?쒖옉 (cart ?붾㈃)
      - points (value: yes | no)                         : ?ъ씤???곷┰ ?щ? (cart ?붾㈃)
      - points_phone (value: ?꾪솕踰덊샇)                   : ?ъ씤???곷┰ ?꾪솕踰덊샇 ?낅젰 (cart ?붾㈃)
      - payment_method (value: card | cash | pay)        : 寃곗젣 ?섎떒 ?좏깮 (cart ?붾㈃)
      - set_language (value: ko | en | zh | ja)          : ?붾㈃ ?몄뼱 蹂寃?      - set_gesture (value: on | off)                    : ?먮룞???몄떇 耳쒓린/?꾧린
      - set_camera (value: on | off)                     : 移대찓??誘몃━蹂닿린 耳쒓린/?꾧린

    ?ㅻⅨ ?붾㈃ 湲곕뒫???꾩슂?섎㈃ navigate 濡?癒쇱? ?대룞?????몄텧?쒕떎.
    """
    if action not in _UI_ACTION_SPEC:
        return f"?ㅻ쪟: 吏?먰븯吏 ?딅뒗 action '{action}' ?낅땲??"

    allowed = _UI_ACTION_SPEC[action]
    if allowed is not None:
        if value not in allowed:
            return (
                f"?ㅻ쪟: action '{action}' ??value ??{sorted(allowed)} 以??섎굹?ъ빞 ?⑸땲??"
            )
    elif action in ("open_item", "points_phone") and not value:
        return f"?ㅻ쪟: action '{action}' ? value 媛 ?꾩슂?⑸땲??"

    payload: dict = {"type": action}
    if action == "update_modal":
        _MODAL_FIELDS = {"qty", "exclusion", "side", "drink"}
        if not field or field not in _MODAL_FIELDS:
            return f"?ㅻ쪟: update_modal ??field ??{sorted(_MODAL_FIELDS)} 以??섎굹?ъ빞 ?⑸땲??"
        if not field_value:
            return "?ㅻ쪟: update_modal ?먮뒗 field_value 媛 ?꾩슂?⑸땲??"
        payload["field"]       = field
        payload["value"]       = field_value
    elif action == "open_item":
        # 移댄깉濡쒓렇 寃利?        try:
            menu_id = int(value)
        except (TypeError, ValueError):
            return "?ㅻ쪟: open_item ??value ??硫붾돱 ID ?レ옄?ъ빞 ?⑸땲??"
        if get_menu(menu_id) is None:
            return f"?ㅻ쪟: 移댄깉濡쒓렇??ID {menu_id} 硫붾돱媛 ?놁뒿?덈떎."
        payload["menu_id"] = menu_id
        if item_type in ("single", "set"):
            payload["item_type"] = item_type
    elif action == "points_phone":
        payload["phone"] = value
    elif value is not None:
        payload["value"] = value

    push_action(payload)
    label = _UI_ACTION_MSG.get(action, action)
    detail = f" ({field}={field_value})" if action == "update_modal" else (f" ({value})" if value else "")
    return f"{label} ?꾨즺{detail}"


ACTION_TOOLS = [
    add_item,
    update_qty,
    update_item,
    remove_item,
    clear_cart,
    navigate,
    checkout,
    ui_action,
]
