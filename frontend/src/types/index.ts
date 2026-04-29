/**
 * TypeScript类型定义
 */

// 数据源类型
export type DataSourceType = 'manual' | 'file' | 'system';

// 系统对接类型
export type SystemSourceType = 'ERP' | 'MES' | 'PLC' | 'DATABASE';

// 图表类型
export type ChartType = 
  | 'xbar_r'   // X̄-R 控制图
  | 'xbar_s'   // X̄-S 控制图
  | 'i_mr'     // I-MR 控制图
  | 'p_chart'  // p 控制图
  | 'np_chart' // np 控制图
  | 'c_chart'  // c 控制图
  | 'u_chart'  // u 控制图
  | 'histogram' // 直方图
  | 'trend';    // 趋势图

// 置信水平
export type ConfidenceLevel = '99.73' | '95.45' | '99';

// 数据源
export interface DataSource {
  id: number;
  name: string;
  source_type: DataSourceType;
  data_values?: number[][];
  file_name?: string;
  file_path?: string;
  system_type?: SystemSourceType;
  connection_config?: Record<string, any>;
  query_config?: string;
  created_at: string;
  updated_at?: string;
}

// 分析配置
export interface AnalysisConfig {
  id: number;
  data_source_id: number;
  chart_type: ChartType;
  subgroup_size: number;
  confidence_level: ConfidenceLevel;
  show_rules: boolean;
  show_prediction: boolean;
  statistics_result?: StatisticsResult;
  created_at: string;
  updated_at?: string;
}

// 统计结果
export interface StatisticsResult {
  sample_count: number;
  mean: number;
  std_dev: number;
  cv: number;
  min_val: number;
  median: number;
  max_val: number;
  range_val: number;
}

// SPC图表数据
export interface SPCChartData {
  labels: string[];
  data: number[];
  ucl?: number;
  lcl?: number;
  cl?: number;
  unit: string;
}

// SPC计算结果
export interface SPCResult {
  chart_type: ChartType;
  chart_data: Record<string, SPCChartData>;
  data_values?: number[][];  // 原始分组数据，供前端展示
  statistics: StatisticsResult;
  control_limits: Record<string, number>;
  anomalies: Anomaly[];
  rules_violations: RuleViolation[];
}

// 异常点
export interface Anomaly {
  index: number;
  value: number;
  type: string;
  limit_violated?: string;
}

// 判异规则违反
export interface RuleViolation {
  rule: string;
  description: string;
  indices?: number[];
  index?: number;
  value?: number;
}

// 监控任务
export interface MonitorTask {
  id: number;
  name: string;
  data_source_id: number;
  analysis_config_id: number;
  interval_seconds: number;
  is_active: boolean;
  last_run_at?: string;
  last_result?: SPCResult;
  has_anomaly: boolean;
  created_at: string;
}

// 系统设置
export interface SystemSettings {
  decimal_places: number;
  chart_theme: 'default' | 'light' | 'dark';
  auto_save: boolean;
}

// API响应
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

// 图表类型选项
export const CHART_TYPE_OPTIONS = [
  { value: 'xbar_r', label: 'X̄-R 控制图（均值-极差）' },
  { value: 'xbar_s', label: 'X̄-S 控制图（均值-标准差）' },
  { value: 'i_mr', label: 'I-MR 控制图（单值-移动极差）' },
  { value: 'p_chart', label: 'p 控制图（不合格品率）' },
  { value: 'np_chart', label: 'np 控制图（不合格品数）' },
  { value: 'c_chart', label: 'c 控制图（缺陷数）' },
  { value: 'u_chart', label: 'u 控制图（单位缺陷数）' },
  { value: 'histogram', label: '直方图' },
  { value: 'trend', label: '趋势图' },
];

// 置信水平选项
export const CONFIDENCE_LEVEL_OPTIONS = [
  { value: '99.73', label: '99.73% (3σ)' },
  { value: '95.45', label: '95.45% (2σ)' },
  { value: '99', label: '99% (2.58σ)' },
];