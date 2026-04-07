# 🤖 LLM 기반 지능형 양방향 배리어프리 키오스크
> **물리적 접근성 극복을 위한 지능형 서비스 디자인**

본 프로젝트는 기존 키오스크의 물리적·심리적 접근성 한계를 극복하기 위해, **LLM 기반 음성 인식 시스템**과 **컴퓨터 비전(CV) 기술**을 결합한 차세대 배리어프리 키오스크를 개발합니다.

## 📂 프로젝트 구조 (Project Structure)

```text
D:\Capstone\CapstoneProject
├── 📂 ai_modules/         # AI 핵심 기능 (STT, CV, LLM) 처리 모듈
│   ├── 📂 cv/             # 컴퓨터 비전 (제스쳐 인식) 관련 로직
│   ├── 📂 llm/            # LangChain 및 Gemini 연동/문맥 관리
│   └── 📂 stt/            # Whisper API 연동 및 음성 전처리
├── 📂 assets/             # 이미지, 아이콘 및 디자인 에셋
├── 📂 backend/            # FastAPI 기반 서버 사이드 소스
│   ├── 📂 api/            # API 엔드포인트 정의 (RESTful)
│   └── 📂 core/           # 서버 설정, 공통 유틸리티
├── 📂 database/           # DB 스키마, 마이그레이션 및 커넥션 관리
├── 📂 frontend/           # 웹 프론트엔드 (React/HTML) 소스
│   └── index.html         # 메인 진입 페이지 (터치/음성 모드)
└── README.md              # 프로젝트 가이드 및 문서
```

---

## 🚀 시작하기 (Getting Started)

### **1. 환경 변수 설정**
본 프로젝트는 보안을 위해 API 키 및 설정을 `.env` 파일로 관리합니다.
1. `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
   ```bash
   cp .env.example .env
   ```
2. 생성된 `.env` 파일에 발급받은 **OpenAI API Key** 및 **Google Gemini API Key**를 입력합니다.

---

## 📅 프로젝트 개요
- **주제**: 물리적 접근성 극복을 위한 LLM 기반 지능형 양방향 배리어프리 키오스크
- **기간**: 2026.03.03 ~ 2026.09.xx
- **조직**: 동양미래대학교 인공지능소프트웨어학과 3-QA (팀명: F5)
- **GitHub**: [https://github.com/Capstone-F5](https://github.com/Capstone-F5)
- **Notion**: [https://www.notion.so/e900f683ea6a83fab6b501875c1ff8e8]
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
- **LLM 기반 정규화**: 사투리나 불분명한 발언을 LLM을 통해 정제하여 인식률 향상.
- **대화 문맥 관리**: LangChain의 `SummaryBufferMemory`를 활용해 "아까 주문한 거 바꿔줘"와 같은 대명사 및 생략 표현 처리.
- **토큰 단위 스트리밍**: 실시간 응답을 위해 토큰 단위로 프론트엔드 및 TTS에 전달.

### 2. 비접촉 제스쳐 제어 (Computer Vision)
- **제스쳐 매핑**: 카메라를 통한 스와이핑(상하좌우), 주먹 쥐기 등 인식.
- **접근성 강화**: 휠체어 이용자 등 물리적으로 터치가 어려운 환경에서도 원격 조작 가능.

### 3. 멀티모달 상황 인지 및 맞춤형 UI
- **사용자 인식**: CV를 통해 연령대 및 환경을 인지하여 최적화된 메뉴 큐레이션 제공.
- **UI 전환 모드**: 일반 터치 모드와 시각장애인/노약자를 위한 음성 우선 모드 지원.
- **실시간 피드백**: 대화 파동 및 자막을 통해 인식 상태를 시각적으로 전달.

---

## 🛠 기술 스택

### **Backend**
- ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi) **FastAPI**: 비동기 이벤트 루프를 활용한 병렬 처리 파이프라인.
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) 

### **AI & Data**
- **LLM**: Gemini / OpenAI Whisper
- **Framework**: LangChain, OpenCV
- **Database**: 메뉴 및 결제 데이터 관리를 위한 DB 구축 예정

### **Frontend**
- **Web**: React (TypeScript 기반 배포 예정)

---

## 📈 프로젝트 진행 현황

- [x] 아이디어 제안 및 확정 (2026-03-17)
- [x] 팀 아이디어 제안서 작성 (2026-03-30)
- [x] 기능명세서 작성 완료 (2026-03-30)
- [ ] UI 디자인 (시작 전)
- [ ] Whisper API 연동 및 백엔드 파이프라인 구축 (진행 예정)
- [ ] DB 설계 및 구축 (시작 전)
