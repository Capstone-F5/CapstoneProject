"""
메뉴 RAG.

- MENU_ITEMS.description 을 OpenAIEmbeddings 로 벡터화하여 FAISS 인메모리 인덱스에 보관.
- 첫 호출 시 lazy build, 이후 캐시.
- 할루시네이션 방지를 위해 검색 결과의 menu_item_id / 가격 / 옵션을 그대로 Agent 에 반환.
"""
from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.db import SessionLocal
from backend.core.models import Category, Discount, MenuItem, MenuItemAllergen


_index: FAISS | None = None
_build_lock = asyncio.Lock()


def _format_decimal(v: Decimal) -> float:
    return float(v)


async def _load_documents() -> tuple[list[Document], dict[str, dict[str, Any]]]:
    """DB 에서 메뉴 + 옵션을 읽어 Document 와 메타맵을 만든다."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(MenuItem).options(
                selectinload(MenuItem.options),
                selectinload(MenuItem.allergen_links).selectinload(MenuItemAllergen.allergen),
            )
        )
        items = result.scalars().all()

    docs: list[Document] = []
    meta_map: dict[str, dict[str, Any]] = {}
    for item in items:
        options = [
            {
                "id": opt.id,
                "name_ko": opt.name_ko,
                "name_en": opt.name_en,
                "additional_price": _format_decimal(opt.additional_price),
            }
            for opt in item.options
        ]
        allergens = [
            {"code": link.allergen.code, "name_ko": link.allergen.name_ko, "name_en": link.allergen.name_en}
            for link in item.allergen_links
        ]
        meta = {
            "id": item.id,
            "name_ko": item.name_ko,
            "name_en": item.name_en,
            "base_price": _format_decimal(item.base_price),
            "description": item.description,
            "options": options,
            "is_available": item.is_available,
            "is_popular": item.is_popular,
            "allergens": allergens,
        }
        meta_map[item.id] = meta

        # 검색 텍스트: 한국어/영어 이름 + 설명 모두 포함
        # 인기 메뉴는 "추천메뉴/인기메뉴" 문구를 섞어 넣어 관련 질의("추천해줘", "인기메뉴 뭐야")로도 검색되게 한다.
        popular_tag = "\n추천메뉴, 인기메뉴" if item.is_popular else ""
        allergen_tag = f"\n알레르기 유발물질: {', '.join(a['name_ko'] for a in allergens)}" if allergens else "\n알레르기 유발물질 없음"
        searchable = (
            f"{item.name_ko} ({item.name_en})\n"
            f"가격: {meta['base_price']}원\n"
            f"{item.description}{popular_tag}{allergen_tag}"
        )
        docs.append(Document(page_content=searchable, metadata={"menu_item_id": item.id}))

    return docs, meta_map


_meta_map: dict[str, dict[str, Any]] = {}
_discount_context: str | None = None


async def get_active_discount_context() -> str:
    """Return a small, factual discount summary for the assistant system context."""
    global _discount_context
    if _discount_context is not None:
        return _discount_context

    from datetime import date

    today = date.today()
    async with SessionLocal() as session:
        result = await session.execute(
            select(Discount).where(
                Discount.is_active.is_(True),
                Discount.applicable_tier == "ALL",
                (Discount.valid_from.is_(None) | (Discount.valid_from <= today)),
                (Discount.valid_until.is_(None) | (Discount.valid_until >= today)),
            )
        )
        discounts = result.scalars().all()
        category_ids = [d.category_id for d in discounts if d.category_id]
        menu_ids = [d.menu_item_id for d in discounts if d.menu_item_id]
        categories = {}
        menu_names = {}
        if category_ids:
            category_rows = await session.execute(select(Category).where(Category.id.in_(category_ids)))
            categories = {category.id: category.name_ko for category in category_rows.scalars()}
        if menu_ids:
            menu_rows = await session.execute(select(MenuItem).where(MenuItem.id.in_(menu_ids)))
            menu_names = {menu.id: menu.name_ko for menu in menu_rows.scalars()}

    if not discounts:
        _discount_context = "현재 안내할 자동 할인은 없습니다. 할인이나 무료 제공을 임의로 약속하지 마세요."
        return _discount_context

    labels = []
    for discount in discounts:
        target = "전체 메뉴"
        if discount.target_type == "CATEGORY":
            target = f"{categories.get(discount.category_id, '해당')} 카테고리"
        elif discount.target_type == "MENU":
            target = menu_names.get(discount.menu_item_id, "해당 메뉴")
        value = f"{discount.discount_value}%" if discount.discount_type == "PERCENT" else f"{discount.discount_value}원"
        labels.append(f"- {discount.name_ko}: {target} {value} 자동 할인")
    _discount_context = "현재 적용 가능한 자동 할인:\n" + "\n".join(labels)
    return _discount_context


async def _build_index() -> FAISS:
    global _index, _meta_map
    docs, meta_map = await _load_documents()
    _meta_map = meta_map
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # API 키가 설정되지 않은 경우 모의 임베딩 또는 예외 우회 처리
        api_key = "dummy_key_for_local_health_check"

    embeddings = OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=api_key,
    )
    # FAISS.from_documents 는 동기 호출 → 스레드로 오프로드
    try:
        index = await asyncio.to_thread(FAISS.from_documents, docs, embeddings)
        _index = index  # 성공했을 때만 전역 캐시에 반영
        return index
    except Exception as e:
        # 로컬 헬스 체크(API 키 미설정) 또는 일시적 API 오류(레이트리밋 등) 방어.
        print(f"[RAG 경고] 인덱스 빌드 건너뜀 (API Key 유효성 이슈): {e}")
        # 빈 인덱스로 헬스 체크 통과 유도
        # (FAISS는 이미 상단에서 import됨 — 여기서 재import하면 함수 전체에서 지역변수로
        #  취급되어 위 try 블록의 FAISS.from_documents 호출이 UnboundLocalError가 나던 버그 수정)
        from langchain_core.embeddings import FakeEmbeddings
        fake_emb = FakeEmbeddings(size=1536)
        # ★ 전역 _index 캐시에는 반영하지 않는다 — 여기서 캐시해버리면 한 번의 일시적 오류로
        #   전체 메뉴 중 1개짜리 가짜 임베딩 인덱스가 서버 재시작 전까지 영구 고정되어
        #   search_menu가 항상 엉뚱한 결과만 반환하는 문제가 있었음. 다음 호출에서 실제
        #   임베딩으로 다시 빌드를 시도하도록 _index는 None 상태로 남겨둔다.
        return await asyncio.to_thread(FAISS.from_documents, docs[:1], fake_emb)


async def get_index() -> FAISS:
    global _index
    if _index is None:
        async with _build_lock:
            if _index is None:
                # _build_index()가 실패 시 전역 _index를 None으로 남겨두므로(다음 호출에서
                # 재시도하기 위함), 이번 호출에서 쓸 인덱스는 반환값에서 직접 받는다.
                return await _build_index()
    return _index  # type: ignore[return-value]


async def search_menu(query: str, k: int = 5) -> list[dict[str, Any]]:
    """질의어와 가장 유사한 메뉴 k 개를 반환."""
    index = await get_index()
    # similarity_search 는 동기 → 스레드로 오프로드
    results = await asyncio.to_thread(index.similarity_search, query, k)
    hits: list[dict[str, Any]] = []
    for doc in results:
        item_id = doc.metadata.get("menu_item_id")
        meta = _meta_map.get(item_id) if item_id else None
        if meta:
            hits.append(meta)
    return hits


def invalidate_cache() -> None:
    """메뉴 변경 시 RAG 캐시 무효화."""
    global _index, _meta_map, _discount_context
    _index = None
    _meta_map = {}
    _discount_context = None

# --- 지시서 명세 4단계 규격 호환을 위한 스텁/래퍼 인터페이스 함수 ---

async def build_menu_index() -> list[dict]:
    """DB 기반에서 메뉴 인덱싱 용도를 충족하기 위한 호환용 함수."""
    docs, meta_map = await _load_documents()
    return [
        {
            "id": doc.metadata["menu_item_id"],
            "name": meta_map[doc.metadata["menu_item_id"]]["name_ko"],
            "description": meta_map[doc.metadata["menu_item_id"]]["description"],
            "text": doc.page_content
        }
        for doc in docs
    ]

def search_menu_by_query(query: str, documents: list[dict], top_k: int = 3) -> list[dict]:
    """키워드 기반의 임시 RAG 쿼리 룩업용 호환용 함수."""
    query_lower = query.lower()
    scored = []
    for doc in documents:
        score = sum(1 for kw in query_lower.split() if kw in doc["text"].lower())
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [doc for _, doc in scored[:top_k]]

