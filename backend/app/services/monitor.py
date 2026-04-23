"""
Monitor Task Scheduler Service
Using APScheduler for periodic SPC monitoring tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import json

from app.core.database import SessionLocal
from app.models import MonitorTask, DataSource, AnalysisConfig, AnomalyRecord
from app.services.spc import calculate_spc
from app.services.feishu import feishu_service
from app.services.ai_agent import ai_service


# Global scheduler instance
scheduler = AsyncIOScheduler()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


async def run_monitor_task(task_id: int) -> Dict[str, Any]:
    """
    Execute a single monitoring task.

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

        # Execute SPC calculation
        if not data_source.data_values:
            return {"success": False, "error": "Data source has no valid data"}

        spc_result = calculate_spc(
            data=data_source.data_values,
            chart_type=analysis_config.chart_type.value,
            subgroup_size=analysis_config.subgroup_size,
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


def start_scheduler():
    """Start the scheduler"""
    if not scheduler.running:
        scheduler.start()
        print("[OK] Monitor scheduler started")


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
