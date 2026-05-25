# 🤖 디지털 약자를 위한 음성 및 제스처 중심의 배리어프리 키오스크
> **물리적 접근성 극복을 위한 지능형 서비스 디자인**

본 프로젝트는 기존 키오스크의 물리적·심리적 접근성 한계를 극복하기 위해, **LLM 기반 음성 인식 시스템**과 **컴퓨터 비전(CV) 기술**을 결합한 차세대 배리어프리 키오스크를 개발합니다.

## 📂 프로젝트 구조 (Project Structure)

```text
CapstoneProject/
├── 📂 ai_modules/          # AI 핵심 기능 처리 모듈
│   ├── 📂 cv/              # 컴퓨터 비전 (제스처 인식) — MediaPipe 기반
│   ├── 📂 llm/             # LangChain 및 GPT 연동/문맥 관리
│   └── 📂 stt/             # OpenAI Whisper API 연동 및 음성 전처리
├── 📂 assets/              # 이미지, 아이콘 및 디자인 에셋
├── 📂 backend/             # FastAPI 기반 서버
│   ├── main.py             # 서버 진입점
│   ├── requirements.txt    # Python 의존성
│   ├── 📂 api/             # API 엔드포인트 (WebSocket / REST)
│   └── 📂 core/            # 서비스 레이어 (AI 모듈 래퍼)
├── 📂 database/            # DB 스키마, 마이그레이션 및 커넥션 관리
├── 📂 frontend/            # React 기반 키오스크 UI
│   └── 📂 src/
│       ├── 📂 screens/     # 화면 컴포넌트 (11개 화면)
│       ├── 📂 components/  # 공통 UI 컴포넌트
│       ├── 📂 hooks/       # 커스텀 훅 (제스처, 유휴 타이머 등)
│       ├── 📂 services/    # API 통신 레이어
│       └── 📂 i18n/        # 다국어 지원 (한국어/영어/중국어/일본어)
├── .env.example            # 환경 변수 예시 파일
└── README.md
```

---

## 🚀 시작하기 (Getting Started)

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 발급받은 **OpenAI API Key**를 입력합니다.

```env
OPENAI_API_KEY=sk-...
```

### 2. 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
```

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 📅 프로젝트 개요

- **주제**: 물리적 접근성 극복을 위한 LLM 기반 지능형 양방향 배리어프리 키오스크
- **기간**: 2026.03.03 ~ 2026.09.xx
- **조직**: 동양미래대학교 인공지능소프트웨어학과 3-QA (팀명: F5)
- **GitHub**: [https://github.com/Capstone-F5](https://github.com/Capstone-F5)
- **Notion**: [Notion(F5_캡스톤디자인)](https://jewel-flock-61a.notion.site/5081121f427f8269b90f81736fb291f6?pvs=73)

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

### 1. 지능형 음성 대화 시스템 (LLM & STT/TTS)
- **OpenAI Whisper API**: 고정밀 음성-텍스트 변환(STT) 수행.
- **LLM 기반 정규화**: 사투리나 불분명한 발언을 GPT를 통해 정제하여 인식률 향상.
- **대화 문맥 관리**: LangChain의 `SummaryBufferMemory`를 활용해 "아까 주문한 거 바꿔줘"와 같은 대명사 및 생략 표현 처리.
- **토큰 단위 스트리밍**: 실시간 응답을 위해 토큰 단위로 프론트엔드 및 TTS에 전달.

### 2. 비접촉 제스처 제어 (Computer Vision)
- **실시간 손 인식**: MediaPipe Hands로 21개 손 관절 좌표를 추출, FastAPI WebSocket으로 스트리밍.
- **지원 제스처**: 스와이프(상/하/좌/우), OK 사인, 손가락 개수(1~5), 검지 포인터 추적.
- **접근성 강화**: 휠체어 이용자 등 물리적으로 터치가 어려운 환경에서도 원격 조작 가능.

### 3. 멀티모달 상황 인지 및 맞춤형 UI
- **다국어 지원**: 한국어 / 영어 / 중국어(간체) / 일본어 실시간 전환.
- **UI 전환 모드**: 일반 터치 모드와 음성 우선 모드 지원.
- **실시간 피드백**: 제스처 포인터 오버레이 및 인식 라벨로 인식 상태 시각적 전달.

---

## 🛠 기술 스택

### Backend
- ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi) **FastAPI** + **Uvicorn**: 비동기 WebSocket 기반 실시간 처리
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) **Python 3.10+**

### AI & Data
- **STT**: OpenAI Whisper API (`whisper-1`)
- **LLM**: OpenAI GPT (예정)
- **CV**: MediaPipe Hands, OpenCV
- **Framework**: LangChain (예정)
- **Database**: SQLite → 추후 확장 예정

### Frontend
- ![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black) **React 18** + **Vite**

---

## 📈 프로젝트 진행 현황

- [x] 아이디어 제안 및 확정 (2026-03-17)
- [x] 팀 아이디어 제안서 작성 (2026-03-30)
- [x] 기능명세서 작성 완료 (2026-03-30)
- [x] UI/UX 디자인
- [x] React 키오스크 UI 구현 (11개 화면: 시작 / 주문방식 / 메뉴 / 장바구니 / 결제 / 완료 등)
- [x] 다국어 지원 (한국어 / 영어 / 중국어 / 일본어)
- [x] 손동작 인식 모듈 구현 (MediaPipe — 스와이프, OK, 손가락 개수)
- [x] FastAPI 백엔드 서버 구축 (WebSocket 제스처 API)
- [x] STT 모듈 구현 (OpenAI Whisper API 연동)
- [ ] STT 백엔드 REST 엔드포인트 구현
- [ ] LLM (GPT) 연동 및 대화 파이프라인 구축
- [ ] DB 설계 및 구축

---

## 🔎 프로젝트 다이어그램
<img width="1600" height="2410" alt="20260402_083028" src="https://github.com/user-attachments/assets/c62dc136-8084-430f-a168-a72c179524ca" />
