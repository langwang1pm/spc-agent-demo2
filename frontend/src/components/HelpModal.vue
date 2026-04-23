<template>
  <a-modal
    v-model:open="visible"
    title="使用帮助"
    width="700px"
    :footer="null"
  >
    <div class="help-content">
      <h3>系统简介</h3>
      <p>SPC Agent 是一个基于飞书的统计过程控制(SPC)智能分析工具，帮助您实时监控生产过程数据，及时发现异常并获取AI智能分析建议。</p>

      <h3>快速开始</h3>
      <ol>
        <li><strong>数据输入</strong>：在左侧区域选择数据输入方式（手动输入/文件导入/系统对接）</li>
        <li><strong>配置分析</strong>：根据需求选择图表类型、子组大小等参数</li>
        <li><strong>查看结果</strong>：系统自动生成控制图和统计结果</li>
        <li><strong>AI分析</strong>：获取智能化的过程分析和改进建议</li>
      </ol>

      <h3>图表类型说明</h3>
      <ul>
        <li><strong>X̄-R 控制图</strong>：用于子组大小2-10的连续数据</li>
        <li><strong>X̄-S 控制图</strong>：用于子组大小≥10的连续数据</li>
        <li><strong>I-MR 控制图</strong>：用于单个测量值（子组大小=1）</li>
        <li><strong>p/np 控制图</strong>：用于计数型数据（不合格品）</li>
        <li><strong>c/u 控制图</strong>：用于计数型数据（缺陷数）</li>
        <li><strong>直方图</strong>：显示数据分布</li>
        <li><strong>趋势图</strong>：显示数据变化趋势</li>
      </ul>

      <h3>判异规则</h3>
      <p>系统支持以下判异规则检测：</p>
      <ul>
        <li>规则1：1个点超出3σ控制限</li>
        <li>规则2：连续2个点中有1个超出2σ控制限</li>
        <li>规则3：连续5个点中有4个超出1σ控制限</li>
        <li>规则4：连续8个点都在中心线同一侧</li>
        <li>规则5：连续6个点递增或递减</li>
      </ul>

      <h3>快捷操作</h3>
      <ul>
        <li><strong>导出图表</strong>：点击控制图右上角"导出"按钮</li>
        <li><strong>全屏查看</strong>：点击"全屏"按钮放大图表</li>
        <li><strong>创建监控</strong>：设置自动监控任务，实时检测异常</li>
      </ul>

      <h3>联系我们</h3>
      <p>如有问题或建议，请联系系统管理员。</p>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits(['update:visible']);

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
});
</script>

<style scoped>
.help-content {
  max-height: 60vh;
  overflow-y: auto;
}

.help-content h3 {
  margin-top: 24px;
  margin-bottom: 12px;
  font-size: 16px;
  color: #1890ff;
}

.help-content h3:first-child {
  margin-top: 0;
}

.help-content p {
  line-height: 1.8;
  color: #333;
}

.help-content ol,
.help-content ul {
  padding-left: 24px;
  line-height: 2;
}

.help-content li {
  line-height: 1.8;
}
</style>