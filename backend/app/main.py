"""
SPC Agent 后端主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.api import data, analysis, monitor, spc, settings as settings_api

# 创建上传目录
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    from app.services.monitor import start_scheduler
    start_scheduler()
    print(f"[OK] {settings.APP_NAME} v{settings.APP_VERSION} started")
    
    yield
    
    # 关闭时
    from app.services.monitor import stop_scheduler
    stop_scheduler()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SPC Agent - 统计过程控制智能助手 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录（用于文件上传）
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册路由
app.include_router(data.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(spc.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api/settings")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 数据库初始化命令
@app.on_event("startup")
async def init_database():
    """初始化数据库表"""
    from app.core.database import engine, Base
    from app.models import models
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables initialized")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )