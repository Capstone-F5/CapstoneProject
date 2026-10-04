"""AI를 거치지 않는 규칙 기반 가드 모음 — 판정은 순수 함수로, 기록·거절 예산만 action_context를 쓴다.

LLM이 손님 말과 다르게 행동하거나 음성 인식(STT)이 틀리게 받아 적은 것을 코드로 바로잡는다.
판정에 LLM을 쓰지 않으므로 추가 API 비용이 들지 않고, 단위 테스트(backend/tests/test_guards.py)가 비용 없이 돈다.

모드 (환경변수 GUARD_MODE)
    enforce(기본): 어긋나면 도구가 오류 문자열을 돌려줘 모델이 다시 확인·호출하게 한다
    shadow       : 막지 않고 기록만 한다(오탐 점검용)
    off          : 가드를 끈다

가드가 개입하면 어떤 경우에도 action_context.record_guard로 기록되고, 응답의 `guards` 필드와
대화 로그(backend/logs/conversations/*.jsonl)에 남는다.

들어 있는 것
    fix_stt           STT 오인식 교정
    block             거절 예산(한 턴 2번)을 지키며 도구 거절 메시지를 만든다
    quantity_in 외    발화에서 수량·삭제 의도·질문형을 뽑는 규칙
    correct_reply     "담았습니다"처럼 말만 하고 실제 액션이 없는 응답을 바로잡는다
    is_noise          도메인과 무관한 소리(배경 소리가 말로 인식된 것)를 걸러낸다
"""
from __future__ import annotations

import os
import re

from ai_modules.llm.action_context import bump_guard_rejects, record_guard

GUARD_BUDGET = 2   # 한 턴에 가드가 도구를 거절할 수 있는 최대 횟수. 넘으면 모델에게 더 시키지 않고 손님에게 되묻게 한다.


def guard_mode() -> str:
    mode = os.getenv("GUARD_MODE", "enforce").strip().lower()
    return mode if mode in ("enforce", "shadow", "off") else "enforce"


# ── STT 오인식 교정표 ─────────────────────────────────────────────────────────
# (패턴, 치환). 문맥 조건을 붙여 다른 뜻의 문장을 건드리지 않는다. 항목을 늘릴 때는 tests에 "교정되는 말"과
# "그대로여야 하는 말"을 함께 넣을 것. 메뉴 이름처럼 다른 메뉴로 잘못 바꿀 위험이 있는 것("엠투버거" 등)은
# 자동 교정하지 않는다.
_STT_FIXES: list[tuple[re.Pattern, str]] = [
    # "매장에서 먹을게요"가 "내장에서 먹을게요"로 들어오는 경우(실제 로그). 뒤에 식사·주문 어휘가 올 때만.
    (re.compile(r"내장(?=\s*에서\s*(?:먹|드|식사|할|해|줘|주문))"), "매장"),
    # "매장 식사로 할게요" → "내장 식사로 할게요", "매장이요" → "내장이요"
    (re.compile(r"내장(?=\s*(?:식사|이요|으로\s*(?:할|해|줘|먹)))"), "매장"),
    # "결제"를 "결재"로 받아 적는 흔한 오타. 키오스크에서 "결재"는 결제 말고는 뜻이 없다. 이대로면 결제 의도로 인식되지 않아
    # "결재할게요"가 결제로 이어지지 않는다(2026-10-04 점검: _CHECKOUT_INTENT가 "결재"를 모름).
    (re.compile(r"결재"), "결제"),
    # "단품"의 오인식(실제 로그: "탐풍.", "단풍", "잔툼으로 쏘옥"). 노이즈로 걸러지거나 주문이 안 되는 원인이었다.
    # 말 끝이거나 "으로/이요/줘…"가 바로 붙을 때만 고친다("단풍잎", "단풍 구경" 같은 다른 말은 건드리지 않는다).
    (re.compile(r"(?<![가-힣])(?:단풍|탐풍|탄품|탐품|잔툼|단퓸|단푼|단픔|단폼|담품|단푹)(?=\s*(?:으로|이요|이에요|요|죠|줘|주세요|[.,!?~]|$))"), "단품"),
    # "단품으로 줘"를 "단풍물을 줘"로 받아 적는 경우(2026-10-04 실험, ko+메뉴 프롬프트). "단품"의 오인식 뒤에 "물(을/를)"이 붙고
    # 바로 "줘/주세요" 또는 문장 끝이 올 때만 — "단풍물감" 같은 다른 낱말은 건드리지 않는다.
    (re.compile(r"(?<![가-힣])(?:단풍|탐풍|탄품|탐품|단푼|단픔|단폼|단푹)물(?:을|를|로)?(?=\s*(?:줘|주세요|죠|[.,!?~]|$))"), "단품으로"),
    # "단품으로 줘"를 "단품으로죠"로 받아 적는다(실제 로그 "단품으로죠."와 2026-10-04 실험 "탄품으로죠"). "죠"는 "줘"의 오인식이다.
    (re.compile(r"(?<=단품)으로\s*죠(?=[.,!?~\s]|$)"), "으로 줘"),
    (re.compile(r"(?<=세트)로\s*죠(?=[.,!?~\s]|$)"), "로 줘"),
]


def fix_stt(text: str) -> str:
    """알려진 STT 오인식을 교정한 문장을 돌려준다. 해당 부분만 바꾸고 나머지는 그대로 둔다."""
    if not text:
        return text
    fixed = text
    for pattern, repl in _STT_FIXES:
        fixed = pattern.sub(repl, fixed)
    return fixed


# ── 도구 거절(기록 + 모드 + 예산) ─────────────────────────────────────────────
def block(rule: str, detail: str, message: str) -> str | None:
    """가드 위반을 기록하고, 이 호출을 거절할 문자열을 돌려준다(통과시키면 None).

    - shadow: 기록만 하고 통과(None)
    - enforce: 거절 메시지를 돌려준다. 한 턴에 GUARD_BUDGET번을 넘으면 모델이 같은 도구를 계속 부르며
      반복 한도를 넘기는 일이 없도록, 더 호출하지 말고 손님에게 되묻게 하는 메시지로 바꾼다.
    """
    mode = guard_mode()
    if mode == "off":
        return None
    if mode == "shadow":
        record_guard(rule, detail, blocked=False)
        return None
    record_guard(rule, detail, blocked=True)
    if bump_guard_rejects() > GUARD_BUDGET:
        return ("오류: 같은 요청이 여러 번 거절되었습니다. 더 이상 도구를 호출하지 말고, 손님에게 어떤 메뉴를 "
                "어떻게 바꾸고 싶은지 정중하게 다시 한번 말씀해 달라고 요청하세요.")
    return message


def fix(rule: str, detail: str) -> bool:
    """코드가 값을 바로잡아 그대로 진행해도 되는지 알려 준다(바로잡을 수 있을 때만 호출).
    enforce면 True(고침으로 기록), shadow면 기록만 하고 False, off면 False.
    모델에게 거절하고 다시 시키는 것보다 확실해서, 손님이 말한 대상이 하나로 정해질 때는 이쪽을 쓴다."""
    mode = guard_mode()
    if mode == "off":
        return False
    if mode == "shadow":
        record_guard(rule, detail, blocked=False, fixed=False)
        return False
    record_guard(rule, detail, blocked=False, fixed=True)
    return True


# ── 발화에서 뽑는 규칙 ────────────────────────────────────────────────────────
_HANGUL = re.compile(r"[가-힣]")
_KO_NUM = {"하나": 1, "한": 1, "둘": 2, "두": 2, "셋": 3, "세": 3, "넷": 4, "네": 4,
           "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10}

def has_hangul(text: str) -> bool:
    return bool(_HANGUL.search(text or ""))


def quantity_in(text: str) -> int | None:
    """발화에 수량 표현이 정확히 하나(같은 값)만 있으면 그 수를, 없거나 여러 값이면 None을 돌려준다."""
    compact = re.sub(r"\s+", "", text or "")
    found: set[int] = set()
    # "열어줘"의 '열', "인터넷"의 '넷'처럼 다른 낱말에 들어 있는 글자를 수로 세지 않도록, 하나를 뺀 나머지는
    # 단위(개·잔 …)가 붙어 있을 때만 수량으로 본다.
    for m in re.finditer(r"(\d+)(?:개|잔|조각|판|명)|(하나)|(둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열)(?:개|잔)|(한|두|세|네)(?:개|잔|조각|판)", compact):
        if m.group(1):
            found.add(int(m.group(1)))
        else:
            found.add(_KO_NUM[m.group(2) or m.group(3) or m.group(4)])
    return next(iter(found)) if len(found) == 1 else None


_REMOVE_INTENT = re.compile(r"빼|삭제|취소|지워|지우|없애|제거|말고|대신|바꿔|바꾸|변경|그만|안\s*할|안할|필요\s*없|됐|아니|다시|수정|줄여|줄이|남겨|남기")
_REDUCE_ONE = re.compile(r"(?:하나|한\s*개|1\s*개)\s*만\s*(?:빼|줄|취소|삭제|지워)|(?:한\s*개|하나|1\s*개)\s*(?:빼|줄여|줄이)|(?:하나|한\s*개)\s*취소")
_QUESTION = re.compile(r"얼마|뭐예요|뭔가요|뭐야|뭐가|있어요\s*\?|있나요|알려|추천|어떤|\?")
_ORDER_VERB = re.compile(r"줘|주세요|주라|주실|담아|담을|추가|할게|할래|주문|먹을게|부탁|바꿔|변경")
_SINGLE_WORDS = re.compile(r"단품|그냥|버거만|단독|single|単品|单品", re.IGNORECASE)
_SET_WORDS = re.compile(r"세트|set\b|セット|套餐", re.IGNORECASE)
_CONFIRM = re.compile(r"^\W*(?:어\W*)?(?:네|예|응|어|그래|맞아|맞아요|좋아|좋아요|그걸로|그거|그렇게|오케이|ok|okay)", re.IGNORECASE)


_ADD_VERB = re.compile(r"담아|추가해|추가할|주세요|줘|주라|주실")
_CHANGE_VERB = re.compile(r"바꿔|바꾸|변경|수정|로\s*해|으로\s*해|로\s*줄|만\s*주|말고|대신")


def has_add_verb(text: str) -> bool:
    return bool(_ADD_VERB.search(text or ""))


def has_change_verb(text: str) -> bool:
    """"바꿔줘/…로 해줘"처럼 수량을 그 값으로 정하라는 뜻이 분명한 표현. ("두 개 더 줘"는 더하라는 뜻이라 넣지 않는다)"""
    return bool(_CHANGE_VERB.search(text or ""))


def has_remove_intent(text: str) -> bool:
    return bool(_REMOVE_INTENT.search(text or ""))


def wants_reduce_one(text: str) -> bool:
    return bool(_REDUCE_ONE.search(re.sub(r"\s+", " ", text or "")))


def is_question_only(text: str) -> bool:
    """질문형이고 주문 동사는 없는 발화("콜라는 얼마예요?")."""
    return bool(_QUESTION.search(text or "")) and not _ORDER_VERB.search(text or "")


def mentions_single(text: str) -> bool:
    return bool(_SINGLE_WORDS.search(text or ""))


def mentions_set(text: str) -> bool:
    return bool(_SET_WORDS.search(text or ""))


def is_confirmation(text: str) -> bool:
    return bool(_CONFIRM.search((text or "").strip()))


def spoken_in(text: str, *names: str) -> bool:
    """이름 중 하나라도(공백·괄호 제거 후) 발화에 들어 있으면 True."""
    compact = re.sub(r"\s+", "", text or "")
    for n in names:
        key = re.sub(r"\s+", "", re.sub(r"\(.*?\)", "", n or ""))
        if len(key) >= 2 and key in compact:
            return True
        # DB 이름이 말한 것보다 한 글자 길 수 있다("뽀로로 음료수" ← "뽀로로음료로 줘")
        if len(key) >= 5 and key[:-1] in compact:
            return True
    return False


# ── 응답 ↔ 액션 일치 ──────────────────────────────────────────────────────────
# 과거형("담았습니다")뿐 아니라 하겠다는 약속("담겠습니다")도 포함한다 — 약속만 하고 도구를 안 부르는 사고가 실제 로그에 있었다
_CLAIM_ADD = re.compile(r"담았(?:습니다|어요|죠)|추가했(?:습니다|어요)|담겠습니다|담아\s*드리겠습니다|추가하겠습니다|추가해\s*드리겠습니다")
_CLAIM_REMOVE = re.compile(r"삭제했(?:습니다|어요)|삭제되었(?:습니다|어요)|뺐(?:습니다|어요)|제거했(?:습니다|어요)|취소했(?:습니다|어요)|취소되었(?:습니다|어요)|지웠(?:습니다|어요)")
_CLAIM_CHANGE = re.compile(r"변경했(?:습니다|어요)|변경되었(?:습니다|어요)|바꿨(?:습니다|어요)|바꿔\s*드렸")

_FULFILL = {
    "add": {"add_item", "update_item"},
    "remove": {"remove_item", "clear_cart", "update_item"},
    "change": None,   # 변경 계열은 종류가 많아(옵션·수량·결제수단·주문유형·언어 …) 어떤 액션이든 있으면 이행으로 본다
}
_UNFULFILLED = {
    "add": "죄송합니다, 아직 장바구니에 담지 못했어요. 메뉴를 한 번 더 말씀해 주세요.",
    "remove": "죄송합니다, 아직 장바구니에서 빼지 못했어요. 어떤 메뉴인지 한 번 더 말씀해 주세요.",
    "change": "죄송합니다, 아직 변경하지 못했어요. 어떻게 바꿀지 한 번 더 말씀해 주세요.",
}


UNFULFILLED_REPLIES = frozenset(_UNFULFILLED.values())


def claims_add(output: str) -> bool:
    """응답이 "담았습니다/추가했습니다"라고 주장하는가."""
    return bool(output) and bool(_CLAIM_ADD.search(output))


def correct_reply(output: str, action_types: list[str]) -> str | None:
    """응답이 "담았습니다/삭제했습니다/변경했습니다"라고 하는데 이번 턴에 그에 맞는 액션이 없으면 안전한 문구를
    돌려준다. 문제가 없으면 None. (기록은 호출한 쪽이 한다)"""
    if not output or not has_hangul(output):
        return None
    have = set(action_types)
    for kind, pattern in (("add", _CLAIM_ADD), ("remove", _CLAIM_REMOVE), ("change", _CLAIM_CHANGE)):
        fulfill = _FULFILL[kind]
        if pattern.search(output) and not (have if fulfill is None else have & fulfill):
            return _UNFULFILLED[kind]
    return None


# ── 알아들을 수 없는 입력 ─────────────────────────────────────────────────────
# 도메인 어휘가 하나도 없고 짧은 한국어 문장이면, 배경 소리·음악이 말로 인식된 것으로 보고 LLM을 부르지 않는다.
# 어휘는 넉넉하게 잡는다(놓치면 LLM이 처리하므로 손해가 적고, 잘못 걸러내면 손님이 불편하다).
_DOMAIN = re.compile(
    r"메뉴|버거|세트|단품|사이드|음료|음식|감자|튀김|너겟|치즈|스틱|콜라|사이다|생수|주스|물|커피|샐러드|코울슬로|콘|"
    r"불고기|새우|비건|치킨|게살|비프|모짜렐라|데리|더블|F버거|주문|담|줘|주세요|주실|추가|빼|삭제|취소|지워|바꿔|변경|수정|"
    r"하나|둘|셋|넷|한\s*개|두\s*개|세\s*개|개|잔|"
    r"결제|계산|카드|현금|페이|간편|영수증|포인트|적립|번호|전화|"
    r"매장|포장|먹|가져|테이크|여기|"
    r"장바구니|화면|뒤로|처음|다음|이전|페이지|"
    r"네|예|응|어|아니|그래|맞|좋|괜찮|됐|그거|이거|저거|그걸|이걸|그냥|잠깐|잠시|다시|아까|방금|"
    r"뭐|뭘|뭔|어떤|어디|얼마|가격|추천|인기|맛있|알레르기|알러지|칼로리|매운|"
    r"영어|일본어|중국어|한국어|언어|카메라|제스처|음성|소리|볼륨|"
    r"도와|도움|안내|설명|읽어|들려|말해|알려|보여|열어|닫아|꺼|켜|"
    r"안녕|감사|고마|죄송|미안|수고|여보세요|저기|저요|있어|없어|주문할|할게|할래|하고|해줘|해\s*주|"
    r"드릴|드실|먹을|마실|시킬|원해|원하|필요|부탁|"
    r"[0-9]|일이삼사|공일공|천원|원\b"
)
NOISE_REPLY = {
    "ko": "잘 못 들었어요. 다시 한번 말씀해 주세요.",
    "en": "Sorry, I didn't catch that. Could you say it again?",
    "ja": "すみません、聞き取れませんでした。もう一度お願いします。",
    "zh": "抱歉，我没听清。请再说一遍。",
}


def is_noise(text: str) -> bool:
    """한국어 문장이면서 도메인 어휘가 전혀 없고 짧은 경우만 True. 외국어·긴 문장·숫자가 있으면 False."""
    t = (text or "").strip()
    if not t or not has_hangul(t):
        return False
    compact = re.sub(r"\s+", "", t)
    if len(compact) > 40:
        return False
    return not _DOMAIN.search(t)
