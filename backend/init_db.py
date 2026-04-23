"""
数据库初始化脚本
用于在 spc_agent_demo schema 下创建表
"""
import sys

# 强制 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import engine, Base
from app.models.models import (
    DataSource, AnalysisConfig, MonitorTask,
    AnomalyRecord, AIAnalysisRecord, SystemSettings
)


def init_db():
    """初始化数据库表"""
    print("[OK] 开始创建数据库表...")

    # 创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)

    print("[OK] 数据库表创建完成！")
    print("已创建的表：")
    for table in Base.metadata.tables:
        print(f"  - {table}")


if __name__ == "__main__":
    init_db()
