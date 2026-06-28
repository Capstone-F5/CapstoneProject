"""
DB API 연동 클라이언트 (stub)
docs/AI_파트_작업명세.md 참고하여 구현할 것.
"""
import httpx
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


async def get_menu() -> dict:
    # TODO: GET /api/menu
    raise NotImplementedError


async def add_cart_item(session_id: str, menu_item_id: str, quantity: int, options: list) -> dict:
    # TODO: POST /api/cart/{session_id}/items
    raise NotImplementedError


async def get_cart(session_id: str) -> dict:
    # TODO: GET /api/cart/{session_id}/items
    raise NotImplementedError


async def remove_cart_item(session_id: str, item_id: str) -> None:
    # TODO: DELETE /api/cart/{session_id}/items/{item_id}
    raise NotImplementedError


async def create_order(session_id: str, user_phone: str = None) -> dict:
    # TODO: POST /api/orders
    raise NotImplementedError


async def get_user_points(phone: str) -> dict:
    # TODO: GET /api/user/points/{phone}
    raise NotImplementedError
