"""
系统设置相关API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import SystemSettings
from app.schemas import SystemSettingsUpdate, SystemSettingsResponse, ApiResponse

router = APIRouter(prefix="/settings", tags=["系统设置"])


@router.get("/", response_model=ApiResponse)
async def get_settings(db: Session = Depends(get_db)):
    """获取系统设置"""
    settings = db.query(SystemSettings).first()
    
    if not settings:
        # 如果没有设置，创建一个默认的
        settings = SystemSettings(
            decimal_places=2,
            chart_theme="default",
            auto_save=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return ApiResponse(
        success=True,
        data={
            "decimal_places": settings.decimal_places,
            "chart_theme": settings.chart_theme,
            "auto_save": settings.auto_save
        }
    )


@router.put("/", response_model=ApiResponse)
async def update_settings(
    update_data: SystemSettingsUpdate,
    db: Session = Depends(get_db)
):
    """更新系统设置"""
    settings = db.query(SystemSettings).first()
    
    if not settings:
        settings = SystemSettings()
        db.add(settings)
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    return ApiResponse(
        success=True,
        message="设置更新成功",
        data={
            "decimal_places": settings.decimal_places,
            "chart_theme": settings.chart_theme,
            "auto_save": settings.auto_save
        }
    )