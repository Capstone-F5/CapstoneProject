"""음성 주문 액션 도구 — DB API 연동 버전."""
from __future__ import annotations

import asyncio
import concurrent.futures
import httpx
from langchain_core.tools import tool

# 세션 및 API 클라이언트 불러오기
# ★ get_session_id는 action_context.py 가 아니라 session_context.py 에서 가져온다.
#   session_context.py 는 ContextVar 기반이라 요청마다 격리되어 안전하다.
#   action_context.py 에 있던 전역 변수(_session_id) 방식은 동시 요청 시 서로 다른 세션의
#   session_id 가 뒤섞이는 버그가 있어 제거했다 — 손님 A의 발화 처리 중 손님 B의 요청이 들어오면
#   전역값이 덮어써져서 A가 담은 메뉴가 B의 장바구니에 들어갈 수 있었다.
from .action_context import push_action
from .session_context import get_session_id, get_order_type
from . import api_client
from .rag import search_menu as _rag_search_menu

def _run(coro):
    """LangChain 동기 tool에서 비동기(async) API 클라이언트를 호출하기 위한 헬퍼.

    coro는 한 번만 await 가능하므로 재실행을 시도하지 않는다. 이전 구현은 실행 중 예외가
    나면(예: httpx 404/409) "이미 소비된 코루틴을 asyncio.run으로 재실행"을 시도해
    RuntimeError로 원래 예외를 덮어써버려서, 품절/재고 등 실제 오류 메시지가 전부
    "처리 중 오류가 발생했습니다" 류의 무의미한 문자열로 뭉개지는 버그가 있었다.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def _friendly_error(prefix: str, e: Exception) -> str:
    """httpx 오류는 backend/api/* 가 detail 필드에 담아 보내는 한국어 메시지를 그대로 꺼내 쓴다.

    이 문자열은 TTS 로 그대로 낭독되므로 str(e) 같은 raw exception 문구를 노출하지 않는다.
    """
    if isinstance(e, httpx.HTTPStatusError):
        try:
            detail = e.response.json().get("detail")
        except Exception:
            detail = None
        if detail:
            return f"{prefix}: {detail}"
        return f"{prefix}: 서버 처리 중 오류가 발생했습니다."
    if isinstance(e, httpx.RequestError):
        return f"{prefix}: 서버에 연결할 수 없습니다."
    return f"{prefix}: 처리 중 오류가 발생했습니다."

@tool
def list_menu() -> str:
    """판매 중인 메뉴 목록을 menu_item_id와 함께 조회한다. add_item 호출 전 menu_item_id 확인용으로 사용."""
    try:
        items = _run(api_client.fetch_menu_items())
    except Exception as e:
        return _friendly_error("메뉴 조회 실패", e)

    if not items:
        return "조회된 메뉴가 없습니다."

    lines = ["[메뉴 목록]"]
    for item in items:
        status = " [품절]" if not item.get("is_available", True) else ""
        popular = " [추천메뉴]" if item.get("is_popular") else ""
        allergens = item.get("allergens") or []
        allergen_tag = f" [알레르기: {', '.join(a['name_ko'] for a in allergens)}]" if allergens else ""
        lines.append(
            f"- {item['name_ko']} {int(float(item['base_price']))}원 "
            f"(menu_item_id: {item['id']}){status}{popular}{allergen_tag}"
        )
    return "\n".join(lines)

@tool
def list_popular_menu() -> str:
    """추천메뉴/인기메뉴만 조회한다. '뭐가 맛있어요', '인기메뉴 뭐예요' 류의 질문에는
    list_menu 대신 반드시 이 도구를 사용한다.

    이 도구는 서버에서 이미 인기 메뉴만 걸러서 반환하므로, 반환된 항목을 그대로 안내하면 되고
    LLM이 별도로 어떤 메뉴가 인기인지 판단하거나 목록에 다른 메뉴를 추가하면 안 된다.
    """
    try:
        items = _run(api_client.fetch_menu_items())
    except Exception as e:
        return _friendly_error("메뉴 조회 실패", e)

    popular_items = [i for i in items if i.get("is_popular") and i.get("is_available", True)]
    if not popular_items:
        return "현재 등록된 추천 메뉴가 없습니다."

    lines = ["[추천 메뉴 — 이 목록에 있는 항목만 안내할 것]"]
    for item in popular_items:
        allergens = item.get("allergens") or []
        allergen_tag = f" [알레르기: {', '.join(a['name_ko'] for a in allergens)}]" if allergens else ""
        lines.append(f"- {item['name_ko']} {int(float(item['base_price']))}원 (menu_item_id: {item['id']}){allergen_tag}")
    return "\n".join(lines)


@tool
def search_menu(query: str, k: int = 5) -> str:
    """메뉴 이름·특징으로 검색해 실제 menu_item_id를 찾는다. list_menu보다 이걸 우선 쓴다.

    발화에 나온 이름이 DB 표기와 살짝 다르거나(예: "F버거" vs DB의 "F 버거"), "비건 버거"처럼
    특징으로만 말했을 때도 임베딩 기반 유사도 검색(rag.py)으로 정확한 항목을 찾아준다.

    Args:
        query: 메뉴 이름이나 특징 (예: 'F버거', '치즈 많은 버거', '비건').
        k: 반환할 후보 개수.
    """
    try:
        hits = _run(_rag_search_menu(query, k=k))
    except Exception as e:
        return _friendly_error("메뉴 검색 실패", e)

    if not hits:
        return "일치하는 메뉴를 찾지 못했습니다. list_menu로 전체 목록을 확인하세요."

    lines = ["[검색 결과]"]
    for h in hits:
        avail = "" if h.get("is_available", True) else " [품절]"
        popular = " [추천메뉴]" if h.get("is_popular") else ""
        desc = h.get("description") or ""
        allergens = h.get("allergens") or []
        line = f"- {h['name_ko']} (menu_item_id: {h['id']}) {int(float(h['base_price']))}원{avail}{popular}"
        if desc:
            line += f"\n  설명: {desc}"
        line += f"\n  알레르기: {', '.join(a['name_ko'] for a in allergens) if allergens else '없음'}"
        lines.append(line)
    return "\n".join(lines)

@tool
def add_item(
    menu_item_id: str,
    quantity: int = 1,
    upgrade_to_set: bool = False,
    side: str | None = None,
    drink: str | None = None,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니에 메뉴를 담는다.

    ⚠️ upgrade_to_set=True(세트)이면 side와 drink를 반드시 함께 지정해야 한다.
    아직 고객에게 사이드·음료를 확인하지 않았다면 이 도구를 호출하지 말고 먼저 질문한다
    (질문 없이 담으면 이 도구가 오류를 반환하며, 임의로 아무 사이드·음료나 골라 담으면 안 된다).

    Args:
        menu_item_id: DB의 메뉴 UUID. 숫자가 아닌 문자열 UUID 형태임.
        quantity: 담을 수량 (1 이상).
        upgrade_to_set: True이면 세트 업그레이드 옵션 추가. True일 땐 side·drink 필수.
        side: 세트 사이드 이름(예: "치즈스틱"). upgrade_to_set=True일 때만 사용.
        drink: 세트 음료 이름(예: "콜라"). upgrade_to_set=True일 때만 사용.
        exclusions: 제외할 재료 이름 목록. 예: ["양파", "양상추"]
        special_note: 주방 전달 비정형 요구사항. 예: "반으로 잘라주세요"
    """
    session_id = get_session_id()

    try:
        # 단건 조회 API 호출
        item = _run(api_client.fetch_menu_item_by_id(menu_item_id))
    except Exception as e:
        return _friendly_error("메뉴 조회 실패", e)

    if item is None:
        return f"오류: 해당 ID의 메뉴를 찾을 수 없습니다 ({menu_item_id})"

    if not item.get("is_available", True):
        return f"죄송합니다, {item['name_ko']}는 현재 품절입니다."

    # 옵션 구성 로직
    selected_options = []
    options = item.get("options", [])

    if upgrade_to_set:
        set_opt = next((o for o in options if o.get("option_group") == "SET_UPGRADE"), None)
        if set_opt is None:
            return f"오류: {item['name_ko']}는 세트 주문이 불가합니다."
        if not side or not drink:
            return (
                "오류: 세트는 사이드와 음료를 먼저 확인해야 담을 수 있습니다. "
                "고객에게 사이드와 음료를 물어본 뒤 side·drink 값을 채워 다시 호출하세요."
            )
        side_opt = next(
            (o for o in options if o.get("option_group") == "SET_SIDE" and side in o["name_ko"]), None
        )
        drink_opt = next(
            (o for o in options if o.get("option_group") == "SET_DRINK" and drink in o["name_ko"]), None
        )
        if side_opt is None:
            return f"오류: 사이드 '{side}'를 찾을 수 없습니다. 감자튀김, 치즈스틱, 치킨너겟, 양념감자튀김 중에서 다시 확인하세요."
        if drink_opt is None:
            return f"오류: 음료 '{drink}'를 찾을 수 없습니다. 콜라, 제로콜라, 사이다, 제로사이다, 생수, 뽀로로음료, 오렌지주스 중에서 다시 확인하세요."
        selected_options.append({"option_id": set_opt["id"], "name": set_opt["name_ko"]})
        selected_options.append({"option_id": side_opt["id"], "name": side_opt["name_ko"]})
        selected_options.append({"option_id": drink_opt["id"], "name": drink_opt["name_ko"]})

    for excl in (exclusions or []):
        opt = next(
            (o for o in options
             if excl in o["name_ko"] and o.get("option_group") == "EXCLUDE" and o.get("is_available", True)),
            None,
        )
        if opt:
            selected_options.append({"option_id": opt["id"], "name": opt["name_ko"]})

    payload = {
        "menu_item_id": menu_item_id,
        "quantity": quantity,
        "selected_options": selected_options,
        "special_note": special_note,
    }

    try:
        # 장바구니 추가 API 호출
        result = _run(api_client.add_cart_item(session_id, payload))
    except Exception as e:
        return _friendly_error("장바구니 추가 실패", e)

    cart_item_id = result.get("cart_item_id")

    # 프론트엔드 액션 큐 반영 (화면 업데이트용) — side/drink 누락 시 MenuScreen의 음성
    # 워크스루가 세트 옵션을 채우지 못하던 버그 수정.
    push_action({
        "type": "add_item",
        "menu_item_id": menu_item_id,
        "name": item["name_ko"],
        "quantity": quantity,
        "upgrade_to_set": upgrade_to_set,
        "side": side,
        "drink": drink,
        "exclusions": exclusions or [],
        "cart_item_id": cart_item_id,
    })

    type_label = "세트" if upgrade_to_set else "단품"
    msg = f"{item['name_ko']}({type_label}) {quantity}개 담음"
    if upgrade_to_set:
        msg += f" [사이드: {side}, 음료: {drink}]"
    if exclusions:
        msg += f" [{', '.join(exclusions)} 제외]"
    if special_note:
        msg += f" [특이사항: {special_note}]"
    return msg

@tool
def remove_item(cart_item_id: str) -> str:
    """장바구니에서 특정 항목을 삭제한다.
    Args:
        cart_item_id: 삭제할 장바구니 항목의 UUID. get_cart_status로 확인 가능.
    """
    session_id = get_session_id()
    try:
        _run(api_client.remove_cart_item(session_id, cart_item_id))
    except Exception as e:
        return _friendly_error("삭제 실패", e)

    push_action({"type": "remove_item", "cart_item_id": cart_item_id})
    return "항목을 장바구니에서 삭제했습니다."

@tool
def update_item_options(
    cart_item_id: str,
    quantity: int | None = None,
    side: str | None = None,
    drink: str | None = None,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니 항목의 수량 또는 옵션을 변경한다.
    Args:
        cart_item_id: 변경할 장바구니 항목 UUID.
        quantity: 새 수량.
        side: 새 세트 사이드 이름(세트 항목에만 해당). 예: "치즈스틱"
        drink: 새 세트 음료 이름(세트 항목에만 해당). 예: "콜라"
        exclusions: 새 제외 옵션 목록.
        special_note: 새 특이사항.
    """
    session_id = get_session_id()
    payload: dict = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if special_note is not None:
        payload["special_note"] = special_note

    if exclusions is not None or side is not None or drink is not None:
        # exclusions/side/drink 가 그동안 payload에 전혀 반영되지 않아 "재료 빼줘",
        # "사이드 바꿔줘" 같은 후속 요청이 조용히 무시되던 버그 수정. 지정되지 않은
        # 그룹(세트업그레이드 등)의 기존 선택은 그대로 유지하고 해당 그룹만 교체한다.
        try:
            cart = _run(api_client.get_cart(session_id))
            cart_item = next(
                (ci for ci in cart.get("items", []) if ci["cart_item_id"] == cart_item_id), None
            )
            if cart_item is None:
                return f"오류: 장바구니에서 해당 항목을 찾을 수 없습니다 ({cart_item_id})"
            menu_item = _run(api_client.fetch_menu_item_by_id(cart_item["menu_item_id"]))
        except Exception as e:
            return _friendly_error("옵션 조회 실패", e)

        options = (menu_item or {}).get("options", [])
        option_by_id = {o["id"]: o for o in options}
        replace_groups = set()
        if exclusions is not None:
            replace_groups.add("EXCLUDE")
        if side is not None:
            replace_groups.add("SET_SIDE")
        if drink is not None:
            replace_groups.add("SET_DRINK")

        kept = [
            sel for sel in cart_item.get("selected_options", [])
            if option_by_id.get(sel["option_id"], {}).get("option_group") not in replace_groups
        ]

        new_selected = []
        for excl in (exclusions or []):
            opt = next(
                (o for o in options
                 if excl in o["name_ko"] and o.get("option_group") == "EXCLUDE" and o.get("is_available", True)),
                None,
            )
            if opt:
                new_selected.append({"option_id": opt["id"], "name": opt["name_ko"]})
        if side is not None:
            opt = next((o for o in options if o.get("option_group") == "SET_SIDE" and side in o["name_ko"]), None)
            if opt is None:
                return f"오류: 사이드 '{side}'를 찾을 수 없습니다."
            new_selected.append({"option_id": opt["id"], "name": opt["name_ko"]})
        if drink is not None:
            opt = next((o for o in options if o.get("option_group") == "SET_DRINK" and drink in o["name_ko"]), None)
            if opt is None:
                return f"오류: 음료 '{drink}'를 찾을 수 없습니다."
            new_selected.append({"option_id": opt["id"], "name": opt["name_ko"]})

        payload["selected_options"] = kept + new_selected

    try:
        _run(api_client.patch_cart_item(session_id, cart_item_id, payload))
    except Exception as e:
        return _friendly_error("수정 실패", e)

    push_action({"type": "update_item", "cart_item_id": cart_item_id, **payload})
    return "장바구니 항목을 수정했습니다."

@tool
def get_cart_status() -> str:
    """현재 장바구니 내용을 조회한다. 항목 수정·삭제 전에 cart_item_id 확인용으로 필수 사용."""
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
    except Exception as e:
        return _friendly_error("장바구니 조회 실패", e)

    items = cart.get("items", [])
    if not items:
        return "장바구니가 비어있습니다."

    lines = ["[현재 장바구니]"]
    for item in items:
        opts = ", ".join(o["name"] for o in item.get("selected_options", []))
        line = f"- {item['name_ko']} x{item['quantity']} ({int(float(item['unit_price']))}원)"
        if opts:
            line += f" [{opts}]"
        if item.get("special_note"):
            line += f" [{item['special_note']}]"
        line += f" (cart_item_id: {item['cart_item_id']})"
        lines.append(line)
    lines.append(f"합계: {int(float(cart.get('total', 0)))}원")
    return "\n".join(lines)

@tool
def clear_cart() -> str:
    """장바구니를 전부 비운다."""
    session_id = get_session_id()
    try:
        _run(api_client.delete_cart(session_id))
    except Exception as e:
        return _friendly_error("초기화 실패", e)
    push_action({"type": "clear_cart"})
    return "장바구니를 비웠습니다."

@tool
def check_user_points(phone: str) -> str:
    """전화번호로 회원 포인트를 조회한다.
    Args:
        phone: 전화번호 (숫자만, 예: 01012345678)
    """
    try:
        data = _run(api_client.get_user_points(phone))
    except Exception as e:
        return _friendly_error("포인트 조회 실패", e)

    if data is None:
        return "등록된 회원 정보가 없습니다. 주문 후 포인트 적립이 가능합니다."

    greeting = f"{data['name']}님, " if data.get("name") else ""
    return (
        f"안녕하세요! {greeting}현재 포인트는 {data['current_points']}점이며, "
        f"등급은 {data.get('tier', 'BASIC')}입니다."
    )

@tool
def navigate(screen: str) -> str:
    """화면을 이동한다. Args: screen: 'menu' | 'cart' | 'payment'"""
    push_action({"type": "navigate", "screen": screen})
    return f"{screen} 화면으로 이동"


@tool
def checkout(method: str | None = None) -> str:
    """결제를 진행한다. 장바구니가 비어 있으면 거부한다.

    Args:
        method: 결제 수단 ('card' | 'cash' | 'pay'). 생략 가능.
    """
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
    except Exception as e:
        return _friendly_error("장바구니 확인 실패", e)

    if not cart.get("items"):
        return "담긴 메뉴가 없어요. 먼저 메뉴를 선택해 주세요."

    action: dict = {"type": "checkout"}
    if method:
        action["method"] = method
    push_action(action)
    return "결제 화면(장바구니)으로 이동합니다."


@tool
def confirm_order(user_phone: str | None = None) -> str:
    """장바구니의 메뉴로 주문을 확정하고 DB에 주문을 생성한다.

    Args:
        user_phone: 포인트 적립용 전화번호 (선택). 예: 01012345678
    """
    session_id = get_session_id()
    order_type = get_order_type()
    try:
        result = _run(api_client.create_order(session_id, user_phone, order_type))
    except Exception as e:
        return _friendly_error("주문 생성 실패", e)

    order_id = result.get("order_id", "")
    push_action({"type": "confirm_order", "order_id": order_id})
    return f"주문이 완료되었습니다! 주문 번호: {order_id}"


# ── ui_action: 화면 조작 범용 도구 ──────────────────────────────────────────
# action 별 허용 value 화이트리스트. None = value 불필요.
_UI_ACTION_SPEC: dict[str, set[str] | None] = {
    "update_modal": None,
    "order_type": {"dine-in", "takeout"},
    "select_category": {"recommended", "burger", "side", "drink"},
    "menu_page": {"next", "prev"},
    "open_item": None,
    "start_checkout": None,
    "points": {"yes", "no"},
    "points_phone": None,
    "payment_method": {"card", "cash", "pay"},
    "set_language": {"ko", "en", "zh", "ja"},
    "set_gesture": {"on", "off"},
    "set_camera": {"on", "off"},
}

_UI_ACTION_MSG: dict[str, str] = {
    "update_modal": "팝업 선택 변경",
    "order_type": "주문 유형 선택",
    "select_category": "메뉴 카테고리 이동",
    "menu_page": "메뉴 페이지 이동",
    "open_item": "메뉴 상세 열기",
    "start_checkout": "결제 시작",
    "points": "포인트 적립 선택",
    "points_phone": "전화번호 입력",
    "payment_method": "결제 수단 선택",
    "set_language": "언어 변경",
    "set_gesture": "제스처 설정",
    "set_camera": "카메라 미리보기 설정",
}


@tool
def ui_action(
    action: str,
    value: str | None = None,
    item_type: str | None = None,
    field: str | None = None,
    field_value: str | None = None,
) -> str:
    """화면 UI를 조작하는 범용 도구. 현재 화면에 맞는 action만 호출한다.

    action 종류와 파라미터:
      - update_modal (field: qty|exclusion|side|drink, field_value: 변경값)
      - order_type (value: dine-in | takeout)
      - select_category (value: recommended|burger|side|drink)
      - menu_page (value: next | prev)
      - open_item (value: 메뉴 UUID)
      - start_checkout
      - points (value: yes | no)
      - points_phone (value: 전화번호)
      - payment_method (value: card | cash | pay)
      - set_language (value: ko | en | zh | ja)
      - set_gesture (value: on | off)
      - set_camera (value: on | off)
    """
    if action not in _UI_ACTION_SPEC:
        return f"오류: 지원하지 않는 action '{action}' 입니다."

    allowed = _UI_ACTION_SPEC[action]
    if allowed is not None:
        if value not in allowed:
            return f"오류: action '{action}' 의 value 는 {sorted(allowed)} 중 하나여야 합니다."
    elif action in ("open_item", "points_phone") and not value:
        return f"오류: action '{action}' 은 value 가 필요합니다."

    payload: dict = {"type": action}
    if action == "update_modal":
        _MODAL_FIELDS = {"qty", "exclusion", "side", "drink"}
        if not field or field not in _MODAL_FIELDS:
            return f"오류: update_modal 의 field 는 {sorted(_MODAL_FIELDS)} 중 하나여야 합니다."
        if not field_value:
            return "오류: update_modal 에는 field_value 가 필요합니다."
        payload["field"] = field
        payload["value"] = field_value
    elif action == "open_item":
        payload["menu_item_id"] = value
        if item_type in ("single", "set"):
            payload["item_type"] = item_type
    elif action == "points_phone":
        payload["phone"] = value
    elif value is not None:
        payload["value"] = value

    push_action(payload)
    label = _UI_ACTION_MSG.get(action, action)
    detail = f" ({field}={field_value})" if action == "update_modal" else (f" ({value})" if value else "")
    return f"{label} 완료{detail}"


# 에이전트가 인식할 최종 도구 리스트 등록
ACTION_TOOLS = [
    list_menu,
    list_popular_menu,
    search_menu,
    add_item,
    remove_item,
    update_item_options,
    get_cart_status,
    clear_cart,
    check_user_points,
    navigate,
    checkout,
    confirm_order,
    ui_action,
]