/**
 * 监控任务相关API
 */
import api from './request';
import type { MonitorTask, ApiResponse } from '@/types';

// 创建监控任务
export const createMonitorTask = (data: {
  name: string;
  data_source_id: number;
  chart_type: string;
  subgroup_size: number;
  confidence_level: string;
  interval_seconds: number;
}) => {
  return api.post<ApiResponse<{ id: number; name: string; analysis_config_id: number }>>('/monitor/tasks', data);
};

// 获取监控任务列表
export const listMonitorTasks = (skip = 0, limit = 20) => {
  return api.get<ApiResponse<{
    total: number;
    running_count: number;
    items: MonitorTask[];
  }>>('/monitor/tasks', {
    params: { skip, limit },
  });
};

// 获取单个监控任务
export const getMonitorTask = (taskId: number) => {
  return api.get<ApiResponse<MonitorTask>>(`/monitor/tasks/${taskId}`);
};

// 刷新监控任务
export const refreshMonitorTask = (taskId: number) => {
  return api.post<ApiResponse<any>>(`/monitor/tasks/${taskId}/refresh`);
};

// 删除监控任务
export const deleteMonitorTask = (taskId: number) => {
  return api.delete<ApiResponse<null>>(`/monitor/tasks/${taskId}`);
};

// 启动/暂停监控任务
export const toggleMonitorTask = (taskId: number) => {
  return api.post<ApiResponse<{ id: number; is_active: boolean }>>(`/monitor/tasks/${taskId}/toggle`);
};

// 获取正在运行的任务
export const listRunningTasks = () => {
  return api.get<ApiResponse<{ count: number; tasks: any[] }>>('/monitor/running');
};

// 获取监控任务的异常记录列表
export const getTaskAnomalies = (
  taskId: number,
  isNewData?: boolean | null,
  skip = 0,
  limit = 50
) => {
  const params: any = { skip, limit };
  if (isNewData !== null && isNewData !== undefined) {
    params.is_new_data = isNewData;
  }
  return api.get<ApiResponse<{
    total: number;
    items: AnomalyRecord[];
  }>>(`/monitor/tasks/${taskId}/anomalies`, { params });
};

// 获取单个异常记录详情
export const getAnomalyDetail = (anomalyId: number) => {
  return api.get<ApiResponse<AnomalyRecord>>(`/monitor/anomalies/${anomalyId}`);
};

// 异常记录类型定义
export interface AnomalyRecord {
  id: number;
  monitor_task_id?: number;
  detected_at: string;
  anomaly_type: string | null;
  anomaly_data: Record<string, any> | null;
  context_data: Record<string, any> | null;
  is_new_data: boolean;
  new_data_count: number | null;
  data_snapshot_before: number[] | null;
  new_data_indices: number[] | null;
  silence_until: string | null;
  alert_type: string | null;
  related_anomaly_ids: number[] | null;
  feishu_notified: boolean;
  notified_at: string | null;
  created_at?: string;
}