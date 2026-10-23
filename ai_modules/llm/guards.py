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
    # "단품으로 줘", "세트로 줘", "생수로 줘", "콜라로 줘", "양념감자튀김으로 줘", "카드로 줘" 등을 "~(으)로죠"로 받아 적는 오인식
    # (실제 로그: "세트로죠.", "생수로죠. 생수로죠.", "단품으로죠." 및 2026-10-04 실험 "탄품으로죠").
    # 의문사("어디로죠", "언제로죠", "누구로죠")는 제외하고 한글/숫자 뒤의 "(으)로죠"가 절·문장 끝에 올 때 "(으)로 줘"로 교정한다.
    (re.compile(r"(?<!어디)(?<!언제)(?<!누구)(?<=[가-힣0-9])(으로|로)\s*죠(?=[.,!?~\s]|$)"), r"\1 줘"),
    # "결제할게"를 "설치할게"로 받아 적는 오인식(실제 로그: "설치할게." 직후 "결제할게." 재발화)
    (re.compile(r"(?<![가-힣])설치(?=\s*(?:할게|할래|해\s*줘|해줘|하겠|할게요|해주세요|[.,!?~]|$))"), "결제"),
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
_REFUSAL_ONLY = re.compile(
    r"^[\s.,!?~…]*(?:아니|아니요|아니오|아뇨|아닙니다|없어|없어요|없습니다|됐어|됐어요|됐습니다|"
    r"괜찮아|괜찮아요|괜찮습니다|그만|끝|충분해|충분해요|필요\s*없(?:어|어요|습니다)|"
    r"더\s*없(?:어|어요|습니다)|안\s*(?:할래|할게|할게요|해요|해)|싫어|싫어요|"
    r"no|nope|nothing|that'?s\s*all|いいえ|大丈夫|結構です|不要|不用了)"
    r"(?:[\s.,!?~…]+(?:아니|아니요|아뇨|괜찮아|괜찮아요|됐어|됐어요|없어|없어요|그만|끝|고마워|감사합니다))*[\s.,!?~…]*$",
    re.IGNORECASE,
)


_ADD_VERB = re.compile(r"담아|추가해|추가할|주세요|줘|주라|주실")
_CHANGE_VERB = re.compile(r"바꿔|바꾸|변경|수정|로\s*해|으로\s*해|로\s*줄|만\s*주|말고|대신")


def has_add_verb(text: str) -> bool:
    return bool(_ADD_VERB.search(text or ""))


def has_change_verb(text: str) -> bool:
    """"바꿔줘/…로 해줘"처럼 수량을 그 값으로 정하라는 뜻이 분명한 표현. ("두 개 더 줘"는 더하라는 뜻이라 넣지 않는다)"""
    return bool(_CHANGE_VERB.search(text or ""))


def has_remove_intent(text: str) -> bool:
    return bool(_REMOVE_INTENT.search(text or ""))


def is_refusal_only(text: str) -> bool:
    """"아니", "아니요", "없어요", "됐어요", "그만"처럼 다른 메뉴나 동작 언급 없이 거절·종료만 답한 발화인가."""
    return bool(_REFUSAL_ONLY.match((text or "").strip()))


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
_CLAIM_ORDER_COMPLETE = re.compile(r"(?:주문|결제)이\s*완료되었(?:습니다|어요)")

_FULFILL = {
    "add": {"add_item", "update_item"},
    "remove": {"remove_item", "clear_cart", "update_item"},
    "change": None,   # 변경 계열은 종류가 많아(옵션·수량·결제수단·주문유형·언어 …) 어떤 액션이든 있으면 이행으로 본다
}
_UNFULFILLED = {
    "add": "죄송합니다, 아직 장바구니에 담지 못했어요. 메뉴를 한 번 더 말씀해 주세요.",
    "remove": "죄송합니다, 아직 장바구니에서 빼지 못했어요. 어떤 메뉴인지 한 번 더 말씀해 주세요.",
    "change": "죄송합니다, 아직 변경하지 못했어요. 어떻게 바꿀지 한 번 더 말씀해 주세요.",
    "order_complete": "더 추가하실 메뉴가 없으시면 결제를 도와드릴까요?",
}


UNFULFILLED_REPLIES = frozenset(_UNFULFILLED.values())


def claims_add(output: str) -> bool:
    """응답이 "담았습니다/추가했습니다"라고 주장하는가."""
    return bool(output) and bool(_CLAIM_ADD.search(output))


def correct_reply(output: str, action_types: list[str]) -> str | None:
    """응답이 "담았습니다/삭제했습니다/변경했습니다"라고 하는데 이번 턴에 그에 맞는 액션이 없으면 안전한 문구를
    돌려준다. 또한 결제 승인 전인데 모델이 임의로 "주문이 완료되었습니다/결제가 완료되었습니다"라고 말하는 것도 바로잡는다."""
    if not output or not has_hangul(output):
        return None
    if _CLAIM_ORDER_COMPLETE.search(output):
        return _UNFULFILLED["order_complete"]
    have = set(action_types)
    for kind, pattern in (("add", _CLAIM_ADD), ("remove", _CLAIM_REMOVE), ("change", _CLAIM_CHANGE)):
        fulfill = _FULFILL[kind]
        if pattern.search(output) and not (have if fulfill is None else have & fulfill):
            return _UNFULFILLED[kind]
    return None


# ── 알아들을 수 없는 입력 (배경 소음 · 매장 음악 · 주변 대화 차단) ───────────────
# 1) 강한 키오스크 도메인 어휘: 문장 길이와 무관하게 이 어휘가 들어 있으면 유효 발화로 인정한다.
#    주의: '어', '네', '예', '응', '좋', '맞', '됐', '물', '콘', '개', '잔' 같은 1글자 조각을 경계 없이 넣으면
#    "어제 영화 봤어", "오늘 날씨 좋다", "눈물이 나네" 같은 주변 대화와 노래 가사가 전부 통과하므로 반드시 경계를 둔다.
_DOMAIN = re.compile(
    r"메뉴|버거|햄버거|세트|단품|사이드|음료|음식|감자|튀김|포테이토|너겟|치즈|스틱|콜라|사이다|생수|주스|오렌지|뽀로로|커피|샐러드|코울슬로|"
    r"(?<![가-힣])콘(?=\s*(?:샐러드|하나|한|두|세|\d+|개|추가|주|달|이요|요|[.,!?~]|$))|"
    r"(?<![가-힣])물(?=\s*(?:하나|한|두|세|네|다섯|\d+|잔|병|개|주|달|더|빼|말고|로|으로|이요|요|은|는|을|를|도|[.,!?~]|$))|"
    r"불고기|새우|비건|치킨|게살|비프|모짜렐라|데리|더블|F\s*버거|에프\s*버거|양파|피클|양상추|소스|패티|토마토|"
    r"주문|시작|장바구니|카트|담아|담을|담기|추가|삭제|취소|지워|지우|바꿔|바꾸|변경|수정|"
    r"빼\s*(?:줘|주세요|주실|달라|갈게|주라)|주세요|주실|드릴|드실|(?<![가-힣])(?:시키|시킬|시켜\s*(?:줘|주|요|먹))|"
    r"(?:하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열|한|두|세|네|\d+)\s*(?:개|잔|병|조각|판|세트)|"
    r"(?:하나|한\s*개|두\s*개|세\s*개)\s*(?:만|더|줘|주|만요)|"
    r"결제|계산|카드|현금|페이|간편|영수증|포인트|적립|할인|행사|쿠폰|번호|전화|"
    r"매장|포장|테이크\s*아웃|먹고\s*갈|가져\s*갈|여기서\s*먹|먹을\s*것\s*같|못\s*먹|"
    r"화면|페이지|뒤로|(?<![가-힣])(?:처음|다음|이전)(?=\s*(?:으로|로|화면|페이지|단계|거|걸로|[.,!?~]|$))|"
    r"얼마|가격|추천|인기|맛있|알레르기|알러지|칼로리|영양|매운|"
    r"영어|일본어|중국어|한국어|언어|카메라|제스처|손동작|음성|목소리\s*(?:키워|줄여|크게|작게|안\s*들려)|볼륨|"
    r"도와|도움|안내|설명|읽어|들려|알려|보여|열어\s*줘|닫아\s*줘|꺼\s*줘|켜\s*줘|"
    r"안녕|감사|고마워|고맙|죄송|미안|여보세요|화장실|나\s*뭐\s*해|"
    r"(?:이거|그거|저거|이걸|그걸|저걸|첫\s*번째|두\s*번째|세\s*번째)\s*(?:로|으로)?\s*(?:줘|주세요|할게|할래|담아|해\s*줘)|"
    r"(?:그렇게|이대로|그대로)\s*(?:줘|주세요|할게|할래|해\s*줘)|"
    r"(?:[0-9]+|백|천|만|십)\s*원|일이삼사|공일공|01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}|010",
    re.IGNORECASE,
)

# 2) 짧은 긍·부정/지시/호응/수량 응답: 키오스크 질문에 짧게 답하는 경우("네", "하나", "어, 그래 맞아.", "아니 괜찮아", "잠깐만" 등).
#    주변 사람들의 긴 대화("응 그래서 내가 어제 말했잖아")가 통과하지 않도록 문장 전체가 짧은 호응/수량 표현으로만 이루어진 경우만 인정한다.
_SHORT_REPLY_RE = re.compile(
    r"^[\s.,!?~]*("
    r"네|예|응|어|그래|그래요|맞아|맞아요|좋아|좋아요|괜찮아|괜찮아요|됐어|됐어요|"
    r"아니|아니요|아뇨|싫어|싫어요|됐습니다|아닙니다|맞습니다|좋습니다|"
    r"오케이|ok|okay|그거|이거|저거|그걸로|이걸로|그냥|잠깐|잠깐만|잠시만|다시|방금\s*거|"
    r"하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열|한\s*개|두\s*개|세\s*개|네\s*개|\d+\s*(?:번|개|잔|원)?"
    r")(?:[\s.,!?~]+("
    r"네|예|응|어|그래|그래요|맞아|맞아요|좋아|좋아요|괜찮아|괜찮아요|됐어|됐어요|"
    r"아니|아니요|아뇨|오케이|ok|okay|그거|이거|저거|그걸로|이걸로|줘|주세요|할게|할래|할게요|해줘|해주세요|요|이요"
    r"))*[\s.,!?~]*$",
    re.IGNORECASE,
)

# 3) 대기 화면(start)에서 지나가는 행인의 단순 추임새("응", "어", "그거", "좋아", "맞아")만으로 화면이 넘어가지 않도록 차단할 패턴
_START_BARE_BACKCHANNEL_RE = re.compile(
    r"^[\s.,!?~]*(?:응|어|음|그거|이거|저거|아까|방금|좋아|좋아요|맞아|맞아요|그래|그래요)[\s.,!?~]*$"
)

# 4) 외국어(영·일·중) 발화용 키오스크 도메인 어휘 — 매장 팝송(영어/J-POP 가사)이 그대로 LLM에 넘어가는 것을 차단
_FOREIGN_DOMAIN_RE = re.compile(
    r"\b(?:burger|cheeseburger|hamburger|menu|order|single|side|drink|coke|cola|sprite|cider|water|juice|fries|potato|nugget|"
    r"set(?:\s+menu|\s+meal|\s+please|\b(?=\s*[.,!?~]*$))|"
    r"cheese|stick|coleslaw|salad|bulgogi|shrimp|vegan|chicken|crab|beef|mozzarella|teriyaki|double|"
    r"add|remove|delete|cancel|change|clear|cart|pay|card|cash|point|receipt|coupon|discount|"
    r"for\s+here|dine\s*in|take\s*out|to\s*go|price|how\s*much|recommend|popular|allergy|calorie|spicy|"
    r"english|korean|japanese|chinese|language|camera|gesture|voice|screen|back|next|start|help|restroom|bathroom|toilet|"
    r"give\s+me|please|yes|yeah|yep|no|nope|ok|okay|sure|hello|hi|hey|thank|thanks|sorry|excuse)\b|"
    r"バーガー|チーズ|불고기|セット|単品|メニュー|注文|サイド|ドリンク|コーラ|ポテト|ナゲット|水|会計|支払|カード|現金|ポイント|店内|持ち帰り|テイクアウト|はい|いいえ|お願い|ください|ありがとう|すみません|こんにちは|"
    r"汉堡|漢堡|套餐|单品|單品|菜单|菜單|点餐|點餐|可乐|可樂|薯条|薯條|鸡块|雞塊|芝士|奶酪|水|结账|結賬|支付|刷卡|现金|現金|积分|積分|堂食|打包|外带|你好|谢谢|謝謝|再来|不要|好的|是的|可以",
    re.IGNORECASE,
)

NOISE_REPLY = {
    "ko": "잘 못 들었어요. 다시 한번 말씀해 주세요.",
    "en": "Sorry, I didn't catch that. Could you say it again?",
    "ja": "すみません、聞き取れませんでした。もう一度お願いします。",
    "zh": "抱歉，我没听清。请再说一遍。",
}


def is_noise(text: str, *, screen: str | None = None) -> bool:
    """배경 소음·매장 음악 가사·주변 테이블의 일상 대화 등 키오스크 도메인과 무관한 발화이면 True.

    - 기존 40자 상한을 제거하여 도메인 어휘가 없는 긴 노래 가사나 주변 수다도 차단한다.
    - 대기 화면(screen='start')에서는 지나가는 사람의 단순 추임새("응", "어")만 들어온 경우도 차단한다.
    """
    t = (text or "").strip()
    if not t:
        return True
    compact = re.sub(r"\s+", "", t)
    if not re.search(r"[0-9a-zA-Z가-힣぀-ヿ一-鿿]", compact):
        return True

    # 대기 화면에서 단순 1단어 추임새("응", "어", "그거")는 주변 행인의 말로 보고 무시
    if screen == "start" and _START_BARE_BACKCHANNEL_RE.match(t):
        return True

    # 전화번호("010-8251-0345")·숫자 단답("1", "2")·"OK" 등은 한글이 없어도 _DOMAIN / _SHORT_REPLY_RE로 먼저 통과시킨다
    if _DOMAIN.search(t):
        return False
    if len(compact) <= 16 and _SHORT_REPLY_RE.match(t):
        return False

    if has_hangul(t):
        return True

    # 한글이 없는 외국어(영어·일본어·중국어) 발화: 도메인/인사/응답 어휘가 하나도 없으면 배경 팝송·잡음으로 판단
    return not bool(_FOREIGN_DOMAIN_RE.search(t))
