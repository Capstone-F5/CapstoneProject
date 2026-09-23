import sys
import os
import importlib
import logging
import time

# 프로젝트 루트를 경로에 추가 (ai_modules 접근용)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv

load_dotenv(os.path.join(_project_root, ".env"))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.cart_logging import cart_logger

# 제스처/수집 라우터는 mediapipe 의존 — 환경에 따라 로드 실패할 수 있으므로 가드.
# 모듈별로 따로 감싼다: 하나가 실패해도 나머지는 등록되어야 한다.
# (mediapipe가 레거시 solutions API를 제거했을 때 gesture_ws 하나 때문에
#  mediapipe와 무관한 approach_ws까지 통째로 내려간 적이 있음)
_cv_routers = []
_cv_load_errors: dict[str, str] = {}

for _cv_name, _cv_module in (
    ("gesture", "api.gesture_ws"),
    ("collect", "api.collect"),
    ("approach", "api.approach_ws"),
):
    try:
        _cv_routers.append(importlib.import_module(_cv_module).router)
    except Exception as _e:  # noqa: BLE001
        _cv_load_errors[_cv_name] = f"{type(_e).__name__}: {_e}"

from api.stt import router as stt_router
from api.tts import router as tts_router
from api.llm import router as llm_router
from api.menu import router as menu_router
from api.cart import router as cart_router
from api.order import router as order_router
from api.discounts import router as discounts_router
from api.payment import router as payment_router
from api.user import router as user_router
from api.settings import router as settings_router
from api.hardware import router as hardware_router
from api.diagnostics import router as diagnostics_router
from api.admin.auth import router as admin_auth_router
from api.admin.menu import router as admin_menu_router
from api.admin.users import router as admin_users_router
from api.admin.orders import router as admin_orders_router
from api.admin.coupons import router as admin_coupons_router
from api.admin.discounts import router as admin_discounts_router
from api.admin.payments import router as admin_payments_router
from api.admin.stats import router as admin_stats_router

from core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Kiosk Backend", lifespan=lifespan)


@app.middleware("http")
async def log_cart_api_requests(request, call_next):
    if not request.url.path.startswith("/api/cart/"):
        return await call_next(request)

    started = time.perf_counter()
    client = request.client.host if request.client else "unknown"
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        level = (
            logging.ERROR if response.status_code >= 500
            else logging.WARNING if response.status_code >= 400
            else logging.INFO
        )
        cart_logger.log(
            level,
            "%s %s status=%s duration_ms=%.1f client=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            client,
        )
        return response
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        cart_logger.exception(
            "%s %s unhandled_exception duration_ms=%.1f client=%s",
            request.method,
            request.url.path,
            elapsed_ms,
            client,
        )
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for _r in _cv_routers:
    app.include_router(_r)
app.include_router(stt_router)
app.include_router(tts_router)
app.include_router(llm_router)
app.include_router(menu_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(discounts_router)
app.include_router(payment_router)
app.include_router(user_router)
app.include_router(settings_router)
app.include_router(hardware_router)
app.include_router(diagnostics_router)
app.include_router(admin_auth_router)
app.include_router(admin_menu_router)
app.include_router(admin_users_router)
app.include_router(admin_orders_router)
app.include_router(admin_coupons_router)
app.include_router(admin_discounts_router)
app.include_router(admin_payments_router)
app.include_router(admin_stats_router)


_static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/health")
async def health():
    return {
        "ok": True,
        "cv_routers_loaded": len(_cv_routers),
        "cv_load_errors": _cv_load_errors,
    }
