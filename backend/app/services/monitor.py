"""
Monitor Task Scheduler Service
Using APScheduler for periodic SPC monitoring tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from app.core.database import SessionLocal
from app.models import MonitorTask, DataSource, AnalysisConfig, AnomalyRecord
from app.services.spc import calculate_spc
from app.services.feishu import feishu_service
from app.services.ai_agent import ai_service
from app.services.system_query import get_system_data_values, SystemQueryError


# Global scheduler instance
scheduler = AsyncIOScheduler()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def _get_latest_data_from_source(data_source: DataSource, subgroup_size: int = 5) -> List[float]:
    """
    从数据源获取最新一次查询到的数据，返回一维数组。
    
    支持:
    - SYSTEM: 从外部系统实时查询
    - FILE: 从文件读取
    - MANUAL: 从 data_values 字段获取
    """
    from app.api.spc import _parse_file_values
    
    source_type = data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type)
    
    if source_type == 'system':
        # 系统对接数据源 - 从外部系统实时查询
        try:
            raw_values = get_system_data_values(
                system_type=data_source.system_type.value,
                connection_config=data_source.connection_config,
                query_config=data_source.query_config
            )
            return raw_values  # 返回一维数组
        except SystemQueryError as e:
            print(f"[ERROR] 系统对接查询失败: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] 获取系统数据异常: {e}")
            return []
    
    elif source_type == 'file':
        # 文件导入 - 从文件读取
        if not data_source.file_path:
            return []
        try:
            values_2d = _parse_file_values(data_source.file_path)
            # 转换为一维数组
            result = []
            for group in values_2d:
                result.extend(group)
            return result
        except Exception as e:
            print(f"[ERROR] 文件解析失败: {e}")
            return []
    
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


async def run_monitor_task(task_id: int) -> Dict[str, Any]:
    """
    Execute a single monitoring task.
    
    流程:
    1. 从 data_sources 表获取最新数据
    2. 更新 monitor_tasks.latest_data 字段（一维数组）
    3. 执行 SPC 计算
    4. 检测异常并处理告警

    Args:
        task_id: Monitoring task ID

    Returns:
        Execution result
    """
    db = SessionLocal()
    try:
        # Get task info
        task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}

        # Get data source and analysis config
        data_source = db.query(DataSource).filter(
            DataSource.id == task.data_source_id
        ).first()
        analysis_config = db.query(AnalysisConfig).filter(
            AnalysisConfig.id == task.analysis_config_id
        ).first()

        if not data_source or not analysis_config:
            return {"success": False, "error": "Data source or config not found"}

        # 【核心改动】获取最新数据并更新 latest_data 字段
        subgroup_size = analysis_config.subgroup_size or 5
        latest_data = _get_latest_data_from_source(data_source, subgroup_size)
        
        if not latest_data:
            return {"success": False, "error": "Failed to get latest data from data source"}
        
        # 更新监控任务记录的最新数据
        task.latest_data = latest_data
        db.commit()
        
        # 将一维数组转换为二维数组（按子组大小分组）用于SPC计算
        data_2d = []
        for i in range(0, len(latest_data), subgroup_size):
            group = latest_data[i:i + subgroup_size]
            if group:  # 忽略空组
                data_2d.append(group)
        
        if not data_2d:
            return {"success": False, "error": "No valid data groups for SPC calculation"}

        # Execute SPC calculation with latest data
        spc_result = calculate_spc(
            data=data_2d,
            chart_type=analysis_config.chart_type.value,
            subgroup_size=subgroup_size,
            confidence_level=analysis_config.confidence_level.value,
            show_rules=analysis_config.show_rules,
            show_prediction=analysis_config.show_prediction
        )

        # Update task status
        task.last_run_at = datetime.now()
        task.last_result = spc_result

        # Check anomalies
        anomalies = spc_result.get("anomalies", [])
        task.has_anomaly = len(anomalies) > 0

        # If anomalies found, create records and send notifications
        if anomalies:
            for anomaly in anomalies:
                anomaly_record = AnomalyRecord(
                    monitor_task_id=task_id,
                    anomaly_type=anomaly.get("type", "unknown"),
                    anomaly_data=anomaly,
                    context_data={
                        "spc_result": spc_result,
                        "data_source_name": data_source.name
                    }
                )
                db.add(anomaly_record)
                db.flush()  # Get the ID

                # Send Feishu alarm
                try:
                    await feishu_service.send_alarm_notification(
                        anomaly_data={
                            "id": anomaly_record.id,
                            "monitor_task_id": task_id,
                            "anomaly_type": anomaly.get("type"),
                            "anomaly_data": anomaly,
                            "task_name": task.name
                        },
                        monitor_task_name=task.name
                    )
                    anomaly_record.feishu_notified = True
                    anomaly_record.notified_at = datetime.now()
                except Exception as e:
                    print(f"[ERROR] Failed to send Feishu alarm: {e}")

            db.commit()

        db.commit()

        return {
            "success": True,
            "task_id": task_id,
            "has_anomaly": task.has_anomaly,
            "anomaly_count": len(anomalies),
            "spc_result": spc_result
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def add_monitor_job(task_id: int, interval_seconds: int):
    """
    Add a monitoring task to the scheduler.

    Args:
        task_id: Task ID
        interval_seconds: Execution interval in seconds
    """
    job_id = f"monitor_task_{task_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Add new job
    scheduler.add_job(
        func=run_monitor_task,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=job_id,
        args=[task_id],
        replace_existing=True
    )


def remove_monitor_job(task_id: int):
    """
    Remove a monitoring task from the scheduler.

    Args:
        task_id: Task ID
    """
    job_id = f"monitor_task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def restore_active_tasks():
    """恢复 is_active=True 的监控任务到调度器（服务重启后调用）"""
    db = SessionLocal()
    try:
        active_tasks = db.query(MonitorTask).filter(MonitorTask.is_active == True).all()
        restored = 0
        for task in active_tasks:
            job_id = f"monitor_task_{task.id}"
            if not scheduler.get_job(job_id):
                scheduler.add_job(
                    func=run_monitor_task,
                    trigger=IntervalTrigger(seconds=task.interval_seconds),
                    id=job_id,
                    args=[task.id],
                    replace_existing=True
                )
                restored += 1
        if restored > 0:
            print(f"[OK] Restored {restored} active monitor tasks to scheduler")
    except Exception as e:
        print(f"[ERROR] Failed to restore active tasks: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the scheduler and restore active tasks"""
    if not scheduler.running:
        scheduler.start()
        print("[OK] Monitor scheduler started")
        # 恢复活跃的监控任务
        restore_active_tasks()


def stop_scheduler():
    """Stop the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        print("[OK] Monitor scheduler stopped")


def get_running_tasks() -> list:
    """Get list of running tasks"""
    jobs = scheduler.get_jobs()
    return [
        {
            "job_id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
        }
        for job in jobs
    ]
