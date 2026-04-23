/**
 * 全局状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { 
  DataSource, 
  AnalysisConfig, 
  SPCResult, 
  MonitorTask,
  SystemSettings 
} from '@/types';

export const useAppStore = defineStore('app', () => {
  // 状态
  const currentDataSource = ref<DataSource | null>(null);
  const currentAnalysisConfig = ref<AnalysisConfig | null>(null);
  const spcResult = ref<SPCResult | null>(null);
  const aiAnalysisResult = ref<string | null>(null);
  const monitorTasks = ref<MonitorTask[]>([]);
  const systemSettings = ref<SystemSettings>({
    decimal_places: 2,
    chart_theme: 'default',
    auto_save: true,
  });
  const loading = ref(false);
  const isDataAdded = ref(false); // 标记是否点击了"添加数据"

  // 计算属性
  const hasDataSource = computed(() => currentDataSource.value !== null);
  const hasSPCResult = computed(() => spcResult.value !== null);
  const hasAnomaly = computed(() => spcResult.value?.anomalies?.length > 0);

  // 方法
  const setDataSource = (data: DataSource | null) => {
    currentDataSource.value = data;
  };

  const setAnalysisConfig = (config: AnalysisConfig | null) => {
    currentAnalysisConfig.value = config;
  };

  const setSPCResult = (result: SPCResult | null) => {
    spcResult.value = result;
  };

  const setAIAnalysisResult = (result: string | null) => {
    aiAnalysisResult.value = result;
  };

  const setMonitorTasks = (tasks: MonitorTask[]) => {
    monitorTasks.value = tasks;
  };

  const updateSystemSettings = (settings: Partial<SystemSettings>) => {
    systemSettings.value = { ...systemSettings.value, ...settings };
  };

  const setLoading = (value: boolean) => {
    loading.value = value;
  };

  const setDataAdded = (value: boolean) => {
    isDataAdded.value = value;
  };

  const reset = () => {
    currentDataSource.value = null;
    currentAnalysisConfig.value = null;
    spcResult.value = null;
    aiAnalysisResult.value = null;
    isDataAdded.value = false;
  };

  return {
    // 状态
    currentDataSource,
    currentAnalysisConfig,
    spcResult,
    aiAnalysisResult,
    monitorTasks,
    systemSettings,
    loading,
    isDataAdded,
    // 计算属性
    hasDataSource,
    hasSPCResult,
    hasAnomaly,
    // 方法
    setDataSource,
    setAnalysisConfig,
    setSPCResult,
    setAIAnalysisResult,
    setMonitorTasks,
    updateSystemSettings,
    setLoading,
    setDataAdded,
    reset,
  };
});