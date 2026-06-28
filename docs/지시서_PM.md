# 작업 지시서 — PM (조예성)

> 이 지시서의 작업을 **모두 완료한 후** DB 파트·AI 파트 담당자에게 각자의 지시서를 배포한다.

---

## Step 1. 환경변수 파일 정비

- [ ] `.env.example` 열기
- [ ] 아래 두 줄 추가 후 저장
  ```
  VITE_API_URL=http://localhost:8000
  API_BASE_URL=http://localhost:8000
  ```
- [ ] 팀 전체에 `.env` 세팅 방법 공유 (카카오톡 or 노션)
  - 루트 `.env` → 백엔드용
  - `frontend/.env` → 프론트용 (`VITE_` 접두사 변수)

## Step 2. 폴더 생성

터미널에서 아래 명령 실행:

```powershell
New-Item -ItemType Directory -Force backend/dao
New-Item -ItemType File -Force backend/dao/__init__.py
New-Item -ItemType Directory -Force backend/schemas
New-Item -ItemType File -Force backend/schemas/__init__.py
```

완료 확인: `backend/dao/`와 `backend/schemas/` 폴더가 존재하면 OK.

## Step 3. Git 브랜치 생성 및 규칙 공지

- [ ] `feature/db-api-server` 브랜치 생성 후 서유민에게 전달
  ```powershell
  git checkout -b feature/db-api-server
  git push -u origin feature/db-api-server
  ```
- [ ] `feature/llm-db-tools` 브랜치 생성 (아직 배포 안 함 — DB 파트 완료 후 배포)
  ```powershell
  git checkout main
  git checkout -b feature/llm-db-tools
  git push -u origin feature/llm-db-tools
  ```
- [ ] 팀에 머지 순서 공지: **DB 파트 → main 머지 완료 후** AI 파트 착수

## Step 4. 지시서 배포

- [ ] `docs/지시서_DB파트.md` → 서유민에게 전달
- [ ] `docs/지시서_AI파트.md` → 김성원·임지연에게 전달
- [ ] 각자 착수 전에 `docs/PM_사전작업.md`의 **API 인터페이스 계약** 섹션을 읽도록 안내

## Step 5. DB 파트 완료 시 PM이 할 일

서유민이 "완료" 신호를 보내면:

- [ ] `feature/db-api-server` → `main` PR 생성 및 직접 코드 리뷰
- [ ] 로컬에서 `GET http://localhost:8000/api/menu` 응답 확인
- [ ] 프론트 `frontend/.env`에 `VITE_API_URL=http://localhost:8000` 설정 후 메뉴 화면 직접 확인
- [ ] 이상 없으면 머지 → 김성원·임지연에게 AI 파트 착수 신호

## Step 6. 최종 통합 검수

AI 파트 완료 신호 수신 후:

- [ ] `feature/llm-db-tools` → `main` PR 리뷰
- [ ] 음성 입력 "F버거 세트 하나 주세요" → 장바구니 화면 확인
- [ ] DB에 `cart_items` 레코드 생성 여부 확인
- [ ] `docs/PM_사전작업.md` 맨 아래 체크리스트 6항목 전부 통과

---

**완료 기준:** Step 6 체크리스트 전부 통과 → 통합 완료 선언
