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
          <div v-if="task.spc_result" class="chart-preview">
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
import { listMonitorTasks, refreshMonitorTask, deleteMonitorTask } from '@/api/monitor';
import dayjs from 'dayjs';
import * as echarts from 'echarts';

type MonitorTaskWithSPC = {
  id: number;
  name: string;
  interval_seconds: number;
  is_active: boolean;
  last_run_at: string | null;
  has_anomaly: boolean;
  spc_result: any;
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
      if (task.spc_result) {
        renderChart(task.id, task.spc_result);
      }
    });
  } catch (error) {
    console.error('加载监控任务失败:', error);
  } finally {
    loading.value = false;
  }
};

const renderChart = (taskId: number, spcResult: any) => {
  const container = document.getElementById(`chart-${taskId}`);
  if (!container) return;
  
  // 销毁旧实例
  if (chartInstances[taskId]) {
    chartInstances[taskId].dispose();
  }
  
  // 创建新实例
  const chart = echarts.init(container);
  chartInstances[taskId] = chart;
  
  const chartData = spcResult.chart_data;
  let series: any[] = [];
  let xAxis: any = { type: 'category', data: [] };
  
  // 解析图表数据
  const primaryKey = Object.keys(chartData)[0];
  if (primaryKey) {
    const primary = chartData[primaryKey];
    xAxis.data = primary.labels;
    
    series = [
      { name: primary.unit, type: 'line', data: primary.data, smooth: true, symbol: 'none', lineStyle: { width: 1.5 } },
      { name: 'UCL', type: 'line', data: Array(primary.data.length).fill(primary.ucl), linestyle: { type: 'dashed', width: 1 }, color: '#ff4d4f' },
      { name: 'CL', type: 'line', data: Array(primary.data.length).fill(primary.cl), linestyle: { type: 'dashed', width: 1 }, color: '#52c41a' },
      { name: 'LCL', type: 'line', data: Array(primary.data.length).fill(primary.lcl), linestyle: { type: 'dashed', width: 1 }, color: '#ff4d4f' },
    ];
    
    // 标记异常点
    spcResult.anomalies?.forEach((a: any) => {
      series[0].markPoint = series[0].markPoint || { data: [] };
      (series[0].markPoint.data as any[]).push({ 
        coord: [a.index, a.value], 
        itemStyle: { color: '#ff4d4f' },
        symbolSize: 6
      });
    });
  }
  
  const option = {
    title: { 
      text: spcResult.chart_type?.toUpperCase(), 
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 10 } },
    grid: { left: '3%', right: '3%', bottom: '15%', top: '15%', containLabel: true },
    xAxis,
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series,
  };
  
  chart.setOption(option);
};

const handleRefresh = async (taskId: number) => {
  try {
    await refreshMonitorTask(taskId);
    message.success('刷新成功');
    await loadTasks();
  } catch (error) {
    message.error('刷新失败');
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
  }
});
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