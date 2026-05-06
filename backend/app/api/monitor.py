"""
监控任务相关API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.core.database import get_db
from app.models import MonitorTask, DataSource, AnalysisConfig, DataSourceType
from app.schemas import MonitorTaskCreate, MonitorTaskResponse, ApiResponse
from app.services.spc import calculate_spc
from app.api.spc import _convert_to_2d
from app.services.monitor import add_monitor_job, remove_monitor_job, run_monitor_task, get_running_tasks
from app.services.system_query import get_system_data_values
import json
import numpy as np

router = APIRouter(prefix="/monitor", tags=["监控任务"])


@router.post("/tasks", response_model=ApiResponse)
async def create_monitor_task(
    task: MonitorTaskCreate,
    db: Session = Depends(get_db)
):
    """
    创建监控任务
    
    支持两种模式:
    1. 复用已有数据源和分析配置 (data_source_id + analysis_config_id)
    2. 新建数据源和分析配置 (data_source + analysis_config)
    """
    data_source = None
    analysis_config = None
    data_values = None
    spc_result = None
    
    # 获取数据源和分析配置
    if task.data_source_id and task.analysis_config_id:
        # 复用已有
        data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
        analysis_config = db.query(AnalysisConfig).filter(AnalysisConfig.id == task.analysis_config_id).first()
    elif task.data_source and task.analysis_config:
        # 新建数据源
        source_info = task.data_source
        data_source = DataSource(
            name=source_info.name,
            source_type=source_info.source_type,
            system_type=source_info.system_type,
            connection_config=source_info.connection_config if isinstance(source_info.connection_config, dict) else source_info.connection_config,
            query_config=source_info.query_config,
            data_values=source_info.data_values,
            file_name=source_info.file_name,
            file_path=source_info.file_path,
        )
        db.add(data_source)
        db.flush()
        
        # 新建分析配置
        cfg_info = task.analysis_config
        analysis_config = AnalysisConfig(
            data_source_id=data_source.id,
            chart_type=cfg_info.chart_type,
            subgroup_size=cfg_info.subgroup_size,
            confidence_level=cfg_info.confidence_level,
            show_rules=cfg_info.show_rules,
            show_prediction=cfg_info.show_prediction,
            auto_refresh=cfg_info.auto_refresh,
            refresh_interval=cfg_info.refresh_interval,
        )
        db.add(analysis_config)
        db.flush()
    else:
        raise HTTPException(status_code=400, detail="请提供 data_source_id+analysis_config_id 或 data_source+analysis_config")
    
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if not analysis_config:
        raise HTTPException(status_code=404, detail="分析配置不存在")
    
    # 查询数据
    # 优先使用请求中传入的 data_values（直接计算，不查外部系统）
    # 只有当未传入 data_values 且是 SYSTEM 类型时才从外部系统查询
    
    # 检查请求中是否已传入 data_values
    source_info = task.data_source
    request_has_data_values = (
        source_info is not None and
        source_info.data_values is not None and
        len(source_info.data_values) > 0
    )
    
    if request_has_data_values:
        # 用户在请求中传入了 data_values，直接使用
        data_values = source_info.data_values
        data_source.data_values = data_values
    elif data_source.source_type == DataSourceType.SYSTEM and data_source.query_config:
        # SYSTEM 类型且用户未传 data_values，从外部系统查询
        try:
            raw_data = get_system_data_values(
                data_source.system_type.value,
                data_source.connection_config,
                data_source.query_config
            )
            # 外部系统返回一维列表，需按子组大小转为二维
            data_values = _convert_to_2d(raw_data, analysis_config.subgroup_size)
            data_source.data_values = data_values
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"数据查询失败: {str(e)}")
    else:
        # 其他类型，使用数据库中存储的 data_values
        raw_data = data_source.data_values
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        # 检测数据维度：如果是二维数组直接使用，如果是一维则转换
        # 注意：数据库可能返回 numpy.ndarray，numpy.float64 等类型
        try:
            # 尝试访问第一个元素判断维度
            first_elem = raw_data[0]
            if isinstance(first_elem, (int, float, np.floating)) or (hasattr(first_elem, '__iter__') and not isinstance(first_elem, str)):
                # 如果第一个元素不可迭代，则是一维数据
                try:
                    iter(first_elem)
                    is_1d = False
                except TypeError:
                    is_1d = True
            else:
                is_1d = True
        except (TypeError, IndexError):
            is_1d = True
        
        if is_1d:
            # 一维数据，转换为二维
            data_values = _convert_to_2d(list(raw_data), analysis_config.subgroup_size)
        else:
            data_values = raw_data
    
    if not data_values:
        raise HTTPException(status_code=400, detail="数据源无数据，请先添加数据")
    
    # 执行SPC计算
    try:
        spc_result = calculate_spc(
            data=data_values,
            chart_type=analysis_config.chart_type.value,
            subgroup_size=analysis_config.subgroup_size,
            confidence_level=analysis_config.confidence_level.value if hasattr(analysis_config.confidence_level, 'value') else str(analysis_config.confidence_level),
            show_rules=analysis_config.show_rules,
            show_prediction=analysis_config.show_prediction
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPC计算失败: {str(e)}")
    
    # 创建监控任务
    db_task = MonitorTask(
        name=task.name,
        data_source_id=data_source.id,
        analysis_config_id=analysis_config.id,
        interval_seconds=task.interval_seconds,
        last_run_at=func.now(),
        last_result={"success": True, "message": "初始化完成"},
        has_anomaly=len(spc_result.get("anomalies", [])) > 0,
        # 存储完整SPC结果用于前端渲染
        spc_cache=spc_result
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
            "interval_seconds": db_task.interval_seconds,
            "spc_result": spc_result,
            "has_anomaly": db_task.has_anomaly
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
                    "spc_result": t.spc_cache,  # 包含完整SPC数据，前端可直接渲染
                    "created_at": t.created_at.isoformat() if t.created_at else None
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
            "spc_result": task.spc_cache,  # 完整SPC数据
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