"""LLM이 도구를 부르지 않고 말로만 처리한 핵심 화면 동작을 규칙으로 보완한다.

현상(대화 로그로 확인): "포장할래" → "포장으로 선택했습니다"라고 답하지만 `order_type` 액션이 없고,
"카드로 할게요" → "카드 단말기에 카드를 삽입해 주세요"라고 답하지만 `payment_method` 액션이 없다.
말은 했는데 화면은 그대로라 손님이 같은 말을 반복하게 된다. gpt-4o-mini가 이런 호출을 가끔 빼먹는 것은
프롬프트 지시만으로 막을 수 없었다(재현 테스트로 확인).

그래서 사용자의 말이 분명하고 화면·결제 단계 조건이 맞는 경우에 한해, 이번 턴에 해당 액션이 빠졌으면
서버가 직접 추가한다. 이미 LLM이 같은 종류의 액션을 냈으면 아무것도 하지 않는다.
- 주문 유형: 시작·주문유형 화면에서 "포장"/"매장"만 분명히 말했을 때
- 결제 시작: 장바구니 화면에서 결제 의사를 분명히 말했고 장바구니가 비어 있지 않을 때
- 결제 수단: 포인트 질문이 이전 턴에 끝난 뒤(순서 규칙 유지) 결제 수단을 하나만 분명히 말했을 때
"""
from __future__ import annotations

import re

from ai_modules.llm import checkout_progress
from ai_modules.llm.action_context import get_actions, push_action
from core.cart_context import _CART_CONTENT_Q_RE, _CART_OPEN_RE

_TAKEOUT = re.compile(
    r"포장|테이크\s*아웃|가져\s*갈|싸\s*가|take\s*-?\s*out|to\s*-?\s*go|持ち帰り|テイクアウト|外带|打包|带走",
    re.IGNORECASE,
)
_DINE_IN = re.compile(
    r"매장|먹고\s*갈|여기서|dine\s*-?\s*in|eat\s*(?:in|here)|for\s*here|stay\s*here|店内|イートイン|堂食|在这里吃",
    re.IGNORECASE,
)
_SWITCH_WORDS = re.compile(r"말고|아니고|대신|아니라|instead|rather|not\b|でなく|不是")

_CHECKOUT_INTENT = re.compile(
    r"결제\s*(?:할게|해줘|해\s*주|하겠|진행|할래|하고\s*싶|부탁)|계산\s*(?:할게|해줘|해\s*주|하겠|할래)|"
    r"check\s*-?\s*out|pay\s+(?:now|please)|i(?:'d| would)? like to pay|支付|结账|買い物を終|会計|お会計",
    re.IGNORECASE,
)

# 결제 수단 키워드: action_tools의 규칙과 같다(삼성페이는 카드 버튼이 담당).
# "페이"/"pay" 같은 일반 단어는 다른 수단이 분명히 언급되지 않았을 때만 간편결제로 본다
# ("삼성페이로", "pay by card"는 카드).
_EXPLICIT_METHOD: list[tuple[str, tuple[str, ...]]] = [
    ("card", ("카드", "삼성페이", "samsung", "card", "credit", "信用卡", "カード", "クレジット")),
    ("cash", ("현금", "cash", "现金", "現金", "キャッシュ")),
    ("pay", ("간편결제", "간편", "카카오페이", "네이버페이", "제로페이", "페이코", "qr", "바코드", "barcode",
             "naver", "kakao", "payco", "扫码", "移动支付", "QRコード")),
]
_GENERIC_PAY = ("페이", "pay")

# 포인트 적립 의사. 부정이 먼저 나오는지 본다("적립 안 할게요" 안에 "적립"과 "할게요"가 같이 있다).
_POINTS_NO = re.compile(r"적립\s*(?:은|는)?\s*(?:안|하지\s*않|않|괜찮|필요\s*없)|no\s*points|don'?t\s*(?:want|need)|不用积分|ポイントは(?:貯めません|いりません)", re.IGNORECASE)
_POINTS_YES = re.compile(r"적립\s*(?:할게|할래|해\s*주세요|해주세요|해\s*줘|해줘|하겠|할께|하고\s*싶|부탁)|포인트\s*(?:쌓|적립)|earn\s*points|collect\s*points|积分|ポイントを貯め", re.IGNORECASE)


def _has(actions: list[dict], kind: str) -> bool:
    return any(a.get("type") == kind for a in actions)


def _order_type_from(text: str) -> str | None:
    take = list(_TAKEOUT.finditer(text))
    dine = list(_DINE_IN.finditer(text))
    if take and not dine:
        return "takeout"
    if dine and not take:
        return "dine-in"
    if take and dine and _SWITCH_WORDS.search(text):
        # "매장 말고 포장"처럼 바꿔 말하면 나중에 나온 쪽을 따른다
        return "takeout" if take[-1].start() > dine[-1].start() else "dine-in"
    return None


def _method_from(text: str) -> str | None:
    lowered = text.lower()
    hits = [name for name, kws in _EXPLICIT_METHOD if any(kw.lower() in lowered for kw in kws)]
    if not hits and any(g in lowered for g in _GENERIC_PAY):
        hits = ["pay"]
    # 여러 수단이 함께 나오면("카드 말고 현금") 모호하므로 보완하지 않는다
    return hits[0] if len(hits) == 1 else None


def ensure_actions(
    session_id: str,
    user_input: str,
    screen: str | None,
    cart: list | None,
    snapshot_before: frozenset[str],
    has_items: bool = False,
) -> list[dict]:
    """빠진 핵심 액션을 push_action으로 추가하고, 추가한 액션 목록을 돌려준다."""
    text = (user_input or "").strip()
    if not text:
        return []
    actions = get_actions()
    added: list[dict] = []

    # 1) 주문 유형
    if screen in ("start", "orderType") and not _has(actions, "order_type"):
        value = _order_type_from(text)
        if value:
            added.append({"type": "order_type", "value": value})

    # 2) 결제 시작 — 메뉴 화면에서 "결제할게요"라고 해도 모델이 "결제를 진행할게요"라고 말만 하는 일이 잦다(고정 시나리오
    # 실측 6건). 요청 cart는 비어 올 수 있어서 서버 장바구니 기준(has_items)으로 본다.
    if (screen in ("cart", "menu") and (cart or has_items) and not _has(actions, "start_checkout")
            and "start_checkout" not in snapshot_before and _CHECKOUT_INTENT.search(text)):
        if screen != "cart" and not _has(actions, "navigate"):
            added.append({"type": "navigate", "screen": "cart"})
        added.append({"type": "start_checkout"})
        checkout_progress.mark_done(session_id, "start_checkout")

    # 3) 결제 수단 — 포인트 질문이 이전 턴에 끝난 뒤에만(서버의 순서 규칙을 우회하지 않는다)
    if (screen == "cart" and not _has(actions, "payment_method")
            and "start_checkout" in snapshot_before and "points" in snapshot_before):
        method = _method_from(text)
        if method:
            added.append({"type": "payment_method", "value": method})

    # 3-2) 포인트 적립 여부 — 질문(start_checkout)이 이전 턴에 끝났고 아직 답이 기록되지 않았을 때만
    if (screen == "cart" and "start_checkout" in snapshot_before and "points" not in snapshot_before
            and not _has(actions, "points") and not _has(actions, "points_phone")
            and not _has(actions, "payment_method")):
        if _POINTS_NO.search(text):
            added.append({"type": "points", "value": "no"})
            checkout_progress.mark_done(session_id, "points")
        elif _POINTS_YES.search(text):
            added.append({"type": "points", "value": "yes"})
            checkout_progress.mark_done(session_id, "points")

    # 4) 장바구니 열기 — "장바구니 보여줘"에 모델이 화면 설명만 하고 navigate를 빼먹는 경우
    if (screen not in ("cart", "payment") and cart and not _has(actions, "navigate")
            and _CART_OPEN_RE.search(text) and not _CART_CONTENT_Q_RE.search(text)):
        added.append({"type": "navigate", "screen": "cart"})

    for action in added:
        push_action(action)
    return added
