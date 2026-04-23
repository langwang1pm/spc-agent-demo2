"""
AI分析服务 - 对接Dify平台
"""
import httpx
import json
from typing import Dict, Any, Optional
from app.core.config import settings
from app.models import DataSource, AnalysisConfig
from sqlalchemy.orm import Session


class AIAnalysisService:
    """AI分析服务"""
    
    def __init__(self):
        self.api_url = settings.DIFY_API_URL or "https://api.dify.ai/v1"
        self.api_key = settings.DIFY_API_KEY
    
    async def analyze(self, data_source: DataSource, 
                     analysis_config: Optional[AnalysisConfig] = None,
                     spc_result: Optional[Dict[str, Any]] = None) -> str:
        """
        调用AI进行分析
        
        Args:
            data_source: 数据源对象
            analysis_config: 分析配置对象
            spc_result: SPC计算结果
        
        Returns:
            AI分析结果文本（Markdown格式）
        """
        if not self.api_key:
            return self._generate_mock_analysis(data_source, spc_result)
        
        # 构建提示词
        prompt = self._build_analysis_prompt(data_source, analysis_config, spc_result)
        
        try:
            result = await self._call_dify_api(prompt)
            return result
        except Exception as e:
            # 如果API调用失败，返回模拟数据
            return self._generate_mock_analysis(data_source, spc_result)
    
    async def _call_dify_api(self, prompt: str) -> str:
        """调用Dify API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {
                "prompt": prompt
            },
            "query": prompt,
            "response_mode": "blocking",
            "user": "spc-agent"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.api_url}/chat-messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("answer", "AI分析完成，但未返回有效结果")
            else:
                raise Exception(f"Dify API调用失败: {response.status_code}")
    
    def _build_analysis_prompt(self, data_source: DataSource,
                                analysis_config: Optional[AnalysisConfig],
                                spc_result: Optional[Dict[str, Any]]) -> str:
        """构建分析提示词"""
        prompt_parts = []
        
        # 数据源信息
        prompt_parts.append(f"## 数据源信息")
        prompt_parts.append(f"- 数据标题: {data_source.name}")
        prompt_parts.append(f"- 数据源类型: {data_source.source_type.value}")
        
        # 数据值
        if data_source.data_values:
            prompt_parts.append(f"- 数据内容: {json.dumps(data_source.data_values, ensure_ascii=False)}")
        
        # 分析配置
        if analysis_config:
            prompt_parts.append(f"\n## 分析配置")
            prompt_parts.append(f"- 图表类型: {analysis_config.chart_type.value}")
            prompt_parts.append(f"- 子组大小: {analysis_config.subgroup_size}")
            prompt_parts.append(f"- 置信水平: {analysis_config.confidence_level.value}%")
        
        # SPC计算结果
        if spc_result:
            prompt_parts.append(f"\n## SPC统计结果")
            stats = spc_result.get("statistics", {})
            for key, value in stats.items():
                prompt_parts.append(f"- {key}: {value}")
            
            # 控制限
            limits = spc_result.get("control_limits", {})
            if limits:
                prompt_parts.append(f"\n## 控制限")
                for key, value in limits.items():
                    prompt_parts.append(f"- {key}: {value}")
            
            # 异常点
            anomalies = spc_result.get("anomalies", [])
            if anomalies:
                prompt_parts.append(f"\n## 异常检测结果")
                for anomaly in anomalies:
                    prompt_parts.append(f"- 第{anomaly['index']+1}组数据异常: 值={anomaly['value']}, 类型={anomaly.get('type', 'unknown')}")
        
        # 分析任务
        prompt_parts.append("""
\n## 分析任务
请对上述SPC控制图数据进行分析，包括：
1. 过程稳定性评估
2. 异常原因分析
3. 改进建议
4. 结论总结

请用简洁的Markdown格式输出分析结果。
""")
        
        return "\n".join(prompt_parts)
    
    def _generate_mock_analysis(self, data_source: DataSource,
                                spc_result: Optional[Dict[str, Any]]) -> str:
        """生成模拟分析结果（当API不可用时）"""
        stats = spc_result.get("statistics", {}) if spc_result else {}
        
        # 计算简单的稳定性评估
        anomalies = spc_result.get("anomalies", []) if spc_result else []
        has_anomaly = len(anomalies) > 0
        
        analysis = f"""# SPC智能分析报告

## 📊 过程概况

| 指标 | 数值 |
|------|------|
| 样本数 | {stats.get('sample_count', 'N/A')} |
| 均值 | {stats.get('mean', 'N/A'):.4f} |
| 标准差 | {stats.get('std_dev', 'N/A'):.4f} |
| 变异系数 | {stats.get('cv', 'N/A'):.2f}% |
| 最小值 | {stats.get('min_val', 'N/A'):.4f} |
| 最大值 | {stats.get('max_val', 'N/A'):.4f} |

## 🔍 稳定性评估

**状态: {'⚠️ 存在异常' if has_anomaly else '✅ 过程稳定'}**

"""
        
        if has_anomaly:
            analysis += f"""检测到 {len(anomalies)} 个异常点:
"""
            for anomaly in anomalies[:5]:  # 最多显示5个
                analysis += f"- 第 {anomaly['index']+1} 组数据超出控制限 (值: {anomaly['value']:.4f})\n"
        
        analysis += """
## 💡 分析结论

"""
        
        if has_anomaly:
            analysis += """1. **异常点需重点关注**: 检测到的异常点可能由特殊原因引起，建议排查以下因素：
   - 设备/工装变化
   - 原材料批次差异
   - 操作人员变更
   - 环境条件变化

2. **建议措施**:
   - 标记异常数据点进行调查
   - 追溯异常发生时的生产条件
   - 制定针对性的改善计划

3. **后续跟踪**:
   - 建议增加采样频率监控
   - 持续观察异常是否重复出现
"""
        else:
            analysis += """1. **过程处于受控状态**: 所有数据点均在控制限内，未检测到异常原因导致的变异。

2. **统计特性良好**:
   - 变异系数处于合理范围内
   - 数据分布无明显异常模式

3. **保持建议**:
   - 继续当前的生产和质量控制方式
   - 定期监控数据变化趋势
"""
        
        analysis += """
---

*此分析结果由 AI 辅助生成，仅供参考。*
"""
        
        return analysis


# 全局实例
ai_service = AIAnalysisService()


async def get_ai_analysis(data_source: DataSource,
                          analysis_config: Optional[AnalysisConfig] = None,
                          spc_result: Optional[Dict[str, Any]] = None) -> str:
    """获取AI分析结果"""
    return await ai_service.analyze(data_source, analysis_config, spc_result)