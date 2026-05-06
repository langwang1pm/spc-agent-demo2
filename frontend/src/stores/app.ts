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
  
  // 自动刷新相关状态
  const refreshTimer = ref<number | null>(null);  // 定时器ID
  const isRefreshing = ref(false);                // 是否正在刷新
  const refreshFailCount = ref(0);                // 连续失败次数
  const maxRefreshFails = 3;                      // 最大失败次数，超过后暂停刷新

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
    // 停止自动刷新
    stopAutoRefresh();
  };
  
  // 自动刷新管理方法
  const startAutoRefresh = (intervalSeconds: number = 60, refreshCallback: () => Promise<void>) => {
    // 清除旧定时器
    stopAutoRefresh();
    
    // 重置失败计数
    refreshFailCount.value = 0;
    
    // 启动新定时器
    refreshTimer.value = window.setInterval(async () => {
      if (isRefreshing.value) return; // 防止重叠执行
      
      isRefreshing.value = true;
      try {
        await refreshCallback();
        refreshFailCount.value = 0; // 成功后重置失败计数
      } catch (error) {
        refreshFailCount.value++;
        console.error(`自动刷新失败 (${refreshFailCount.value}/${maxRefreshFails}):`, error);
        
        // 连续失败超过阈值，暂停刷新
        if (refreshFailCount.value >= maxRefreshFails) {
          console.warn('连续失败次数过多，已暂停自动刷新');
          stopAutoRefresh();
        }
      } finally {
        isRefreshing.value = false;
      }
    }, intervalSeconds * 1000);
    
    console.log(`自动刷新已启动，间隔: ${intervalSeconds}秒`);
  };
  
  const stopAutoRefresh = () => {
    if (refreshTimer.value) {
      clearInterval(refreshTimer.value);
      refreshTimer.value = null;
      console.log('自动刷新已停止');
    }
    refreshFailCount.value = 0;
  };
  
  const isAutoRefreshActive = () => {
    return refreshTimer.value !== null;
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
    // 自动刷新
    refreshTimer,
    isRefreshing,
    refreshFailCount,
    startAutoRefresh,
    stopAutoRefresh,
    isAutoRefreshActive,
  };
});