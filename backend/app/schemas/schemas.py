"""
Pydantic数据模型（Schemas）
用于API请求/响应的数据验证
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举定义 ====================

class DataSourceType(str, Enum):
    MANUAL = "manual"
    FILE = "file"
    SYSTEM = "system"


class SystemSourceType(str, Enum):
    ERP = "ERP"
    MES = "MES"
    PLC = "PLC"
    DATABASE = "DATABASE"


class ChartType(str, Enum):
    XBAR_R = "xbar_r"
    XBAR_S = "xbar_s"
    I_MR = "i_mr"
    P_CHART = "p_chart"
    NP_CHART = "np_chart"
    C_CHART = "c_chart"
    U_CHART = "u_chart"
    HISTOGRAM = "histogram"
    TREND = "trend"


class ConfidenceLevel(str, Enum):
    THREE_SIGMA = "99.73"
    TWO_SIGMA = "95.45"
    TWO_FIVE_EIGHT_SIGMA = "99"


# ==================== 数据输入相关 ====================

class ManualDataInput(BaseModel):
    """手动输入数据"""
    name: str = Field(..., description="数据标题")
    data_values: List[float] = Field(..., description="数据值，一维数组")


class FileDataInput(BaseModel):
    """文件导入数据"""
    name: str = Field(..., description="数据标题")
    file_name: str = Field(..., description="原始文件名")


class SystemDataInput(BaseModel):
    """系统对接配置"""
    name: str = Field(..., description="数据标题")
    system_type: SystemSourceType = Field(..., description="系统类型")
    connection_config: Dict[str, Any] = Field(..., description="连接配置")
    query_config: str = Field(..., description="数据查询配置")


class DataSourceCreate(BaseModel):
    """创建数据源"""
    source_type: DataSourceType = Field(..., description="数据源类型")
    name: str = Field(..., description="数据标题")
    data_values: Optional[List[List[float]]] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    system_type: Optional[SystemSourceType] = None
    connection_config: Optional[Dict[str, Any]] = None
    query_config: Optional[str] = None


class DataSourceResponse(BaseModel):
    """数据源响应"""
    id: int
    name: str
    source_type: DataSourceType
    data_values: Optional[List[List[float]]] = None
    file_name: Optional[str] = None
    system_type: Optional[SystemSourceType] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 分析配置相关 ====================

class AnalysisConfigCreate(BaseModel):
    """创建分析配置"""
    data_source_id: int = Field(..., description="数据源ID")
    chart_type: ChartType = Field(default=ChartType.XBAR_R, description="图表类型")
    subgroup_size: int = Field(default=5, ge=1, le=100, description="子组大小")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.TWO_FIVE_EIGHT_SIGMA, description="置信水平")
    show_rules: bool = Field(default=True, description="显示判异规则")
    show_prediction: bool = Field(default=False, description="显示预测区间")


class AnalysisConfigUpdate(BaseModel):
    """更新分析配置"""
    chart_type: Optional[ChartType] = None
    subgroup_size: Optional[int] = Field(None, ge=1, le=100)
    confidence_level: Optional[ConfidenceLevel] = None
    show_rules: Optional[bool] = None
    show_prediction: Optional[bool] = None


class AnalysisConfigResponse(BaseModel):
    """分析配置响应"""
    id: int
    data_source_id: int
    chart_type: ChartType
    subgroup_size: int
    confidence_level: ConfidenceLevel
    show_rules: bool
    show_prediction: bool
    statistics_result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 统计结果相关 ====================

class StatisticsResult(BaseModel):
    """统计结果"""
    sample_count: int = Field(..., description="样本数")
    mean: float = Field(..., description="均值")
    std_dev: float = Field(..., description="标准差")
    cv: float = Field(..., description="变异系数")
    min_val: float = Field(..., description="最小值")
    median: float = Field(..., description="中位数")
    max_val: float = Field(..., description="最大值")
    range_val: float = Field(..., description="极差")
    
    # 控制限
    ucl: Optional[float] = Field(None, description="上控制限")
    lcl: Optional[float] = Field(None, description="下控制限")
    cl: Optional[float] = Field(None, description="中心线")


# ==================== 监控任务相关 ====================

class MonitorTaskCreate(BaseModel):
    """创建监控任务"""
    name: str = Field(..., description="任务名称")
    data_source_id: int = Field(..., description="数据源ID")
    analysis_config_id: int = Field(..., description="分析配置ID")
    interval_seconds: int = Field(default=10, ge=1, le=3600, description="监控间隔（秒）")


class MonitorTaskResponse(BaseModel):
    """监控任务响应"""
    id: int
    name: str
    data_source_id: int
    analysis_config_id: int
    interval_seconds: int
    is_active: bool
    last_run_at: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None
    has_anomaly: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== AI分析相关 ====================

class AIAnalysisRequest(BaseModel):
    """AI分析请求"""
    data_source_id: int = Field(..., description="数据源ID")
    analysis_config_id: Optional[int] = Field(None, description="分析配置ID")


class AIAnalysisResponse(BaseModel):
    """AI分析响应"""
    id: int
    data_source_id: int
    analysis_result: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 系统设置相关 ====================

class SystemSettingsUpdate(BaseModel):
    """更新系统设置"""
    decimal_places: Optional[int] = Field(None, ge=0, le=10, description="小数位数")
    chart_theme: Optional[str] = Field(None, description="图表主题")
    auto_save: Optional[bool] = Field(None, description="自动保存")


class SystemSettingsResponse(BaseModel):
    """系统设置响应"""
    id: int
    decimal_places: int
    chart_theme: str
    auto_save: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 通用响应 ====================

class ApiResponse(BaseModel):
    """通用API响应"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    error_code: Optional[str] = None