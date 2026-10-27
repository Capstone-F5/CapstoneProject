# 🤖 디지털 약자를 위한 음성 및 제스처 중심의 배리어프리 키오스크
> **물리적 접근성 극복을 위한 지능형 서비스 디자인**

본 프로젝트는 기존 키오스크의 물리적·심리적 접근성 한계를 극복하기 위해, **LLM 기반 음성 주문**과 **컴퓨터 비전(CV) 기술**을 결합한 배리어프리 키오스크(F BURGER)입니다.
손님은 터치, 음성, 손동작 중 편한 방식으로 주문하고, 흰 지팡이·휠체어 이용자가 키오스크에 다가오면 그에 맞는 입력 방식을 자동으로 안내합니다.

---

## 📂 프로젝트 구조 (Project Structure)

```text
CapstoneProject/
├── 📂 ai_modules/              # AI 핵심 기능 처리 모듈
│   ├── 📂 llm/                 # LangChain 에이전트·도구·규칙 가드·알레르기 응답·주문 파서·RAG
│   ├── 📂 cv/                  # 제스처 인식(MediaPipe), 접근 감지(YOLOv8n TFLite), 학습 스크립트
│   └── 📂 stt/                 # 음성 인식 모듈
├── 📂 backend/                 # FastAPI 서버
│   ├── main.py                 # 서버 진입점
│   ├── requirements.txt        # Python 의존성
│   ├── 📂 api/                 # REST / WebSocket 엔드포인트 (+ admin/ 관리자 API)
│   ├── 📂 core/                # 서비스 레이어 (LLM 서비스, STT/TTS, 직접 명령, 설정, 모델·시드)
│   ├── 📂 dao/                 # DB 접근 계층
│   ├── 📂 schemas/             # Pydantic 스키마
│   ├── 📂 tests/               # 단위 테스트
│   └── 📂 tools/               # 음성 시나리오 검증·비용 추정·벤치마크 도구
├── 📂 frontend/                # React 키오스크 UI + 관리자 대시보드
│   ├── index.html · admin.html · signup.html
│   ├── 📂 public/audio/        # 사전 녹음 TTS (자주 쓰는 안내·주문번호 조각)
│   └── 📂 src/
│       ├── 📂 screens/         # 키오스크 화면 12개 (시작·주문방식·메뉴·장바구니·결제·완료 등)
│       ├── 📂 components/      # 음성 대화 창(ChatPanel), 배속 컨트롤, 아이콘(Glyph) 등
│       ├── 📂 hooks/           # 제스처, 접근 감지, 시리얼(아두이노), 유휴 타이머 등
│       ├── 📂 admin/           # 관리자 페이지 (대시보드·메뉴·주문·결제·회원·쿠폰·키오스크 설정)
│       ├── 📂 services/ · utils/   # API 통신, 오디오 게이트·TTS 캐시·배속 등
│       └── 📂 i18n/            # 다국어 (한국어/영어/중국어/일본어)
├── 📂 deploy/raspberry-pi/     # 라즈베리파이 4B 키오스크 모드 실행 스크립트·Chromium 정책
├── 📂 docs/                    # 작업 일지, 명세, 성능·비용 문서
├── start_servers.bat / .ps1    # 백엔드 + 프론트엔드 한 번에 실행 (빈 포트 자동 탐색)
├── .env.example                # 환경 변수 예시
└── README.md
```

---

## 🚀 시작하기 (Getting Started)

### 사전 준비
Python 3.10+, Node.js 18+, MySQL 8.0+, OpenAI API 키. 자세한 설치는 [`docs/개발환경_설정_가이드.md`](docs/개발환경_설정_가이드.md)를 참고하세요.

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env`에 최소한 아래 값을 채웁니다.

```env
OPENAI_API_KEY=sk-...
DB_HOST=...  DB_PORT=3306  DB_USER=...  DB_PASSWORD=...  DB_NAME=kiosk_db
ADMIN_JWT_SECRET=<긴 임의 문자열>
ADMIN_BOOTSTRAP_USERNAME=admin
ADMIN_BOOTSTRAP_PASSWORD=<첫 로그인 후 변경>
```

모델 이름(`OPENAI_LLM_MODEL=gpt-4o-mini`, `OPENAI_STT_MODEL=whisper-1`, `OPENAI_TTS_MODEL=tts-1` 등)과 그 외 항목은 `.env.example`에 있습니다.
테이블은 서버 첫 기동 때 자동으로 만들어지고 메뉴·알레르기 등 초기 데이터가 시드됩니다(마이그레이션 도구는 없음 — [`docs/DB_스키마_현황.md`](docs/DB_스키마_현황.md)).

### 2. 한 번에 실행 (Windows)

```bash
start_servers.bat      # 백엔드(기본 8000)와 프론트엔드(기본 5173)를 각각 새 창에서 실행, 사용 중인 포트는 자동으로 건너뜀
```

### 3. 개별 실행

```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules   # → http://localhost:8000 (API 문서: /docs)

# 프론트엔드
cd frontend
npm install
npm run dev                                                           # → https://localhost:5173
```

- **키오스크**: `/`, **관리자**: `/admin` (초기 계정은 `.env`의 `ADMIN_BOOTSTRAP_*`)
- 프론트는 개발 서버를 HTTPS로 띄웁니다(마이크·카메라·Web Serial 권한). 외부 TLS(Cloudflare Tunnel 등)를 쓰면 `VITE_HTTPS=false`.
- 라즈베리파이 4B는 브라우저 클라이언트로만 쓰고(Chromium 키오스크 모드, `deploy/raspberry-pi/`), AI 추론과 서버는 PC에서 돌립니다.

---

## 📅 프로젝트 개요

- **주제**: 물리적 접근성 극복을 위한 LLM 기반 지능형 양방향 배리어프리 키오스크
- **기간**: 2026.03.03 ~ 2026.09.xx
- **조직**: 동양미래대학교 인공지능소프트웨어학과 3-QA (팀명: F5)
- **GitHub**: [https://github.com/Capstone-F5](https://github.com/Capstone-F5)
- **Notion**: [Notion(F5_캡스톤디자인)](https://jewel-flock-61a.notion.site/5081121f427f8269b90f81736fb291f6?pvs=73)
- **회의록(Notion)**: [회의록 모음](https://app.notion.com/p/e6a1121f427f8390a48e0100cc786def?source=copy_link)

---

## 👥 팀원 소개 및 역할

| 이름 | 학번 | 역할 | 담당 업무 |
| :--- | :---: | :---: | :--- |
| **조예성** | 20241519 | **팀장** | 웹 프론트엔드 개발, 기능명세서 작성 |
| **김명서** | 20242513 | 팀원 | UI/UX 디자인, 아이디어 기획 |
| **진수민** | 20241479 | 팀원 | UI/UX 디자인, 아이디어 기획 |
| **김성원** | 20241491 | 팀원 | 백엔드 구현 (음성인식/로직), LLM 연동 |
| **임지연** | 20242514 | 팀원 | 백엔드 구현 (음성인식/로직), 비동기 파이프라인 |
| **서유민** | 20242517 | 팀원 | 데이터베이스 설계 및 구축, 제안서 작성 |

---

## ✨ 핵심 기능

### 1. LLM 음성 주문 (STT → LLM → TTS)
- **STT**: OpenAI Whisper(`whisper-1`). 전송 전 브라우저에서 Silero VAD와 음향 게이트(음량·신호 대 잡음비·지속 시간)로 소음·충격음을 거르고, 서버에서 신뢰도(`no_speech_prob`·`avg_logprob`·압축비)와 환각 문구 필터를 한 번 더 적용합니다.
- **STT 오인식 교정**: "내장에서 먹을게요 → 매장에서", "단풍 → 단품", "정립할게 → 적립할게"처럼 실제 로그에서 나온 오인식을 문맥 조건부 규칙으로 교정합니다.
- **LangChain 도구 호출 에이전트**(`gpt-4o-mini`): 메뉴 담기·삭제·옵션 변경·결제 진행 등을 화면 액션으로 내보내고, 대화 문맥(`SummaryBufferMemory`)으로 "아까 뺀 거 다시 담아줘" 같은 생략 표현을 처리합니다.
- **규칙 기반 가드**: 모델이 도구를 잘못 부르거나 "담았습니다"라고 말만 하는 사고를 코드가 막거나 바로잡습니다(메뉴 id 대신 이름, 무관한 줄 삭제, 단품/세트 가정, 같은 줄 반복 수정, 결제 단계 건너뛰기 등).
- **직접 명령(LLM 우회)**: 문장 모양이 분명한 명령은 코드가 바로 처리해 빠르고 일관됩니다 — 되돌리기, 세트 한 번에 담기, 단품↔세트, 세트 옵션 변경, 줄 삭제, 하나 빼기, 수량 지정("5개로 바꿔줘"), 교체("A 말고 B 세트로 바꿔줘").
- **알레르기 안내**: DB의 알레르기 마스터와 메뉴별 성분으로 코드가 직접 답하고, 손님이 밝힌 성분이 든 메뉴는 이름을 말하지 않은 채 담지 못하게 막습니다.
- **TTS**: OpenAI `tts-1` 스트리밍 + 자주 쓰는 안내문은 사전 녹음(`frontend/public/audio`)으로 즉시 재생. 대화 음성은 **음성 대화 창에서 배속 조절** 가능(관리자가 기본·최소·최대 배속 설정).
- **결제 흐름**: 포인트 적립 질문 → 전화번호 → 결제 수단 순서를 코드가 강제하고, 음성 모드에서는 번호 입력창이 열릴 때 안내합니다.

### 2. 접근 감지 (흰 지팡이 · 휠체어)
- 대기 화면에서 카메라 프레임(2fps)을 서버로 보내 **YOLOv8n INT8 TFLite**(3클래스: 사람·흰 지팡이·휠체어)로 접근을 감지합니다(`/ws/approach`, `ai-edge-litert`).
- 흰 지팡이 → **음성 대화 모드**, 휠체어 → **제스처 모드**를 자동으로 켜고, 여러 프레임에서 연속 감지돼야 확정합니다. 배경 변화가 없으면 프레임 전송을 줄이는 모션 게이트가 있습니다.
- 학습 시 기록된 mAP@0.5는 0.936입니다. 학습 데이터와 겹칠 수 있는 평가이므로 현장 성능은 별도 검증이 필요합니다 — [`docs/AI 모델 성과 지표.md`](docs/AI%20모델%20성과%20지표.md).

### 3. 비접촉 제스처 제어 (Computer Vision)
- **MediaPipe Hands**(브라우저 온디바이스)로 21개 손 관절을 추출해 커서 이동·선택(스와이프, OK 사인, 손가락 개수, 검지 포인터)을 처리합니다. 서버용 WebSocket(`/ws/gesture`, `/ws/finger`)도 있습니다.
- 손 인식 거리, 화면 매핑 마진, 목표 FPS는 관리자 설정에서 실시간 튜닝합니다(Pi 4B 부하 조절용 프리셋 포함).

### 4. 터치 주문·결제·하드웨어
- 12개 화면(시작 / 주문방식 / 메뉴 / 단품·세트 / 장바구니 / 결제 수단 / 카드·현금·간편결제 / 완료 / 회원가입), 4개 언어(한/영/중/일) 전환, 유휴 시 처음으로 복귀.
- 아두이노 **Web Serial** 연동(지폐·동전·카드 신호), 쿠폰 QR·바코드 스캔, 포인트 적립(30일 만료), 할인 적용, 주문번호 음성 낭독.

### 5. 관리자 대시보드 (`/admin`)
- 대시보드·메뉴(알레르기·옵션 포함)·주문·결제·회원·쿠폰·할인 관리(JWT 로그인).
- **키오스크 설정(개발자 옵션)**: 마이크 감도, 접근 감지 거리·신뢰도, 제스처 파라미터, 음성 배속을 DB 마이그레이션 없이 실시간 조회·수정하고, 실시간 마이크·카메라 테스트와 최근 감지·차단 로그를 볼 수 있습니다.

---

## 🛠 기술 스택

| 영역 | 사용 기술 |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2 (async) + aiomysql, httpx, JWT(python-jose)·bcrypt |
| **DB** | MySQL 8.0 (`utf8mb4`) — 앱 기동 시 테이블·시드 자동 생성 |
| **LLM / RAG** | OpenAI `gpt-4o-mini`, LangChain 0.2 (에이전트·메모리), FAISS, `text-embedding-3-small` |
| **음성** | OpenAI `whisper-1`(STT), `tts-1`(TTS), Silero VAD(브라우저, ONNX) |
| **CV** | MediaPipe Hands/Tasks, OpenCV, YOLOv8n → INT8 TFLite (`ai-edge-litert`) |
| **Frontend** | React 18, Vite 5, onnxruntime-web, ZXing(QR·바코드) |
| **기기** | Raspberry Pi 4B(Chromium 키오스크), 웹캠·마이크, 아두이노(Web Serial) |

---

## 🧪 테스트와 검증

### 단위 테스트
```bash
# 프로젝트 루트와 backend 폴더가 모두 파이썬 경로에 있어야 합니다 (ai_modules, core 임포트)
cd backend
PYTHONPATH=..:. python -m unittest tests.test_guards tests.test_action_guards tests.test_cart_commands \
  tests.test_allergy tests.test_kiosk_tts_settings tests.test_flow_gen tests.test_suite_metrics   # 다른 test_*.py도 같은 방식
cd ../frontend
node --test tests/menuOptions.test.js tests/ttsSpeed.test.js
```
> 파이썬 환경의 site-packages에 다른 `tests` 패키지가 설치돼 있으면 프로젝트 `tests`를 가려 임포트 오류가 납니다(Windows 팀원 환경에서 확인). 그때는 가상환경에서 해당 패키지를 제거하거나 `tests` 패키지 경로를 프로젝트의 `backend/tests`로 지정하세요. `test_pricing.py`의 2건은 기존 실패입니다.

### 음성 시나리오 검증 (백엔드 실행 필요, OpenAI 비용 발생)
`backend/tools/voice_scenario_suite.py`가 STT 이후 텍스트를 서버에 넣어 액션·장바구니·응답을 자동 검증합니다. 기대 장바구니는 참조 장바구니가 자동 계산합니다.

```bash
cd backend
python tools/voice_scenario_suite.py --url http://localhost:8000 --category 회귀            # 실제 로그에서 나온 실패 사례(G01~)
python tools/voice_scenario_suite.py --url http://localhost:8000 --category 대량 --workers 4 # 고정 100개(W001~W100)
python tools/voice_scenario_suite.py --url http://localhost:8000 --random 50 --seed 1 --tier 사람처럼 --human 1
python tools/voice_scenario_suite.py --random 10 --dry-run                                  # 발화만 확인 (비용 0)
python tools/persona_sim.py --count 4 --dry-run                                             # LLM 손님 시뮬레이터(탐색용)
```

- `--tier 사람처럼`은 마음 바꾸기·질문 끼워 넣기·주변 소음·알레르기·결제 실수를, `--human 0|1|2`는 군말과 STT 오인식을 섞습니다.
- 결과는 시나리오 통과율 외에 **연쇄 실패를 제외한 턴당 실패율**, 조작별 신뢰구간, 응답 시간으로 집계합니다.
- 최근 측정(2026-10-26): 고정 100개 **99/100**, 사람처럼 50개 **49/50**, 회귀 13/13. 수정과 같은 시드로 측정한 값이라 일반화된 성능이 아니며, 텍스트만 보내므로 마이크·VAD·실제 STT 오인식은 포함하지 않습니다. 자세한 내용은 [`docs/2026-10-26.md`](docs/2026-10-26.md).

### API 비용
음성 1턴 약 $0.0024(LLM + STT + TTS), 음성 주문 1건(약 11턴) 약 37원입니다. 월 비용은 [`docs/API_비용_추정_2026-10-03.md`](docs/API_비용_추정_2026-10-03.md)와 `backend/tools/api_cost_estimate.py`로 계산합니다.

---

## 📈 프로젝트 진행 현황

- [x] 아이디어 제안·기능명세서·UI/UX 디자인
- [x] React 키오스크 UI (12개 화면) 및 다국어(한/영/중/일)
- [x] FastAPI 백엔드, MySQL DB 설계·구축(회원·메뉴·알레르기·주문·결제·쿠폰·할인)
- [x] STT·TTS, LLM 에이전트 주문 파이프라인, 규칙 기반 가드·직접 명령
- [x] 손동작 인식(MediaPipe)과 제스처 커서 제어
- [x] 흰 지팡이·휠체어 접근 감지 및 입력 모드 자동 전환
- [x] 관리자 대시보드와 키오스크 개발자 설정(실시간 튜닝)
- [x] 아두이노 시리얼 결제 연동, 라즈베리파이 4B 키오스크 배포
- [x] 음성 시나리오 자동 검증 체계(고정 100개·랜덤·회귀)
- [ ] 접근 감지 현장 성능 검증(흰 지팡이 재현율 개선, 오탐 억제)
- [ ] 실제 매장 환경 음성 인식 검증(마이크 게이트·STT 오인식)
- [ ] 알레르기 시드 데이터의 실제 레시피 기준 검증

---

## 📚 문서

| 문서 | 내용 |
| :--- | :--- |
| [`docs/2026-10-26.md`](docs/2026-10-26.md) · [`docs/2026-10-22.md`](docs/2026-10-22.md) | 작업 일지 (음성 로그 분석·검증 도구 / 접근 감지·제스처 튜닝) |
| [`docs/인수인계_2026-10-02.md`](docs/인수인계_2026-10-02.md) | 인수인계, 다른 PC 환경 세팅, 테스트 실행법 |
| [`docs/DB_스키마_현황.md`](docs/DB_스키마_현황.md) | 테이블별 스키마 |
| [`docs/백엔드_기능명세.md`](docs/백엔드_기능명세.md) | 백엔드 기능 명세 |
| [`docs/AI 모델 성과 지표.md`](docs/AI%20모델%20성과%20지표.md) | 접근 감지·제스처 모델 지표와 한계 |
| [`docs/성능_검증_결과_2026-10-03.md`](docs/성능_검증_결과_2026-10-03.md) | 성능 검증 결과 |
| [`docs/raspberry-pi-optimization.md`](docs/raspberry-pi-optimization.md) | 라즈베리파이 최적화 |
| [`docs/개발환경_설정_가이드.md`](docs/개발환경_설정_가이드.md) | 처음 실행하는 사람을 위한 설정 |

---

## 🔎 프로젝트 다이어그램
<img width="1600" height="2410" alt="20260402_083028" src="https://github.com/user-attachments/assets/c62dc136-8084-430f-a168-a72c179524ca" />
