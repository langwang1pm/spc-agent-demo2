"""
监控任务相关API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import MonitorTask, DataSource, AnalysisConfig
from app.schemas import MonitorTaskCreate, MonitorTaskResponse, ApiResponse
from app.services.monitor import add_monitor_job, remove_monitor_job, run_monitor_task, get_running_tasks
from app.services.system_query import get_system_data_values, SystemQueryError
from datetime import datetime
import json

router = APIRouter(prefix="/monitor", tags=["监控任务"])


def _get_latest_data_from_source(data_source: DataSource, subgroup_size: int = 5) -> list:
    """
    从数据源获取最新一次查询到的数据，返回一维数组。
    
    支持:
    - SYSTEM: 从外部系统实时查询
    - FILE: 从文件读取
    - MANUAL: 从 data_values 字段获取
    """
    source_type = data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type)
    
    if source_type == 'system':
        # 系统对接数据源 - 从外部系统查询
        raw_values = get_system_data_values(
            system_type=data_source.system_type.value,
            connection_config=data_source.connection_config,
            query_config=data_source.query_config
        )
        return raw_values  # 返回一维数组
    
    elif source_type == 'file':
        # 文件导入 - 从文件读取
        if not data_source.file_path:
            return []
        from app.api.spc import _parse_file_values
        values_2d = _parse_file_values(data_source.file_path)
        # 转换为一维数组
        result = []
        for group in values_2d:
            result.extend(group)
        return result
    
    else:
        # 手动输入 - 从 data_values 获取
        raw_data = data_source.data_values
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        if not raw_data:
            return []
        if isinstance(raw_data[0], (int, float)):
            return raw_data  # 本身是一维数组
        else:
            # 二维数组转换为一维
            result = []
            for group in raw_data:
                result.extend(group)
            return result


@router.post("/tasks", response_model=ApiResponse)
async def create_monitor_task(
    task: MonitorTaskCreate,
    db: Session = Depends(get_db)
):
    """
    创建监控任务
    
    流程:
    1. 保存分析配置到 analysis_configs 表
    2. 创建监控任务到 monitor_tasks 表，同时保存最新数据快照
    """
    # 检查数据源是否存在
    data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    
    # 1. 保存分析配置到 analysis_configs 表
    db_config = AnalysisConfig(
        data_source_id=task.data_source_id,
        chart_type=task.chart_type,
        subgroup_size=task.subgroup_size,
        confidence_level=task.confidence_level
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    # 2. 获取最新一次查询到的数据（一维数组）
    latest_data = _get_latest_data_from_source(data_source, task.subgroup_size)
    
    # 3. 创建监控任务
    db_task = MonitorTask(
        name=task.name,
        data_source_id=task.data_source_id,
        analysis_config_id=db_config.id,
        interval_seconds=task.interval_seconds,
        latest_data=latest_data
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # 添加到调度器
    add_monitor_job(db_task.id, task.interval_seconds)
    
    return ApiResponse(
        success=True,
        message="监控任务创建成功",
        data={
            "id": db_task.id,
            "name": db_task.name,
            "analysis_config_id": db_config.id,
            "interval_seconds": db_task.interval_seconds
        }
    )


@router.get("/tasks", response_model=ApiResponse)
async def list_monitor_tasks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取监控任务列表"""
    total = db.query(MonitorTask).count()
    tasks = db.query(MonitorTask).order_by(
        MonitorTask.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # 获取正在运行的任务
    running = get_running_tasks()
    running_ids = [int(r["job_id"].split("_")[-1]) for r in running]
    
    return ApiResponse(
        success=True,
        data={
            "total": total,
            "running_count": len(running),
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                    "data_source_id": t.data_source_id,
                    "analysis_config_id": t.analysis_config_id,
                    "interval_seconds": t.interval_seconds,
                    "is_active": t.id in running_ids,
                    "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                    "has_anomaly": t.has_anomaly,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "latest_data": t.latest_data,
                    "chart_type": t.analysis_config.chart_type.value if t.analysis_config else None,
                    "subgroup_size": t.analysis_config.subgroup_size if t.analysis_config else 5,
                    "confidence_level": t.analysis_config.confidence_level.value if t.analysis_config else None,
                }
                for t in tasks
            ]
        }
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse)
async def get_monitor_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取单个监控任务详情"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    return ApiResponse(
        success=True,
        data={
            "id": task.id,
            "name": task.name,
            "data_source_id": task.data_source_id,
            "analysis_config_id": task.analysis_config_id,
            "interval_seconds": task.interval_seconds,
            "is_active": True,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "last_result": task.last_result,
            "has_anomaly": task.has_anomaly,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
    )


@router.post("/tasks/{task_id}/refresh", response_model=ApiResponse)
async def refresh_monitor_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """手动刷新监控任务"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    # 立即执行一次
    result = await run_monitor_task(task_id)
    
    return ApiResponse(
        success=result.get("success", False),
        message="刷新成功" if result.get("success") else f"刷新失败: {result.get('error')}",
        data=result
    )


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
async def delete_monitor_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """删除监控任务"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    # 从调度器移除
    remove_monitor_job(task_id)
    
    db.delete(task)
    db.commit()
    
    return ApiResponse(success=True, message="监控任务删除成功")


@router.post("/tasks/{task_id}/toggle", response_model=ApiResponse)
async def toggle_monitor_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """启动/暂停监控任务"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    if task.is_active:
        # 暂停
        task.is_active = False
        remove_monitor_job(task_id)
        db.commit()
        return ApiResponse(success=True, message="监控任务已暂停", data={"id": task_id, "is_active": False})
    else:
        # 启动
        task.is_active = True
        add_monitor_job(task_id, task.interval_seconds)
        db.commit()
        return ApiResponse(success=True, message="监控任务已启动", data={"id": task_id, "is_active": True})


@router.get("/running", response_model=ApiResponse)
async def list_running_tasks():
    """获取正在运行的监控任务"""
    running = get_running_tasks()
    
    return ApiResponse(
        success=True,
        data={
            "count": len(running),
            "tasks": running
        }
    )