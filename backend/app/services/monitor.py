"""
Monitor Task Scheduler Service
Using APScheduler for periodic SPC monitoring tasks

核心改动（2026-05-08）：
- 增量检测：每次监控只对新增数据点做异常判定
- 去重告警：静默窗口内不重复发送同类告警
- 判异规则：X̄-R / X̄-S / I-MR 均支持西电判异规则
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import json

from app.core.database import SessionLocal
from app.models import MonitorTask, DataSource, AnalysisConfig, AnomalyRecord
from app.services.spc import calculate_spc, RULES_SUPPORTED_CHART_TYPES
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
    """
    from app.api.spc import _parse_file_values

    source_type = (
        data_source.source_type.value
        if hasattr(data_source.source_type, "value")
        else str(data_source.source_type)
    )

    if source_type == "system":
        try:
            raw_values = get_system_data_values(
                system_type=data_source.system_type.value,
                connection_config=data_source.connection_config,
                query_config=data_source.query_config,
            )
            return raw_values
        except SystemQueryError as e:
            print(f"[ERROR] 系统对接查询失败: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] 获取系统数据异常: {e}")
            return []

    elif source_type == "file":
        if not data_source.file_path:
            return []
        try:
            values_2d = _parse_file_values(data_source.file_path)
            result = []
            for group in values_2d:
                result.extend(group)
            return result
        except Exception as e:
            print(f"[ERROR] 文件解析失败: {e}")
            return []

    else:
        raw_data = data_source.data_values
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        if not raw_data:
            return []
        if isinstance(raw_data[0], (int, float)):
            return raw_data
        else:
            result = []
            for group in raw_data:
                result.extend(group)
            return result


def _convert_to_2d(data_1d: List[float], subgroup_size: int) -> List[List[float]]:
    """
    将一维数组按子组大小转换为二维数组，用于 SPC 计算。
    """
    data_2d = []
    for i in range(0, len(data_1d), subgroup_size):
        group = data_1d[i : i + subgroup_size]
        if group:
            data_2d.append(group)
    return data_2d


def _detect_new_data_indices(
    old_data: Optional[List[float]], new_data: List[float]
) -> Tuple[int, int, List[float]]:
    """
    比对旧快照与新数据，提取新增数据点。

    支持多种场景：
    - 尾部追加：新数据在数组尾部（asc 排序）
    - 头部插入：新数据在数组头部（desc 排序）
    - 窗口滑动：新数据挤掉旧数据（LIMIT 查询，长度相同但内容变化）

    Returns:
        (start_idx, end_idx, new_points)
        - start_idx: 新增数据在一维数组中的起始索引
        - end_idx:   新增数据在一维数组中的结束索引（左闭右开）
        - new_points: 新增数据点列表
    """
    if old_data is None or len(old_data) == 0:
        # 首次运行，全部视为新增
        return (0, len(new_data), new_data)

    old_len = len(old_data)
    new_len = len(new_data)

    # 完全相同，无新增
    if old_data == new_data:
        return (old_len, old_len, [])

    # ---- 长度增长的情况 ----
    if new_len > old_len:
        # Case 1: 精确尾部追加（new_data[:old_len] == old_data）
        if new_data[:old_len] == old_data:
            new_points = new_data[old_len:]
            return (old_len, new_len, new_points)

        # Case 2: 精确头部插入（new_data[-old_len:] == old_data）
        if new_data[-old_len:] == old_data:
            new_count = new_len - old_len
            return (0, new_count, new_data[:new_count])

        # Case 3: 模糊匹配（LIMIT 窗口滑动场景）
        min_overlap = max(old_len // 2, 5)
        for overlap_len in range(min(old_len, new_len), min_overlap, -1):
            if old_data[-overlap_len:] == new_data[:overlap_len]:
                new_points = new_data[overlap_len:]
                return (overlap_len, new_len, new_points)
            if old_data[:overlap_len] == new_data[-overlap_len:]:
                new_count = new_len - overlap_len
                return (0, new_count, new_data[:new_count])

        # 无法匹配，保守返回全部作为新增
        return (0, new_len, new_data)

    # ---- 长度相同或减少但内容变化的情况 ----
    # LIMIT 查询场景：新数据插入后挤掉了旧数据，长度不变但内容变化
    # 策略：搜索 old_data 在 new_data 中的最大重叠，找出变化部分
    min_overlap = max(old_len // 2, 5)

    for overlap_len in range(min(old_len, new_len), min_overlap, -1):
        # old_data 的尾部 == new_data 的头部？→ 新数据追加在尾部
        if old_data[-overlap_len:] == new_data[:overlap_len]:
            new_count = new_len - overlap_len
            if new_count > 0:
                new_points = new_data[overlap_len:]
                return (overlap_len, new_len, new_points)

        # old_data 的头部 == new_data 的尾部？→ 新数据插入在头部
        if old_data[:overlap_len] == new_data[-overlap_len:]:
            new_count = new_len - overlap_len
            if new_count > 0:
                return (0, new_count, new_data[:new_count])

    # 无法确定变化位置，保守标记全部数据为新增
    return (0, new_len, new_data)


def _is_in_silence_window(
    db: Session, task_id: int, silence_window_seconds: int
) -> bool:
    """
    检查当前是否在静默窗口内。
    若上一次告警时间距今 < silence_window_seconds，返回 True（应静默）。
    """
    if silence_window_seconds <= 0:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=silence_window_seconds)
    recent = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.monitor_task_id == task_id,
            AnomalyRecord.feishu_notified == True,
            AnomalyRecord.detected_at >= cutoff,
        )
        .order_by(AnomalyRecord.detected_at.desc())
        .first()
    )
    return recent is not None


def _extract_primary_sequence(
    spc_result: Dict[str, Any], chart_type: str
) -> Tuple[List[int], List[float]]:
    """
    从 SPC 计算结果中提取主序列（均值序列或单值序列），
    用于增量异常检测。

    Returns:
        (indices, values): 索引列表和对应的值列表
    """
    chart_data = spc_result.get("chart_data", {})

    if chart_type == "xbar_r" and "xbar" in chart_data:
        series = chart_data["xbar"]
        return (list(range(len(series["data"]))), series["data"])
    elif chart_type == "xbar_s" and "xbar" in chart_data:
        series = chart_data["xbar"]
        return (list(range(len(series["data"]))), series["data"])
    elif chart_type == "i_mr" and "individual" in chart_data:
        series = chart_data["individual"]
        return (list(range(len(series["data"]))), series["data"])
    else:
        # 计数型图表暂不提供判异规则支持
        return ([], [])


def _build_incremental_anomalies(
    old_data_len: int,
    new_data_indices: List[int],
    spc_result: Dict[str, Any],
    chart_type: str,
) -> Tuple[List[Dict], List[Dict]]:
    """
    在已知的全量 SPC 结果中，过滤出仅由新增数据点触发的异常。

    区分两类异常：
      - out_of_control: 新增点在超限检测中触发
      - rules_violation: 新增点触犯了西电判异规则

    新增点的判定方式：
      - 超限异常：直接比对 anomaly.index 是否在 [new_data_indices) 范围内
      - 规则异常：遍历 rules_violations，只要其 indices 列表中有任意一个索引
        落在 [new_data_indices) 范围内，即标记该违规为"新增数据触发"

    Args:
        old_data_len:      旧快照长度
        new_data_indices:  [start, end) 左闭右开区间
        spc_result:        全量 SPC 计算结果
        chart_type:        图表类型

    Returns:
        (new_out_of_control, new_rules_violations)
    """
    start, end = new_data_indices
    new_out_of_control = []
    new_rules_violations = []

    # ---- 超限检测 ----
    for a in spc_result.get("anomalies", []):
        idx = a.get("index")
        if idx is not None and start <= idx < end:
            new_out_of_control.append(a)

    # ---- 判异规则 ----
    # 仅计量型图表支持判异规则
    if chart_type not in RULES_SUPPORTED_CHART_TYPES:
        return new_out_of_control, new_rules_violations

    for rv in spc_result.get("rules_violations", []):
        indices = rv.get("indices", [])
        if not indices:
            idx = rv.get("index")
            if idx is not None and start <= idx < end:
                new_rules_violations.append(rv)
        else:
            # 任一 index 落在新增区间，即认为是新增触发的违规
            if any(start <= i < end for i in indices):
                new_rules_violations.append(rv)

    return new_out_of_control, new_rules_violations


async def run_monitor_task(task_id: int) -> Dict[str, Any]:
    """
    执行单个监控任务。

    流程:
    1. 从数据源获取最新全量数据
    2. 与上次快照比对，提取新增数据点
    3. 全量数据执行 SPC 计算（含判异规则）
    4. 过滤出仅由新增数据触发的异常
    5. 检查静默窗口，决定是否发告警
    6. 发送飞书告警（新增数据异常）
    7. 更新 latest_data 快照

    Args:
        task_id: 监控任务ID

    Returns:
        执行结果
    """
    db = SessionLocal()
    try:
        # ---- 加载任务及关联数据 ----
        task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}

        data_source = db.query(DataSource).filter(
            DataSource.id == task.data_source_id
        ).first()
        analysis_config = db.query(AnalysisConfig).filter(
            AnalysisConfig.id == task.analysis_config_id
        ).first()

        if not data_source or not analysis_config:
            return {"success": False, "error": "Data source or config not found"}

        subgroup_size = analysis_config.subgroup_size or 5
        chart_type = analysis_config.chart_type.value
        confidence_level = analysis_config.confidence_level.value
        show_rules = analysis_config.show_rules
        silence_window = task.silence_window_seconds or 300

        # ---- 获取最新全量数据 ----
        latest_full = _get_latest_data_from_source(data_source, subgroup_size)
        if not latest_full:
            return {"success": False, "error": "Failed to get latest data from data source"}

        old_snapshot: Optional[List[float]] = task.latest_data
        old_len = len(old_snapshot) if old_snapshot else 0

        # ---- 增量检测：提取新增数据点 ----
        start_idx, end_idx, new_points = _detect_new_data_indices(
            old_snapshot, latest_full
        )

        task.last_run_at = datetime.now(timezone.utc)
        task.last_result = {"new_data_count": len(new_points)}

        if not new_points:
            # 无新增数据，仅更新快照后结束
            task.latest_data = latest_full
            db.commit()
            return {
                "success": True,
                "task_id": task_id,
                "new_data_count": 0,
                "has_anomaly": False,
            }

        # ---- 全量 SPC 计算 ----
        # 全量二维数组
        data_2d = _convert_to_2d(latest_full, subgroup_size)
        if not data_2d:
            return {"success": False, "error": "No valid data groups for SPC calculation"}

        spc_result = calculate_spc(
            data=data_2d,
            chart_type=chart_type,
            subgroup_size=subgroup_size,
            confidence_level=confidence_level,
            show_rules=show_rules,
            show_prediction=False,
        )

        # ---- 过滤新增数据触发的异常 ----
        new_out_of_limit, new_rules = _build_incremental_anomalies(
            old_data_len=old_len,
            new_data_indices=[start_idx, end_idx],
            spc_result=spc_result,
            chart_type=chart_type,
        )

        has_new_anomaly = len(new_out_of_limit) > 0 or len(new_rules) > 0
        task.has_anomaly = task.has_anomaly or has_new_anomaly  # 保留历史异常标记

        # ---- 静默窗口检查 ----
        should_silence = _is_in_silence_window(db, task_id, silence_window)

        # ---- 异常记录写入 + 飞书告警 ----
        if has_new_anomaly and not should_silence:
            silence_until = datetime.now(timezone.utc) + timedelta(
                seconds=silence_window
            )

            # 批量写入异常记录
            anomaly_records = []

            # 超限异常记录
            for a in new_out_of_limit:
                record = AnomalyRecord(
                    monitor_task_id=task_id,
                    anomaly_type=a.get("type", "out_of_control"),
                    anomaly_data=a,
                    context_data={
                        "spc_result": spc_result,
                        "data_source_name": data_source.name,
                        "control_limits": spc_result.get("control_limits", {}),
                        "statistics": spc_result.get("statistics", {}),
                    },
                    is_new_data=True,
                    new_data_count=len(new_points),
                    data_snapshot_before=old_snapshot,
                    new_data_indices=[start_idx, end_idx],
                    silence_until=silence_until,
                    alert_type="new_data_out_of_limit",
                )
                db.add(record)
                anomaly_records.append(record)

            # 规则违规异常记录
            for rv in new_rules:
                record = AnomalyRecord(
                    monitor_task_id=task_id,
                    anomaly_type="rule_violation",
                    anomaly_data=rv,
                    context_data={
                        "spc_result": spc_result,
                        "data_source_name": data_source.name,
                        "control_limits": spc_result.get("control_limits", {}),
                    },
                    is_new_data=True,
                    new_data_count=len(new_points),
                    data_snapshot_before=old_snapshot,
                    new_data_indices=[start_idx, end_idx],
                    silence_until=silence_until,
                    alert_type="new_data_rule_violation",
                )
                db.add(record)
                anomaly_records.append(record)

            db.flush()

            # ---- 飞书告警（批量，只发一条合并消息） ----
            try:
                await feishu_service.send_new_data_alarm(
                    task_name=task.name,
                    data_source_name=data_source.name,
                    new_data_count=len(new_points),
                    new_out_of_limit=new_out_of_limit,
                    new_rules=new_rules,
                    control_limits=spc_result.get("control_limits", {}),
                    chart_type=chart_type,
                    detected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

                # 更新已发送通知的记录
                for record in anomaly_records:
                    record.feishu_notified = True
                    record.notified_at = datetime.now(timezone.utc)

            except Exception as e:
                print(f"[ERROR] Failed to send Feishu alarm: {e}")

            db.commit()
        else:
            db.commit()

        # ---- 更新数据快照 ----
        task.latest_data = latest_full
        db.commit()

        return {
            "success": True,
            "task_id": task_id,
            "new_data_count": len(new_points),
            "new_data_indices": [start_idx, end_idx],
            "has_anomaly": has_new_anomaly,
            "out_of_limit_count": len(new_out_of_limit),
            "rules_violation_count": len(new_rules),
            "silenced": should_silence,
            "spc_result": spc_result,
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def add_monitor_job(task_id: int, interval_seconds: int):
    """
    Add a monitoring task to the scheduler.
    """
    job_id = f"monitor_task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        func=run_monitor_task,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=job_id,
        args=[task_id],
        replace_existing=True,
    )


def remove_monitor_job(task_id: int):
    """
    Remove a monitoring task from the scheduler.
    """
    job_id = f"monitor_task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def restore_active_tasks():
    """恢复 is_active=True 的监控任务到调度器（服务重启后调用）"""
    db = SessionLocal()
    try:
        active_tasks = (
            db.query(MonitorTask)
            .filter(MonitorTask.is_active == True)
            .all()
        )
        restored = 0
        for task in active_tasks:
            job_id = f"monitor_task_{task.id}"
            if not scheduler.get_job(job_id):
                scheduler.add_job(
                    func=run_monitor_task,
                    trigger=IntervalTrigger(seconds=task.interval_seconds),
                    id=job_id,
                    args=[task.id],
                    replace_existing=True,
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
            "next_run_time": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
        }
        for job in jobs
    ]
