import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Переключаемся на SQLite для локального MVP
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./notes_db.sqlite3")

# Для SQLite отключаем pool_size и max_overflow
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session