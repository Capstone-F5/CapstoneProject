"""
흰 지팡이 접근 감지 시나리오 상태 머신.

- temp/main.py의 시나리오 로직(10초 간격 3회 안내)을 서버 세션 단위로 이식.
- TTS 오디오는 최초 1회 OpenAI TTS로 생성 후 메모리 캐시.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

ANNOUNCEMENT_MESSAGE = "햄버거 주문을 위한 키오스크 입니다."
ANNOUNCEMENT_INTERVAL = 10.0
MAX_ANNOUNCEMENTS = 3

# 모듈 레벨 TTS 오디오 캐시 (bytes: MP3 바이너리)
_tts_cache: bytes | None = None


async def get_tts_audio() -> bytes:
    """
    안내 문구 TTS 오디오를 최초 1회 생성 후 캐시.
    이후 호출은 캐시된 바이너리를 즉시 반환.
    """
    global _tts_cache
    if _tts_cache is not None:
        return _tts_cache

    from core.tts_service import stream_tts

    chunks: list[bytes] = []
    async for chunk in stream_tts(ANNOUNCEMENT_MESSAGE, language="ko"):
        chunks.append(chunk)
    _tts_cache = b"".join(chunks)
    return _tts_cache


@dataclass
class ApproachSession:
    voice_mode_on: bool = False
    announcement_count: int = 0
    last_announcement_time: float = field(default=0.0)
    user_input_received: bool = False

    def activate(self) -> None:
        self.voice_mode_on = True
        self.announcement_count = 0
        self.last_announcement_time = 0.0  # 첫 안내를 즉시 트리거
        self.user_input_received = False

    def reset(self) -> None:
        self.voice_mode_on = False
        self.announcement_count = 0
        self.last_announcement_time = 0.0
        self.user_input_received = False


def process_frame_result(
    session: ApproachSession,
    white_cane_detected: bool,
    confidence: float,
) -> dict:
    """
    프레임 추론 결과와 세션 상태를 기반으로 시나리오 로직 실행.

    Returns:
        {
            "white_cane_detected": bool,
            "confidence": float,
            "voice_mode_on": bool,
            "announcement_count": int,
            "play_tts": bool,   # True이면 서버가 TTS 오디오 binary 프레임을 이어서 전송
            "mode_ended": bool,
        }
    """
    play_tts = False
    mode_ended = False
    current_time = time.time()

    # IDLE → VOICE_MODE
    if white_cane_detected and not session.voice_mode_on:
        session.activate()

    # VOICE_MODE 내 타이머 처리
    if session.voice_mode_on:
        elapsed = current_time - session.last_announcement_time
        if elapsed >= ANNOUNCEMENT_INTERVAL:
            if session.announcement_count < MAX_ANNOUNCEMENTS:
                play_tts = True
                session.last_announcement_time = current_time
                session.announcement_count += 1
            else:
                session.reset()
                mode_ended = True

    return {
        "white_cane_detected": white_cane_detected,
        "confidence": round(confidence, 4),
        "voice_mode_on": session.voice_mode_on,
        "announcement_count": session.announcement_count,
        "play_tts": play_tts,
        "mode_ended": mode_ended,
    }


def handle_user_input(session: ApproachSession) -> dict:
    """사용자 입력(터치 등) 수신 시 음성 안내 모드 즉시 종료."""
    session.user_input_received = True
    session.reset()
    return {
        "type": "ack",
        "voice_mode_on": False,
        "mode_ended": True,
    }
