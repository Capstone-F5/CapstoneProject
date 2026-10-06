"""흰 지팡이 / 휠체어 접근 감지 시나리오 상태 머신.

- temp/main.py의 시나리오 로직을 서버 세션 단위로 이식.
- 휠체어 안내 음성은 프론트 TTS로 재생하고, 재생 후 3초 간격으로 알림음을 두 번 낸다.
  흰 지팡이는 음성 주문 인사말(ChatPanel START_GREETING)이 안내를 대신한다.
- 감지 대상에 따라 프론트가 켤 입력 모드가 다름 (docs/AI 질의.md 설계):
    흰 지팡이(시각장애인) -> 음성 대화 모드, 휠체어 -> 제스처 인식 모드
- 한 프레임 오탐으로 발동하지 않도록 최근 CONFIRM_WINDOW 프레임 중 CONFIRM_HITS 프레임 이상 감지돼야 확정한다.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

# 트리거별로 프론트가 자동으로 켜야 할 입력 모드
MODE_ACTIONS = {
    "white_cane": "voice",
    "wheelchair": "gesture",
}
ANNOUNCEMENT_INTERVAL = 10.0
MAX_ANNOUNCEMENTS = 3
# 안내 종료 후 대상이 이 프레임 수만큼 연속으로 안 보여야 다시 감지를 받음 (프레임 0.5초 간격 → 약 3초)
REARM_ABSENT_FRAMES = 6
# 감지 확정: 최근 4프레임 중 3프레임 (2fps 기준 약 1.5초)
CONFIRM_WINDOW = 4
CONFIRM_HITS = 3


@dataclass
class ApproachSession:
    mode_on: bool = False
    trigger_type: str | None = None
    announcement_count: int = 0
    last_announcement_time: float = field(default=0.0)
    user_input_received: bool = False
    # 안내가 끝난 뒤 대상이 화면에서 사라질 때까지 재시작을 막는 잠금
    latched: bool = False
    absent_frames: int = 0
    # 클래스별 최근 프레임 감지 이력 (확정 판정용)
    history: dict = field(default_factory=lambda: {
        "white_cane": deque(maxlen=CONFIRM_WINDOW),
        "wheelchair": deque(maxlen=CONFIRM_WINDOW),
    })

    def confirmed(self, name: str, detected: bool) -> bool:
        h = self.history[name]
        h.append(detected)
        return sum(h) >= CONFIRM_HITS

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

    def finish(self) -> None:
        """안내 사이클 종료(3회 완료 또는 사용자 입력) — 대상이 사라질 때까지 재시작 잠금."""
        self.reset()
        self.latched = True
        self.absent_frames = 0


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
            "mode_ended": bool,
            "confirmed": {"white_cane": bool, "wheelchair": bool},  # 연속 프레임 확정 여부
        }
    """
    mode_ended = False
    current_time = time.time()

    white_cane_ok = session.confirmed("white_cane", white_cane_detected)
    wheelchair_ok = session.confirmed("wheelchair", wheelchair_detected)
    trigger = _pick_trigger(white_cane_ok, wheelchair_ok)

    if session.latched:
        # 종료 후 잠금: 대상이 연속으로 안 보이면 해제, 다시 보이면 카운트 리셋
        if trigger is None:
            session.absent_frames += 1
            if session.absent_frames >= REARM_ABSENT_FRAMES:
                session.latched = False
                session.absent_frames = 0
        else:
            session.absent_frames = 0
    elif not session.mode_on and trigger:
        # IDLE → ACTIVE
        session.activate(trigger)

    # ACTIVE 상태 내 타이머 처리
    if session.mode_on:
        elapsed = current_time - session.last_announcement_time
        if elapsed >= ANNOUNCEMENT_INTERVAL:
            if session.announcement_count < MAX_ANNOUNCEMENTS:
                session.last_announcement_time = current_time
                session.announcement_count += 1
            else:
                session.finish()
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
        "mode_ended": mode_ended,
        "confirmed": {"white_cane": white_cane_ok, "wheelchair": wheelchair_ok},
    }


def handle_user_input(session: ApproachSession) -> dict:
    """사용자 입력(터치 등) 수신 시 진행 중인 안내를 즉시 종료.

    안내 중일 때만 잠금을 건다 — 평소 화면을 만지는 것만으로 다음 대상 감지를 막지 않도록.
    """
    was_active = session.mode_on
    if was_active:
        session.user_input_received = True
        session.finish()
    return {
        "type": "ack",
        "mode_on": False,
        "mode_ended": was_active,
    }
