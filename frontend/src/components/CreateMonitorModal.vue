<template>
  <a-modal
    v-model:open="visible"
    title="创建监控任务"
    :width="620"
    :footer="null"
    @cancel="handleClose"
  >
    <a-form layout="vertical" class="create-monitor-form">
      <!-- 任务名称 -->
      <a-form-item label="任务名称" required>
        <a-input
          v-model:value="formData.name"
          placeholder="请输入任务名称"
          :maxlength="100"
        />
      </a-form-item>

      <!-- 任务配置预览 -->
      <a-divider>任务配置预览</a-divider>

      <div class="config-preview">
        <div class="config-item">
          <span class="config-label">数据标题:</span>
          <span class="config-value">{{ props.dataSourceName || '-' }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">数据源类型:</span>
          <span class="config-value">{{ sourceTypeLabels[props.sourceType] || props.sourceType || '-' }}</span>
        </div>
        <div class="config-item config-item--block">
          <span class="config-label">连接配置:</span>
          <pre class="config-value config-value--code">{{ maskConnectionConfig(props.connectionConfig) }}</pre>
        </div>
        <div class="config-item config-item--block">
          <span class="config-label">数据查询:</span>
          <pre class="config-value config-value--code">{{ props.queryConfig || '-' }}</pre>
        </div>
        <div class="config-item">
          <span class="config-label">图表类型:</span>
          <span class="config-value">{{ getChartTypeLabel(formData.chart_type) }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">子组大小:</span>
          <span class="config-value">{{ formData.subgroup_size }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">置信水平:</span>
          <span class="config-value">{{ getConfidenceLevelLabel(formData.confidence_level) }}</span>
        </div>
      </div>

      <!-- 监控间隔配置 -->
      <a-divider>监控设置</a-divider>

      <a-form-item label="监控间隔（秒）" required>
        <a-input-number
          v-model:value="formData.interval_seconds"
          :min="1"
          :max="3600"
          style="width: 100%"
        />
        <div class="form-hint">范围: 1-3600秒，建议设置为10秒以上</div>
      </a-form-item>
    </a-form>

    <div class="modal-footer">
      <a-button @click="handleClose">取消</a-button>
      <a-button type="primary" :loading="loading" @click="handleSubmit">
        确定
      </a-button>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { message } from 'ant-design-vue';
import { createMonitorTask } from '@/api/monitor';

const props = defineProps<{
  visible: boolean;
  dataSourceId: number;
  dataSourceName: string;
  sourceType: string;
  connectionConfig: Record<string, any> | null;
  queryConfig: string;
  chartType: string;
  subgroupSize: number;
  confidenceLevel: string;
}>();

const emit = defineEmits(['update:visible', 'success']);

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
});

const loading = ref(false);

const formData = reactive({
  name: '',
  data_source_id: 0,
  chart_type: 'xbar_r',
  subgroup_size: 5,
  confidence_level: '99',
  interval_seconds: 10,
});

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

// 置信水平选项
const confidenceLevelOptions = [
  { value: '99.73', label: '99.73% (3σ)' },
  { value: '95.45', label: '95.45% (2σ)' },
  { value: '99', label: '99% (2.58σ)' },
];

// 获取图表类型标签
const getChartTypeLabel = (value: string) => {
  const option = chartTypeOptions.find(opt => opt.value === value);
  return option ? option.label : value;
};

// 获取置信水平标签
const getConfidenceLevelLabel = (value: string) => {
  const option = confidenceLevelOptions.find(opt => opt.value === value);
  return option ? option.label : value;
};

// 数据源类型标签映射
const sourceTypeLabels: Record<string, string> = {
  manual: '手动输入',
  file: '文件导入',
  system: '系统对接',
  ERP: 'ERP',
  MES: 'MES',
  PLC: 'PLC',
  DATABASE: '数据库',
};

// 将连接配置中的密码字段转为密文
const maskConnectionConfig = (config: Record<string, any> | null): string => {
  if (!config) return '-';
  const masked = { ...config };
  // 常见密码字段名
  const passwordKeys = ['password', 'passwd', 'pwd', 'secret', 'token', 'key'];
  for (const key of Object.keys(masked)) {
    if (passwordKeys.some(pk => key.toLowerCase().includes(pk))) {
      masked[key] = '********';
    }
  }
  return JSON.stringify(masked, null, 2);
};

// 监听props变化，更新formData
watch(() => props.visible, (val) => {
  if (val) {
    formData.name = `监控任务_${Date.now()}`;
    formData.data_source_id = props.dataSourceId;
    formData.chart_type = props.chartType;
    formData.subgroup_size = props.subgroupSize;
    formData.confidence_level = props.confidenceLevel;
    formData.interval_seconds = 10;
  }
});

const handleClose = () => {
  visible.value = false;
};

const handleSubmit = async () => {
  if (!formData.name.trim()) {
    message.warning('请输入任务名称');
    return;
  }

  if (formData.interval_seconds < 1 || formData.interval_seconds > 3600) {
    message.warning('监控间隔必须在1-3600秒之间');
    return;
  }

  loading.value = true;
  try {
    await createMonitorTask({
      name: formData.name.trim(),
      data_source_id: formData.data_source_id,
      chart_type: formData.chart_type,
      subgroup_size: formData.subgroup_size,
      confidence_level: formData.confidence_level,
      interval_seconds: formData.interval_seconds,
    });

    message.success('监控任务创建成功');
    emit('success');
    handleClose();
  } catch (error: any) {
    const errMsg = error?.response?.data?.detail || '创建失败';
    message.error(errMsg);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.create-monitor-form {
  padding: 8px 0;
}

.config-preview {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e8e8e8;
}

.config-item:last-child {
  border-bottom: none;
}

.config-item--block {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.config-label {
  color: #666;
  font-size: 14px;
  white-space: nowrap;
  min-width: 80px;
}

.config-value {
  color: #333;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.config-value--code {
  text-align: left;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  font-weight: 400;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 8px 10px;
  margin: 0;
  width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 160px;
  overflow-y: auto;
}

.form-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
}
</style>