"""
키오스크 개발자 설정(마이크/STT 감도 및 흰 지팡이·휠체어 접근 감지 파라미터) 런타임 관리 모듈.

- 관리자 대시보드의 '키오스크 설정 (개발자 옵션)' 탭에서 실시간 조회·수정·초기화한다.
- DB 스키마 마이그레이션 없이 즉시 동작하도록 `backend/logs/kiosk_dev_settings.json`에 영구 저장하며,
  메모리 캐시를 통해 매 오디오 청크/카메라 프레임 추론 시 디스크 I/O 없이 즉시 참조한다.
"""
from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_SETTINGS_FILE = _LOG_DIR / "kiosk_dev_settings.json"

DEFAULT_KIOSK_SETTINGS: dict[str, Any] = {
    "debug_mode": False,                       # 키오스크 하단 컨트롤 바에 디버깅 페이지 버튼 표시 여부
    "mic": {
        "preset": "standard",                  # quiet | standard | noisy | strict | custom
        "auto_gain_control": False,            # 웹캠 마이크 자동 증폭(AGC) 허용 여부 (False = 강제 차단 권장)
        "min_speech_rms": 0.018,               # Stage 1: 근접 발화 최소 활성 RMS (0.004 ~ 0.080)
        "snr_margin": 2.0,                     # Stage 1: 배경 소음 바닥 대비 최소 신호비 배수 (1.1 ~ 5.0)
        "min_active_ms": 120,                  # Stage 1: 최소 유효 발화 지속 시간 ms (박수·식기 충격음 차단)
        "vad_positive_threshold": 0.80,        # Silero VAD: 음성 시작 확률 임계값 (0.50 ~ 0.95)
        "vad_negative_threshold": 0.45,        # Silero VAD: 음성 종료 확률 임계값 (0.20 ~ 0.80)
        "vad_redemption_frames": 8,            # Silero VAD: 말 끝 대기 프레임 수 (3 ~ 20)
        "no_speech_threshold": 0.65,           # Stage 2: Whisper 세그먼트 무음 확률 차단 임계값 (0.30 ~ 0.95)
        "logprob_threshold": -1.0,             # Stage 2: Whisper 세그먼트 평균 로그확률 하한 (-2.0 ~ -0.3)
        "short_word_logprob_threshold": -1.35, # Stage 2: '네','단품' 등 단답 완화 로그확률 하한 (-2.2 ~ -0.5)
        "compression_threshold": 2.4,          # Stage 2: 반복 환각 루프 압축비 상한 (1.5 ~ 4.0)
        "domain_guard_enabled": True,          # Stage 3: 노래 가사·주변 일상 대화 도메인 필터 활성화
        "barge_in_enabled": False,             # TTS 안내 재생 중 사용자 음성 끼어들기(Barge-in) 허용
    },
    "tts": {
        "default_speed": 1.0,                  # LLM 대화 음성의 기본 배속 (min_speed ~ max_speed 안). 새 손님은 이 값으로 시작
        "min_speed": 0.7,                      # 하단 컨트롤 바에서 손님이 낮출 수 있는 최저 배속 (0.5 ~ 1.0)
        "max_speed": 1.5,                      # 하단 컨트롤 바에서 손님이 올릴 수 있는 최고 배속 (1.0 ~ 2.0)
    },
    "approach": {
        "preset": "standard",                  # near | standard | far | custom
        "enabled": True,                       # 대기 화면 접근 감지 활성화 여부
        "confidence_threshold": 0.50,          # (기본값) TFLite 모델 객체 인식 최소 신뢰도 (0.20 ~ 0.90)
        "wheelchair_confidence": 0.50,         # 휠체어 인식 최소 신뢰도 (0.15 ~ 0.95)
        "person_confidence": 0.50,             # 일반 사람(보행자) 인식 최소 신뢰도 (0.15 ~ 0.95)
        "white_cane_confidence": 0.50,         # 흰 지팡이 인식 최소 신뢰도 (0.15 ~ 0.95)
        "min_box_h": 0.15,                     # 화면 높이 대비 최소 박스 높이 비율 (0.05 ~ 0.50, 클수록 근거리만 인식)
        "frame_interval_ms": 500,              # 카메라 프레임 추론 주기 ms (200 ~ 2000, 기본 500ms = 2fps)
        "confirm_window": 4,                   # 연속 감지 판정 윈도우 프레임 수 (1 ~ 10)
        "confirm_hits": 3,                     # 윈도우 내 확정 최소 감지 프레임 수 (1 ~ 10)
        "rearm_absent_frames": 6,              # 안내 종료 후 잠금 해제까지 필요한 연속 미감지 프레임 수 (2 ~ 20)
        "announcement_interval_sec": 10.0,     # 안내 음성 반복 주기 초 (4.0 ~ 30.0)
        "max_announcements": 3,                # 최대 안내 반복 횟수 (1 ~ 5)
        "motion_gate_enabled": True,           # 배경 변화 적을 시 카메라 프레임 전송 스킵 (모션 게이트)
        "motion_threshold": 0.025,             # 모션 감지 활성 픽셀 최소 비율 (0.005 ~ 0.100, 기본 2.5%)
        "motion_keepalive_sec": 4.0,           # 정적 대기 시 하트비트 전송 주기 초 (1.0 ~ 10.0초)
    },
    "gesture": {
        "preset": "standard",                  # standard | far_reach | rpi_eco | custom
        "enabled": True,                       # 온디바이스 제스처 인식 활성화 여부
        "min_palm_size": 0.08,                 # 손 인식 최소 손바닥 크기 비율 (0.03 ~ 0.18, 낮출수록 원거리 손 인식)
        "detection_confidence": 0.65,          # MediaPipe 손 검출 최소 신뢰도 (0.35 ~ 0.85)
        "tracking_confidence": 0.50,           # MediaPipe 관절 랜드마크 추적 신뢰도 (0.30 ~ 0.80)
        "target_fps": 15,                      # 온디바이스 목표 FPS (8 ~ 24, RPi 4B 발열 및 CPU 부하 제어)
        "cam_width": 640,                      # 카메라 입력 가로 해상도 (320 | 480 | 640)
        "cam_height": 480,                     # 카메라 입력 세로 해상도 (240 | 360 | 480)
        "margin_left": 0.20,                   # 화면 매핑 좌측 모서리 마진 비율 (0.02 ~ 0.40)
        "margin_right": 0.20,                  # 화면 매핑 우측 모서리 마진 비율 (0.02 ~ 0.40)
        "margin_top": 0.25,                    # 화면 매핑 상단 모서리 마진 비율 (0.02 ~ 0.45)
        "margin_bottom": 0.10,                 # 화면 매핑 하단 모서리 마진 비율 (0.02 ~ 0.35)
        "edge_pad": 0.05,                      # 화면 모서리 도달 가속 패딩 (0.00 ~ 0.15)
        "margin_x": 0.20,                      # 하위 호환용 (좌우 대칭)
        "margin_bot": 0.10,                    # 하위 호환용 (하단)
    },
}

_cached_settings: dict[str, dict[str, Any]] | None = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        elif k in result:
            result[k] = v
    return result


def _clamp_float(value: Any, lo: float, hi: float, fallback: float) -> float:
    """숫자가 아니거나 NaN/무한대이면 fallback(범위 안으로 자름), 아니면 [lo, hi]로 자른다."""
    try:
        v = float(value)
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError
    except (TypeError, ValueError):
        v = fallback
    return max(lo, min(hi, v))


def _sanitize(settings: dict[str, Any]) -> dict[str, Any]:
    s = _deep_merge(DEFAULT_KIOSK_SETTINGS, settings)
    s["debug_mode"] = bool(s.get("debug_mode", False))
    m = s["mic"]
    m["auto_gain_control"] = bool(m.get("auto_gain_control", False))
    m["min_speech_rms"] = round(max(0.003, min(0.10, float(m.get("min_speech_rms", 0.018)))), 4)
    m["snr_margin"] = round(max(1.1, min(6.0, float(m.get("snr_margin", 2.0)))), 2)
    m["min_active_ms"] = int(max(30, min(600, int(m.get("min_active_ms", 120)))))
    m["vad_positive_threshold"] = round(max(0.40, min(0.98, float(m.get("vad_positive_threshold", 0.80)))), 2)
    m["vad_negative_threshold"] = round(max(0.15, min(0.90, float(m.get("vad_negative_threshold", 0.45)))), 2)
    m["vad_redemption_frames"] = int(max(2, min(30, int(m.get("vad_redemption_frames", 8)))))
    m["no_speech_threshold"] = round(max(0.20, min(0.98, float(m.get("no_speech_threshold", 0.65)))), 2)
    m["logprob_threshold"] = round(max(-2.5, min(-0.2, float(m.get("logprob_threshold", -1.0)))), 2)
    m["short_word_logprob_threshold"] = round(
        max(-3.0, min(-0.3, float(m.get("short_word_logprob_threshold", -1.35)))), 2
    )
    m["compression_threshold"] = round(max(1.4, min(5.0, float(m.get("compression_threshold", 2.4)))), 2)
    m["domain_guard_enabled"] = bool(m.get("domain_guard_enabled", True))
    m["barge_in_enabled"] = bool(m.get("barge_in_enabled", False))

    if not isinstance(s.get("tts"), dict):   # 잘못된 타입이 들어오면 기본값으로
        s["tts"] = copy.deepcopy(DEFAULT_KIOSK_SETTINGS["tts"])
    t = s["tts"]
    t["min_speed"] = round(_clamp_float(t.get("min_speed"), 0.5, 1.0, 0.7), 2)
    t["max_speed"] = round(_clamp_float(t.get("max_speed"), 1.0, 2.0, 1.5), 2)
    t["default_speed"] = round(_clamp_float(t.get("default_speed"), t["min_speed"], t["max_speed"], 1.0), 2)

    a = s["approach"]
    a["enabled"] = bool(a.get("enabled", True))
    default_conf = round(max(0.15, min(0.95, float(a.get("confidence_threshold", 0.50)))), 2)
    a["confidence_threshold"] = default_conf
    a["wheelchair_confidence"] = round(max(0.15, min(0.95, float(a.get("wheelchair_confidence", default_conf)))), 2)
    a["person_confidence"] = round(max(0.15, min(0.95, float(a.get("person_confidence", default_conf)))), 2)
    a["white_cane_confidence"] = round(max(0.15, min(0.95, float(a.get("white_cane_confidence", default_conf)))), 2)
    a["min_box_h"] = round(max(0.03, min(0.70, float(a.get("min_box_h", 0.15)))), 2)
    a["frame_interval_ms"] = int(max(150, min(3000, int(a.get("frame_interval_ms", 500)))))
    a["confirm_window"] = int(max(1, min(15, int(a.get("confirm_window", 4)))))
    a["confirm_hits"] = int(max(1, min(a["confirm_window"], int(a.get("confirm_hits", 3)))))
    a["rearm_absent_frames"] = int(max(1, min(30, int(a.get("rearm_absent_frames", 6)))))
    a["announcement_interval_sec"] = round(max(3.0, min(60.0, float(a.get("announcement_interval_sec", 10.0)))), 1)
    a["max_announcements"] = int(max(1, min(10, int(a.get("max_announcements", 3)))))
    a["motion_gate_enabled"] = bool(a.get("motion_gate_enabled", True))
    a["motion_threshold"] = round(max(0.005, min(0.120, float(a.get("motion_threshold", 0.025)))), 3)
    a["motion_keepalive_sec"] = round(max(1.0, min(15.0, float(a.get("motion_keepalive_sec", 4.0)))), 1)

    g = s.setdefault("gesture", {})
    g["enabled"] = bool(g.get("enabled", True))
    g["min_palm_size"] = round(max(0.03, min(0.20, float(g.get("min_palm_size", 0.08)))), 3)
    g["detection_confidence"] = round(max(0.30, min(0.90, float(g.get("detection_confidence", 0.65)))), 2)
    g["tracking_confidence"] = round(max(0.30, min(0.90, float(g.get("tracking_confidence", 0.50)))), 2)
    g["target_fps"] = int(max(8, min(30, int(g.get("target_fps", 15)))))
    g["cam_width"] = int(g.get("cam_width", 640))
    if g["cam_width"] not in (320, 480, 640):
        g["cam_width"] = 640
    g["cam_height"] = int(g.get("cam_height", 480))
    if g["cam_height"] not in (240, 360, 480):
        g["cam_height"] = 480
    # 마진 및 활성 영역 정제
    ml = g.get("margin_left", g.get("margin_x", 0.20))
    mr = g.get("margin_right", g.get("margin_x", 0.20))
    mt = g.get("margin_top", 0.25)
    mb = g.get("margin_bottom", g.get("margin_bot", 0.10))
    g["margin_left"] = round(max(0.02, min(0.40, float(ml))), 2)
    g["margin_right"] = round(max(0.02, min(0.40, float(mr))), 2)
    g["margin_top"] = round(max(0.02, min(0.45, float(mt))), 2)
    g["margin_bottom"] = round(max(0.02, min(0.35, float(mb))), 2)
    g["edge_pad"] = round(max(0.00, min(0.15, float(g.get("edge_pad", 0.05)))), 2)
    # 하위 호환 필드 동기화
    g["margin_x"] = g["margin_left"]
    g["margin_bot"] = g["margin_bottom"]
    return s


def get_kiosk_settings() -> dict[str, dict[str, Any]]:
    """현재 활성화된 키오스크 개발자 설정을 반환 (메모리 캐시 우선)."""
    global _cached_settings
    if _cached_settings is not None:
        return _cached_settings

    if _SETTINGS_FILE.exists():
        try:
            loaded = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            _cached_settings = _sanitize(loaded)
            return _cached_settings
        except Exception as e:
            logger.warning("kiosk_dev_settings.json 로드 실패, 기본값 사용: %s", e)

    _cached_settings = copy.deepcopy(DEFAULT_KIOSK_SETTINGS)
    return _cached_settings


def update_kiosk_settings(patch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """설정을 병합·검증한 뒤 파일과 메모리 캐시에 즉시 반영한다."""
    global _cached_settings
    current = get_kiosk_settings()
    merged = _sanitize(_deep_merge(current, patch))
    _cached_settings = merged
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        _SETTINGS_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("kiosk_dev_settings.json 저장 실패: %s", e)
    return merged


def reset_kiosk_settings() -> dict[str, dict[str, Any]]:
    """모든 설정을 기본값(DEFAULT_KIOSK_SETTINGS)으로 초기화한다."""
    global _cached_settings
    _cached_settings = copy.deepcopy(DEFAULT_KIOSK_SETTINGS)
    try:
        if _SETTINGS_FILE.exists():
            _SETTINGS_FILE.unlink()
    except Exception as e:
        logger.warning("kiosk_dev_settings.json 삭제 실패: %s", e)
    return _cached_settings
