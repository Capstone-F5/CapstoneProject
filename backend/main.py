import sys
import os

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

# 제스처/수집 라우터는 mediapipe 의존 — 환경에 따라 로드 실패할 수 있으므로 가드.
try:
    from api.gesture_ws import router as gesture_router
    from api.collect import router as collect_router
    _cv_routers = [gesture_router, collect_router]
    _cv_load_error: str | None = None
except Exception as _e:  # noqa: BLE001
    _cv_routers = []
    _cv_load_error = f"{type(_e).__name__}: {_e}"

from api.stt import router as stt_router
from api.tts import router as tts_router
from api.llm import router as llm_router
from api.menu import router as menu_router
from api.cart import router as cart_router
from api.order import router as order_router
from api.payment import router as payment_router
from api.user import router as user_router
from api.settings import router as settings_router
from api.hardware import router as hardware_router
from api.admin.auth import router as admin_auth_router
from api.admin.menu import router as admin_menu_router
from api.admin.users import router as admin_users_router

from core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Kiosk Backend", lifespan=lifespan)

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
app.include_router(payment_router)
app.include_router(user_router)
app.include_router(settings_router)
app.include_router(hardware_router)
app.include_router(admin_auth_router)
app.include_router(admin_menu_router)
app.include_router(admin_users_router)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "cv_routers_loaded": bool(_cv_routers),
        "cv_load_error": _cv_load_error,
    }
