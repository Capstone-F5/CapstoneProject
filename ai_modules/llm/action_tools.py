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
import re
from .action_context import (
    push_action, get_actions, get_user_input, get_checkout_snapshot, get_last_bot_text, get_recent_user_text,
    add_seen_this_turn, get_recent_turns,
)
from . import guards
from .order_parser import menu_key as _menu_key, named_menus as _named_menus
from .session_context import get_session_id
from core.cart_context import cart_status_text, resolve_cart_item
from . import api_client
from . import checkout_progress
from . import cart_history
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

def _price_label(item: dict) -> str:
    """가격 안내 문구. 할인 중이면 "정가 7,800원 → 현재 할인가 3,900원"처럼 둘 다 적는다.
    예전에는 정가(base_price)만 출력해서 모델이 할인가를 볼 수 없었고, 50% 할인 중인데도 정가를 말했다(실제 로그)."""
    orig = int(float(item.get("original_price") or item["base_price"]))
    final = int(float(item.get("final_price") or orig))
    return f"정가 {orig:,}원 → 현재 할인가 {final:,}원" if final < orig else f"{orig:,}원"


def _current_price(item: dict) -> float:
    """현재 판매가(할인 적용 후). 가격 비교·정렬은 이 값으로 한다."""
    return float(item.get("final_price") or item["base_price"])


@tool
def list_menu() -> str:
    """판매 중인 전체 메뉴를 가격 낮은 순으로 조회한다. add_item 호출 전 menu_item_id 확인용이며,
    "가장 싼/비싼 메뉴", "세트로 바꾸면 얼마 더", 전체 목록·가격 비교 질문에는 반드시 이 도구를 쓴다
    (결과 맨 위에 버거 최저가·최고가와 세트 추가 요금이 적혀 있다). 가격을 말할 때는 현재 판매가(할인가)를 말하고,
    할인 중이면 정가도 함께 알려 준다."""
    try:
        items = _run(api_client.fetch_menu_items())
    except Exception as e:
        return _friendly_error("메뉴 조회 실패", e)

    if not items:
        return "조회된 메뉴가 없습니다."

    # 가격 오름차순으로 보여 "가장 저렴한/비싼" 질문을 모델이 직접 비교하다 틀리지 않게 한다.
    items = sorted(items, key=_current_price)
    burgers = [i for i in items if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    lines = ["[메뉴 목록 — 가격 낮은 순]"]
    if burgers:
        lines.append(
            f"(버거 중 가장 저렴: {burgers[0]['name_ko']} {_price_label(burgers[0])}, "
            f"가장 비쌈: {burgers[-1]['name_ko']} {_price_label(burgers[-1])})"
        )
    for item in items:
        status = " [품절]" if not item.get("is_available", True) else ""
        popular = " [추천메뉴]" if item.get("is_popular") else ""
        allergens = item.get("allergens") or []
        allergen_tag = f" [알레르기: {', '.join(a['name_ko'] for a in allergens)}]" if allergens else ""
        upgrade = next((o for o in item.get("options") or [] if o.get("option_group") == "SET_UPGRADE"), None)
        set_tag = f" [세트로 바꾸면 +{int(float(upgrade['additional_price']))}원]" if upgrade else ""
        lines.append(
            f"- {item['name_ko']} {_price_label(item)} "
            f"(menu_item_id: {item['id']}){status}{popular}{set_tag}{allergen_tag}"
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
        lines.append(f"- {item['name_ko']} {_price_label(item)} (menu_item_id: {item['id']}){allergen_tag}")
    return "\n".join(lines)


@tool
def search_menu(query: str, k: int = 5) -> str:
    """메뉴 이름·특징으로 검색해 실제 menu_item_id를 찾는다. 특정 메뉴를 담을 때 쓴다.
    결과는 유사도 순 상위 몇 개뿐이라 "가장 싼/비싼" 같은 가격 비교·전체 목록 질문에는 쓰지 말고 list_menu를 쓴다.

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
        line = f"- {h['name_ko']} (menu_item_id: {h['id']}) {_price_label(h)}{avail}{popular}"
        if desc:
            line += f"\n  설명: {desc}"
        line += f"\n  알레르기: {', '.join(a['name_ko'] for a in allergens) if allergens else '없음'}"
        lines.append(line)
    return "\n".join(lines)

def _mentions_other_menu(text: str, item: dict, last_bot: str = "", upgrade_to_set: bool = False,
                         menu: list | None = None, recent: str = "") -> tuple[str, bool] | None:
    """LLM이 넘긴 메뉴(`item`)가 손님이 말한 메뉴와 다르면 (손님이 말한 쪽 이름, 그 메뉴가 하나로 정해지는지)를
    돌려준다(맞거나 모르면 None). 하나로 정해지면 호출한 쪽이 거절하지 않고 맞는 메뉴로 바로잡을 수 있다.

    - 버거: 이번 발화에 버거 이름이 있으면 그 버거여야 한다. 발화에 이름이 없는 "맞아요" 같은 확인
      답변이면 직전에 키오스크가 말한 버거여야 한다. (직전 턴의 id를 재사용해 비건 버거 세트가
      더블 불고기 버거로 담기던 문제를 막는다)
    - 그 외(사이드·음료 등): 발화에 다른 메뉴 이름은 있고 이 메뉴 이름은 없으면 어긋난 것으로 본다.
    """
    compact = re.sub(r"\s+", "", text or "")
    mine = _menu_key(item.get("name_ko", ""))
    if not mine:
        return None
    if menu is None:
        try:
            menu = _run(api_client.fetch_menu_items())
        except Exception:  # noqa: BLE001 - 가드 때문에 주문이 막히면 안 된다
            return None
    is_burger = any(o.get("option_group") == "SET_UPGRADE" for o in item.get("options") or [])
    if is_burger:
        burgers = [i["name_ko"] for i in menu
                   if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
        expected = _named_menus(compact, burgers)
        if not expected and not upgrade_to_set:
            # 버거 이름 없이 다른 메뉴(콜라 등)만 말했는데 단품 버거를 담으려는 경우 — 직전 안내의 버거를
            # 재사용한 것이다. (세트 주문에서는 사이드·음료 이름이 정상적으로 나오므로 제외)
            others = [n for n in _named_menus(compact, list({i["name_ko"] for i in menu})) if n not in burgers]
            if others and not any(_menu_key(n) in mine or mine in _menu_key(n) for n in others):
                return others[0], len(others) == 1
        if not expected:
            expected = _named_menus(re.sub(r"\s+", "", last_bot or ""), burgers)
        if not expected:
            # 직전 키오스크 안내에도 버거 이름이 없으면, 버거 이름이 나온 가장 최근 손님 발화를 따른다
            # ("치킨다릿살버거 세트로 하나 줘" → … → "콜라로 주세요"처럼 이름 없이 이어 말하는 경우)
            for turn in reversed([t for t in (recent or "").split("¦") if t.strip()]):
                expected = _named_menus(re.sub(r"\s+", "", turn), burgers)
                if expected:
                    break
        if expected and not any(_menu_key(n) == mine for n in expected):
            return expected[0], len(expected) == 1
        return None
    if not compact:
        return None
    # 발화에서 읽히는 메뉴 이름(긴 이름 먼저). "감자튀김"이 "양념감자튀김"의 일부라는 이유로 맞다고 보지 않는다.
    spoken = _named_menus(compact, list({i["name_ko"] for i in menu}))
    if any(_menu_key(n) == mine for n in spoken) or (not spoken and mine in compact):
        return None
    others = [n for n in spoken if _menu_key(n) != mine]
    return (others[0], len(others) == 1) if others else None


def _spoken_exclusions(text: str, options: list[dict]) -> list[str]:
    """발화에서 "양파 빼고"처럼 이 메뉴의 EXCLUDE 옵션 재료 뒤에 빼/제외/없이가 붙은 것만 골라낸다."""
    found: list[str] = []
    compact = (text or "").replace(" ", "")
    for o in options:
        if o.get("option_group") != "EXCLUDE" or not o.get("is_available", True):
            continue
        ingredient = o["name_ko"].replace("제외", "").replace("다진", "").strip().replace(" ", "")
        if ingredient and re.search(re.escape(ingredient) + r"(은|는|를|을|만)?(빼|제외|없이|넣지)", compact):
            found.append(o["name_ko"])
    return found


_ADD_MORE = re.compile(r"더\s*(?:줘|주세요|담|추가|해)|더\s*$|추가|또\s")


def _option_context(user: str, recent: str, item_name: str, menu: list | None) -> str:
    """세트의 사이드·음료를 손님이 말했는지 찾아볼 발화 범위. 이번 발화에 버거 이름이 있으면 이번 발화만 본다.
    없으면 최근 발화를 거슬러 올라가다가 버거 이름이 나온 발화에서 멈춘다(그 버거가 이 항목이 아니면 그 발화는 제외).
    이전에 다른 세트를 주문하며 말한 사이드·음료가 이번 세트의 근거로 인정돼 되묻지 않고 담기던 문제를 막는다."""
    if not menu:
        return f"{recent} {user}"
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    if _named_menus(re.sub(r"\s+", "", user), burgers):
        return user
    kept: list[str] = []
    for turn in reversed([t for t in (recent or "").split("¦") if t.strip()]):
        named = _named_menus(re.sub(r"\s+", "", turn), burgers)
        if named:
            if any(_menu_key(n) == _menu_key(item_name) for n in named):
                kept.append(turn)
            else:
                kept = []   # 그 뒤에 나온 사이드·음료 발화는 다른 버거의 세트에 대한 말이다
            break
        kept.append(turn)
    return " ".join(reversed(kept)) + " " + user


_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _resolve_menu_by_name(name: str, menu: list | None) -> dict | None:
    """메뉴 이름(또는 비슷한 이름)으로 메뉴 하나를 찾는다. "치킨너겟" → "너겟(4조각)". 하나로 정해질 때만 돌려준다."""
    key = _menu_key(name)
    if not menu or len(key) < 2:
        return None
    exact = [i for i in menu if _menu_key(i["name_ko"]) == key]
    if len(exact) == 1:
        return exact[0]
    near = [i for i in menu if key in _menu_key(i["name_ko"]) or _menu_key(i["name_ko"]) in key]
    if len(near) == 1:
        return near[0]
    # 여럿이면 이름이 가장 길게 겹치는 하나(그 길이가 유일할 때만)
    scored = sorted(((len(_menu_key(i["name_ko"])), i) for i in near), key=lambda x: -x[0])
    if len(scored) >= 2 and scored[0][0] > scored[1][0]:
        return scored[0][1]
    return None


def _check_add_item(item: dict, quantity: int, upgrade_to_set: bool, side: str | None, drink: str | None
                    ) -> tuple[str | None, dict, int]:
    """add_item 호출이 손님이 한 말과 맞는지 규칙으로 검사한다. (거절 메시지 또는 None, 사용할 항목, 사용할 수량)을 돌려준다.
    메뉴가 어긋났는데 손님이 말한 메뉴가 하나로 정해지면 거절하지 않고 맞는 메뉴로 바로잡는다(항목이 바뀜).
    모든 개입은 guards가 기록한다. 한국어 발화에서만 동작하고, 근거가 없으면 막지 않는다."""
    user, recent, last_bot = get_user_input(), get_recent_user_text(), get_last_bot_text()
    name = item["name_ko"]
    try:
        menu = _run(api_client.fetch_menu_items())
    except Exception:  # noqa: BLE001 - 가드 때문에 주문이 막히면 안 된다
        menu = None

    # 1) 메뉴 일치 — 직전 턴의 menu_item_id 재사용
    found = _mentions_other_menu(user, item, last_bot, upgrade_to_set, menu, recent)
    if found:
        wrong, unique = found
        # 여러 메뉴를 한꺼번에 말한 발화에서는 모델이 다른 품목의 id를 넣은 것일 수 있어 자동으로 바꾸면 한 메뉴가 중복으로
        # 담긴다(2개+1개). 한 가지 메뉴만 말했을 때만 바로잡고 아니면 모델이 다시 호출하게 한다.
        many = bool(menu) and len(_named_menus(re.sub(r"\s+", "", user), list({i["name_ko"] for i in menu}))) > 1
        target = _resolve_menu_by_name(wrong, menu) if unique and not many else None
        if target and (not upgrade_to_set or any(o.get("option_group") == "SET_UPGRADE" for o in target.get("options") or [])):
            if guards.fix("menu_mismatch", f"「{user[:30]}」 {name} → {target['name_ko']}(손님이 말한 메뉴)로 바로잡음"):
                try:
                    fixed_item = _run(api_client.fetch_menu_item_by_id(target["id"]))
                except Exception:  # noqa: BLE001
                    fixed_item = None
                if fixed_item:
                    item, name = fixed_item, fixed_item["name_ko"]
                    found = None
        if found:
            msg = guards.block(
                "menu_mismatch", f"「{user[:30]}」 말한 메뉴={wrong} / 전달된 메뉴={name}",
                f"오류: 손님이 말한 메뉴는 '{wrong}'인데 전달된 menu_item_id는 '{name}'입니다. "
                f"search_menu로 '{wrong}'의 menu_item_id를 찾아 다시 호출하세요.")
            if msg:
                return msg, item, quantity
    if not (guards.has_hangul(user) or guards.has_hangul(recent)):
        return None, item, quantity   # 외국어 발화는 아래 한국어 규칙을 적용하지 않는다

    # 2) 질문형 발화에서는 담지 않는다 ("콜라는 얼마예요?")
    if guards.is_question_only(user):
        msg = guards.block(
            "question_add", f"「{user[:30]}」 질문형인데 {name} 담기 시도",
            "오류: 손님이 가격·정보를 물었을 뿐 담아 달라고 하지 않았습니다. 장바구니에 담지 말고 질문에 답하세요.")
        if msg:
            return msg, item, quantity

    is_burger = any(o.get("option_group") == "SET_UPGRADE" for o in item.get("options") or [])

    # 3) 세트로 담으려면 손님이 세트를 말했어야 한다(이전 턴·직전 안내에 대한 긍정 포함)
    if upgrade_to_set and not (guards.mentions_set(user) or guards.mentions_set(recent)
                               or (guards.is_confirmation(user) and guards.mentions_set(last_bot))):
        msg = guards.block(
            "set_ungrounded", f"「{user[:30]}」 세트라고 말하지 않았는데 {name} 세트 담기 시도",
            f"오류: 손님이 '{name}'을(를) 세트로 달라고 말하지 않았습니다. 단품/세트를 먼저 물어보세요.")
        if msg:
            return msg, item, quantity

    # 4) 세트의 사이드·음료는 손님이 실제로 말한 것이어야 한다(지어내서 채우기 금지)
    if upgrade_to_set:
        ctx = _option_context(user, recent, name, menu)
        for label, value in (("사이드", side), ("음료", drink)):
            if value and not guards.spoken_in(ctx, value) and not (
                    guards.is_confirmation(user) and guards.spoken_in(last_bot, value)):
                msg = guards.block(
                    "set_option_ungrounded", f"{label} '{value}'를 손님이 말하지 않음 ({name} 세트)",
                    f"오류: 손님이 {label}를 '{value}'(으)로 말하지 않았습니다. 임의로 고르지 말고 {label}를 먼저 "
                    f"물어본 뒤 손님이 고른 것으로 다시 호출하세요.")
                if msg:
                    return msg, item, quantity

    # 5) 버거는 단품/세트를 말하지 않았으면 먼저 물어야 한다(같은 단품을 더 담는 경우는 예외)
    if is_burger and not upgrade_to_set and not (
            guards.mentions_single(user)
            or guards.mentions_set(user) or (guards.is_confirmation(user) and guards.mentions_single(last_bot))):
        # 예외는 "하나 더 줘/추가"처럼 이미 담은 것을 더하겠다고 분명히 말한 경우뿐이다. "치킨가슴살버거 하나 줘"는
        # 이미 장바구니에 있어도 단품/세트를 새로 묻는 것이 설계다(같은 버거의 세트를 담을 수도 있다).
        already = False
        try:
            cart = _run(api_client.get_cart(get_session_id()))
            already = bool(_ADD_MORE.search(user)) and any(i.get("menu_item_id") == item.get("id") and not any(
                o.get("option_group") == "SET_UPGRADE" for o in i.get("selected_options", []))
                for i in cart.get("items", []))
        except Exception:  # noqa: BLE001
            already = True   # 확인할 수 없으면 막지 않는다
        if not already:
            msg = guards.block(
                "single_set_unasked", f"「{user[:30]}」 단품/세트를 말하지 않았는데 {name} 단품 담기 시도",
                f"오류: 손님이 '{name}'을(를) 단품으로 달라고 말하지 않았습니다. 담지 말고 "
                f"'단품으로 드릴까요, 세트로 드릴까요?'라고 먼저 물어보세요.")
            if msg:
                return msg, item, quantity

    # 6) 수량 — 발화에 수량 표현이 하나뿐이고 메뉴도 하나뿐이면 둘이 같아야 한다
    spoken_qty = guards.quantity_in(user)
    if spoken_qty is not None and menu:
        named = _named_menus(re.sub(r"\s+", "", user), list({i["name_ko"] for i in menu}))
        if len(named) == 1 and spoken_qty != quantity:
            # 손님이 말한 수량이 하나로 정해지므로 거절하지 않고 그 수량으로 바로잡는다(모델은 거절을 받으면
            # 같은 호출을 되풀이하다 반복 한도에 걸리는 일이 있었다)
            if guards.fix("quantity_mismatch", f"「{user[:30]}」 수량 {quantity} → {spoken_qty}(손님이 말한 수량)로 바로잡음"):
                quantity = spoken_qty
            else:
                msg = guards.block(
                    "quantity_mismatch", f"「{user[:30]}」 말한 수량={spoken_qty} / 전달된 수량={quantity}",
                    f"오류: 손님이 말한 수량은 {spoken_qty}개인데 quantity={quantity}로 호출했습니다. "
                    f"quantity={spoken_qty}로 다시 호출하세요.")
                if msg:
                    return msg, item, quantity
    return None, item, quantity


def _topic_burger(user: str, menu: list | None, turns: list) -> str | None:
    """지금 이야기 중인 버거. 발화에 버거 이름이 정확히 하나 있으면 그것, 둘 이상이면 모호하므로 None, 하나도 없으면 최근 대화
    (키오스크 안내·손님 발화)를 최근 것부터 거슬러 올라가 버거 이름이 나온 첫 턴이 정확히 하나를 가리킬 때 그것."""
    if not menu or not guards.has_hangul(user):
        return None
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    said = _named_menus(re.sub(r"\s+", "", user), burgers)
    if said:
        return said[0] if len(said) == 1 else None
    for _role, text in reversed(turns or []):
        named = _named_menus(re.sub(r"\s+", "", text or ""), burgers)
        if named:
            return named[0] if len(named) == 1 else None
    return None


def _target_mismatch(user: str, target_name: str, menu: list | None) -> str | None:
    """수량 변경 대상으로 넘어온 장바구니 줄이 손님이 말한 메뉴와 다르면 손님이 말한 메뉴 이름을 돌려준다."""
    if not menu or not guards.has_hangul(user):
        return None
    compact = re.sub(r"\s+", "", user)
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    others = [i["name_ko"] for i in menu if i["name_ko"] not in burgers]
    named = _named_menus(compact, burgers) or _named_menus(compact, others)
    if len(named) != 1:
        return None
    mine, want = _menu_key(target_name), _menu_key(named[0])
    return None if (want in mine or mine in want) else named[0]


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

    # 모델이 menu_item_id 자리에 UUID 대신 메뉴 이름("치킨너겟")을 넣는 경우가 많다(다품목 주문에서 특히).
    # 그대로 두면 "메뉴를 찾을 수 없다"가 되고, 모델이 그러고도 "담았습니다"라고 답하기도 한다 → 이름으로 찾아 준다.
    if not _UUID_RE.match(str(menu_item_id or "")):
        try:
            by_name = _resolve_menu_by_name(str(menu_item_id or ""), _run(api_client.fetch_menu_items()))
        except Exception:  # noqa: BLE001
            by_name = None
        if by_name and guards.fix("id_is_name", f"menu_item_id='{menu_item_id}' → {by_name['name_ko']}"):
            menu_item_id = by_name["id"]

    try:
        # 단건 조회 API 호출
        item = _run(api_client.fetch_menu_item_by_id(menu_item_id))
    except Exception as e:
        return _friendly_error("메뉴 조회 실패", e)

    if item is None:
        return f"오류: 해당 ID의 메뉴를 찾을 수 없습니다 ({menu_item_id})"

    if not item.get("is_available", True):
        return f"죄송합니다, {item['name_ko']}는 현재 품절입니다."

    # 규칙 기반 검사(ai_modules/llm/guards.py): 손님이 한 말과 어긋난 호출은 되돌려 보낸다.
    blocked, item, quantity = _check_add_item(item, quantity, upgrade_to_set, side, drink)
    if blocked:
        return blocked
    menu_item_id = item.get("id", menu_item_id)   # 메뉴가 바로잡혔으면 그 id로 담는다

    # 같은 턴에 같은 추가를 또 하려는 호출은 무시한다. 모델이 틀린 id로 add_item을 여러 번 부르고 가드가 그것들을
    # 같은 메뉴로 바로잡으면 같은 메뉴가 중복으로 담긴다(실제로 데리버거가 6개가 됨).
    dup_key = (item.get("id"), bool(upgrade_to_set), side, drink)   # 수량이 달라도 같은 발화의 같은 메뉴는 한 번만(2개+1개로 쪼개 3개가 되던 사고)
    if add_seen_this_turn(dup_key):
        guards.fix("duplicate_add", f"이번 턴에 이미 담은 {item['name_ko']} {quantity}개 중복 호출 무시")
        return f"{item['name_ko']} {quantity}개는 이번 요청에서 이미 담았습니다. 다시 담지 말고 손님에게 결과를 안내하세요."

    # 같은 턴에 수량을 이미 늘린 메뉴(update_item)를 add_item으로 또 담으면 두 번 더해진다(3개+2개 요청이 7개가 됨)
    if not upgrade_to_set and any(e["via"] == "update" and e["name"] == item["name_ko"] for e in
                                   cart_history.peek_added(session_id, this_turn_only=True)):
        guards.fix("add_after_update", f"이번 턴에 수량을 이미 늘린 {item['name_ko']}를 다시 담으려는 호출 무시")
        return f"{item['name_ko']}은(는) 이번 요청에서 이미 수량을 늘렸습니다. 다시 담지 말고 손님에게 결과를 안내하세요."

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

    if not exclusions:
        exclusions = _spoken_exclusions(get_user_input(), options)   # 모델이 제외를 빼먹은 경우 발화에서 보완

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
    cart_history.record_added(session_id, cart_item_id, item["name_ko"], quantity)

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
def remove_item(cart_item_id: str | None = None) -> str:
    """장바구니에서 특정 항목을 삭제한다.
    Args:
        cart_item_id: 삭제할 장바구니 항목의 UUID. 생략 시 항목이 하나일 때만 자동 선택한다.
    """
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
        cart_item, error = resolve_cart_item(cart, cart_item_id)
        if error:
            return error
        cart_item_id = cart_item["cart_item_id"]
        user = get_user_input()
        if guards.has_hangul(user):
            if not guards.has_remove_intent(user):
                msg = guards.block(
                    "remove_no_intent", f"「{user[:30]}」 삭제 의사 없이 {cart_item.get('name_ko')} 삭제 시도",
                    "오류: 손님이 삭제·취소를 말하지 않았습니다. 장바구니에서 지우지 말고 손님이 원하는 것을 다시 확인하세요.")
                if msg:
                    return msg
            elif cart_item.get("quantity", 1) > 1 and guards.wants_reduce_one(user):
                n = cart_item["quantity"]
                msg = guards.block(
                    "remove_should_reduce", f"「{user[:30]}」 {cart_item.get('name_ko')} {n}개 중 하나만 빼려는데 전체 삭제 시도",
                    f"오류: 손님은 {cart_item.get('name_ko')} {n}개 중 하나만 빼 달라고 했습니다. 줄 전체를 지우지 말고 "
                    f"update_item_options(cart_item_id=..., quantity={n - 1})로 수량만 줄이세요.")
                if msg:
                    return msg
        _run(api_client.remove_cart_item(session_id, cart_item_id))
    except Exception as e:
        return _friendly_error("삭제 실패", e)

    push_action({"type": "remove_item", "cart_item_id": cart_item_id})
    cart_history.record_removed(session_id, cart_item)
    return "항목을 장바구니에서 삭제했습니다."

@tool
def update_item_options(
    cart_item_id: str | None = None,
    quantity: int | None = None,
    item_type: str | None = None,
    side: str | None = None,
    drink: str | None = None,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니 항목의 수량, 단품/세트 여부 또는 옵션을 변경한다.
    Args:
        cart_item_id: 변경할 장바구니 항목 UUID. 생략 시 항목이 하나일 때만 자동 선택한다.
        quantity: 새 수량.
        item_type: 단품/세트 전환 시 single 또는 set. 세트로 바꿀 때 사이드와 음료도 지정한다.
        side: 새 세트 사이드 이름(세트 항목에만 해당). 예: "치즈스틱"
        drink: 새 세트 음료 이름(세트 항목에만 해당). 예: "콜라"
        exclusions: 새 제외 옵션 목록.
        special_note: 새 특이사항.
    """
    session_id = get_session_id()
    if item_type not in (None, "single", "set"):
        return "오류: item_type은 single 또는 set이어야 합니다."
    if item_type == "single":
        side = drink = None   # 단품에는 사이드·음료가 없다. 세트→단품 전환 때 모델이 넘겨도 오류 대신 무시한다.
    if not any(value is not None for value in (quantity, item_type, side, drink, exclusions, special_note)):
        return "변경할 내용을 알려주세요."

    user_now = get_user_input()
    if ((side is not None or drink is not None) and item_type is None and guards.has_hangul(user_now)
            and guards.quantity_in(user_now) is not None and not guards.mentions_set(user_now)
            and not guards.has_change_verb(user_now)):
        # "양념감자튀김 세 개 그리고 제로콜라 세 잔 줘"는 사이드·음료를 따로 주문한 것이다(세트가 장바구니에 있어도 세트 옵션 변경이 아니다)
        msg = guards.block(
            "option_update_instead_of_item", f"「{user_now[:30]}」 수량을 말한 사이드·음료 주문을 세트 옵션 변경으로 처리하려 함",
            "오류: 손님은 사이드·음료를 수량과 함께 따로 주문했습니다. 세트 옵션을 바꾸지 말고 각 메뉴를 add_item으로 담으세요.")
        if msg:
            return msg
    try:
        cart = _run(api_client.get_cart(session_id))
        cart_item, error = resolve_cart_item(cart, cart_item_id)
        if error:
            return error
        cart_item_id = cart_item["cart_item_id"]
        # 변경하려는 줄이 지금 이야기 중인 버거의 줄인지 확인한다. 실제 로그: 더블 불고기 버거는 담긴 적이 없는데 모델이 "더블 불고기
        # 버거 세트로 변경했습니다"라고 하면서 장바구니의 다른 버거(그릴드 비프)의 옵션을 바꿨다.
        try:
            topic = _topic_burger(get_user_input(), _run(api_client.fetch_menu_items()), get_recent_turns())
        except Exception:  # noqa: BLE001 - 가드 때문에 변경이 막히면 안 된다
            topic = None
        if topic and _menu_key(cart_item.get("name_ko", "")) != _menu_key(topic):
            same = [i for i in cart.get("items", []) if _menu_key(i.get("name_ko", "")) == _menu_key(topic)]
            if same or len(cart.get("items", [])) >= 2:   # 줄이 하나뿐이면 그 줄이 대상일 수밖에 없다
                if same:
                    hint = f"장바구니에서 '{topic}' 줄의 cart_item_id를 찾아 다시 호출하세요."
                else:
                    hint = (f"'{topic}'은(는) 장바구니에 없습니다. 다른 메뉴의 줄을 바꾸지 말고, 손님에게 아직 담기지 않았다고 알린 뒤 "
                            "담을지 물어보세요.")
                msg = guards.block(
                    "update_wrong_target",
                    f"「{get_user_input()[:30]}」 이야기 중인 메뉴={topic} / 변경 대상={cart_item.get('name_ko')}",
                    f"오류: 지금 이야기 중인 메뉴는 '{topic}'인데 변경하려는 줄은 '{cart_item.get('name_ko')}'입니다. {hint}")
                if msg:
                    return msg
        if any(e["cart_item_id"] == cart_item_id for e in cart_history.peek_added(session_id, this_turn_only=True)):
            # 방금 이 요청에서 담은 줄을 또 수정하려는 호출 — 담은 직후의 "확인용" 수정이 "하나 더"로 해석돼 수량이 두 배가 됐다
            guards.fix("update_after_add", f"이번 턴에 담은 {cart_item.get('name_ko')} 줄을 같은 턴에 다시 수정하려는 호출 무시")
            return f"{cart_item.get('name_ko')}은(는) 이번 요청에서 이미 담았습니다. 다시 수정하지 말고 손님에게 결과를 안내하세요."
        is_set_line = any(s.get("option_group") == "SET_UPGRADE" for s in cart_item.get("selected_options", []))
        # item_type="single"을 함께 넘겨도 이미 단품인 줄이면 수량만 바꾸는 호출이다(이걸 놓쳐 "두 개 줘"가 2개로 줄던 사고)
        if (quantity is not None and exclusions is None and side is None and drink is None
                and (item_type is None or (item_type == "single" and not is_set_line))):
            try:
                menu = _run(api_client.fetch_menu_items())
            except Exception:  # noqa: BLE001
                menu = None
            user_text = get_user_input()
            spoken = guards.quantity_in(user_text)
            if (spoken is not None and quantity == spoken and guards.has_add_verb(user_text)
                    and not guards.has_change_verb(user_text) and not guards.has_remove_intent(user_text)):
                # "게살버거 단품 두 개 담아줘"는 이미 1개가 있으면 3개가 되어야 한다(모델이 2개로 "변경"하는 사고)
                current = int(cart_item.get("quantity", 1))
                if guards.fix("update_should_add",
                              f"「{user_text[:30]}」 {cart_item.get('name_ko')} 기존 {current}개 + {spoken}개 = {current + spoken}개"):
                    quantity = current + spoken
            is_burger_line = bool(menu) and any(
                i["id"] == cart_item.get("menu_item_id") and any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])
                for i in menu)
            # 세트 줄에 "세트로 하나 줘"를, 버거 줄에 단품/세트 말 없이 "X 하나 줘"를 수량 변경으로 처리하려는 경우 — 새 주문이다
            new_order = (guards.mentions_set(user_text) if is_set_line else
                         (is_burger_line and not guards.mentions_single(user_text) and not guards.mentions_set(user_text)
                          and guards.has_add_verb(user_text)))
            if new_order and not _ADD_MORE.search(user_text) and not guards.has_change_verb(user_text):
                msg = guards.block(
                    "set_update_instead_of_add", f"「{user_text[:30]}」 세트 새 주문을 기존 세트 줄 수량 변경으로 처리하려 함",
                    "오류: 손님은 이 메뉴를 새로 주문했습니다. 기존 줄의 수량을 바꾸지 말고, 단품/세트를 말하지 않았으면 "
                    "단품으로 드릴지 세트로 드릴지 먼저 묻고, 세트면 사이드와 음료를 물어본 뒤 add_item으로 담으세요.")
                if msg:
                    return msg
            wrong = _target_mismatch(get_user_input(), cart_item.get("name_ko", ""), menu)
            if wrong:
                msg = guards.block(
                    "update_wrong_target", f"「{get_user_input()[:30]}」 말한 메뉴={wrong} / 변경 대상={cart_item.get('name_ko')}",
                    f"오류: 손님이 말한 메뉴는 '{wrong}'인데 변경하려는 줄은 '{cart_item.get('name_ko')}'입니다. "
                    f"장바구니에서 '{wrong}'의 cart_item_id를 찾아 다시 호출하세요.")
                if msg:
                    return msg
    except Exception as e:
        return _friendly_error("장바구니 조회 실패", e)

    payload: dict = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if special_note is not None:
        payload["special_note"] = special_note

    if exclusions is not None or side is not None or drink is not None or item_type is not None:
        # exclusions/side/drink 가 그동안 payload에 전혀 반영되지 않아 "재료 빼줘",
        # "사이드 바꿔줘" 같은 후속 요청이 조용히 무시되던 버그 수정. 지정되지 않은
        # 그룹(세트업그레이드 등)의 기존 선택은 그대로 유지하고 해당 그룹만 교체한다.
        try:
            menu_item = _run(api_client.fetch_menu_item_by_id(cart_item["menu_item_id"]))
        except Exception as e:
            return _friendly_error("옵션 조회 실패", e)

        if menu_item is None:
            return f"오류: 메뉴 정보를 찾을 수 없습니다 ({cart_item['menu_item_id']})"
        options = (menu_item or {}).get("options", [])
        option_by_id = {o["id"]: o for o in options}
        replace_groups = set()
        if item_type is not None:
            replace_groups.update({"SET_UPGRADE", "SET_SIDE", "SET_DRINK"})
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
        if item_type == "set":
            set_opt = next((o for o in options if o.get("option_group") == "SET_UPGRADE"), None)
            if set_opt is None:
                return f"오류: {menu_item['name_ko']}는 세트 주문이 불가합니다."
            if not side or not drink:
                return "세트로 변경하려면 사이드와 음료를 모두 확인해야 합니다. 고객에게 먼저 물어보세요."
            new_selected.append({"option_id": set_opt["id"], "name": set_opt["name_ko"]})
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
    if quantity is not None and quantity > int(cart_item.get("quantity", 1)):
        cart_history.record_added(session_id, cart_item_id, cart_item.get("name_ko", ""),
                                  quantity - int(cart_item.get("quantity", 1)), via="update")
    return "장바구니 항목을 수정했습니다."

@tool
def get_cart_status() -> str:
    """현재 장바구니 내용을 조회한다. 항목 수정·삭제 전에 cart_item_id 확인용으로 필수 사용."""
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
    except Exception as e:
        return _friendly_error("장바구니 조회 실패", e)

    return cart_status_text(cart)

_CLEAR_CART_RE = re.compile(
    r"전부|모두|다\s*지|싹|비워|비우|초기화|처음부터|주문\s*(?:전체\s*)?취소|전체\s*(?:삭제|취소)|"
    r"clear|empty|remove\s+(?:all|everything)|delete\s+(?:all|everything)|start\s+over|reset|cancel\s+(?:the\s+)?(?:whole\s+)?order|"
    r"全部|清空|取消订单|すべて削除|全部削除|空にして|クリア|最初から|从头|重新开始",
    re.IGNORECASE,
)


_KO_DIGITS = {"공": "0", "영": "0", "일": "1", "이": "2", "삼": "3", "사": "4",
              "오": "5", "육": "6", "륙": "6", "칠": "7", "팔": "8", "구": "9"}


def _spoken_digits(text: str) -> str:
    """발화에서 숫자(아라비아 숫자와 '공일공' 같은 한국어 숫자 읽기)만 이어 붙여 돌려준다.

    전화번호를 말한 턴인지 판단하는 용도라, 숫자가 거의 없는 발화는 빈 문자열을 돌려 검사를 건너뛴다.
    """
    # 일반 단어에도 '일·이·오·구'가 들어 있으므로, 숫자 글자가 (공백·하이픈만 사이에 두고) 이어진 구간만 센다.
    # "…오육칠팔이요"의 '이요'는 숫자 '이(2)'가 아니라 서술 어미라서 숫자 뒤에 붙은 어미는 먼저 뗀다.
    text = re.sub(r"(?<=[0-9공영일이삼사오육륙칠팔구])(이요|이에요|이예요|입니다)", " ", text or "")
    runs = re.findall(r"[0-9공영일이삼사오육륙칠팔구](?:[\s\-]*[0-9공영일이삼사오육륙칠팔구])+", text or "")
    best = max(("".join(c if c.isdigit() else _KO_DIGITS[c] for c in r if c.isdigit() or c in _KO_DIGITS)
                for r in runs), key=len, default="")
    return best if len(best) >= 3 else ""


def _explicit_clear_request(text: str) -> bool:
    return bool(_CLEAR_CART_RE.search(text or ""))


@tool
def clear_cart() -> str:
    """장바구니를 전부 비운다."""
    # ★ 되돌릴 수 없는 동작이므로 손님이 전체 삭제를 분명히 말했을 때만 실행한다. "결제 취소하고 주문
    # 수정할래"를 장바구니 비우기로 해석해 손님의 주문이 통째로 사라지는 사례가 재현되어 걸어 둔다.
    if not _explicit_clear_request(get_user_input()):
        return (
            "오류: 손님이 장바구니 전체 삭제를 분명히 말하지 않았습니다. 장바구니를 비우지 말고, "
            "무엇을 수정하고 싶은지(수량·옵션·특정 메뉴 삭제 등) 물어보세요."
        )
    session_id = get_session_id()
    try:
        _run(api_client.delete_cart(session_id))
    except Exception as e:
        return _friendly_error("초기화 실패", e)
    checkout_progress.reset(session_id)  # 새 주문을 시작하므로 이전 결제 진행 상태도 초기화
    cart_history.reset(session_id)
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

    if action == "points_phone":
        # 전화번호는 10~11자리여야 한다. 모자란 번호를 그대로 화면에 보내면 잘못된 번호로 조회·적립된다.
        phone_digits = "".join(ch for ch in (value or "") if ch.isdigit())
        # 모델이 들은 자릿수가 모자랄 때 번호를 지어내 채우는 일이 재현되므로, 손님 발화에서 읽힌 숫자와도 맞춰 본다.
        heard = _spoken_digits(get_user_input())
        if heard and heard != phone_digits:
            phone_digits = heard
        if len(phone_digits) not in (10, 11):
            return (
                f"오류: 손님이 말한 전화번호가 {len(phone_digits)}자리뿐입니다(10~11자리여야 함). 액션을 보내지 말고 "
                "번호를 임의로 채우지도 말고, 번호를 처음부터 다시 말씀해 달라고 안내하세요."
            )
        value = phone_digits

    if action == "start_checkout":
        # ★ 결제 시작은 한 번이면 된다. 포인트 단계까지 이미 끝났거나(이전 턴), 이번 턴에 결제 수단을 이미
        # 정했는데 start_checkout을 또 부르면 화면이 포인트 질문 팝업을 다시 띄운다 — 손님이 "카드로 할게요"라고
        # 할 때마다 "결제 전 포인트 적립하시겠어요?"가 반복되던 현상(대화 로그로 확인)의 원인.
        if "points" in get_checkout_snapshot() or any(x.get("type") == "payment_method" for x in get_actions()):
            return (
                "오류: 결제는 이미 시작되어 포인트 단계까지 진행됐습니다. start_checkout을 다시 호출하지 말고, "
                "포인트 질문도 다시 하지 말고, 고객이 말한 다음 단계(결제 수단 선택 등)만 처리하세요."
            )

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
