"""
分析配置相关API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import AnalysisConfig, DataSource
from app.schemas import (
    AnalysisConfigCreate,
    AnalysisConfigUpdate,
    AnalysisConfigResponse,
    ApiResponse
)

router = APIRouter(prefix="/analysis", tags=["分析配置"])


@router.post("/config", response_model=ApiResponse)
async def create_analysis_config(
    config: AnalysisConfigCreate,
    db: Session = Depends(get_db)
):
    """创建分析配置"""
    # 检查数据源是否存在
    data_source = db.query(DataSource).filter(DataSource.id == config.data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    db_config = AnalysisConfig(
        data_source_id=config.data_source_id,
        chart_type=config.chart_type,
        subgroup_size=config.subgroup_size,
        confidence_level=config.confidence_level,
        show_rules=config.show_rules,
        show_prediction=config.show_prediction
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return ApiResponse(
        success=True,
        message="分析配置创建成功",
        data={
            "id": db_config.id,
            "data_source_id": db_config.data_source_id,
            "chart_type": db_config.chart_type.value,
            "subgroup_size": db_config.subgroup_size,
            "confidence_level": db_config.confidence_level.value,
            "show_rules": db_config.show_rules,
            "show_prediction": db_config.show_prediction
        }
    )


@router.put("/config/{config_id}", response_model=ApiResponse)
async def update_analysis_config(
    config_id: int,
    config: AnalysisConfigUpdate,
    db: Session = Depends(get_db)
):
    """更新分析配置"""
    db_config = db.query(AnalysisConfig).filter(AnalysisConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="分析配置不存在")
    
    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    
    return ApiResponse(
        success=True,
        message="分析配置更新成功",
        data={
            "id": db_config.id,
            "chart_type": db_config.chart_type.value,
            "subgroup_size": db_config.subgroup_size,
            "confidence_level": db_config.confidence_level.value,
            "show_rules": db_config.show_rules,
            "show_prediction": db_config.show_prediction
        }
    )


@router.get("/config/{config_id}", response_model=ApiResponse)
async def get_analysis_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """获取分析配置详情"""
    db_config = db.query(AnalysisConfig).filter(AnalysisConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="分析配置不存在")
    
    return ApiResponse(
        success=True,
        data={
            "id": db_config.id,
            "data_source_id": db_config.data_source_id,
            "chart_type": db_config.chart_type.value,
            "subgroup_size": db_config.subgroup_size,
            "confidence_level": db_config.confidence_level.value,
            "show_rules": db_config.show_rules,
            "show_prediction": db_config.show_prediction,
            "statistics_result": db_config.statistics_result,
            "created_at": db_config.created_at.isoformat() if db_config.created_at else None,
            "updated_at": db_config.updated_at.isoformat() if db_config.updated_at else None
        }
    )


@router.get("/list/{data_source_id}", response_model=ApiResponse)
async def list_analysis_configs(
    data_source_id: int,
    db: Session = Depends(get_db)
):
    """获取指定数据源的分析配置列表"""
    configs = db.query(AnalysisConfig).filter(
        AnalysisConfig.data_source_id == data_source_id
    ).order_by(AnalysisConfig.created_at.desc()).all()
    
    return ApiResponse(
        success=True,
        data=[
            {
                "id": c.id,
                "chart_type": c.chart_type.value,
                "subgroup_size": c.subgroup_size,
                "confidence_level": c.confidence_level.value,
                "show_rules": c.show_rules,
                "show_prediction": c.show_prediction,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in configs
        ]
    )