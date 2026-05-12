<template>
  <a-modal
    v-model:open="visible"
    title="监控中心"
    width="1200px"
    :footer="null"
  >
    <div class="monitor-center">
      <div class="monitor-list" v-if="tasks.length > 0">
        <div v-for="task in tasks" :key="task.id" class="monitor-card">
          <div class="card-header">
            <div class="task-info">
              <span class="task-name">{{ task.name }}</span>
              <span class="task-update">更新时间: {{ formatTime(task.last_run_at) }}</span>
            </div>
            <div class="card-actions">
              <a-button
                size="small"
                :type="task.is_active ? 'default' : 'primary'"
                @click="handleToggle(task.id, task.is_active)"
              >
                <template #icon>
                  <PauseCircleOutlined v-if="task.is_active" />
                  <PlayCircleOutlined v-else />
                </template>
                {{ task.is_active ? '暂停' : '启动' }}
              </a-button>
              <a-button size="small" @click="handleViewAnomalies(task.id)" :disabled="!task.has_anomaly">
                <template #icon><WarningOutlined /></template>
                异常记录
              </a-button>
              <a-button size="small" @click="handleExport(task.id)" :disabled="!task.latest_data">
                <template #icon><ExportOutlined /></template>
                导出
              </a-button>
              <a-button size="small" @click="handleFullscreen(task.id)" :disabled="!task.latest_data">
                <template #icon><FullscreenOutlined /></template>
                全屏
              </a-button>
              <a-button size="small" @click="handleRefresh(task.id)">
                刷新
              </a-button>
              <a-button size="small" danger @click="handleDelete(task.id)">
                删除
              </a-button>
            </div>
          </div>
          
          <!-- 状态信息 -->
          <div class="card-status">
            <div class="status-item">
              <span class="label">监控间隔:</span>
              <span class="value">{{ task.interval_seconds }}秒</span>
            </div>
            <div class="status-item">
              <span class="label">状态:</span>
              <a-tag :color="task.is_active ? 'green' : 'red'">
                {{ task.is_active ? '运行中' : '已停止' }}
              </a-tag>
            </div>
            <div class="status-item">
              <span class="label">异常:</span>
              <a-tag :color="task.has_anomaly ? 'red' : 'green'">
                {{ task.has_anomaly ? '有异常' : '正常' }}
              </a-tag>
            </div>
          </div>
          
          <!-- 控制图预览 -->
          <div v-if="task.latest_data && task.latest_data.length > 0 && task.chart_type" class="chart-preview">
            <div :id="`chart-${task.id}`" class="mini-chart"></div>
          </div>
          <div v-else class="no-data">暂无图表数据</div>
        </div>
      </div>
      <div v-else class="empty-state">
        <p>暂无监控任务</p>
        <p class="hint">在控制图区域点击“监控”按钮创建监控任务</p>
      </div>
    </div>

    <!-- 异常记录弹窗 -->
    <a-modal
      v-model:open="showAnomalyModal"
      :title="`异常记录 - ${currentTaskName}`"
      width="900px"
      :footer="null"
    >
      <div class="anomaly-modal-content">
        <!-- 筛选 -->
        <div class="anomaly-filter">
          <a-radio-group v-model:value="anomalyFilter" @change="loadAnomalies">
            <a-radio-button :value="null">全部</a-radio-button>
            <a-radio-button :value="true">新增异常</a-radio-button>
            <a-radio-button :value="false">历史异常</a-radio-button>
          </a-radio-group>
        </div>
        
        <!-- 异常列表 -->
        <a-table
          :columns="anomalyColumns"
          :data-source="anomalyRecords"
          :loading="anomalyLoading"
          :pagination="anomalyPagination"
          @change="handleAnomalyTableChange"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'is_new_data'">
              <a-tag :color="record.is_new_data ? 'orange' : 'blue'">
                {{ record.is_new_data ? '新增异常' : '历史异常' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'anomaly_type'">
              <span>{{ record.anomaly_type || '-' }}</span>
            </template>
            <template v-else-if="column.key === 'detected_at'">
              <span>{{ formatTime(record.detected_at) }}</span>
            </template>
            <template v-else-if="column.key === 'feishu_notified'">
              <a-tag :color="record.feishu_notified ? 'green' : 'default'">
                {{ record.feishu_notified ? '已通知' : '未通知' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button size="small" type="link" @click="handleViewAnomalyDetail(record)">
                查看详情
              </a-button>
            </template>
          </template>
        </a-table>
      </div>
    </a-modal>

    <!-- 异常详情弹窗 -->
    <a-modal
      v-model:open="showAnomalyDetailModal"
      title="异常详情"
      width="700px"
      :footer="null"
    >
      <div v-if="currentAnomaly" class="anomaly-detail">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="异常ID">{{ currentAnomaly.id }}</a-descriptions-item>
          <a-descriptions-item label="检测时间">{{ formatTime(currentAnomaly.detected_at) }}</a-descriptions-item>
          <a-descriptions-item label="异常类型">{{ currentAnomaly.anomaly_type || '-' }}</a-descriptions-item>
          <a-descriptions-item label="异常分类">
            <a-tag :color="currentAnomaly.is_new_data ? 'orange' : 'blue'">
              {{ currentAnomaly.is_new_data ? '新增异常' : '历史异常' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="新增数据点数" v-if="currentAnomaly.is_new_data">
            {{ currentAnomaly.new_data_count || 0 }}
          </a-descriptions-item>
          <a-descriptions-item label="新增数据索引" v-if="currentAnomaly.new_data_indices">
            {{ currentAnomaly.new_data_indices?.join(', ') }}
          </a-descriptions-item>
          <a-descriptions-item label="飞书通知">
            <a-tag :color="currentAnomaly.feishu_notified ? 'green' : 'default'">
              {{ currentAnomaly.feishu_notified ? '已通知' : '未通知' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="通知时间">
            {{ formatTime(currentAnomaly.notified_at) || '-' }}
          </a-descriptions-item>
        </a-descriptions>
        
        <div class="anomaly-data-section" v-if="currentAnomaly.anomaly_data">
          <h4>异常数据</h4>
          <pre class="json-display">{{ JSON.stringify(currentAnomaly.anomaly_data, null, 2) }}</pre>
        </div>
        
        <div class="anomaly-data-section" v-if="currentAnomaly.context_data">
          <h4>上下文数据</h4>
          <pre class="json-display">{{ JSON.stringify(currentAnomaly.context_data, null, 2) }}</pre>
        </div>
      </div>
    </a-modal>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import { listMonitorTasks, refreshMonitorTask, deleteMonitorTask, toggleMonitorTask, getTaskAnomalies, getAnomalyDetail, type AnomalyRecord } from '@/api/monitor';
import { ExportOutlined, FullscreenOutlined, PlayCircleOutlined, PauseCircleOutlined, WarningOutlined } from '@ant-design/icons-vue';
import dayjs from 'dayjs';
import * as echarts from 'echarts';

type MonitorTaskWithSPC = {
  id: number;
  name: string;
  interval_seconds: number;
  is_active: boolean;
  last_run_at: string | null;
  has_anomaly: boolean;
  latest_data: number[] | null;
  chart_type: string | null;
  subgroup_size: number;
  confidence_level: string | null;
};

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['update:visible']);

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
});

const tasks = ref<MonitorTaskWithSPC[]>([]);
const loading = ref(false);
const chartInstances: Record<number, echarts.ECharts> = {};
let pollTimer: ReturnType<typeof setInterval> | null = null;

// 异常记录相关状态
const showAnomalyModal = ref(false);
const showAnomalyDetailModal = ref(false);
const currentTaskId = ref<number | null>(null);
const currentTaskName = ref('');
const anomalyRecords = ref<AnomalyRecord[]>([]);
const anomalyLoading = ref(false);
const anomalyFilter = ref<boolean | null>(null);
const currentAnomaly = ref<AnomalyRecord | null>(null);
const anomalyPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
});

// 异常记录表格列定义
const anomalyColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '检测时间', dataIndex: 'detected_at', key: 'detected_at', width: 160 },
  { title: '异常类型', dataIndex: 'anomaly_type', key: 'anomaly_type', width: 100 },
  { title: '分类', dataIndex: 'is_new_data', key: 'is_new_data', width: 100 },
  { title: '飞书通知', dataIndex: 'feishu_notified', key: 'feishu_notified', width: 80 },
  { title: '操作', key: 'action', width: 80 },
];

const formatTime = (time: string | null) => {
  if (!time) return '从未运行';
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss');
};

const loadTasks = async () => {
  loading.value = true;
  try {
    const res = await listMonitorTasks();
    tasks.value = res.data.items || [];

    // 加载完成后渲染图表
    await nextTick();
    tasks.value.forEach(task => {
      if (task.latest_data && task.latest_data.length > 0 && task.chart_type) {
        // 计算子组原始数据
        const subgroupRawData: number[][] = [];
        for (let i = 0; i < task.latest_data.length; i += task.subgroup_size) {
          subgroupRawData.push(task.latest_data.slice(i, i + task.subgroup_size));
        }
        renderChart(task.id, task.latest_data, task.chart_type, task.subgroup_size, task.confidence_level, subgroupRawData);
      }
    });
  } catch (error) {
    console.error('加载监控任务失败:', error);
  } finally {
    loading.value = false;
  }
};

const renderChart = (taskId: number, data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null, subgroupRawData?: number[][]) => {
  const container = document.getElementById(`chart-${taskId}`);
  if (!container || !data || data.length === 0) return;

  // 销毁旧实例
  if (chartInstances[taskId]) {
    chartInstances[taskId].dispose();
  }

  // 创建新实例
  const chart = echarts.init(container);
  chartInstances[taskId] = chart;

  // 计算控制图数据
  const chartData = calculateSPCData(data, chartType, subgroupSize, confidenceLevel, subgroupRawData);

  // 自动计算Y轴范围，避免从0开始
  let yAxisMin: number | undefined;
  let yAxisMax: number | undefined;
  
  // 收集所有系列的数据值
  const allValues: number[] = [];
  chartData.series.forEach((s: any) => {
    if (s.data && Array.isArray(s.data)) {
      s.data.forEach((val: any) => {
        if (typeof val === 'number' && !isNaN(val)) {
          allValues.push(val);
        }
      });
    }
  });
  
  if (allValues.length > 0) {
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const padding = (maxVal - minVal) * 0.1 || maxVal * 0.1; // 10%边距，防止除零
    
    yAxisMin = Math.floor((minVal - padding) * 100) / 100;
    yAxisMax = Math.ceil((maxVal + padding) * 100) / 100;
    
    // 对于比例/计数型控制图，确保Y轴最小值不小于0
    if (chartType === 'p_chart' || chartType === 'np_chart' || chartType === 'c_chart' || chartType === 'u_chart') {
      yAxisMin = Math.max(0, yAxisMin);
    }
  }
  
  const option = {
    title: {
      text: getChartTitle(chartType),
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    tooltip: { 
      trigger: 'axis',
      formatter: (params: any) => {
        // 当前数据点的索引
        const dataIndex = params[0]?.dataIndex;
        if (dataIndex === undefined) return '';
        
        // 当前数据点的值（从series[0]获取）
        const currentValue = chartData.series[0]?.data?.[dataIndex];
        
        // 构建 tooltip 内容
        let html = `<div style="padding: 8px;">`;
        html += `<strong>${chartData.labels[dataIndex] || '样本 ' + (dataIndex + 1)}</strong><br/>`;
        html += `子组计算的最终数据: <strong>${currentValue}</strong><br/>`;
        
        // 如果有子组原始数据，显示它
        if (chartData.subgroup_raw_data && chartData.subgroup_raw_data[dataIndex]) {
          const rawData = chartData.subgroup_raw_data[dataIndex];
          html += `子组的原始数据: <strong>${rawData.join(', ')}</strong><br/>`;
        }
        
        // 显示UCL/CL/LCL（从series中获取）
        const uclSeries = chartData.series.find((s: any) => s.name === 'UCL');
        const clSeries = chartData.series.find((s: any) => s.name === 'CL');
        const lclSeries = chartData.series.find((s: any) => s.name === 'LCL');
        
        if (uclSeries && clSeries) {
          html += `UCL: ${uclSeries.data[dataIndex]?.toFixed(4) || 'N/A'} | CL: ${clSeries.data[dataIndex]?.toFixed(4) || 'N/A'}`;
          if (lclSeries) {
            html += ` | LCL: ${lclSeries.data[dataIndex]?.toFixed(4) || 'N/A'}`;
          }
          html += `<br/>`;
        }
        
        // 检查是否是异常点（与UCL/LCL比较）
        if (uclSeries && lclSeries && currentValue !== undefined) {
          const ucl = uclSeries.data[dataIndex];
          const lcl = lclSeries.data[dataIndex];
          if (currentValue > ucl || currentValue < lcl) {
            html += `<span style="color: #ff4d4f; font-weight: bold;">⚠️ 异常点（超出控制限）</span>`;
          }
        }
        
        html += `</div>`;
        return html;
      }
    },
    legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 10 } },
    grid: { left: '3%', right: '3%', bottom: '15%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: chartData.labels },
    yAxis: { 
      type: 'value', 
      splitLine: { lineStyle: { type: 'dashed' } },
      min: yAxisMin,
      max: yAxisMax,
      axisLabel: { show: true }
    },
    series: chartData.series,
  };

  chart.setOption(option);
};

// 增量更新图表(只刷当前卡片,不影响其他实例)
const updateChart = (taskId: number, data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null, subgroupRawData?: number[][]) => {
  const chart = chartInstances[taskId];
  if (!chart) {
    // 实例不存在(卡片首次有数据),走完整初始化
    renderChart(taskId, data, chartType, subgroupSize, confidenceLevel, subgroupRawData);
    return;
  }
  const chartData = calculateSPCData(data, chartType, subgroupSize, confidenceLevel, subgroupRawData);
  chart.setOption({
    xAxis: { data: chartData.labels },
    series: chartData.series,
  }, { replaceMerge: ['series'] });
};

// 10s 轮询:自动刷新所有卡片的最新数据(不走 loadTasks 避免全局重渲染)
const startPolling = async () => {
  stopPolling();
  pollTimer = setInterval(async () => {
    if (!props.visible || tasks.value.length === 0) return;
    try {
      const res = await listMonitorTasks(0, 100);
      const freshMap = new Map((res.data.items || []).map((t: any) => [t.id, t]));

      for (let i = 0; i < tasks.value.length; i++) {
        const fresh = freshMap.get(tasks.value[i].id);
        if (!fresh) continue;
        const changed =
          JSON.stringify(fresh.last_run_at) !== JSON.stringify(tasks.value[i].last_run_at) ||
          JSON.stringify(fresh.latest_data) !== JSON.stringify(tasks.value[i].latest_data) ||
          fresh.has_anomaly !== tasks.value[i].has_anomaly ||
          fresh.is_active !== tasks.value[i].is_active;
        if (!changed) continue;

        tasks.value[i] = { ...tasks.value[i], ...fresh };
        if (fresh.latest_data && fresh.latest_data.length > 0 && fresh.chart_type) {
          // 计算子组原始数据
          const subgroupRawData: number[][] = [];
          for (let i = 0; i < fresh.latest_data.length; i += fresh.subgroup_size) {
            subgroupRawData.push(fresh.latest_data.slice(i, i + fresh.subgroup_size));
          }
          updateChart(tasks.value[i].id, fresh.latest_data, fresh.chart_type, fresh.subgroup_size, fresh.confidence_level, subgroupRawData);
        }
      }
    } catch (e) {
      console.error('轮询刷新失败', e);
    }
  }, 10000);
};

const stopPolling = () => {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

// 计算SPC数据
const calculateSPCData = (data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null, subgroupRawData?: number[][]) => {
  const labels = data.map((_, i) => `${i + 1}`);
  const series: any[] = [];

  // 根据图表类型计算
  if (chartType === 'xbar_r' || chartType === 'xbar_s') {
    // 均值图
    const { means, ucl, cl, lcl } = calculateXBar(data, subgroupSize, confidenceLevel);
    series.push(
      { name: '均值', type: 'line', data: means, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(means.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(means.length).fill(cl), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(means.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    
    // 标记异常点（超出UCL或LCL）
    const markPointData: any[] = [];
    means.forEach((value, index) => {
      if (value > ucl || value < lcl) {
        markPointData.push({ coord: [index, value], value: value, itemStyle: { color: '#ff4d4f' } });
      }
    });
    if (markPointData.length > 0) {
      series[0].markPoint = { data: markPointData, tooltip: { show: true, formatter: (params: any) => {
        const dataIndex = params.dataIndex || 0;
        const currentValue = params.value || params.data?.value || means[dataIndex];
        
        // 构建 tooltip 内容
        let html = `<div style="padding: 8px;">`;
        html += `<strong>${means.map((_, i) => `${i + 1}`)[dataIndex] || '样本 ' + (dataIndex + 1)}</strong><br/>`;
        html += `子组计算的最终数据: <strong>${currentValue}</strong><br/>`;
        
        // 如果有子组原始数据，显示它
        if (subgroupRawData && subgroupRawData[dataIndex]) {
          const rawData = subgroupRawData[dataIndex];
          html += `子组的原始数据: <strong>${rawData.join(', ')}</strong><br/>`;
        }
        
        html += `UCL: ${ucl.toFixed(4)} | CL: ${cl.toFixed(4)} | LCL: ${lcl.toFixed(4)}<br/>`;
        html += `<span style="color: #ff4d4f; font-weight: bold;">⚠️ 异常点（超出控制限）</span>`;
        
        html += `</div>`;
        return html;
      } } };
    }
    
    return { labels: means.map((_, i) => `${i + 1}`), series, subgroup_raw_data: subgroupRawData };
  } else if (chartType === 'i_mr') {
    // 单值移动极差图
    const { values, ucl, cl, lcl } = calculateIMR(data, confidenceLevel);
    series.push(
      { name: '单值', type: 'line', data: values, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(values.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(values.length).fill(cl), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(values.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    
    // 标记异常点（超出UCL或LCL）
    const markPointData: any[] = [];
    values.forEach((value, index) => {
      if (value > ucl || value < lcl) {
        markPointData.push({ coord: [index, value], value: value, itemStyle: { color: '#ff4d4f' } });
      }
    });
    if (markPointData.length > 0) {
      series[0].markPoint = { data: markPointData, tooltip: { show: true, formatter: (params: any) => {
        const dataIndex = params.dataIndex || 0;
        const currentValue = params.value || params.data?.value || values[dataIndex];
        
        // 构建 tooltip 内容
        let html = `<div style="padding: 8px;">`;
        html += `<strong>${labels.slice(0, values.length)[dataIndex] || '样本 ' + (dataIndex + 1)}</strong><br/>`;
        html += `子组计算的最终数据: <strong>${currentValue}</strong><br/>`;
        
        // 如果有子组原始数据，显示它
        if (subgroupRawData && subgroupRawData[dataIndex]) {
          const rawData = subgroupRawData[dataIndex];
          html += `子组的原始数据: <strong>${rawData.join(', ')}</strong><br/>`;
        }
        
        html += `UCL: ${ucl.toFixed(4)} | CL: ${cl.toFixed(4)} | LCL: ${lcl.toFixed(4)}<br/>`;
        html += `<span style="color: #ff4d4f; font-weight: bold;">⚠️ 异常点（超出控制限）</span>`;
        
        html += `</div>`;
        return html;
      } } };
    }
    
    return { labels: labels.slice(0, values.length), series, subgroup_raw_data: subgroupRawData };
  } else {
    // 默认趋势图
    const mean = data.reduce((a, b) => a + b, 0) / data.length;
    const std = Math.sqrt(data.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / data.length);
    const ucl = mean + 3 * std;
    const lcl = mean - 3 * std;
    series.push(
      { name: '数据', type: 'line', data: data, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(data.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(data.length).fill(mean), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(data.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    
    // 标记异常点（超出UCL或LCL）
    const markPointData: any[] = [];
    data.forEach((value, index) => {
      if (value > ucl || value < lcl) {
        markPointData.push({ coord: [index, value], value: value, itemStyle: { color: '#ff4d4f' } });
      }
    });
    if (markPointData.length > 0) {
      series[0].markPoint = { data: markPointData, tooltip: { show: true, formatter: (params: any) => {
        const dataIndex = params.dataIndex || 0;
        const currentValue = params.value || params.data?.value || data[dataIndex];
        
        // 构建 tooltip 内容
        let html = `<div style="padding: 8px;">`;
        html += `<strong>${labels[dataIndex] || '样本 ' + (dataIndex + 1)}</strong><br/>`;
        html += `子组计算的最终数据: <strong>${currentValue}</strong><br/>`;
        
        // 如果有子组原始数据，显示它
        if (subgroupRawData && subgroupRawData[dataIndex]) {
          const rawData = subgroupRawData[dataIndex];
          html += `子组的原始数据: <strong>${rawData.join(', ')}</strong><br/>`;
        }
        
        html += `UCL: ${ucl.toFixed(4)} | CL: ${mean.toFixed(4)} | LCL: ${lcl.toFixed(4)}<br/>`;
        html += `<span style="color: #ff4d4f; font-weight: bold;">⚠️ 异常点（超出控制限）</span>`;
        
        html += `</div>`;
        return html;
      } } };
    }
    
    return { labels, series, subgroup_raw_data: subgroupRawData };
  }
};

// 计算XBar控制图
const calculateXBar = (data: number[], subgroupSize: number, confidenceLevel: string | null) => {
  const numGroups = Math.floor(data.length / subgroupSize);
  const means: number[] = [];
  const ranges: number[] = [];

  for (let i = 0; i < numGroups; i++) {
    const group = data.slice(i * subgroupSize, (i + 1) * subgroupSize);
    means.push(group.reduce((a, b) => a + b, 0) / subgroupSize);
    ranges.push(Math.max(...group) - Math.min(...group));
  }

  const overallMean = means.reduce((a, b) => a + b, 0) / means.length;
  const avgRange = ranges.reduce((a, b) => a + b, 0) / ranges.length;

  // A2因子(子组大小为5时,A2=0.577)
  const A2Factors: Record<number, number> = { 2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308 };
  const A2 = A2Factors[subgroupSize] || 0.577;

  const ucl = overallMean + A2 * avgRange;
  const lcl = overallMean - A2 * avgRange;

  return { means, ucl, cl: overallMean, lcl };
};

// 计算I-MR控制图
const calculateIMR = (data: number[], confidenceLevel: string | null) => {
  const values = data;
  const movingRanges = [0];
  for (let i = 1; i < data.length; i++) {
    movingRanges.push(Math.abs(data[i] - data[i - 1]));
  }

  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const avgMR = movingRanges.slice(1).reduce((a, b) => a + b, 0) / (movingRanges.length - 1);

  // d2因子(n=2时,d2=1.128)
  const d2 = 1.128;
  const ucl = mean + 3 * avgMR / d2;
  const lcl = mean - 3 * avgMR / d2;

  return { values, ucl, cl: mean, lcl };
};

// 获取图表标题
const getChartTitle = (chartType: string) => {
  const titles: Record<string, string> = {
    'xbar_r': 'X̄-R 控制图',
    'xbar_s': 'X̄-S 控制图',
    'i_mr': 'I-MR 控制图',
    'p_chart': 'p 控制图',
    'np_chart': 'np 控制图',
    'c_chart': 'c 控制图',
    'u_chart': 'u 控制图',
    'histogram': '直方图',
    'trend': '趋势图',
  };
  return titles[chartType] || 'SPC 控制图';
};

const handleExport = (taskId: number) => {
  const task = tasks.value.find(t => t.id === taskId);
  if (!task) return;

  // 计算子组原始数据
  const subgroupRawData: number[][] = [];
  if (task.latest_data && task.subgroup_size) {
    for (let i = 0; i < task.latest_data.length; i += task.subgroup_size) {
      subgroupRawData.push(task.latest_data.slice(i, i + task.subgroup_size));
    }
  }

  const chart = chartInstances[taskId];
  if (!chart) {
    // 如果图表实例不存在,创建一个临时图表来导出
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.width = '1200px';
    tempContainer.style.height = '600px';
    document.body.appendChild(tempContainer);

    const tempChart = echarts.init(tempContainer);
    const chartData = calculateSPCData(task.latest_data!, task.chart_type!, task.subgroup_size, task.confidence_level, subgroupRawData);
    tempChart.setOption({
      title: { text: getChartTitle(task.chart_type!), left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, type: 'scroll' },
      grid: { left: '3%', right: '3%', bottom: '10%', top: '15%', containLabel: true },
      xAxis: { type: 'category', data: chartData.labels },
      yAxis: (() => {
        // 自动计算Y轴范围
        const allValues: number[] = [];
        chartData.series.forEach((s: any) => {
          if (s.data && Array.isArray(s.data)) {
            s.data.forEach((val: any) => {
              if (typeof val === 'number' && !isNaN(val)) {
                allValues.push(val);
              }
            });
          }
        });
        
        let min: number | undefined;
        let max: number | undefined;
        if (allValues.length > 0) {
          const minVal = Math.min(...allValues);
          const maxVal = Math.max(...allValues);
          const padding = (maxVal - minVal) * 0.1 || maxVal * 0.1;
          min = Math.floor((minVal - padding) * 100) / 100;
          max = Math.ceil((maxVal + padding) * 100) / 100;
          
          if (task.chart_type === 'p_chart' || task.chart_type === 'np_chart' || task.chart_type === 'c_chart' || task.chart_type === 'u_chart') {
            min = Math.max(0, min);
          }
        }
        
        return { 
          type: 'value', 
          splitLine: { lineStyle: { type: 'dashed' } },
          min,
          max,
          axisLabel: { show: true }
        };
      })(),
      series: chartData.series,
    });

    const url = tempChart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
    const a = document.createElement('a');
    a.href = url;
    a.download = `${task.name || 'monitor-chart'}.png`;
    a.click();

    tempChart.dispose();
    document.body.removeChild(tempContainer);
    return;
  }

  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
  const a = document.createElement('a');
  a.href = url;
  a.download = `${task.name || 'monitor-chart'}.png`;
  a.click();
};

const handleFullscreen = (taskId: number) => {
  const container = document.getElementById(`chart-${taskId}`);
  if (!container) return;

  // 注册一次性全屏事件:进入时放大,退出时缩回
  const onFullscreenChange = async () => {
    await nextTick();
    const chart = chartInstances[taskId];
    if (!chart) return;

    if (document.fullscreenElement) {
      // 进入全屏:图表撑满屏幕
      chart.resize({ width: container.clientWidth, height: container.clientHeight });
    } else {
      // 退出全屏:还原到原始容器尺寸
      chart.resize({ width: container.clientWidth, height: 200 });
    }
  };

  document.addEventListener('fullscreenchange', onFullscreenChange);
  container.requestFullscreen?.();
};

// 单卡刷新:只更新当前卡片数据,增量 setOption,不影响其他卡片
const handleRefresh = async (taskId: number) => {
  const idx = tasks.value.findIndex(t => t.id === taskId);
  if (idx === -1) return;

  try {
    // 1. 调用后端刷新 API
    await refreshMonitorTask(taskId);
    message.success('刷新成功');

    // 2. 从列表接口只取该任务最新数据(避免全局重渲染)
    const res = await listMonitorTasks(0, 100);
    const fresh = (res.data.items || []).find((t: any) => t.id === taskId);
    if (!fresh) return;

    // 3. 合并更新到当前任务(保留图表相关字段)
    tasks.value[idx] = {
      ...tasks.value[idx],
      is_active: fresh.is_active,
      last_run_at: fresh.last_run_at,
      has_anomaly: fresh.has_anomaly,
      latest_data: fresh.latest_data,
    };

    // 4. 增量更新图表(只刷当前卡片)
    const t = tasks.value[idx];
    if (t.latest_data && t.latest_data.length > 0 && t.chart_type) {
      updateChart(taskId, t.latest_data, t.chart_type, t.subgroup_size, t.confidence_level);
    }
  } catch (error) {
    message.error('刷新失败');
  }
};

const handleToggle = async (taskId: number, isActive: boolean) => {
  try {
    const res = await toggleMonitorTask(taskId);
    message.success(isActive ? '监控任务已暂停' : '监控任务已启动');
    await loadTasks();
  } catch (error) {
    message.error(isActive ? '暂停失败' : '启动失败');
  }
};

const handleDelete = async (taskId: number) => {
  try {
    await deleteMonitorTask(taskId);
    message.success('删除成功');

    // 销毁图表实例
    if (chartInstances[taskId]) {
      chartInstances[taskId].dispose();
      delete chartInstances[taskId];
    }

    await loadTasks();
  } catch (error) {
    message.error('删除失败');
  }
};

// 查看异常记录
const handleViewAnomalies = async (taskId: number) => {
  const task = tasks.value.find(t => t.id === taskId);
  if (!task) return;
  
  currentTaskId.value = taskId;
  currentTaskName.value = task.name;
  showAnomalyModal.value = true;
  
  await loadAnomalies();
};

// 加载异常记录
const loadAnomalies = async () => {
  if (!currentTaskId.value) return;
  
  anomalyLoading.value = true;
  try {
    const skip = (anomalyPagination.value.current - 1) * anomalyPagination.value.pageSize;
    const res = await getTaskAnomalies(
      currentTaskId.value,
      anomalyFilter.value,
      skip,
      anomalyPagination.value.pageSize
    );
    anomalyRecords.value = res.data.items || [];
    anomalyPagination.value.total = res.data.total || 0;
  } catch (error) {
    console.error('加载异常记录失败:', error);
    message.error('加载异常记录失败');
  } finally {
    anomalyLoading.value = false;
  }
};

// 异常表格分页变化
const handleAnomalyTableChange = (pagination: any) => {
  anomalyPagination.value.current = pagination.current;
  anomalyPagination.value.pageSize = pagination.pageSize;
  loadAnomalies();
};

// 查看异常详情
const handleViewAnomalyDetail = async (record: AnomalyRecord) => {
  try {
    const res = await getAnomalyDetail(record.id);
    currentAnomaly.value = res.data;
    showAnomalyDetailModal.value = true;
  } catch (error) {
    console.error('加载异常详情失败:', error);
    message.error('加载异常详情失败');
  }
};

watch(() => props.visible, (val) => {
  if (val) {
    loadTasks();
    startPolling();
  } else {
    stopPolling();
    // 关闭弹窗时销毁所有图表实例释放内存
    Object.values(chartInstances).forEach(chart => chart.dispose());
    Object.keys(chartInstances).forEach(key => delete chartInstances[Number(key)]);
  }
});

// 监听全屏变化,重新渲染图表(解决全屏后图表尺寸异常)
if (typeof document !== 'undefined') {
  document.addEventListener('fullscreenchange', async () => {
    if (!document.fullscreenElement) {
      await nextTick();
      tasks.value.forEach(task => {
        if (task.latest_data && task.latest_data.length > 0 && task.chart_type && chartInstances[task.id]) {
          chartInstances[task.id].resize();
        }
      });
    }
  });
}
</script>

<style scoped>
.monitor-center {
  min-height: 200px;
}

.monitor-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.monitor-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-weight: 500;
  font-size: 16px;
}

.task-update {
  font-size: 12px;
  color: #999;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.card-status {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-item .label {
  color: #666;
}

.status-item .value {
  font-weight: 500;
}

.chart-preview {
  margin-top: 12px;
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.mini-chart {
  width: 100%;
  height: 200px;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.hint {
  font-size: 12px;
  margin-top: 8px;
}

/* 异常记录相关样式 */
.anomaly-modal-content {
  min-height: 300px;
}

.anomaly-filter {
  margin-bottom: 16px;
}

.anomaly-detail {
  padding: 16px 0;
}

.anomaly-data-section {
  margin-top: 16px;
}

.anomaly-data-section h4 {
  margin-bottom: 8px;
  color: #333;
}

.json-display {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}
</style>