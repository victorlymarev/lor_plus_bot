from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


engine = create_async_engine(url='sqlite+aiosqlite:///../db/database.db')
async_session = async_sessionmaker(engine, class_=AsyncSession)


class Base(DeclarativeBase):
    pass
