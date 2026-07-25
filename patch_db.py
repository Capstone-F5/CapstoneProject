import asyncio
from sqlalchemy import text
from backend.core.db import engine

async def main():
    print("비동기 DB 연결 중...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE orders ADD COLUMN status VARCHAR(32) DEFAULT 'RECEIVED';"))
            print("-> orders 테이블에 status 컬럼 추가 완료!")
        except Exception as e:
            print("-> status 컬럼이 이미 존재합니다.")

        try:
            await conn.execute(text("ALTER TABLE orders ADD COLUMN user_coupon_id VARCHAR(36);"))
            print("-> orders 테이블에 user_coupon_id 컬럼 추가 완료!")
        except Exception as e:
            print("-> user_coupon_id 컬럼이 이미 존재합니다.")

    print("🎉 DB 마이그레이션 적용 완료!")

if __name__ == "__main__":
    asyncio.run(main())
