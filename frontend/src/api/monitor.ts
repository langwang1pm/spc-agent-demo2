/**
 * 监控任务相关API
 */
import api from './request';
import type { MonitorTask, ApiResponse } from '@/types';

// 创建监控任务
export const createMonitorTask = (data: {
  name: string;
  data_source_id: number;
  analysis_config_id: number;
  interval_seconds: number;
}) => {
  return api.post<ApiResponse<{ id: number; name: string }>>('/monitor/tasks', data);
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

// 获取正在运行的任务
export const listRunningTasks = () => {
  return api.get<ApiResponse<{ count: number; tasks: any[] }>>('/monitor/running');
};