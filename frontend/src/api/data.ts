/**
 * 数据输入相关API
 */
import api from './request';
import type { DataSource, ApiResponse } from '@/types';

// 创建手动输入数据
export const createManualData = (data: {
  name: string;
  data_values: number[][];
}) => {
  return api.post<ApiResponse<{ id: number; name: string }>>('/data/manual', data);
};

// 上传文件数据
export const uploadFileData = (name: string, file: File) => {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('file', file);
  
  return api.post<ApiResponse<{ id: number; name: string; file_name: string; subgroup_size?: number }>>(
    '/data/file',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
};

// 创建系统对接数据源
export const createSystemData = (data: {
  name: string;
  system_type: string;
  connection_config: Record<string, any>;
  query_config: string;
}) => {
  return api.post<ApiResponse<{ id: number; name: string }>>('/data/system', {
    source_type: 'system',
    ...data,
  });
};

// 获取数据源列表
export const listDataSources = (skip = 0, limit = 20) => {
  return api.get<ApiResponse<{
    total: number;
    items: DataSource[];
  }>>('/data/list', {
    params: { skip, limit },
  });
};

// 获取单个数据源
export const getDataSource = (id: number) => {
  return api.get<ApiResponse<DataSource>>(`/data/${id}`);
};

// 删除数据源
export const deleteDataSource = (id: number) => {
  return api.delete<ApiResponse<null>>(`/data/${id}`);
};