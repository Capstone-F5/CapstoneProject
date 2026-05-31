"""
메뉴 카탈로그 — frontend/src/data/menuData.js 와 수동 동기화.

⚠️ menuData.js 를 수정하면 이 파일도 함께 업데이트해야 음성 주문이 정상 동작한다.
   (Phase 5 에서 공유 JSON 일원화 검토)
"""
from __future__ import annotations

# ── 메뉴 카탈로그 ──────────────────────────────────────────────────────────
# 각 항목: id, name, price, category, has_set, exclusions
MENU_CATALOG: list[dict] = [
    # 버거 (id 1~12) — 모두 has_set=True
    {"id":  1, "name": "F버거",          "price": 7500, "category": "burger", "has_set": True,  "exclusions": ["없음", "양상추 제외", "양파 제외"]},
    {"id":  2, "name": "불고기버거",     "price": 4500, "category": "burger", "has_set": True,  "exclusions": ["없음", "양상추 제외"]},
    {"id":  3, "name": "더블불고기버거", "price": 6000, "category": "burger", "has_set": True,  "exclusions": ["없음", "양상추 제외"]},
    {"id":  4, "name": "새우버거",       "price": 4800, "category": "burger", "has_set": True,  "exclusions": ["없음", "소스 제외"]},
    {"id":  5, "name": "치즈버거",       "price": 4200, "category": "burger", "has_set": True,  "exclusions": ["없음", "양파 제외"]},
    {"id":  6, "name": "치킨다릿살버거", "price": 6200, "category": "burger", "has_set": True,  "exclusions": ["없음", "양상추 제외"]},
    {"id":  7, "name": "치킨가슴살버거", "price": 5500, "category": "burger", "has_set": True,  "exclusions": ["없음", "양상추 제외"]},
    {"id":  8, "name": "데리버거",       "price": 4000, "category": "burger", "has_set": True,  "exclusions": ["없음"]},
    {"id":  9, "name": "게살버거",       "price": 5000, "category": "burger", "has_set": True,  "exclusions": ["없음", "소스 제외"]},
    {"id": 10, "name": "비건버거",       "price": 6800, "category": "burger", "has_set": True,  "exclusions": ["없음"]},
    {"id": 11, "name": "모짜렐라버거",   "price": 7200, "category": "burger", "has_set": True,  "exclusions": ["없음"]},
    {"id": 12, "name": "그릴드비프버거", "price": 7800, "category": "burger", "has_set": True,  "exclusions": ["없음", "양파 제외"]},
    # 사이드 (id 13~16) — has_set=False
    {"id": 13, "name": "감자튀김",       "price": 2000, "category": "side",   "has_set": False, "exclusions": []},
    {"id": 14, "name": "치즈스틱",       "price": 2000, "category": "side",   "has_set": False, "exclusions": []},
    {"id": 15, "name": "치킨너겟",       "price": 3000, "category": "side",   "has_set": False, "exclusions": []},
    {"id": 16, "name": "양념감자튀김",   "price": 2500, "category": "side",   "has_set": False, "exclusions": []},
    # 음료 (id 17~23) — has_set=False
    # ※ 단품 메뉴명(코카콜라/코카콜라제로/…)과 세트 옵션명(콜라/제로콜라/…)은 별개
    {"id": 17, "name": "코카콜라",       "price": 2000, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 18, "name": "코카콜라제로",   "price": 2000, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 19, "name": "사이다",         "price": 2500, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 20, "name": "사이다제로",     "price": 2000, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 21, "name": "생수",           "price": 1000, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 22, "name": "오렌지주스",     "price": 2500, "category": "drink",  "has_set": False, "exclusions": []},
    {"id": 23, "name": "뽀로로음료수",   "price": 2000, "category": "drink",  "has_set": False, "exclusions": []},
]

# ── 세트 옵션 (menuData.js 의 SET_SIDES / SET_DRINKS / SET_SURCHARGE 와 동기화) ──
SET_SIDES: list[dict] = [
    {"name": "감자튀김",    "extra": 0},
    {"name": "치즈스틱",    "extra": 0},
    {"name": "치킨너겟",    "extra": 0},
    {"name": "양념감자튀김", "extra": 500},
]

SET_DRINKS: list[dict] = [
    {"name": "콜라",       "extra": 0},
    {"name": "제로콜라",   "extra": 0},
    {"name": "사이다",     "extra": 0},
    {"name": "제로사이다", "extra": 0},
    {"name": "생수",       "extra": 0},
    {"name": "뽀로로음료", "extra": 0},
    {"name": "오렌지주스", "extra": 500},
]

SET_SURCHARGE: int = 2000

# ── 빠른 조회용 인덱스 ───────────────────────────────────────────────────────
_CATALOG_BY_ID: dict[int, dict] = {m["id"]: m for m in MENU_CATALOG}


def get_menu(menu_id: int) -> dict | None:
    """ID 로 메뉴 항목 반환. 없으면 None."""
    return _CATALOG_BY_ID.get(menu_id)


def render_vocab_for_stt() -> str:
    """Whisper `prompt` 로 줄 메뉴 어휘 힌트 문자열.

    고유 메뉴명/세트 옵션명을 Whisper 에 미리 알려 전사 정확도를 높인다.
    (prompt 는 도메인 어휘 편향용 — 음성과 같은 언어/문맥으로 제공)
    """
    # 짧은 키오스크 어휘를 먼저, 고유 메뉴명을 뒤에 배치한다.
    # (Whisper prompt 는 마지막 ~224 토큰만 반영하므로 중요한 메뉴명을 끝쪽에 둠)
    names = [m["name"] for m in MENU_CATALOG]
    names += [s["name"] for s in SET_SIDES]
    names += [d["name"] for d in SET_DRINKS]
    seen: set[str] = set()
    uniq = [n for n in names if not (n in seen or seen.add(n))]
    menu_str = ", ".join(uniq)
    return f"햄버거 키오스크 주문. 세트, 단품, 결제. 메뉴: {menu_str}."


def render_catalog_for_prompt() -> str:
    """프롬프트에 삽입할 사람이 읽는 메뉴표 문자열 반환."""
    lines: list[str] = ["[메뉴 카탈로그]"]

    category_labels = {"burger": "버거", "side": "사이드", "drink": "음료"}
    current_cat: str | None = None
    for m in MENU_CATALOG:
        cat = m["category"]
        if cat != current_cat:
            current_cat = cat
            lines.append(f"\n■ {category_labels.get(cat, cat)}")
        excl = "·".join(m["exclusions"]) if m["exclusions"] else "없음"
        set_mark = " [세트가능]" if m["has_set"] else ""
        lines.append(
            f"  ID {m['id']:>2}  {m['name']:<12}  {m['price']:>5}원"
            f"  제외옵션: {excl}{set_mark}"
        )

    lines.append("\n※ 사이드·음료 단품 메뉴(위 목록 ID 13~23)는 단독 주문 가능합니다.")
    lines.append("   세트 사이드·음료 옵션(아래)은 버거 세트 구성 시에만 선택하는 옵션이며 별도 주문 불가.")
    lines.append("\n■ 세트 사이드 옵션 (버거 세트 주문 시 선택)")
    for s in SET_SIDES:
        extra_str = f"+{s['extra']}원" if s["extra"] else "기본"
        lines.append(f"  {s['name']} ({extra_str})")

    lines.append("\n■ 세트 음료 옵션 (버거 세트 주문 시 선택)")
    for d in SET_DRINKS:
        extra_str = f"+{d['extra']}원" if d["extra"] else "기본"
        lines.append(f"  {d['name']} ({extra_str})")

    lines.append(f"\n■ 세트 기본 추가금: {SET_SURCHARGE}원")
    lines.append("  세트 unitPrice = 버거가격 + 세트추가금(2000) + 사이드extra + 음료extra")

    return "\n".join(lines)
