"""
飞书服务 - 消息通知和卡片消息
"""
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.config import settings


class FeishuService:
    """飞书服务"""
    
    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.webhook_url = settings.FEISHU_WEBHOOK_URL
        self.api_base = "https://open.feishu.cn/open-apis"
        self._tenant_access_token = None
    
    async def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self._tenant_access_token:
            return self._tenant_access_token
        
        url = f"{self.api_base}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            
            if data.get("code") == 0:
                self._tenant_access_token = data.get("tenant_access_token")
                return self._tenant_access_token
            else:
                raise Exception(f"获取飞书Access Token失败: {data.get('msg')}")
    
    async def send_webhook_message(self, msg_type: str = "text", content: str = "") -> bool:
        """
        发送Webhook消息到飞书群
        
        Args:
            msg_type: 消息类型 (text/card/interactive)
            content: 消息内容
        
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            print("[WARN] Feishu Webhook URL not configured")
            return False
        
        payload = {
            "msg_type": msg_type,
            "content": content if msg_type == "text" else None,
            "card": content if msg_type in ["card", "interactive"] else None
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                result = response.json()
                return result.get("code", -1) == 0 or response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Failed to send Feishu message: {e}")
            return False
    
    async def send_alarm_notification(self, anomaly_data: Dict[str, Any],
                                       monitor_task_name: str = "SPC监控任务") -> bool:
        """
        发送SPC异常告警通知到飞书群
        
        Args:
            anomaly_data: 异常数据
            monitor_task_name: 监控任务名称
        
        Returns:
            是否发送成功
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构建卡片消息
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "🚨 SPC异常告警"
                    },
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**任务名称:** {monitor_task_name}\n**检测时间:** {timestamp}"
                        }
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**异常类型:** {anomaly_data.get('anomaly_type', '超限')}\n**异常数据:** {json.dumps(anomaly_data.get('anomaly_data', {}), ensure_ascii=False)}"
                        }
                    },
                    {"tag": "hr"},
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "查看详情"
                                },
                                "type": "primary",
                                "url": self._build_detail_url(anomaly_data)
                            }
                        ]
                    }
                ]
            }
        }
        
        return await self.send_webhook_message("interactive", card)
    
    def _build_detail_url(self, anomaly_data: Dict[str, Any]) -> str:
        """构建详情URL"""
        # 这里应该构建一个可以跳转到系统的URL
        # 由于是飞书H5应用，可以构建一个飞书小程序或H5页面链接
        task_id = anomaly_data.get('monitor_task_id', '')
        anomaly_id = anomaly_data.get('id', '')
        
        # 预留链接格式
        return f"spc-agent://detail?task={task_id}&anomaly={anomaly_id}"
    
    async def send_chart_image(self, chart_image_base64: str,
                               anomaly_data: Dict[str, Any],
                               monitor_task_name: str = "SPC监控任务") -> bool:
        """
        发送图表图片到飞书
        
        Args:
            chart_image_base64: 图表图片的Base64编码
            anomaly_data: 异常数据
            monitor_task_name: 监控任务名称
        
        Returns:
            是否发送成功
        """
        # 构建图片消息卡片
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "📊 SPC异常时刻图表"
                    },
                    "template": "orange"
                },
                "elements": [
                    {
                        "tag": "img",
                        "img_key": f"data:image/png;base64,{chart_image_base64[:100]}...",  # 实际应用中需要上传到飞书获取img_key
                        "alt": {"tag": "plain_text", "content": "SPC控制图"}
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**任务:** {monitor_task_name}\n**时间:** {timestamp}"
                        }
                    }
                ]
            }
        }
        
        # 注意：飞书发送图片需要先上传图片获取img_key
        # 这里只是一个框架，实际使用时需要完善
        return await self.send_webhook_message("interactive", card)
    
    async def send_monitor_summary(self, task_data: Dict[str, Any]) -> bool:
        """
        发送监控任务汇总消息
        
        Args:
            task_data: 监控任务数据
        
        Returns:
            是否发送成功
        """
        status_emoji = "🟢" if task_data.get("is_active") else "🔴"
        
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{status_emoji} SPC监控任务状态"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"""**任务名称:** {task_data.get('name')}
**监控间隔:** {task_data.get('interval_seconds')}秒
**最近运行:** {task_data.get('last_run_at', '从未运行')}
**状态:** {'运行中' if task_data.get('is_active') else '已停止'}
**异常标记:** {'是' if task_data.get('has_anomaly') else '否'}"""
                        }
                    }
                ]
            }
        }
        
        return await self.send_webhook_message("interactive", card)


# 全局实例
feishu_service = FeishuService()


async def send_alarm(anomaly_data: Dict[str, Any], 
                     monitor_task_name: str = "SPC监控任务") -> bool:
    """发送告警通知"""
    return await feishu_service.send_alarm_notification(anomaly_data, monitor_task_name)


async def send_message(msg_type: str = "text", content: str = "") -> bool:
    """发送消息"""
    return await feishu_service.send_webhook_message(msg_type, content)