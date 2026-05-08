<template>
  <a-modal
    v-model:open="visible"
    title="监控中心"
    width="1000px"
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
        <p class="hint">在控制图区域点击"监控"按钮创建监控任务</p>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import { message } from 'ant-design-vue';
import { listMonitorTasks, refreshMonitorTask, deleteMonitorTask, toggleMonitorTask } from '@/api/monitor';
import { ExportOutlined, FullscreenOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons-vue';
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
        renderChart(task.id, task.latest_data, task.chart_type, task.subgroup_size, task.confidence_level);
      }
    });
  } catch (error) {
    console.error('加载监控任务失败:', error);
  } finally {
    loading.value = false;
  }
};

const renderChart = (taskId: number, data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null) => {
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
  const chartData = calculateSPCData(data, chartType, subgroupSize, confidenceLevel);
  
  const option = {
    title: { 
      text: getChartTitle(chartType), 
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 10 } },
    grid: { left: '3%', right: '3%', bottom: '15%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: chartData.labels },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: chartData.series,
  };
  
  chart.setOption(option);
};

// 增量更新图表（只刷当前卡片，不影响其他实例）
const updateChart = (taskId: number, data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null) => {
  const chart = chartInstances[taskId];
  if (!chart) {
    // 实例不存在（卡片首次有数据），走完整初始化
    renderChart(taskId, data, chartType, subgroupSize, confidenceLevel);
    return;
  }
  const chartData = calculateSPCData(data, chartType, subgroupSize, confidenceLevel);
  chart.setOption({
    xAxis: { data: chartData.labels },
    series: chartData.series,
  }, { replaceMerge: ['series'] });
};

// 10s 轮询：自动刷新所有卡片的最新数据（不走 loadTasks 避免全局重渲染）
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
          updateChart(tasks.value[i].id, fresh.latest_data, fresh.chart_type, fresh.subgroup_size, fresh.confidence_level);
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
const calculateSPCData = (data: number[], chartType: string, subgroupSize: number, confidenceLevel: string | null) => {
  const labels = data.map((_, i) => `${i + 1}`);
  const series: any[] = [];
  
  // 根据图表类型计算
  if (chartType === 'xbar_r' || chartType === 'xbar_s') {
    // 均值图
    const { means, ucl, cl, lcl } = calculateXBar(data, subgroupSize, confidenceLevel);
    series.push(
      { name: '均值', type: 'line', data: means, smooth: true, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(means.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(means.length).fill(cl), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(means.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    return { labels: means.map((_, i) => `${i + 1}`), series };
  } else if (chartType === 'i_mr') {
    // 单值移动极差图
    const { values, ucl, cl, lcl } = calculateIMR(data, confidenceLevel);
    series.push(
      { name: '单值', type: 'line', data: values, smooth: true, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(values.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(values.length).fill(cl), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(values.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    return { labels: labels.slice(0, values.length), series };
  } else {
    // 默认趋势图
    const mean = data.reduce((a, b) => a + b, 0) / data.length;
    const std = Math.sqrt(data.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / data.length);
    const ucl = mean + 3 * std;
    const lcl = mean - 3 * std;
    series.push(
      { name: '数据', type: 'line', data: data, smooth: true, symbol: 'circle', symbolSize: 4, lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(data.length).fill(ucl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' },
      { name: 'CL', type: 'line', data: Array(data.length).fill(mean), lineStyle: { type: 'dashed', width: 1 }, color: '#52c41a', symbol: 'none' },
      { name: 'LCL', type: 'line', data: Array(data.length).fill(lcl), lineStyle: { type: 'dashed', width: 1 }, color: '#ff4d4f', symbol: 'none' }
    );
    return { labels, series };
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
  
  // A2因子（子组大小为5时，A2=0.577）
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
  
  // d2因子（n=2时，d2=1.128）
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
  
  const chart = chartInstances[taskId];
  if (!chart) {
    // 如果图表实例不存在，创建一个临时图表来导出
    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.width = '1200px';
    tempContainer.style.height = '600px';
    document.body.appendChild(tempContainer);
    
    const tempChart = echarts.init(tempContainer);
    const chartData = calculateSPCData(task.latest_data!, task.chart_type!, task.subgroup_size, task.confidence_level);
    tempChart.setOption({
      title: { text: getChartTitle(task.chart_type!), left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, type: 'scroll' },
      grid: { left: '3%', right: '3%', bottom: '10%', top: '15%', containLabel: true },
      xAxis: { type: 'category', data: chartData.labels },
      yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
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
  
  // 注册一次性全屏事件：进入时放大，退出时缩回
  const onFullscreenChange = async () => {
    await nextTick();
    const chart = chartInstances[taskId];
    if (!chart) return;
    
    if (document.fullscreenElement) {
      // 进入全屏：图表撑满屏幕
      chart.resize({ width: container.clientWidth, height: container.clientHeight });
    } else {
      // 退出全屏：还原到原始容器尺寸
      chart.resize({ width: container.clientWidth, height: 200 });
    }
  };
  
  document.addEventListener('fullscreenchange', onFullscreenChange);
  container.requestFullscreen?.();
};

// 单卡刷新：只更新当前卡片数据，增量 setOption，不影响其他卡片
const handleRefresh = async (taskId: number) => {
  const idx = tasks.value.findIndex(t => t.id === taskId);
  if (idx === -1) return;

  try {
    // 1. 调用后端刷新 API
    await refreshMonitorTask(taskId);
    message.success('刷新成功');

    // 2. 从列表接口只取该任务最新数据（避免全局重渲染）
    const res = await listMonitorTasks(0, 100);
    const fresh = (res.data.items || []).find((t: any) => t.id === taskId);
    if (!fresh) return;

    // 3. 合并更新到当前任务（保留图表相关字段）
    tasks.value[idx] = {
      ...tasks.value[idx],
      is_active: fresh.is_active,
      last_run_at: fresh.last_run_at,
      has_anomaly: fresh.has_anomaly,
      latest_data: fresh.latest_data,
    };

    // 4. 增量更新图表（只刷当前卡片）
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

// 监听全屏变化，重新渲染图表（解决全屏后图表尺寸异常）
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
</style>