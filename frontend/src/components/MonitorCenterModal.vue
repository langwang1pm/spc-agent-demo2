<template>
  <a-modal
    v-model:open="visible"
    title="监控中心"
    width="800px"
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
          <div class="card-body">
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
import { ref, watch, computed } from 'vue';
import { message } from 'ant-design-vue';
import { listMonitorTasks, refreshMonitorTask, deleteMonitorTask } from '@/api/monitor';
import dayjs from 'dayjs';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['update:visible']);

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
});

const tasks = ref<any[]>([]);
const loading = ref(false);

const formatTime = (time: string | null) => {
  if (!time) return '从未运行';
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss');
};

const loadTasks = async () => {
  loading.value = true;
  try {
    const res = await listMonitorTasks();
    tasks.value = res.data.items || [];
  } catch (error) {
    console.error('加载监控任务失败:', error);
  } finally {
    loading.value = false;
  }
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
  gap: 12px;
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

.card-body {
  display: flex;
  gap: 24px;
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