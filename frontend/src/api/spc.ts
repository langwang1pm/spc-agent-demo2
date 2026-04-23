/**
 * SPC分析相关API
 */
import api from './request';
import type { SPCResult, AnalysisConfig, ApiResponse } from '@/types';

// SPC计算
export const calculateSPC = (params: {
  data_source_id: number;
  chart_type?: string;
  subgroup_size?: number;
  confidence_level?: string;
  show_rules?: boolean;
  show_prediction?: boolean;
}) => {
  return api.get<ApiResponse<SPCResult>>('/spc/calculate', { params });
};

// AI分析
export const analyzeWithAI = (dataSourceId: number, analysisConfigId?: number) => {
  return api.post<ApiResponse<{
    id: number;
    analysis_result: string;
    created_at: string;
  }>>('/spc/analyze', null, {
    params: { data_source_id: dataSourceId, analysis_config_id: analysisConfigId },
  });
};

// 导出SPC图表数据
export const exportSPCChart = (dataSourceId: number, params?: {
  chart_type?: string;
  subgroup_size?: number;
  confidence_level?: string;
}) => {
  return `${api.defaults.baseURL}/spc/export/chart?data_source_id=${dataSourceId}${
    params?.chart_type ? `&chart_type=${params.chart_type}` : ''
  }${params?.subgroup_size ? `&subgroup_size=${params.subgroup_size}` : ''}${
    params?.confidence_level ? `&confidence_level=${params.confidence_level}` : ''
  }`;
};

// 导出原始数据
export const exportRawData = (dataSourceId: number) => {
  return `${api.defaults.baseURL}/spc/export/raw?data_source_id=${dataSourceId}`;
};

// 导出分析报告
export const exportReport = (dataSourceId: number, format: 'docx' | 'html' | 'pdf' = 'docx') => {
  return `${api.defaults.baseURL}/spc/export/report?data_source_id=${dataSourceId}&format=${format}`;
};

// 分析配置
export const createAnalysisConfig = (config: {
  data_source_id: number;
  chart_type: string;
  subgroup_size: number;
  confidence_level: string;
  show_rules: boolean;
  show_prediction: boolean;
}) => {
  return api.post<ApiResponse<AnalysisConfig>>('/analysis/config', config);
};

export const updateAnalysisConfig = (configId: number, config: Partial<AnalysisConfig>) => {
  return api.put<ApiResponse<AnalysisConfig>>(`/analysis/config/${configId}`, config);
};

export const getAnalysisConfig = (configId: number) => {
  return api.get<ApiResponse<AnalysisConfig>>(`/analysis/config/${configId}`);
};