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
from backend.core.models import MenuItem


_index: FAISS | None = None
_build_lock = asyncio.Lock()


def _format_decimal(v: Decimal) -> float:
    return float(v)


async def _load_documents() -> tuple[list[Document], dict[str, dict[str, Any]]]:
    """DB 에서 메뉴 + 옵션을 읽어 Document 와 메타맵을 만든다."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(MenuItem).options(selectinload(MenuItem.options))
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
        meta = {
            "id": item.id,
            "name_ko": item.name_ko,
            "name_en": item.name_en,
            "base_price": _format_decimal(item.base_price),
            "description": item.description,
            "options": options,
            "is_available": item.is_available,
        }
        meta_map[item.id] = meta

        # 검색 텍스트: 한국어/영어 이름 + 설명 모두 포함
        searchable = (
            f"{item.name_ko} ({item.name_en})\n"
            f"가격: {meta['base_price']}원\n"
            f"{item.description}"
        )
        docs.append(Document(page_content=searchable, metadata={"menu_item_id": item.id}))

    return docs, meta_map


_meta_map: dict[str, dict[str, Any]] = {}


async def _build_index() -> FAISS:
    global _index, _meta_map
    docs, meta_map = await _load_documents()
    _meta_map = meta_map
    embeddings = OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    # FAISS.from_documents 는 동기 호출 → 스레드로 오프로드
    _index = await asyncio.to_thread(FAISS.from_documents, docs, embeddings)
    return _index


async def get_index() -> FAISS:
    global _index
    if _index is None:
        async with _build_lock:
            if _index is None:
                await _build_index()
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
    global _index, _meta_map
    _index = None
    _meta_map = {}
