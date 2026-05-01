import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from models import Base, User
from auth import get_password_hash
from config import settings

async def create_default_user():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            default_user = User(
                username="admin",
                password_hash=get_password_hash("admin123")
            )
            session.add(default_user)
            await session.commit()
            print("默认用户创建成功:")
            print("  用户名: admin")
            print("  密码: admin123")
        else:
            print("默认用户已存在")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_default_user())
