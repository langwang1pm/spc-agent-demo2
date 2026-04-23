"""
数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库连接URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://le_owner:PG^le=[2021)@sh-postgres-h3849b66.sql.tencentcdb.com:21656/icoastline"
)

# 数据库Schema
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "spc_agent_demo")

# 创建引擎，设置search_path到指定schema
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=os.getenv("APP_DEBUG", "false").lower() == "true"
)

# 设置默认schema
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {DATABASE_SCHEMA}, public;")
    cursor.close()

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()