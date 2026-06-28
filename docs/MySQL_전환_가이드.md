# MySQL 전환 가이드

> 현재 코드베이스는 SQLite(`aiosqlite`)로 동작한다.  
> DB 파트 작업 시작 전에 MySQL로 전환한다.  
> SQLAlchemy를 추상화 계층으로 사용하고 있어 **코드 변경은 최소화**되고,  
> 설정 파일과 드라이버 교체가 핵심이다.

---

## 변경 대상 파일 요약

| 파일 | 변경 내용 |
|---|---|
| `backend/requirements.txt` | `aiosqlite` 제거, `aiomysql` 추가 |
| `backend/core/db.py` | 엔진 옵션에 MySQL 전용 설정 추가 |
| `.env.example` / `.env` | `DATABASE_URL` 형식 변경 |
| `backend/core/models.py` | **수정 불필요** — 이미 MySQL 호환 타입 사용 중 |

---

## 1. requirements.txt 수정

`backend/requirements.txt`의 DB 섹션을 아래와 같이 교체:

```diff
 # DB
 SQLAlchemy>=2.0.30
-aiosqlite>=0.20.0
-greenlet>=3.0.0
+aiomysql>=0.2.0
```

> `aiomysql`은 SQLAlchemy의 `mysql+aiomysql://` 드라이버.  
> `greenlet`은 `aiosqlite`의 의존성이었으므로 함께 제거한다.

설치:
```bash
pip install -r requirements.txt
```

---

## 2. db.py 수정

`backend/core/db.py`를 아래와 같이 교체:

```python
"""
SQLAlchemy 비동기 엔진 / 세션 / Base.
DB URL은 .env의 DATABASE_URL (MySQL 기본값)
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:password@localhost:3306/kiosk_db?charset=utf8mb4"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,    # 끊긴 커넥션 자동 감지
    pool_size=10,
    max_overflow=20,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """FastAPI Depends용 세션 컨텍스트."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """앱 시작 시 테이블 생성 + 메뉴 시드."""
    from . import models  # noqa: F401
    from .seed import seed_menu

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await seed_menu(session)
```

**변경 포인트:**
- `pool_pre_ping=True` — MySQL은 idle 상태에서 커넥션이 끊기는 경우가 있어 필수
- `pool_size`, `max_overflow` — SQLite는 단일 파일이라 불필요했지만 MySQL은 명시 권장
- `charset=utf8mb4` — 한국어·이모지 정상 저장

---

## 3. .env 수정

DB 서버 주소·계정 정보를 개별 환경변수로 관리한다.  
`db.py`가 이 값들을 조합해 연결 URL을 자동 생성한다.

```env
DB_HOST=실제DB서버주소       # 예: db.example.com 또는 192.168.0.10
DB_PORT=3306
DB_USER=계정명
DB_PASSWORD=비밀번호
DB_NAME=kiosk_db
```

전체 URL을 직접 지정하고 싶을 때는 `DATABASE_URL` 하나로 오버라이드 가능:
```env
# DATABASE_URL이 있으면 위의 DB_* 변수를 모두 무시하고 이 값을 우선 사용
DATABASE_URL=mysql+aiomysql://계정:비밀번호@호스트:3306/kiosk_db?charset=utf8mb4
```

---

## 4. MySQL 데이터베이스 생성

SQLite와 달리 MySQL은 데이터베이스를 **서버 기동 전에 미리 만들어야** 한다.  
테이블은 `init_db()` 가 자동 생성하므로 DB만 만들면 된다.

MySQL CLI:
```sql
CREATE DATABASE kiosk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

MySQL Workbench 사용 시:
1. 좌측 패널 빈 곳 우클릭 → `Create Schema`
2. Name: `kiosk_db`
3. Charset: `utf8mb4`, Collation: `utf8mb4_unicode_ci`
4. Apply

---

## 5. DB 파트 담당자 주의사항

`DB_파트_작업명세.md`에 적힌 라우터 코드에서 세션 의존성 함수 이름 확인:

```python
# db.py의 함수명은 get_session() 이다 — get_db()가 아님
from core.db import get_session

# 라우터에서 사용 시
async def endpoint(db: AsyncSession = Depends(get_session)):
    ...
```

명세서에 `get_db`로 표기된 부분은 모두 `get_session`으로 대체해서 사용한다.

---

## 6. 전환 확인

서버 기동 후 아래 로그가 없으면 정상:
```
# 에러 없이 기동 완료 시
INFO:     Application startup complete.
```

MySQL Workbench에서 `kiosk_db` → `Tables`에 아래 13개 테이블이 생성되면 성공:
- users, memberships, coupons, user_coupons
- categories, menu_items, menu_options, discounts
- carts, cart_items, orders, order_items, payments

---

## SQLite → MySQL 호환성 메모

현재 `models.py`는 이미 MySQL 호환 타입을 사용하고 있어 수정이 불필요하다.

| 확인 항목 | 현재 상태 |
|---|---|
| `String` 길이 지정 | ✅ 모두 `String(36)`, `String(64)` 등 명시됨 |
| `Text` 타입 | ✅ MySQL의 `TEXT`와 동일 |
| `JSON` 타입 | ✅ MySQL 5.7.8+ 네이티브 지원 |
| `Numeric(12,2)` | ✅ MySQL `DECIMAL(12,2)` 매핑 |
| `server_default=func.now()` | ✅ MySQL `DEFAULT CURRENT_TIMESTAMP` |
| `onupdate=func.now()` | ✅ MySQL `ON UPDATE CURRENT_TIMESTAMP` |
