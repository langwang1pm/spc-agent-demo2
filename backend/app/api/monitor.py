"""
监控任务相关API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import MonitorTask, DataSource, AnalysisConfig
from app.schemas import MonitorTaskCreate, MonitorTaskResponse, ApiResponse
from app.services.monitor import add_monitor_job, remove_monitor_job, run_monitor_task, get_running_tasks

router = APIRouter(prefix="/monitor", tags=["监控任务"])


@router.post("/tasks", response_model=ApiResponse)
async def create_monitor_task(
    task: MonitorTaskCreate,
    db: Session = Depends(get_db)
):
    """创建监控任务"""
    # 检查数据源和分析配置是否存在
    data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
    analysis_config = db.query(AnalysisConfig).filter(AnalysisConfig.id == task.analysis_config_id).first()
    
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if not analysis_config:
        raise HTTPException(status_code=404, detail="分析配置不存在")
    
    db_task = MonitorTask(
        name=task.name,
        data_source_id=task.data_source_id,
        analysis_config_id=task.analysis_config_id,
        interval_seconds=task.interval_seconds
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