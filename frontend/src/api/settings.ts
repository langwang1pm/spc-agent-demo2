/**
 * 系统设置相关API
 */
import api from './request';
import type { SystemSettings, ApiResponse } from '@/types';

// 获取系统设置
export const getSettings = () => {
  return api.get<ApiResponse<SystemSettings>>('/settings/');
};

// 更新系统设置
export const updateSettings = (settings: Partial<SystemSettings>) => {
  return api.put<ApiResponse<SystemSettings>>('/settings/', settings);
};