"""
물리적 결제 장치(카드 리더 / 현금 수납기 등) 연동 확장 지점.

지금은 연결된 하드웨어가 없어 로그만 남기고 즉시 성공을 반환(시뮬레이션)한다.
★ 확장 지점: 나중에 아두이노 등 실제 장치를 연동할 때는 trigger_hardware_action() 내부
구현만 시리얼/HTTP/MQTT 호출로 교체하면 되고, 엔드포인트 경로·요청/응답 형태와
프론트(hardwareService.js)/결제 흐름(CartScreen.jsx)은 그대로 유지할 수 있다.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hardware", tags=["hardware"])


class HardwareTriggerIn(BaseModel):
    action: str  # "card_payment" | "cash_payment"
    order_id: str | None = None


@router.post("/trigger")
async def trigger_hardware_action(body: HardwareTriggerIn):
    logger.info("hardware trigger (simulated): action=%s order_id=%s", body.action, body.order_id)
    return {"ok": True, "simulated": True, "action": body.action}
