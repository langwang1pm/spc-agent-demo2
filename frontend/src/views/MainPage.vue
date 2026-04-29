<template>
  <div class="spc-app">
    <!-- Header -->
    <header class="spc-header">
      <div class="header-left">
        <h1 class="app-title">SPC Agent</h1>
        <span class="app-subtitle">统计过程控制智能助手</span>
      </div>
      <div class="header-right">
        <a-button @click="showMonitorCenter = true">
          <template #icon><MonitorIcon /></template>
          监控中心
        </a-button>
        <a-button @click="showHelp = true">
          <template #icon><QuestionCircleIcon /></template>
          帮助
        </a-button>
        <a-button @click="showSettings = true">
          <template #icon><SettingIcon /></template>
          设置
        </a-button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="spc-main">
      <!-- 区域1: 数据输入 -->
      <section class="panel data-input-panel">
        <div class="panel-header">
          <h2>数据输入</h2>
        </div>
        <div class="panel-content">
          <a-tabs v-model:activeKey="dataInputTab">
            <!-- 手动输入 -->
            <a-tab-pane key="manual" tab="手动输入">
              <div class="tab-form">
                <a-form layout="vertical">
                  <a-form-item label="数据标题">
                    <a-input v-model:value="manualData.name" placeholder="请输入数据标题" />
                  </a-form-item>
                  <a-form-item label="数据值">
                    <a-textarea
                      v-model:value="manualData.values"
                      placeholder="请输入要分析的数据值，数值之间用英文逗号分隔。&#10;例如:&#10;10.2,10.5,10.0,10.3,10.2,10.5,10.3,10.1,10.4,10.2"
                      :rows="8"
                    />
                  </a-form-item>
                </a-form>
              </div>
            </a-tab-pane>

            <!-- 导入文件 -->
            <a-tab-pane key="file" tab="导入文件">
              <div class="tab-form">
                <a-form layout="vertical">
                  <a-form-item label="数据标题">
                    <a-input v-model:value="fileData.name" placeholder="请输入数据标题" />
                  </a-form-item>
                  <a-form-item>
                    <template #label>上传文件 <a class="template-link" href="/api/data/template" target="_blank">下载模板</a></template>
                    <a-upload
                      :before-upload="handleFileUpload"
                      :file-list="fileList"
                      :on-remove="handleFileRemove"
                      accept=".xlsx,.xls,.csv"
                    >
                      <a-button>
                        <UploadOutlined /> 选择文件
                      </a-button>
                    </a-upload>
                    <div class="upload-hint" v-if="fileList.length === 0">支持 Excel(.xlsx/.xls) 或 CSV 文件</div>
                  </a-form-item>
                </a-form>
              </div>
            </a-tab-pane>

            <!-- 系统对接 -->
            <a-tab-pane key="system" tab="系统对接">
              <div class="tab-form">
                <a-form layout="vertical">
                  <a-form-item label="数据标题">
                    <a-input v-model:value="systemData.name" placeholder="请输入数据标题" />
                  </a-form-item>
                  <a-form-item label="数据源类型">
                    <a-select v-model:value="systemData.sourceType" placeholder="请选择数据源类型">
                      <a-select-option value="DATABASE">数据库</a-select-option>
                      <a-select-option value="ERP">ERP</a-select-option>
                      <a-select-option value="MES">MES</a-select-option>
                      <a-select-option value="PLC">PLC设备</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="连接配置">
                    <a-textarea
                      v-model:value="systemData.connectionConfig"
                      :rows="4"
                      placeholder='{"DB_type": "postgresql", "host": "sh-postgres-h3849b66.sql.tencentcdb.com", "port": 21656, "dbname": "icoastline", "user": "xxx", "password": "***"}'
                    />
                  </a-form-item>
                  <a-form-item label="数据查询">
                    <a-textarea
                      v-model:value="systemData.queryConfig"
                      :rows="3"
                      placeholder="select measure_value_a from table_name_A a where a.inspection_type = 'IQC' limit 100;"
                    />
                  </a-form-item>
                </a-form>
              </div>
            </a-tab-pane>
          </a-tabs>
          
          <!-- 添加数据按钮 -->
          <div class="action-bar">
            <a-button type="primary" size="large" :loading="loading" @click="handleAddData">
              添加数据
            </a-button>
          </div>
        </div>
      </section>

      <!-- 区域2: 分析配置 -->
      <section class="panel analysis-config-panel">
        <div class="panel-header">
          <h2>分析配置</h2>
        </div>
        <div class="panel-content">
          <a-form layout="vertical">
            <a-form-item label="图表类型">
              <a-select v-model:value="analysisConfig.chartType" :disabled="!hasData">
                <a-select-option v-for="opt in chartTypeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="子组大小">
              <a-input-number v-model:value="analysisConfig.subgroupSize" :min="1" :max="100" :disabled="!hasData || subgroupSizeLocked" />
              <div v-if="subgroupSizeLocked" class="locked-hint">已从文件解析，不可修改</div>
            </a-form-item>
            <a-form-item label="置信水平">
              <a-select v-model:value="analysisConfig.confidenceLevel" :disabled="!hasData">
                <a-select-option value="99.73">99.73% (3σ)</a-select-option>
                <a-select-option value="95.45">95.45% (2σ)</a-select-option>
                <a-select-option value="99">99% (2.58σ)</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="显示判异规则">
              <a-switch v-model:checked="analysisConfig.showRules" :disabled="!hasData" />
            </a-form-item>
            <a-form-item label="显示预测区间">
              <a-switch v-model:checked="analysisConfig.showPrediction" :disabled="!hasData" />
            </a-form-item>
          </a-form>
        </div>
      </section>

      <!-- 区域3: 控制图 -->
      <section class="panel chart-panel">
        <div class="panel-header">
          <h2>控制图</h2>
          <div class="panel-actions">
            <a-button @click="handleExportChart">
              <template #icon><ExportIcon /></template>
              导出
            </a-button>
            <a-button @click="handleFullscreen">
              <template #icon><FullscreenIcon /></template>
              全屏
            </a-button>
            <a-button type="primary" @click="handleCreateMonitor" :disabled="!hasData">
              <template #icon><MonitorIcon /></template>
              监控
            </a-button>
          </div>
        </div>
        <div class="panel-content chart-content">
          <div v-if="!hasData" class="empty-placeholder">
            <InboxOutlined style="font-size: 48px; color: #ccc;" />
            <p>请先添加数据</p>
          </div>
          <div v-else id="spc-chart" ref="chartRef" style="width: 100%; height: 100%;"></div>
        </div>
      </section>

      <!-- 区域4: 统计结果 -->
      <section class="panel statistics-panel">
        <div class="panel-header">
          <h2>统计结果</h2>
        </div>
        <div class="panel-content">
          <div v-if="!hasSPCResult" class="empty-placeholder">
            <p>暂无数据</p>
          </div>
          <div v-else class="statistics-grid">
            <div class="stat-item">
              <div class="stat-label">样本数</div>
              <div class="stat-value">{{ spcStatistics.sample_count }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">均值</div>
              <div class="stat-value">{{ spcStatistics.mean?.toFixed(decimalPlaces) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">标准差</div>
              <div class="stat-value">{{ spcStatistics.std_dev?.toFixed(decimalPlaces) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">变异系数</div>
              <div class="stat-value">{{ spcStatistics.cv?.toFixed(decimalPlaces) }}%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">最小值</div>
              <div class="stat-value">{{ spcStatistics.min_val?.toFixed(decimalPlaces) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">中位数</div>
              <div class="stat-value">{{ spcStatistics.median?.toFixed(decimalPlaces) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">最大值</div>
              <div class="stat-value">{{ spcStatistics.max_val?.toFixed(decimalPlaces) }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">极差</div>
              <div class="stat-value">{{ spcStatistics.range_val?.toFixed(decimalPlaces) }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 区域5: 控制图原始数据 -->
      <section class="panel raw-data-panel">
        <div class="panel-header">
          <h2>控制图原始数据</h2>
          <a-button @click="handleExportRawData" :disabled="!hasData">
            <template #icon><ExportIcon /></template>
            导出
          </a-button>
        </div>
        <div class="panel-content">
          <a-table
            v-if="hasData"
            :columns="rawDataColumns"
            :data-source="rawDataSource"
            :pagination="{ pageSize: 10 }"
            size="small"
          />
          <div v-else class="empty-placeholder">
            <p>暂无数据</p>
          </div>
        </div>
      </section>

      <!-- 区域6: AI智能分析 -->
      <section class="panel ai-analysis-panel">
        <div class="panel-header">
          <h2>AI智能分析</h2>
        </div>
        <div class="panel-content ai-content">
          <div v-if="!hasSPCResult" class="empty-placeholder">
            <p>请先生成SPC图表</p>
          </div>
          <div v-else>
            <div v-if="aiLoading" class="ai-loading">
              <a-spin tip="AI分析中..." />
            </div>
            <div v-else-if="aiAnalysisResult" class="ai-result" v-html="renderMarkdown(aiAnalysisResult)"></div>
            <div v-else class="empty-placeholder">
              <p>点击下方按钮启动AI分析</p>
            </div>
          </div>
        </div>
        <div class="ai-actions">
          <a-button type="primary" @click="handleAIAnalysis" :loading="aiLoading" :disabled="!hasSPCResult">
            重新分析
          </a-button>
          <a-button @click="handleExportReport" :disabled="!aiAnalysisResult">
            导出分析报告
          </a-button>
        </div>
      </section>
    </main>

    <!-- 监控中心弹窗 -->
    <MonitorCenterModal v-model:visible="showMonitorCenter" />

    <!-- 帮助弹窗 -->
    <HelpModal v-model:visible="showHelp" />

    <!-- 设置弹窗 -->
    <SettingsModal v-model:visible="showSettings" @update="handleSettingsUpdate" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import { 
  InboxOutlined, 
  UploadOutlined,
  ExportOutlined as ExportIcon,
  FullscreenOutlined as FullscreenIcon,
  MonitorOutlined as MonitorIcon,
  QuestionCircleOutlined as QuestionCircleIcon,
  SettingOutlined as SettingIcon,
} from '@ant-design/icons-vue';
import * as echarts from 'echarts';
import type { UploadFile } from 'ant-design-vue';
import { useAppStore } from '@/stores/app';
import { createManualData, uploadFileData, createSystemData, getDataSource } from '@/api/data';
import { calculateSPC, analyzeWithAI } from '@/api/spc';
import MonitorCenterModal from '@/components/MonitorCenterModal.vue';
import HelpModal from '@/components/HelpModal.vue';
import SettingsModal from '@/components/SettingsModal.vue';

const store = useAppStore();

// 响应式状态
const dataInputTab = ref('manual');
const loading = ref(false);
const aiLoading = ref(false);
const showMonitorCenter = ref(false);
const showHelp = ref(false);
const showSettings = ref(false);
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = ref<echarts.ECharts | null>(null);
const fileList = ref<UploadFile[]>([]);

// 手动输入数据
const manualData = reactive({
  name: '',
  values: '',
});

// 文件数据
const fileData = reactive({
  name: '',
  file: null as File | null,
});

// 系统对接数据
const systemData = reactive({
  name: '',
  sourceType: 'DATABASE',
  connectionConfig: '',
  queryConfig: '',
});

// 分析配置
const analysisConfig = reactive({
  chartType: 'xbar_r',
  subgroupSize: 5,
  confidenceLevel: '99',
  showRules: true,
  showPrediction: false,
});

// 子组大小是否被锁定（从文件解析后禁止编辑）
const subgroupSizeLocked = ref(false);

// 图表类型选项
const chartTypeOptions = [
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

// 计算属性
const hasData = computed(() => store.isDataAdded && store.currentDataSource !== null);
const hasSPCResult = computed(() => store.spcResult !== null);
const decimalPlaces = computed(() => store.systemSettings.decimal_places);
const spcStatistics = computed(() => store.spcResult?.statistics || {});
const aiAnalysisResult = computed(() => store.aiAnalysisResult);

// 原始数据列
const rawDataColumns = [
  { title: '序号', dataIndex: 'index', key: 'index' },
  { title: '组号', dataIndex: 'group', key: 'group' },
  { title: '数据值', dataIndex: 'value', key: 'value' },
];

// 原始数据源
const rawDataSource = computed(() => {
  // 优先从 SPC 计算结果中取原始分组数据（三种数据源类型通用）
  const values = store.spcResult?.data_values || store.currentDataSource?.data_values;
  if (!values) return [];
  // 支持一维数组和二维数组
  if (values.length > 0 && typeof values[0] === 'number') {
    // 一维数组 → 按子组大小拆分为二维
    const subgroupSize = analysisConfig.subgroupSize;
    const result: { index: number; group: number; value: number }[] = [];
    let idx = 1;
    for (let i = 0; i < values.length; i += subgroupSize) {
      const groupNum = Math.floor(i / subgroupSize) + 1;
      for (let j = 0; j < subgroupSize && i + j < values.length; j++) {
        result.push({ index: idx++, group: groupNum, value: values[i + j] });
      }
    }
    return result;
  } else {
    // 二维数组
    const result: { index: number; group: number; value: number }[] = [];
    let idx = 1;
    values.forEach((group, gi) => {
      (group as number[]).forEach((val) => {
        result.push({ index: idx++, group: gi + 1, value: val });
      });
    });
    return result;
  }
});

// 方法
const parseDataValues = (text: string): number[] => {
  // 将所有数值解析为一维数组（按行顺序）
  const lines = text.trim().split('\n').filter(line => line.trim());
  const result: number[] = [];
  lines.forEach(line => {
    line.split(/[,，\t]+/).forEach(v => {
      const num = parseFloat(v.trim());
      if (!isNaN(num)) {
        result.push(num);
      }
    });
  });
  return result;
};

const handleAddData = async () => {
  loading.value = true;
  try {
    let dataSourceId: number;
    
    if (dataInputTab.value === 'manual') {
      if (!manualData.name) {
        message.warning('请输入数据标题');
        return;
      }
      const dataValues = parseDataValues(manualData.values);
      if (dataValues.length === 0) {
        message.warning('请输入有效的数据');
        return;
      }
      
      const res = await createManualData({ name: manualData.name, data_values: dataValues });
      dataSourceId = res.data.id;
      // 手动输入时，解锁子组大小字段
      subgroupSizeLocked.value = false;
    } else if (dataInputTab.value === 'file') {
      if (!fileData.name) {
        message.warning('请输入数据标题');
        return;
      }
      if (!fileData.file) {
        message.warning('请选择文件');
        return;
      }
      
      const res = await uploadFileData(fileData.name, fileData.file);
      dataSourceId = res.data.id;
      
      // 从文件解析的子组大小，更新配置并锁定
      if (res.data.subgroup_size && res.data.subgroup_size > 0) {
        analysisConfig.subgroupSize = res.data.subgroup_size;
        subgroupSizeLocked.value = true;
      }
    } else {
      // 系统对接
      if (!systemData.name) {
        message.warning('请输入数据标题');
        loading.value = false;
        return;
      }
      if (!systemData.connectionConfig) {
        message.warning('请填写连接配置');
        loading.value = false;
        return;
      }
      if (!systemData.queryConfig) {
        message.warning('请填写数据查询语句');
        loading.value = false;
        return;
      }
      let res;
      try {
        res = await createSystemData({
          name: systemData.name,
          system_type: systemData.sourceType,
          connection_config: systemData.connectionConfig.trim(),
          query_config: systemData.queryConfig,
        });
      } catch (error: any) {
        const errMsg = error?.response?.data?.detail || '数据源保存失败，所选数据源对应功能暂未开发，敬请期待。';
        message.error(errMsg);
        loading.value = false;
        return;
      }
      dataSourceId = res.data.id;
      // 系统对接数据，解锁子组大小
      subgroupSizeLocked.value = false;
    }
    
    store.setDataAdded(true);
    
    // 获取完整数据源（包含 data_values）
    const fullDataRes = await getDataSource(dataSourceId);
    store.setDataSource(fullDataRes.data);
    
    // 自动触发SPC计算
    await performSPCAnalysis(dataSourceId);
    
    // 自动触发AI分析
    await performAIAnalysis(dataSourceId);
    
    message.success('数据添加成功');
  } catch (error) {
    message.error('添加数据失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const performSPCAnalysis = async (dataSourceId: number) => {
  try {
    const res = await calculateSPC({
      data_source_id: dataSourceId,
      chart_type: analysisConfig.chartType,
      subgroup_size: analysisConfig.subgroupSize,
      confidence_level: analysisConfig.confidenceLevel,
      show_rules: analysisConfig.showRules,
      show_prediction: analysisConfig.showPrediction,
    });
    
    store.setSPCResult(res.data);
    await nextTick();
    renderChart(res.data);
  } catch (error) {
    message.error('SPC计算失败');
    console.error(error);
  }
};

const performAIAnalysis = async (dataSourceId: number) => {
  try {
    const res = await analyzeWithAI(dataSourceId);
    store.setAIAnalysisResult(res.data.analysis_result);
  } catch (error) {
    console.error('AI分析失败:', error);
    // AI分析失败不阻断主流程，静默处理
  }
};

const renderChart = (data: any) => {
  if (!chartRef.value) return;
  
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value);
  }
  
  const chartData = data.chart_data;
  let series: any[] = [];
  let xAxis: any = { type: 'category', data: [] };
  
  if (chartData.xbar || chartData.individual || chartData.p || chartData.np || chartData.c || chartData.u) {
    const primaryKey = Object.keys(chartData)[0];
    const primary = chartData[primaryKey];
    xAxis.data = primary.labels;
    
    series = [
      { name: primary.unit, type: 'line', data: primary.data, smooth: true },
      { name: 'UCL', type: 'line', data: Array(primary.data.length).fill(primary.ucl), linestyle: { type: 'dashed' }, color: '#ff4d4f' },
      { name: 'CL', type: 'line', data: Array(primary.data.length).fill(primary.cl), linestyle: { type: 'dashed' }, color: '#52c41a' },
      { name: 'LCL', type: 'line', data: Array(primary.data.length).fill(primary.lcl), linestyle: { type: 'dashed' }, color: '#ff4d4f' },
    ];
    
    // 标记异常点
    data.anomalies?.forEach((a: any) => {
      series[0].markPoint = series[0].markPoint || { data: [] };
      (series[0].markPoint.data as any[]).push({ coord: [a.index, a.value], itemStyle: { color: '#ff4d4f' } });
    });
  } else if (chartData.histogram) {
    const hist = chartData.histogram;
    series = [{ type: 'bar', data: hist.frequencies.map((f: number, i: number) => ({ value: f, itemStyle: { color: '#1890ff' } })) }];
    xAxis = { type: 'category', data: hist.bins.map((b: number) => b.toFixed(2)) };
  } else if (chartData.trend) {
    const trend = chartData.trend;
    xAxis.data = trend.labels;
    series = [
      { name: '数据', type: 'line', data: trend.data, smooth: true },
      { name: '趋势线', type: 'line', data: trend.trend_line, smooth: true, lineStyle: { type: 'dashed' } },
    ];
  }
  
  const option = {
    title: { text: data.chart_type.toUpperCase() + ' 控制图', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 10 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis,
    yAxis: { type: 'value' },
    series,
  };
  
  chartInstance.value.setOption(option);
};

const handleAIAnalysis = async () => {
  if (!store.currentDataSource) return;
  
  aiLoading.value = true;
  try {
    const res = await analyzeWithAI(store.currentDataSource.id);
    store.setAIAnalysisResult(res.data.analysis_result);
    message.success('AI分析完成');
  } catch (error) {
    message.error('AI分析失败');
    console.error(error);
  } finally {
    aiLoading.value = false;
  }
};

const handleFileUpload = (file: File) => {
  // 仅当数据标题为空时，才自动填入文件名（去掉扩展名）
  if (!fileData.name) {
    fileData.name = file.name.replace(/\.(xlsx|xls|csv)$/i, '');
  }
  fileData.file = file;
  fileList.value = [file as any];
  return false;
};

const handleFileRemove = () => {
  fileData.file = null;
  fileData.name = '';
  fileList.value = [];
};

const handleExportChart = () => {
  if (chartInstance.value) {
    const url = chartInstance.value.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    const a = document.createElement('a');
    a.href = url;
    a.download = 'spc-chart.png';
    a.click();
  }
};

const handleFullscreen = () => {
  if (chartRef.value) {
    chartRef.value.requestFullscreen?.();
  }
};

const handleCreateMonitor = () => {
  message.info('监控功能：将在Phase 5实现');
};

const handleExportRawData = () => {
  message.info('导出原始数据');
  // 实际实现会调用API
};

const handleExportReport = () => {
  message.info('导出分析报告');
  // 实际实现会调用API
};

const handleSettingsUpdate = (settings: any) => {
  store.updateSystemSettings(settings);
};

const renderMarkdown = (text: string) => {
  // 简单实现，实际项目中可使用marked等库
  return text
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/\n/gim, '<br>');
};

// 监听分析配置变化
watch(() => analysisConfig, async (newConfig) => {
  if (store.currentDataSource?.id) {
    await performSPCAnalysis(store.currentDataSource.id);
  }
}, { deep: true });

// 窗口大小变化时重新渲染图表
onMounted(() => {
  window.addEventListener('resize', () => {
    chartInstance.value?.resize();
  });
});
</script>

<style scoped>
.spc-app {
  min-height: 100vh;
  background: #f0f2f5;
}

.spc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #001529;
  color: white;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.app-title {
  font-size: 20px;
  font-weight: bold;
  margin: 0;
}

.app-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
}

.header-right {
  display: flex;
  gap: 8px;
}

.spc-main {
  display: grid;
  grid-template-columns: 320px 1fr;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
  padding: 16px;
  min-height: calc(100vh - 68px); /* 改为 min-height，允许随内容撑开 */
}

.panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-content {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.data-input-panel {
  grid-row: 1 / 2;
}

.analysis-config-panel {
  grid-row: 2 / 3;
}

.chart-panel {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
}

.statistics-panel {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
}

.raw-data-panel {
  grid-column: 1 / 3;
  grid-row: 3 / 4;
  /* 最小高度，允许随内容撑开 */
  min-height: 400px;
}

.raw-data-panel .panel-content {
  overflow: visible;
  /* 不设置固定高度，让内容自然撑开 */
}

.ai-analysis-panel {
  display: none; /* AI功能区域暂时合并到主区域 */
}

.tab-form {
  margin-bottom: 16px;
}

.upload-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #999;
}

.template-link {
  font-size: 13px;
  font-weight: normal;
  color: #1677ff;
  text-decoration: none;
  margin-left: 8px;
}

.template-link:hover {
  text-decoration: underline;
}

.action-bar {
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}

.action-bar button {
  width: 100%;
}

.locked-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.chart-content {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.empty-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
  text-align: center;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.ai-content {
  min-height: 200px;
}

.ai-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.ai-result {
  line-height: 1.8;
}

.ai-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  justify-content: center;
}
</style>