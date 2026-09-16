"""흰 지팡이 / 휠체어 접근 감지 시나리오 상태 머신.

- temp/main.py의 시나리오 로직(10초 간격 3회 안내)을 서버 세션 단위로 이식.
- TTS 오디오는 트리거 종류별로 최초 1회 OpenAI TTS로 생성 후 메모리 캐시.
- 감지 대상에 따라 프론트가 켤 입력 모드가 다름 (docs/AI 질의.md 설계):
    흰 지팡이(시각장애인) -> 음성 대화 모드, 휠체어 -> 제스처 인식 모드
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

ANNOUNCEMENT_MESSAGES = {
    "white_cane": "햄버거 주문을 위한 키오스크 입니다.",
    "wheelchair": "휠체어 이용 고객님, 손동작으로 메뉴를 선택하실 수 있습니다.",
}
# 트리거별로 프론트가 자동으로 켜야 할 입력 모드
MODE_ACTIONS = {
    "white_cane": "voice",
    "wheelchair": "gesture",
}
ANNOUNCEMENT_INTERVAL = 10.0
MAX_ANNOUNCEMENTS = 3

# 모듈 레벨 TTS 오디오 캐시 (트리거 타입별 bytes: MP3 바이너리)
_tts_cache: dict[str, bytes] = {}


async def get_tts_audio(trigger_type: str) -> bytes:
    """
    안내 문구 TTS 오디오를 트리거 타입별로 최초 1회 생성 후 캐시.
    이후 호출은 캐시된 바이너리를 즉시 반환.
    """
    cached = _tts_cache.get(trigger_type)
    if cached is not None:
        return cached

    from core.tts_service import stream_tts

    message = ANNOUNCEMENT_MESSAGES[trigger_type]
    chunks: list[bytes] = []
    async for chunk in stream_tts(message, language="ko"):
        chunks.append(chunk)
    audio = b"".join(chunks)
    _tts_cache[trigger_type] = audio
    return audio


@dataclass
class ApproachSession:
    mode_on: bool = False
    trigger_type: str | None = None
    announcement_count: int = 0
    last_announcement_time: float = field(default=0.0)
    user_input_received: bool = False

    def activate(self, trigger_type: str) -> None:
        self.mode_on = True
        self.trigger_type = trigger_type
        self.announcement_count = 0
        self.last_announcement_time = 0.0  # 첫 안내를 즉시 트리거
        self.user_input_received = False

    def reset(self) -> None:
        self.mode_on = False
        self.trigger_type = None
        self.announcement_count = 0
        self.last_announcement_time = 0.0
        self.user_input_received = False


def _pick_trigger(white_cane_detected: bool, wheelchair_detected: bool) -> str | None:
    # 동시 감지 시 휠체어를 우선 — 흔치 않은 케이스라 임의 우선순위
    if wheelchair_detected:
        return "wheelchair"
    if white_cane_detected:
        return "white_cane"
    return None


def process_frame_result(
    session: ApproachSession,
    white_cane_detected: bool,
    white_cane_confidence: float,
    wheelchair_detected: bool,
    wheelchair_confidence: float,
) -> dict:
    """
    프레임 추론 결과와 세션 상태를 기반으로 시나리오 로직 실행.

    Returns:
        {
            "white_cane_detected": bool,
            "white_cane_confidence": float,
            "wheelchair_detected": bool,
            "wheelchair_confidence": float,
            "active_trigger": "white_cane" | "wheelchair" | None,
            "mode_action": "voice" | "gesture" | None,  # 프론트가 켤 입력 모드
            "mode_on": bool,
            "announcement_count": int,
            "play_tts": bool,   # True이면 서버가 TTS 오디오 binary 프레임을 이어서 전송
            "mode_ended": bool,
        }
    """
    play_tts = False
    mode_ended = False
    current_time = time.time()

    # IDLE → ACTIVE
    if not session.mode_on:
        trigger = _pick_trigger(white_cane_detected, wheelchair_detected)
        if trigger:
            session.activate(trigger)

    # ACTIVE 상태 내 타이머 처리
    if session.mode_on:
        elapsed = current_time - session.last_announcement_time
        if elapsed >= ANNOUNCEMENT_INTERVAL:
            if session.announcement_count < MAX_ANNOUNCEMENTS:
                play_tts = True
                session.last_announcement_time = current_time
                session.announcement_count += 1
            else:
                session.reset()
                mode_ended = True

    active_trigger = session.trigger_type
    return {
        "white_cane_detected": white_cane_detected,
        "white_cane_confidence": round(white_cane_confidence, 4),
        "wheelchair_detected": wheelchair_detected,
        "wheelchair_confidence": round(wheelchair_confidence, 4),
        "active_trigger": active_trigger,
        "mode_action": MODE_ACTIONS.get(active_trigger) if active_trigger else None,
        "mode_on": session.mode_on,
        "announcement_count": session.announcement_count,
        "play_tts": play_tts,
        "mode_ended": mode_ended,
    }


def handle_user_input(session: ApproachSession) -> dict:
    """사용자 입력(터치 등) 수신 시 안내 모드 즉시 종료."""
    session.user_input_received = True
    session.reset()
    return {
        "type": "ack",
        "mode_on": False,
        "mode_ended": True,
    }
