# STT 최적화 계획: faster-whisper 로컬 전환

> 작성일: 2026-09-19  
> 대상: `backend/core/stt_service.py`  
> 목적: OpenAI STT API 할루시네이션 감소 + 비용 절감 + 파라미터 완전 제어

---

## 1. 현재 구조와 문제점

### 현재 흐름

```
VAD (프론트, @ricky0123/vad-react)
  → 음성 구간 감지
  → POST /ai_modules/stt
    → OpenAI gpt-4o-mini-transcribe API 호출
      → 첫 발화: language=None (자동 감지)
      → 이후 발화: language 고정 (ko/en/zh/ja)
    → 환각 필터 (_HALLUCINATION_FRAGMENTS, _is_prompt_echo)
    → 결제 키워드 정규화
  → LLM으로 전달
```

### 할루시네이션 발생 원인

| 원인 | 설명 |
|---|---|
| `no_speech_threshold` 미설정 | 무음/잡음 입력에도 텍스트 생성 |
| `logprob_threshold` 미설정 | 저신뢰 출력도 그대로 반환 |
| `condition_on_previous_text` 기본값 True | 이전 출력을 참조해 반복·연쇄 환각 발생 |
| API 모델 파라미터 제한 | `gpt-4o-mini-transcribe`는 위 파라미터를 노출하지 않음 |

현재 코드에서 `_HALLUCINATION_FRAGMENTS`·`_is_prompt_echo` 필터로 일부를 걸러내고 있으나,  
**발생 자체를 차단하지 못하고 사후 감지에 의존**하는 구조다.

---

## 2. 제안: faster-whisper 로컬 전환

### 왜 faster-whisper인가

`faster-whisper`는 OpenAI Whisper를 CTranslate2 백엔드로 재구현한 라이브러리다.

- **동일 모델, 다른 런타임**: Whisper large-v3-turbo 가중치를 그대로 사용
- **INT8 양자화**: 메모리 절반, 속도 2–4배 향상
- **파라미터 완전 제어**: `no_speech_threshold`, `logprob_threshold` 등 직접 지정 가능
- **비용 없음**: 로컬 실행이므로 OpenAI API 비용 없음
- **서버 실행**: 라즈베리파이4가 아닌 별도 서버 PC에서 실행

### 성능 비교

| 방식 | 지연시간 (3초 발화 기준) | 비용 | 할루시네이션 파라미터 제어 |
|---|---|---|---|
| OpenAI gpt-4o-mini-transcribe (현재) | 300–800ms + 네트워크 왕복 | 유료 ($0.003/min) | 불가 |
| faster-whisper large-v3-turbo (CPU) | 1–2s | 무료 | 완전 제어 |
| faster-whisper large-v3-turbo (GPU, CUDA) | 0.3–0.7s | 무료 | 완전 제어 |
| faster-whisper medium (CPU) | 0.5–1.5s | 무료 | 완전 제어 |

> 서버 사양에 따라 달라짐. CPU만 있으면 `medium`, GPU가 있으면 `large-v3-turbo` 권장.

---

## 3. 언어별 전용 모델 분리 방안

사용자가 제안한 "언어마다 다른 STT 모델"에 대한 분석.

### 방안 A: 첫 발화 → Whisper, 이후 → 언어별 전용 모델

```
첫 발화 → faster-whisper (language=None, 언어 감지)
  → ko → Naver CLOVA Speech API
  → en → faster-whisper (language='en' 고정)
  → zh → Alibaba FunASR 또는 faster-whisper
  → ja → faster-whisper (language='ja' 고정)
```

| 언어 | 전용 모델 후보 | 장점 | 단점 |
|---|---|---|---|
| 한국어 | Naver CLOVA Speech | 국내 최고 수준 한국어 특화 | API 유료, 의존성 추가 |
| 한국어 | ETRI 한국어 STT | 공공 API, 한국어 특화 | 승인 필요, 속도 제한 |
| 영어 | faster-whisper 유지 | Whisper는 영어가 가장 강함 | — |
| 중국어 | Alibaba FunASR (로컬) | 중국어 정확도 최상 | 별도 모델 다운로드 (~3GB) |
| 일본어 | faster-whisper 유지 | Whisper 일본어도 우수 | — |

**결론:** 한국어를 제외한 나머지 언어는 faster-whisper만으로 충분하다.  
한국어 전용 모델은 Naver CLOVA가 유일한 실질적 선택지이나, 비용·의존성 추가 대비 효과가 크지 않다.

### 방안 B: faster-whisper 단일 모델 + 파라미터 최적화 (권장)

```
첫 발화 → faster-whisper (language=None)
이후 발화 → faster-whisper (language 고정)
```

**언어를 고정해주는 것만으로 정확도가 크게 오른다.**  
현재 코드도 이 로직을 갖추고 있으나, API 레벨에서 파라미터 제어가 안 되는 게 문제.  
faster-whisper로 전환하면 아래 파라미터가 해결된다:

```python
segments, info = model.transcribe(
    audio_array,
    language=detected_lang_or_none,
    no_speech_threshold=0.6,          # 핵심: 무음·잡음 → 빈 텍스트
    logprob_threshold=-1.0,           # 저신뢰 출력 차단
    condition_on_previous_text=False, # 반복 환각 차단
    temperature=0,                    # 확정적 출력 (랜덤성 제거)
    word_timestamps=False,            # 불필요한 연산 생략
    beam_size=5,
)
```

---

## 4. 구현 계획

### 4-1. 의존성 추가 (`backend/requirements.txt`)

```
# 현재 (제거)
# openai>=1.30.0  ← TTS·LLM에도 사용하므로 완전 제거 불가, STT만 대체

# 추가
faster-whisper>=1.0.0
```

GPU 사용 시 추가:
```
nvidia-cublas-cu12
nvidia-cudnn-cu12
```

### 4-2. 모델 선택 가이드

| 서버 환경 | 권장 모델 | 메모리 | 예상 지연 |
|---|---|---|---|
| CPU only | `medium` (int8) | ~1.5GB | 1–3s |
| CPU only (고성능) | `large-v3-turbo` (int8) | ~3GB | 1–2s |
| GPU (VRAM 4GB+) | `large-v3-turbo` (float16) | ~3.5GB | 0.3–0.7s |

모델은 최초 실행 시 `~/.cache/huggingface/hub/` 에 자동 다운로드된다.

### 4-3. stt_service.py 변경 골자

```python
from faster_whisper import WhisperModel

# 서버 시작 시 1회 로드 (콜드스타트 방지)
_fw_model: WhisperModel | None = None

def _get_fw_model() -> WhisperModel:
    global _fw_model
    if _fw_model is None:
        device    = "cuda" if torch.cuda.is_available() else "cpu"
        compute   = "float16" if device == "cuda" else "int8"
        model_id  = os.getenv("FASTER_WHISPER_MODEL", "large-v3-turbo")
        _fw_model = WhisperModel(model_id, device=device, compute_type=compute)
    return _fw_model

async def transcribe_bytes(audio_bytes, filename="audio.webm", language=None):
    model = _get_fw_model()
    audio = _decode_audio(audio_bytes)   # ffmpeg → numpy float32

    segments, info = model.transcribe(
        audio,
        language=language,
        no_speech_threshold=0.6,
        logprob_threshold=-1.0,
        condition_on_previous_text=False,
        temperature=0,
    )

    text = " ".join(s.text for s in segments).strip()
    detected_lang = info.language if not language else language

    # 기존 필터 재사용
    if _is_prompt_echo(text) or _is_hallucination(text):
        text = ""
    else:
        text = _normalize_payment_text(text)

    return {"text": text, "language": detected_lang, "duration": info.duration}
```

### 4-4. 오디오 디코딩 처리

faster-whisper는 numpy float32 배열 또는 파일 경로를 입력받는다.  
브라우저에서 올라오는 `webm/opus` 포맷을 디코딩하려면 ffmpeg가 필요하다.

```python
import ffmpeg
import numpy as np

def _decode_audio(audio_bytes: bytes) -> np.ndarray:
    out, _ = (
        ffmpeg
        .input("pipe:0")
        .output("pipe:1", format="f32le", ac=1, ar=16000)
        .run(input=audio_bytes, capture_stdout=True, capture_stderr=True)
    )
    return np.frombuffer(out, dtype=np.float32)
```

서버에 ffmpeg가 없으면:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Conda
conda install -c conda-forge ffmpeg
```

### 4-5. 마이그레이션 순서

1. `faster-whisper` 설치 확인 및 모델 사전 다운로드
2. `stt_service.py` 교체 (기존 환각 필터·정규화 코드 재사용)
3. `openai` 패키지는 TTS·LLM에서 계속 사용하므로 유지
4. 환경변수 추가: `FASTER_WHISPER_MODEL=large-v3-turbo`
5. 로컬 테스트 → 배포

### 4-6. 환경변수

```env
# .env 에 추가
FASTER_WHISPER_MODEL=large-v3-turbo   # medium / large-v3-turbo
# GPU 서버면 자동 감지되므로 별도 설정 불필요
```

---

## 5. 기존 코드 재사용 가능 항목

전환 후에도 그대로 쓸 수 있는 것들:

| 항목 | 파일 | 재사용 여부 |
|---|---|---|
| `_HALLUCINATION_FRAGMENTS` | `stt_service.py` | ✅ 그대로 |
| `_is_prompt_echo()` | `stt_service.py` | ✅ 그대로 |
| `_normalize_payment_text()` | `stt_service.py` | ✅ 그대로 |
| `_detect_language()` | `stt_service.py` | ✅ (faster-whisper가 이미 감지하므로 fallback용) |
| `_STT_PROMPT` (메뉴 어휘 힌트) | `stt_service.py` | ⚠️ faster-whisper도 prompt 지원하나, `no_speech_threshold` 사용 시 불필요 |
| STT API 엔드포인트 | `api/stt.py` | ✅ 변경 없음 |
| ChatPanel STT 호출 코드 | `frontend/` | ✅ 변경 없음 |

---

## 6. 요약

| 항목 | 현재 | 전환 후 |
|---|---|---|
| 모델 | gpt-4o-mini-transcribe (API) | faster-whisper large-v3-turbo (로컬) |
| 할루시네이션 | 사후 필터로 일부 차단 | no_speech_threshold로 발생 차단 |
| 비용 | $0.003/min | 무료 |
| 지연시간 | 300–800ms + 네트워크 | CPU: 1–2s / GPU: 0.3–0.7s |
| 언어 지원 | ko/en/zh/ja | 동일 (Whisper 기반 동일) |
| 파라미터 제어 | 불가 | 완전 제어 |
| 추가 의존성 | 없음 | faster-whisper, ffmpeg |
