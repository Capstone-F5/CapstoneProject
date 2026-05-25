import sys
import os

# 프로젝트 루트를 경로에 추가 (ai_modules 접근용)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir  = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
sys.path.insert(0, _backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.gesture_ws import router as gesture_router
from api.collect    import router as collect_router

app = FastAPI(title="Kiosk Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gesture_router)
app.include_router(collect_router)
