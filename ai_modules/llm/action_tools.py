"""음성 주문 액션 도구 — DB API 연동 버전."""
from __future__ import annotations

import asyncio
import concurrent.futures
from langchain_core.tools import tool

# 지연님이 세팅한 세션 및 API 클라이언트 불러오기
from .action_context import push_action, get_session_id
from . import api_client

def _run(coro):
    """LangChain 동기 tool에서 비동기(async) API 클라이언트를 호출하기 위한 헬퍼."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)

@tool
def add_item(
    menu_item_id: str,
    quantity: int = 1,
    upgrade_to_set: bool = False,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니에 메뉴를 담는다.
    Args:
        menu_item_id: DB의 메뉴 UUID. 숫자가 아닌 문자열 UUID 형태임.
        quantity: 담을 수량 (1 이상).
        upgrade_to_set: True이면 세트 업그레이드 옵션 자동 추가.
        exclusions: 제외할 재료 이름 목록. 예: ["양파", "양상추"]
        special_note: 주방 전달 비정형 요구사항. 예: "반으로 잘라주세요"
    """
    session_id = get_session_id()

    try:
        # 지연님이 만든 단건 조회 기능 사용
        item = _run(api_client.fetch_menu_item_by_id(menu_item_id))
    except Exception as e:
        return f"오류: 메뉴 조회 실패 — {e}"

    if item is None:
        return f"오류: 해당 ID의 메뉴를 찾을 수 없습니다 ({menu_item_id})"

    if not item.get("is_available", True):
        return f"죄송합니다, {item['name_ko']}는 현재 품절입니다."

    # 옵션 구성 로직
    selected_options = []
    options = item.get("options", [])

    if upgrade_to_set:
        set_opt = next((o for o in options if "세트" in o["name_ko"]), None)
        if set_opt:
            selected_options.append({"option_id": set_opt["id"], "name": set_opt["name_ko"]})
        else:
            return f"오류: {item['name_ko']}는 세트 주문이 불가합니다."

    for excl in (exclusions or []):
        opt = next((o for o in options if excl in o["name_ko"] and o.get("is_available", True)), None)
        if opt:
            selected_options.append({"option_id": opt["id"], "name": opt["name_ko"]})

    payload = {
        "menu_item_id": menu_item_id,
        "quantity": quantity,
        "selected_options": selected_options,
        "special_note": special_note,
    }

    try:
        # 지연님이 연동한 장바구니 추가 API 호출
        result = _run(api_client.add_cart_item(session_id, payload))
    except Exception as e:
        return f"오류: 장바구니 추가 실패 — {e}"

    cart_item_id = result.get("cart_item_id")

    # 프론트엔드 액션 큐 반영 (화면 업데이트용)
    push_action({
        "type": "add_item",
        "menu_item_id": menu_item_id,
        "name": item["name_ko"],
        "quantity": quantity,
        "upgrade_to_set": upgrade_to_set,
        "exclusions": exclusions or [],
        "cart_item_id": cart_item_id,
    })

    type_label = "세트" if upgrade_to_set else "단품"
    msg = f"{item['name_ko']}({type_label}) {quantity}개 담음"
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
        return f"오류: 삭제 실패 — {e}"

    push_action({"type": "remove_item", "cart_item_id": cart_item_id})
    return "항목을 장바구니에서 삭제했습니다."

@tool
def update_item_options(
    cart_item_id: str,
    quantity: int | None = None,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니 항목의 수량 또는 옵션을 변경한다.
    Args:
        cart_item_id: 변경할 장바구니 항목 UUID.
        quantity: 새 수량.
        exclusions: 새 제외 옵션 목록.
        special_note: 새 특이사항.
    """
    session_id = get_session_id()
    payload: dict = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if special_note is not None:
        payload["special_note"] = special_note

    try:
        _run(api_client.patch_cart_item(session_id, cart_item_id, payload))
    except Exception as e:
        return f"오류: 수정 실패 — {e}"

    push_action({"type": "update_item", "cart_item_id": cart_item_id, **payload})
    return "장바구니 항목을 수정했습니다."

@tool
def get_cart_status() -> str:
    """현재 장바구니 내용을 조회한다. 항목 수정·삭제 전에 cart_item_id 확인용으로 필수 사용."""
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
    except Exception as e:
        return f"오류: 장바구니 조회 실패 — {e}"

    items = cart.get("items", [])
    if not items:
        return "장바구니가 비어있습니다."

    lines = ["[현재 장바구니]"]
    for item in items:
        opts = ", ".join(o["name"] for o in item.get("selected_options", []))
        line = f"- {item['name_ko']} x{item['quantity']} ({int(item['unit_price'])}원)"
        if opts:
            line += f" [{opts}]"
        if item.get("special_note"):
            line += f" [{item['special_note']}]"
        line += f" (cart_item_id: {item['cart_item_id']})"
        lines.append(line)
    lines.append(f"합계: {int(cart.get('total', 0))}원")
    return "\n".join(lines)

@tool
def clear_cart() -> str:
    """장바구니를 전부 비운다."""
    session_id = get_session_id()
    try:
        _run(api_client.delete_cart(session_id))
    except Exception as e:
        return f"오류: 초기화 실패 — {e}"
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
        return f"오류: 포인트 조회 실패 — {e}"

    if data is None:
        return "등록된 회원 정보가 없습니다. 주문 후 포인트 적립이 가능합니다."

    return (
        f"안녕하세요! 현재 포인트는 {data['current_points']}점이며, "
        f"등급은 {data.get('tier', 'BASIC')}입니다."
    )

@tool
def navigate(screen: str) -> str:
    """화면을 이동한다. Args: screen: 'menu' | 'cart' | 'payment'"""
    push_action({"type": "navigate", "screen": screen})
    return f"{screen} 화면으로 이동"

# 에이전트가 인식할 최종 도구 리스트 등록
ACTION_TOOLS = [
    add_item,
    remove_item,
    update_item_options,
    get_cart_status,
    clear_cart,
    check_user_points,
    navigate,
]