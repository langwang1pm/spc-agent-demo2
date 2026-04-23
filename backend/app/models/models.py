"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import Table
import enum
from app.core.database import Base


class DataSourceType(str, enum.Enum):
    """数据源类型枚举"""
    MANUAL = "manual"           # 手动输入
    FILE = "file"               # 文件导入
    SYSTEM = "system"           # 系统对接


class SystemSourceType(str, enum.Enum):
    """系统对接类型枚举"""
    ERP = "ERP"
    MES = "MES"
    PLC = "PLC"
    DATABASE = "DATABASE"


class ChartType(str, enum.Enum):
    """图表类型枚举"""
    XBAR_R = "xbar_r"           # X̄-R 控制图（均值-极差）
    XBAR_S = "xbar_s"           # X̄-S 控制图（均值-标准差）
    I_MR = "i_mr"               # I-MR 控制图（单值-移动极差）
    P_CHART = "p_chart"         # p 控制图（不合格品率）
    NP_CHART = "np_chart"       # np 控制图（不合格品数）
    C_CHART = "c_chart"         # c 控制图（缺陷数）
    U_CHART = "u_chart"         # u 控制图（单位缺陷数）
    HISTOGRAM = "histogram"     # 直方图
    TREND = "trend"             # 趋势图


class ConfidenceLevel(str, enum.Enum):
    """置信水平枚举"""
    THREE_SIGMA = "99.73"       # 3σ
    TWO_SIGMA = "95.45"         # 2σ
    TWO_FIVE_EIGHT_SIGMA = "99" # 2.58σ


class DataSource(Base):
    """数据源表 - 存储用户输入的各种数据源"""
    __tablename__ = "data_sources"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="数据标题")
    source_type = Column(SQLEnum(DataSourceType), nullable=False, default=DataSourceType.MANUAL, comment="数据源类型")
    
    # 手动输入数据
    data_values = Column(JSON, nullable=True, comment="数据值，二维数组格式")
    
    # 文件导入
    file_path = Column(String(500), nullable=True, comment="文件路径")
    file_name = Column(String(255), nullable=True, comment="原始文件名")
    
    # 系统对接
    system_type = Column(SQLEnum(SystemSourceType), nullable=True, comment="系统类型：ERP/MES/PLC/DATABASE")
    connection_config = Column(JSON, nullable=True, comment="连接配置")
    query_config = Column(Text, nullable=True, comment="数据查询配置")
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 关联
    analysis_configs = relationship("AnalysisConfig", back_populates="data_source")
    monitor_tasks = relationship("MonitorTask", back_populates="data_source")


class AnalysisConfig(Base):
    """分析配置表"""
    __tablename__ = "analysis_configs"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey("spc_agent_demo.data_sources.id"), nullable=False, comment="关联的数据源ID")
    
    # 配置项
    chart_type = Column(SQLEnum(ChartType), nullable=False, default=ChartType.XBAR_R, comment="图表类型")
    subgroup_size = Column(Integer, nullable=False, default=5, comment="子组大小")
    confidence_level = Column(SQLEnum(ConfidenceLevel), nullable=False, default=ConfidenceLevel.TWO_FIVE_EIGHT_SIGMA, comment="置信水平")
    show_rules = Column(Boolean, default=True, comment="显示判异规则")
    show_prediction = Column(Boolean, default=False, comment="显示预测区间")
    
    # 计算结果缓存
    statistics_result = Column(JSON, nullable=True, comment="统计结果缓存")
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    data_source = relationship("DataSource", back_populates="analysis_configs")
    monitor_tasks = relationship("MonitorTask", back_populates="analysis_config")


class MonitorTask(Base):
    """监控任务表"""
    __tablename__ = "monitor_tasks"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="任务名称")
    data_source_id = Column(Integer, ForeignKey("spc_agent_demo.data_sources.id"), nullable=False, comment="数据源ID")
    analysis_config_id = Column(Integer, ForeignKey("spc_agent_demo.analysis_configs.id"), nullable=False, comment="分析配置ID")
    
    # 监控配置
    interval_seconds = Column(Integer, nullable=False, default=10, comment="监控间隔（秒）")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 运行状态
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="上次运行时间")
    last_result = Column(JSON, nullable=True, comment="上次运行结果")
    has_anomaly = Column(Boolean, default=False, comment="是否存在异常")
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联
    data_source = relationship("DataSource", back_populates="monitor_tasks")
    analysis_config = relationship("AnalysisConfig", back_populates="monitor_tasks")
    anomaly_records = relationship("AnomalyRecord", back_populates="monitor_task")


class AnomalyRecord(Base):
    """异常记录表"""
    __tablename__ = "anomaly_records"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monitor_task_id = Column(Integer, ForeignKey("spc_agent_demo.monitor_tasks.id"), nullable=False, comment="监控任务ID")
    
    # 异常信息
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), comment="检测时间")
    anomaly_type = Column(String(100), nullable=True, comment="异常类型")
    anomaly_data = Column(JSON, nullable=True, comment="异常数据")
    context_data = Column(JSON, nullable=True, comment="上下文数据（前后10组数据）")
    
    # 通知状态
    feishu_notified = Column(Boolean, default=False, comment="是否已发送飞书通知")
    notified_at = Column(DateTime(timezone=True), nullable=True, comment="通知时间")
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    monitor_task = relationship("MonitorTask", back_populates="anomaly_records")


class AIAnalysisRecord(Base):
    """AI分析记录表"""
    __tablename__ = "ai_analysis_records"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey("spc_agent_demo.data_sources.id"), nullable=False, comment="数据源ID")
    analysis_config_id = Column(Integer, ForeignKey("spc_agent_demo.analysis_configs.id"), nullable=True, comment="分析配置ID")
    
    # AI分析结果
    analysis_result = Column(Text, nullable=True, comment="分析结果（Markdown格式）")
    raw_response = Column(JSON, nullable=True, comment="原始AI响应")
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemSettings(Base):
    """系统设置表"""
    __tablename__ = "system_settings"
    __table_args__ = {"schema": "spc_agent_demo"}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 设置项
    decimal_places = Column(Integer, default=2, comment="小数位数")
    chart_theme = Column(String(50), default="default", comment="图表主题：default/light/dark")
    auto_save = Column(Boolean, default=True, comment="自动保存")
    
    # 元数据
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())