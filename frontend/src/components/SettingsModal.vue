<template>
  <a-modal
    v-model:open="visible"
    title="系统设置"
    width="500px"
    @ok="handleSave"
  >
    <a-form layout="vertical">
      <a-form-item label="小数位数">
        <a-select v-model:value="settings.decimal_places">
          <a-select-option :value="2">2位</a-select-option>
          <a-select-option :value="3">3位</a-select-option>
          <a-select-option :value="4">4位</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="图表主题">
        <a-select v-model:value="settings.chart_theme">
          <a-select-option value="default">默认</a-select-option>
          <a-select-option value="light">浅色</a-select-option>
          <a-select-option value="dark">深色</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="自动保存">
        <a-switch v-model:checked="settings.auto_save" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { message } from 'ant-design-vue';
import { getSettings, updateSettings } from '@/api/settings';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['update:visible', 'update']);

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
});

const settings = ref({
  decimal_places: 2,
  chart_theme: 'default',
  auto_save: true,
});

const loadSettings = async () => {
  try {
    const res = await getSettings();
    settings.value = res.data;
  } catch (error) {
    console.error('加载设置失败:', error);
  }
};

const handleSave = async () => {
  try {
    await updateSettings(settings.value);
    emit('update', settings.value);
    message.success('设置保存成功');
    visible.value = false;
  } catch (error) {
    message.error('设置保存失败');
  }
};

watch(() => props.visible, (val) => {
  if (val) {
    loadSettings();
  }
});
</script>