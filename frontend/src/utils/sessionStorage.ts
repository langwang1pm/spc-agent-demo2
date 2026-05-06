/**
 * sessionStorage 持久化工具
 * 用于页面刷新时保存/恢复状态
 */

const SESSION_KEY = 'spc_agent_page_state';

/** 需要持久化的页面状态结构 */
export interface PersistedPageState {
  // 数据输入
  dataInputTab: string;
  manualData: { name: string; values: string };
  fileData: { name: string };
  systemData: {
    name: string;
    sourceType: string;
    connectionConfig: string;
    queryConfig: string;
  };
  // 分析配置
  analysisConfig: {
    chartType: string;
    subgroupSize: number;
    confidenceLevel: string;
    showRules: boolean;
    showPrediction: boolean;
  };
  subgroupSizeLocked: boolean;
  // 是否已添加过数据（决定是否恢复 SPC 相关结果）
  isDataAdded: boolean;
  // 当前数据源（不含大数据，仅含基础信息）
  currentDataSourceId: number | null;
  currentDataSourceName: string | null;
  currentDataSourceType: string | null;
}

export const pageStateSession = {
  /** 保存状态 */
  save(state: PersistedPageState): void {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('[sessionStorage] 保存失败:', e);
    }
  },

  /** 恢复状态，返回 null 表示无保存数据 */
  restore(): PersistedPageState | null {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      return JSON.parse(raw) as PersistedPageState;
    } catch (e) {
      console.warn('[sessionStorage] 恢复失败:', e);
      return null;
    }
  },

  /** 清除保存的状态 */
  clear(): void {
    sessionStorage.removeItem(SESSION_KEY);
  },
};
