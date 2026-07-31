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
from .action_context import push_action, get_user_input, get_checkout_snapshot
from .session_context import get_session_id
from . import api_client
from . import checkout_progress
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


# 일본어·영어·중국어 사이드/음료 별칭 → 한국어(DB 저장명) 정규화 테이블.
# 외국어 사용자가 "フライドポテト", "Fries" 등으로 말할 때 add_item이 올바른 이름으로 조회하도록.
_OPTION_NAME_ALIASES: dict[str, str] = {
    # ── 사이드(SET_SIDE) ────────────────────────────────────────────────────
    "フライドポテト": "감자튀김",    "Fries": "감자튀김",    "fries": "감자튀김",    "薯条": "감자튀김",
    "チーズスティック": "치즈스틱",  "Cheese Sticks": "치즈스틱", "cheese sticks": "치즈스틱", "芝士棒": "치즈스틱",
    "チキンナゲット": "치킨너겟",    "Nuggets": "치킨너겟",  "nuggets": "치킨너겟",  "鸡块": "치킨너겟",
    "ヤンニョムポテト": "양념감자튀김", "Seasoned Fries": "양념감자튀김", "seasoned fries": "양념감자튀김", "辣味薯条": "양념감자튀김",
    # ── 음료(SET_DRINK) ──────────────────────────────────────────────────────
    "コーラ": "콜라",    "Cola": "콜라",    "cola": "콜라",    "可乐": "콜라",
    "ゼロコーラ": "제로콜라",  "Zero-Sugar Cola": "제로콜라", "Coke Zero": "제로콜라", "零糖可乐": "제로콜라",
    "サイダー": "사이다",  "Cider": "사이다", "cider": "사이다", "雪碧": "사이다",
    "ゼロサイダー": "제로사이다", "Zero-Sugar Cider": "제로사이다", "零糖雪碧": "제로사이다",
    "お水": "생수",  "Water": "생수",  "water": "생수",  "矿泉水": "생수",
    "ポロロドリンク": "뽀로로음료", "Pororo Drink": "뽀로로음료", "啵乐乐": "뽀로로음료",
    "オレンジジュース": "오렌지주스", "Orange Juice": "오렌지주스", "orange juice": "오렌지주스", "橙汁": "오렌지주스",
}


def _find_option_by_name(
    options: list[dict], group: str, name: str, available_only: bool = False
) -> dict | None:
    """옵션 그룹 내에서 이름으로 옵션을 찾는다. 정확히 일치하는 이름을 항상 먼저 확인하고,
    없을 때만 부분 일치로 폴백한다.

    "감자튀김"은 "양념감자튀김"의 부분 문자열이고 "콜라"/"사이다"도 각각 "제로콜라"/
    "제로사이다"의 부분 문자열이다. 옵션 목록은 정렬이 보장되지 않으므로(UUID PK 순서는
    삽입 순서와 무관) 부분 일치만으로 고르면 반환 순서에 따라 "감자튀김"을 요청했는데
    "양념감자튀김"이 선택되는 등 비결정적으로 엉뚱한 옵션이 골라질 수 있었다.
    """
    # 일본어·영어·중국어 별칭 → 한국어로 정규화 (DB 검색을 위해)
    name = _OPTION_NAME_ALIASES.get(name, name)
    candidates = [
        o for o in options
        if o.get("option_group") == group and (not available_only or o.get("is_available", True))
    ]
    exact = next((o for o in candidates if o["name_ko"] == name), None)
    if exact:
        return exact
    return next((o for o in candidates if name in o["name_ko"]), None)

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
        side_opt = _find_option_by_name(options, "SET_SIDE", side)
        drink_opt = _find_option_by_name(options, "SET_DRINK", drink)
        if side_opt is None:
            return f"오류: 사이드 '{side}'를 찾을 수 없습니다. 감자튀김, 치즈스틱, 치킨너겟, 양념감자튀김 중에서 다시 확인하세요."
        if drink_opt is None:
            return f"오류: 음료 '{drink}'를 찾을 수 없습니다. 콜라, 제로콜라, 사이다, 제로사이다, 생수, 뽀로로음료, 오렌지주스 중에서 다시 확인하세요."
        selected_options.append({"option_id": set_opt["id"], "name": set_opt["name_ko"]})
        selected_options.append({"option_id": side_opt["id"], "name": side_opt["name_ko"]})
        selected_options.append({"option_id": drink_opt["id"], "name": drink_opt["name_ko"]})

    for excl in (exclusions or []):
        opt = _find_option_by_name(options, "EXCLUDE", excl, available_only=True)
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
            opt = _find_option_by_name(options, "EXCLUDE", excl, available_only=True)
            if opt:
                new_selected.append({"option_id": opt["id"], "name": opt["name_ko"]})
        if side is not None:
            opt = _find_option_by_name(options, "SET_SIDE", side)
            if opt is None:
                return f"오류: 사이드 '{side}'를 찾을 수 없습니다."
            new_selected.append({"option_id": opt["id"], "name": opt["name_ko"]})
        if drink is not None:
            opt = _find_option_by_name(options, "SET_DRINK", drink)
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
    checkout_progress.reset(session_id)  # 새 주문을 시작하므로 이전 결제 진행 상태도 초기화
    push_action({"type": "clear_cart"})
    return "장바구니를 비웠습니다."

@tool
def check_user_points(phone: str) -> str:
    """전화번호로 회원 포인트를 조회한다.
    Args:
        phone: 전화번호 (숫자만, 예: 01012345678)
    """
    # 음성으로 번호를 부를 때 "010-1234-5678"/"010 1234 5678"처럼 끊어 말하는 경우가 실제로
    # 재현됨 — 숫자만 남기고 나머지는 버린다.
    digits = "".join(ch for ch in phone if ch.isdigit())
    try:
        data = _run(api_client.get_user_points(digits or phone))
    except Exception as e:
        return _friendly_error("포인트 조회 실패", e)

    # ★ 결제 중 전화번호 입력 단계에서 모델이 이 툴로 잘못 라우팅해도(포인트 단순 조회와
    # 헷갈리는 경우) 화면이 실제로 진행되도록 points_phone 액션을 함께 발행한다. cart 화면이
    # 아니면 처리할 곳이 없어 조용히 무시되므로 다른 상황에서 호출돼도 안전하다.
    if len(digits) == 11:
        push_action({"type": "points_phone", "phone": digits})
        checkout_progress.mark_done(get_session_id(), "points")

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


# ★ 여기 있던 checkout(method=...) 툴은 제거했다. ui_action(start_checkout)과 navigate('cart')로
# 이미 완전히 커버되는데도, "method" 파라미터가 있다는 이유로 모델이 이걸 결제수단 확정/주문
# 완료 툴로 오인해서 호출하고("카드로 할게" → checkout(method='card')), 그 결과("결제 화면으로
# 이동합니다"라는 평범한 문구)를 무시한 채 "결제가 완료되었습니다! 감사합니다"처럼 실제로는
# 전혀 일어나지 않은 결제·주문 완료를 스스로 지어내 답하는 사례가 재현됨. payment_method 가드로
# 못 잡는 새로운 완주 경로였다 — 아예 없애는 게 확실하다.


# ★ 여기 있던 confirm_order 툴(POST /api/orders를 직접 호출해 DB에 주문을 생성)은 제거했다.
# 실제 결제(카드 리더/현금 확인/QR 결제)를 전혀 거치지 않고도 "주문이 완료되었습니다"라고
# 답하며 DB에 진짜 주문을 만들어버리는 구조적 우회로였다 — CartScreen.jsx의 결제 대기 팝업
# (카드/현금/간편결제 UI, 하드웨어 트리거, processPayment 호출)을 건너뛰는 유일한 경로였음.
# 주문 확정은 반드시 화면의 결제 흐름(ui_action start_checkout → points → payment_method)을
# 거쳐 CartScreen의 handleComplete()가 결제 성공을 직접 확인한 뒤에만 이루어져야 한다.
# 그 경로는 프론트엔드에만 있고 LLM 툴로는 절대 재현할 수 없어야 한다.


# ── 결제수단 환각 방지 가드 ──────────────────────────────────────────────────
# "결제할게"처럼 결제수단을 말하지 않은 한 마디에도 모델이 스스로 payment_method(cash) 등을
# 정해서 호출해버리는 사례가 재현됨(프롬프트 지시만으로는 8회 중 최대 7회까지 재현 — 프롬프트
# 보강만으로는 못 막음). 이 발화에 결제수단을 실제로 언급했는지를 키워드로 확인해, 근거 없이
# 값을 정했으면 툴 자체에서 거부한다. 삼성페이는 화면상 카드 버튼에 같이 묶여 있으므로 card
# 키워드에도 포함시켰다(카카오페이 등 나머지 간편결제는 pay에만 포함).
_PAYMENT_METHOD_KEYWORDS: dict[str, list[str]] = {
    "card": ["카드", "신용카드", "삼성페이", "samsung", "card", "credit", "信用卡", "卡", "カード", "クレジット"],
    "cash": ["현금", "cash", "现金", "現金", "キャッシュ"],
    "pay": [
        "간편결제", "간편", "페이", "pay", "qr", "바코드", "barcode",
        "네이버페이", "카카오페이", "제로페이", "페이코", "naver", "kakao", "payco",
        "扫码", "移动支付", "QRコード",
    ],
}


def _payment_method_supported_by_input(value: str) -> bool:
    text = get_user_input().lower()
    keywords = _PAYMENT_METHOD_KEYWORDS.get(value, [])
    return any(kw.lower() in text for kw in keywords)


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

    if action == "points":
        # ★ 포인트 질문은 반드시 고객이 실제로 그 질문을 들은 뒤(=start_checkout이 이전 턴에
        # 이미 끝난 뒤)에만 대답으로 인정한다. 같은 턴에서 start_checkout 직후 곧바로
        # points(no)를 스스로 정해버리는 사례가 재현되어("결제할게" 한 마디에 포인트 질문 자체를
        # 건너뛰고 답까지 정함) 걸어둔다.
        if "start_checkout" not in get_checkout_snapshot():
            return (
                "오류: 아직 포인트 적립 여부를 묻지 않았습니다. 이번 턴에는 points를 호출하지 말고, "
                "결제를 시작한 뒤 '포인트 적립하시겠어요?'라고 물어보기만 하세요. 고객이 실제로 "
                "대답한 다음 턴에만 points를 호출할 수 있습니다."
            )

    if action == "payment_method":
        # ★ 결제수단보다 포인트 적립 질문이 항상 먼저다 — 예외 없음. 스냅샷은 "이번 턴이
        # 시작되기 전" 기준이므로, 같은 턴에서 방금 points를 호출했다는 이유로는 통과되지 않는다
        # (그렇게 허용하면 "카드로 결제할게" 한 마디로 포인트 질문 자체를 건너뛰고 완주해버림).
        if "points" not in get_checkout_snapshot():
            return (
                "오류: 포인트 적립 여부를 먼저 물어야 합니다. 결제수단을 언급했더라도, 이번 턴에는 "
                "결제수단을 정하지 말고 '포인트 적립하시겠어요?'를 먼저 물어보세요."
            )
        if not _payment_method_supported_by_input(value):
            return (
                "오류: 이번 발화에 결제수단이 실제로 언급되지 않았습니다. 카드/현금/간편결제 중 "
                "고객이 직접 말한 수단이 아니면 임의로 정하지 말고, 결제수단을 다시 물어보세요."
            )

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
        # "010-1234-5678"/"010 1234 5678"처럼 끊어 말한 값이 그대로 들어와도 숫자만 남긴다.
        digits = "".join(ch for ch in (value or "") if ch.isdigit())
        payload["phone"] = digits or value
    elif value is not None:
        payload["value"] = value

    push_action(payload)
    if action in ("start_checkout", "points"):
        checkout_progress.mark_done(get_session_id(), action)
    elif action == "points_phone":
        # points_phone은 고객이 "적립할게"라고 답한 뒤에만 도달하는 단계다. 중간의 points(yes)
        # 툴 호출 자체가 가끔 생략돼도(재현되는 신뢰도 문제) 여기 도달했다는 사실 자체가 포인트
        # 질문에 실제로 답했다는 증거이므로, points 완료로도 함께 기록해 결제수단 단계가
        # 불필요하게 막히지 않게 한다.
        checkout_progress.mark_done(get_session_id(), "points")
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
    ui_action,
]