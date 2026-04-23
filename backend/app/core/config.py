"""
应用配置
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    APP_NAME: str = "SPC Agent"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://le_owner:PG^le=[2021)@sh-postgres-h3849b66.sql.tencentcdb.com:21656/icoastline"
    DATABASE_SCHEMA: str = "spc_agent_demo"
    
    # 飞书配置
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    FEISHU_WEBHOOK_URL: Optional[str] = None
    
    # Dify AI配置
    DIFY_API_URL: str = "https://api.dify.ai/v1"
    DIFY_API_KEY: Optional[str] = None
    
    # 监控配置
    MONITOR_DEFAULT_INTERVAL: int = 10  # 默认监控间隔（秒）
    
    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()