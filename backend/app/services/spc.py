"""
SPC核心计算服务
实现9种控制图的计算逻辑
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ChartType(str, Enum):
    """图表类型枚举"""
    XBAR_R = "xbar_r"
    XBAR_S = "xbar_s"
    I_MR = "i_mr"
    P_CHART = "p_chart"
    NP_CHART = "np_chart"
    C_CHART = "c_chart"
    U_CHART = "u_chart"
    HISTOGRAM = "histogram"
    TREND = "trend"


# 控制图常数表（子组大小 n=2~25）
CONTROL_CHART_CONSTANTS = {
    # n: (d2, d3, D3, D4, c4, A2, A3, B3, B4)
    2:  (1.128, 0.853, 0.000, 3.267, 0.7979, 1.880, 2.224, 0.000, 3.267),
    3:  (1.693, 0.888, 0.000, 2.574, 0.8862, 1.023, 1.266, 0.000, 2.568),
    4:  (2.059, 0.880, 0.000, 2.282, 0.9213, 0.729, 0.855, 0.000, 2.266),
    5:  (2.326, 0.864, 0.000, 2.114, 0.9400, 0.577, 0.658, 0.000, 2.089),
    6:  (2.534, 0.848, 0.000, 2.004, 0.9515, 0.483, 0.544, 0.030, 1.970),
    7:  (2.704, 0.833, 0.076, 1.924, 0.9594, 0.419, 0.469, 0.118, 1.882),
    8:  (2.847, 0.820, 0.136, 1.864, 0.9650, 0.373, 0.415, 0.185, 1.815),
    9:  (2.970, 0.808, 0.184, 1.816, 0.9693, 0.337, 0.373, 0.239, 1.761),
    10: (3.078, 0.797, 0.223, 1.777, 0.9727, 0.308, 0.340, 0.284, 1.716),
    15: (3.472, 0.755, 0.388, 1.612, 0.9823, 0.223, 0.242, 0.544, 1.456),
    20: (3.735, 0.729, 0.459, 1.540, 0.9869, 0.180, 0.194, 0.621, 1.380),
    25: (3.931, 0.709, 0.504, 1.496, 0.9896, 0.153, 0.164, 0.681, 1.319),
}


@dataclass
class SPCResult:
    """SPC计算结果"""
    chart_type: str
    chart_data: Dict[str, Any]  # 图表需要的数据
    statistics: Dict[str, float]  # 统计指标
    control_limits: Dict[str, float]  # 控制限
    anomalies: List[Dict[str, Any]]  # 异常点列表
    rules_violations: List[Dict[str, Any]]  # 判异规则违反


class SPCCalculator:
    """SPC计算器"""
    
    def __init__(self, data: List[List[float]], chart_type: str = "xbar_r", 
                 subgroup_size: int = 5, confidence_level: str = "99"):
        """
        初始化SPC计算器
        
        Args:
            data: 二维数组数据
            chart_type: 图表类型
            subgroup_size: 子组大小
            confidence_level: 置信水平 (99.73/95.45/99)
        """
        self.data = np.array(data, dtype=float)
        self.chart_type = chart_type
        self.subgroup_size = subgroup_size
        self.confidence_level = confidence_level
        
        # 获取sigma倍数
        self.sigma_multiplier = self._get_sigma_multiplier()
        
        # 获取常数
        self._get_constants()
    
    def _get_sigma_multiplier(self) -> float:
        """根据置信水平获取sigma倍数"""
        multipliers = {
            "99.73": 3.0,   # 3σ
            "95.45": 2.0,  # 2σ
            "99": 2.58     # 2.58σ
        }
        return multipliers.get(self.confidence_level, 3.0)
    
    def _get_constants(self) -> Dict[str, float]:
        """获取控制图常数"""
        n = self.subgroup_size
        if n in CONTROL_CHART_CONSTANTS:
            d2, d3, D3, D4, c4, A2, A3, B3, B4 = CONTROL_CHART_CONSTANTS[n]
        else:
            # 对于n>25的情况，使用近似值
            d2 = 1.0 + 2.66 * np.log10(n)
            c4 = 1.0 - 1.0 / (2.0 * n)
            A2 = 2.0 / (d2)
            D3, D4 = 0.0, 3.0
        
        self.constants = {
            "d2": d2, "d3": d3, "D3": D3, "D4": D4,
            "c4": c4, "A2": A2, "A3": A3, "B3": B3, "B4": B4
        }
        return self.constants
    
    def calculate(self) -> SPCResult:
        """执行计算"""
        calculators = {
            "xbar_r": self._calculate_xbar_r,
            "xbar_s": self._calculate_xbar_s,
            "i_mr": self._calculate_i_mr,
            "p_chart": self._calculate_p_chart,
            "np_chart": self._calculate_np_chart,
            "c_chart": self._calculate_c_chart,
            "u_chart": self._calculate_u_chart,
            "histogram": self._calculate_histogram,
            "trend": self._calculate_trend,
        }
        
        calc_func = calculators.get(self.chart_type, self._calculate_xbar_r)
        return calc_func()
    
    def _calculate_xbar_r(self) -> SPCResult:
        """X̄-R 控制图（均值-极差）"""
        data = self.data
        n = self.subgroup_size
        
        # 计算子组均值
        group_means = np.mean(data, axis=1)
        # 计算子组极差
        group_ranges = np.max(data, axis=1) - np.min(data, axis=1)
        
        # 计算总体统计量
        x_double_bar = np.mean(group_means)  # 总均值
        r_bar = np.mean(group_ranges)  # 平均极差
        
        # 计算控制限
        d2 = self.constants["d2"]
        D3, D4 = self.constants["D3"], self.constants["D4"]
        A2 = self.constants["A2"]
        
        sigma_x = r_bar / d2
        
        UCL_X = x_double_bar + D4 * r_bar
        LCL_X = x_double_bar - D3 * r_bar
        CL_X = x_double_bar
        
        # R图控制限
        UCL_R = D4 * r_bar
        LCL_R = D3 * r_bar
        CL_R = r_bar
        
        # 检测异常
        anomalies = []
        for i, x in enumerate(group_means):
            if x > UCL_X or x < LCL_X:
                anomalies.append({
                    "index": i,
                    "value": float(x),
                    "type": "out_of_control",
                    "limit_violated": "UCL" if x > UCL_X else "LCL"
                })
        
        # 判异规则检测
        rules_violations = self._check_western_electric_rules(group_means, CL_X, sigma_x)
        
        # 统计结果
        flat_data = data.flatten()
        statistics = {
            "sample_count": len(flat_data),
            "mean": float(np.mean(flat_data)),
            "std_dev": float(np.std(flat_data, ddof=1)),
            "cv": float(np.std(flat_data, ddof=1) / np.mean(flat_data) * 100),
            "min_val": float(np.min(flat_data)),
            "median": float(np.median(flat_data)),
            "max_val": float(np.max(flat_data)),
            "range_val": float(np.max(flat_data) - np.min(flat_data)),
        }
        
        # 图表数据
        chart_data = {
            "xbar": {
                "labels": [f"组{i+1}" for i in range(len(group_means))],
                "data": group_means.tolist(),
                "ucl": float(UCL_X),
                "lcl": float(LCL_X),
                "cl": float(CL_X),
                "unit": "均值"
            },
            "range": {
                "labels": [f"组{i+1}" for i in range(len(group_ranges))],
                "data": group_ranges.tolist(),
                "ucl": float(UCL_R),
                "lcl": float(LCL_R),
                "cl": float(CL_R),
                "unit": "极差"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={
                "UCL": float(UCL_X), "LCL": float(LCL_X), "CL": float(CL_X),
                "UCL_R": float(UCL_R), "LCL_R": float(LCL_R), "CL_R": float(CL_R)
            },
            anomalies=anomalies,
            rules_violations=rules_violations
        )
    
    def _calculate_xbar_s(self) -> SPCResult:
        """X̄-S 控制图（均值-标准差）"""
        data = self.data
        n = self.subgroup_size
        
        # 计算子组均值
        group_means = np.mean(data, axis=1)
        # 计算子组标准差
        group_stds = np.std(data, axis=1, ddof=1)
        
        # 计算总体统计量
        x_double_bar = np.mean(group_means)  # 总均值
        s_bar = np.mean(group_stds)  # 平均标准差
        
        # 计算控制限
        c4 = self.constants["c4"]
        A3, B3, B4 = self.constants["A3"], self.constants["B3"], self.constants["B4"]
        
        sigma_s = s_bar / c4
        
        UCL_X = x_double_bar + A3 * s_bar
        LCL_X = x_double_bar - A3 * s_bar
        CL_X = x_double_bar
        
        UCL_S = B4 * s_bar
        LCL_S = B3 * s_bar
        CL_S = s_bar
        
        # 检测异常
        anomalies = []
        for i, x in enumerate(group_means):
            if x > UCL_X or x < LCL_X:
                anomalies.append({
                    "index": i,
                    "value": float(x),
                    "type": "out_of_control"
                })
        
        # 统计结果
        flat_data = data.flatten()
        statistics = {
            "sample_count": len(flat_data),
            "mean": float(np.mean(flat_data)),
            "std_dev": float(np.std(flat_data, ddof=1)),
            "cv": float(np.std(flat_data, ddof=1) / np.mean(flat_data) * 100),
            "min_val": float(np.min(flat_data)),
            "median": float(np.median(flat_data)),
            "max_val": float(np.max(flat_data)),
            "range_val": float(np.max(flat_data) - np.min(flat_data)),
        }
        
        chart_data = {
            "xbar": {
                "labels": [f"组{i+1}" for i in range(len(group_means))],
                "data": group_means.tolist(),
                "ucl": float(UCL_X),
                "lcl": float(LCL_X),
                "cl": float(CL_X),
                "unit": "均值"
            },
            "std": {
                "labels": [f"组{i+1}" for i in range(len(group_stds))],
                "data": group_stds.tolist(),
                "ucl": float(UCL_S),
                "lcl": float(LCL_S),
                "cl": float(CL_S),
                "unit": "标准差"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={
                "UCL": float(UCL_X), "LCL": float(LCL_X), "CL": float(CL_X),
                "UCL_S": float(UCL_S), "LCL_S": float(LCL_S), "CL_S": float(CL_S)
            },
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_i_mr(self) -> SPCResult:
        """I-MR 控制图（单值-移动极差）"""
        data = self.data.flatten()
        
        # 计算移动极差
        moving_ranges = np.abs(np.diff(data))
        
        # 统计量
        x_bar = np.mean(data)
        mr_bar = np.mean(moving_ranges)
        
        d2 = self.constants["d2"]
        D3, D4 = self.constants["D3"], self.constants["D4"]
        
        sigma = mr_bar / d2
        
        UCL_I = x_bar + self.sigma_multiplier * sigma
        LCL_I = x_bar - self.sigma_multiplier * sigma
        CL_I = x_bar
        
        UCL_MR = D4 * mr_bar
        LCL_MR = D3 * mr_bar
        CL_MR = mr_bar
        
        # 检测异常
        anomalies = []
        for i, x in enumerate(data):
            if x > UCL_I or x < LCL_I:
                anomalies.append({
                    "index": i,
                    "value": float(x),
                    "type": "out_of_control"
                })
        
        # 统计结果
        statistics = {
            "sample_count": len(data),
            "mean": float(x_bar),
            "std_dev": float(np.std(data, ddof=1)),
            "cv": float(np.std(data, ddof=1) / np.mean(data) * 100),
            "min_val": float(np.min(data)),
            "median": float(np.median(data)),
            "max_val": float(np.max(data)),
            "range_val": float(np.max(data) - np.min(data)),
        }
        
        chart_data = {
            "individual": {
                "labels": [f"{i+1}" for i in range(len(data))],
                "data": data.tolist(),
                "ucl": float(UCL_I),
                "lcl": float(LCL_I),
                "cl": float(CL_I),
                "unit": "单值"
            },
            "mr": {
                "labels": [f"{i+2}" for i in range(len(moving_ranges))],
                "data": moving_ranges.tolist(),
                "ucl": float(UCL_MR),
                "lcl": float(LCL_MR),
                "cl": float(CL_MR),
                "unit": "移动极差"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={
                "UCL": float(UCL_I), "LCL": float(LCL_I), "CL": float(CL_I),
                "UCL_MR": float(UCL_MR), "LCL_MR": float(LCL_MR), "CL_MR": float(CL_MR)
            },
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_p_chart(self) -> SPCResult:
        """p 控制图（不合格品率）"""
        data = self.data
        n = self.subgroup_size  # 子组大小
        
        # 每行是一个子组，第一列是不合格品数，第二列可以是样本数（可选）
        defectives = data[:, 0] if data.shape[1] >= 1 else data.flatten()
        
        # 计算不合格品率
        p_bar = np.sum(defectives) / np.sum([n] * len(defectives))
        
        sigma_p = np.sqrt(p_bar * (1 - p_bar) / n)
        
        UCL = p_bar + self.sigma_multiplier * sigma_p
        LCL = max(0, p_bar - self.sigma_multiplier * sigma_p)
        CL = p_bar
        
        # 检测异常
        p_values = defectives / n
        anomalies = []
        for i, p in enumerate(p_values):
            if p > UCL or p < LCL:
                anomalies.append({
                    "index": i,
                    "value": float(p),
                    "type": "out_of_control"
                })
        
        statistics = {
            "sample_count": int(np.sum([n] * len(defectives))),
            "mean": float(p_bar),
            "std_dev": float(sigma_p),
            "cv": float(sigma_p / p_bar * 100) if p_bar != 0 else 0,
            "min_val": float(np.min(p_values)),
            "median": float(np.median(p_values)),
            "max_val": float(np.max(p_values)),
            "range_val": float(np.max(p_values) - np.min(p_values)),
        }
        
        chart_data = {
            "p": {
                "labels": [f"组{i+1}" for i in range(len(p_values))],
                "data": p_values.tolist(),
                "ucl": float(UCL),
                "lcl": float(LCL),
                "cl": float(CL),
                "unit": "不合格品率"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={"UCL": float(UCL), "LCL": float(LCL), "CL": float(CL)},
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_np_chart(self) -> SPCResult:
        """np 控制图（不合格品数）"""
        data = self.data.flatten()
        n = self.subgroup_size
        
        p_bar = np.sum(data) / (n * len(data))
        
        sigma_np = np.sqrt(n * p_bar * (1 - p_bar))
        
        UCL = n * p_bar + self.sigma_multiplier * sigma_np
        LCL = max(0, n * p_bar - self.sigma_multiplier * sigma_np)
        CL = n * p_bar
        
        anomalies = []
        for i, x in enumerate(data):
            if x > UCL or x < LCL:
                anomalies.append({
                    "index": i,
                    "value": float(x),
                    "type": "out_of_control"
                })
        
        statistics = {
            "sample_count": len(data) * n,
            "mean": float(n * p_bar),
            "std_dev": float(sigma_np),
            "cv": float(sigma_np / (n * p_bar) * 100) if p_bar != 0 else 0,
            "min_val": float(np.min(data)),
            "median": float(np.median(data)),
            "max_val": float(np.max(data)),
            "range_val": float(np.max(data) - np.min(data)),
        }
        
        chart_data = {
            "np": {
                "labels": [f"组{i+1}" for i in range(len(data))],
                "data": data.tolist(),
                "ucl": float(UCL),
                "lcl": float(LCL),
                "cl": float(CL),
                "unit": "不合格品数"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={"UCL": float(UCL), "LCL": float(LCL), "CL": float(CL)},
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_c_chart(self) -> SPCResult:
        """c 控制图（缺陷数）"""
        data = self.data.flatten()
        
        c_bar = np.mean(data)
        sigma_c = np.sqrt(c_bar)
        
        UCL = c_bar + self.sigma_multiplier * sigma_c
        LCL = max(0, c_bar - self.sigma_multiplier * sigma_c)
        CL = c_bar
        
        anomalies = []
        for i, x in enumerate(data):
            if x > UCL or x < LCL:
                anomalies.append({
                    "index": i,
                    "value": float(x),
                    "type": "out_of_control"
                })
        
        statistics = {
            "sample_count": len(data),
            "mean": float(c_bar),
            "std_dev": float(sigma_c),
            "cv": float(sigma_c / c_bar * 100) if c_bar != 0 else 0,
            "min_val": float(np.min(data)),
            "median": float(np.median(data)),
            "max_val": float(np.max(data)),
            "range_val": float(np.max(data) - np.min(data)),
        }
        
        chart_data = {
            "c": {
                "labels": [f"组{i+1}" for i in range(len(data))],
                "data": data.tolist(),
                "ucl": float(UCL),
                "lcl": float(LCL),
                "cl": float(CL),
                "unit": "缺陷数"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={"UCL": float(UCL), "LCL": float(LCL), "CL": float(CL)},
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_u_chart(self) -> SPCResult:
        """u 控制图（单位缺陷数）"""
        data = self.data
        n = self.subgroup_size
        
        defects = data[:, 0] if data.shape[1] >= 1 else data.flatten()
        u_values = defects / n
        
        u_bar = np.sum(defects) / np.sum(n for _ in range(len(defects)))
        sigma_u = np.sqrt(u_bar / n)
        
        UCL = u_bar + self.sigma_multiplier * sigma_u
        LCL = max(0, u_bar - self.sigma_multiplier * sigma_u)
        CL = u_bar
        
        anomalies = []
        for i, u in enumerate(u_values):
            if u > UCL or u < LCL:
                anomalies.append({
                    "index": i,
                    "value": float(u),
                    "type": "out_of_control"
                })
        
        statistics = {
            "sample_count": int(np.sum(n for _ in range(len(defects)))),
            "mean": float(u_bar),
            "std_dev": float(np.std(u_values, ddof=1)),
            "cv": float(np.std(u_values, ddof=1) / u_bar * 100) if u_bar != 0 else 0,
            "min_val": float(np.min(u_values)),
            "median": float(np.median(u_values)),
            "max_val": float(np.max(u_values)),
            "range_val": float(np.max(u_values) - np.min(u_values)),
        }
        
        chart_data = {
            "u": {
                "labels": [f"组{i+1}" for i in range(len(u_values))],
                "data": u_values.tolist(),
                "ucl": float(UCL),
                "lcl": float(LCL),
                "cl": float(CL),
                "unit": "单位缺陷数"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={"UCL": float(UCL), "LCL": float(LCL), "CL": float(CL)},
            anomalies=anomalies,
            rules_violations=[]
        )
    
    def _calculate_histogram(self) -> SPCResult:
        """直方图"""
        data = self.data.flatten()
        
        # 计算统计量
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        min_val = np.min(data)
        max_val = np.max(data)
        
        # 创建直方图数据
        n_bins = min(20, int(np.sqrt(len(data))) + 1)
        hist, bin_edges = np.histogram(data, bins=n_bins)
        
        # 统计结果
        statistics = {
            "sample_count": len(data),
            "mean": float(mean),
            "std_dev": float(std),
            "cv": float(std / mean * 100),
            "min_val": float(min_val),
            "median": float(np.median(data)),
            "max_val": float(max_val),
            "range_val": float(max_val - min_val),
        }
        
        chart_data = {
            "histogram": {
                "bins": bin_edges.tolist(),
                "frequencies": hist.tolist(),
                "mean": float(mean),
                "std": float(std),
                "unit": "数据值"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={},
            anomalies=[],
            rules_violations=[]
        )
    
    def _calculate_trend(self) -> SPCResult:
        """趋势图"""
        data = self.data.flatten()
        
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        # 添加趋势线（线性回归）
        x = np.arange(len(data))
        slope, intercept = np.polyfit(x, data, 1)
        trend_line = slope * x + intercept
        
        statistics = {
            "sample_count": len(data),
            "mean": float(mean),
            "std_dev": float(std),
            "cv": float(std / mean * 100),
            "min_val": float(np.min(data)),
            "median": float(np.median(data)),
            "max_val": float(np.max(data)),
            "range_val": float(np.max(data) - np.min(data)),
        }
        
        chart_data = {
            "trend": {
                "labels": [f"{i+1}" for i in range(len(data))],
                "data": data.tolist(),
                "trend_line": trend_line.tolist(),
                "mean": float(mean),
                "upper_limit": float(mean + 2 * std),
                "lower_limit": float(mean - 2 * std),
                "unit": "数据值"
            }
        }
        
        return SPCResult(
            chart_type=self.chart_type,
            chart_data=chart_data,
            statistics=statistics,
            control_limits={
                "upper_limit": float(mean + 2 * std),
                "lower_limit": float(mean - 2 * std),
                "CL": float(mean)
            },
            anomalies=[],
            rules_violations=[]
        )
    
    def _check_western_electric_rules(self, data: np.ndarray, 
                                       cl: float, sigma: float) -> List[Dict[str, Any]]:
        """西格玛规则检测（判异规则）"""
        violations = []
        n = len(data)
        
        # 规则1: 1个点超出3σ控制限
        ucl = cl + 3 * sigma
        lcl = cl - 3 * sigma
        for i, x in enumerate(data):
            if x > ucl or x < lcl:
                violations.append({
                    "rule": "Rule 1",
                    "description": "1个点超出3σ控制限",
                    "index": i,
                    "value": float(x)
                })
        
        # 规则2: 连续2个点中有1个超出2σ控制限
        ucl2 = cl + 2 * sigma
        lcl2 = cl - 2 * sigma
        for i in range(n - 1):
            if (data[i] > ucl2 or data[i] < lcl2) or (data[i+1] > ucl2 or data[i+1] < lcl2):
                if data[i] > ucl2 or data[i] < lcl2:
                    violations.append({
                        "rule": "Rule 2",
                        "description": "连续2个点中有1个超出2σ控制限",
                        "indices": [i, i+1]
                    })
        
        # 规则3: 连续5个点中有4个超出1σ控制限
        ucl1 = cl + sigma
        lcl1 = cl - sigma
        for i in range(n - 4):
            segment = data[i:i+5]
            beyond_1sigma = sum(1 for x in segment if x > ucl1 or x < lcl1)
            if beyond_1sigma >= 4:
                violations.append({
                    "rule": "Rule 3",
                    "description": "连续5个点中有4个超出1σ控制限",
                    "indices": list(range(i, i+5))
                })
        
        # 规则4: 连续8个点都在中心线同一侧
        for i in range(n - 7):
            segment = data[i:i+8]
            if all(x > cl for x in segment) or all(x < cl for x in segment):
                violations.append({
                    "rule": "Rule 4",
                    "description": "连续8个点都在中心线同一侧",
                    "indices": list(range(i, i+8))
                })
        
        # 规则5: 连续6个点递增或递减
        for i in range(n - 5):
            segment = data[i:i+6]
            if all(segment[j] < segment[j+1] for j in range(5)):
                violations.append({
                    "rule": "Rule 5",
                    "description": "连续6个点递增",
                    "indices": list(range(i, i+6))
                })
            elif all(segment[j] > segment[j+1] for j in range(5)):
                violations.append({
                    "rule": "Rule 5",
                    "description": "连续6个点递减",
                    "indices": list(range(i, i+6))
                })
        
        return violations


def calculate_spc(data: List[List[float]], chart_type: str = "xbar_r",
                  subgroup_size: int = 5, confidence_level: str = "99",
                  show_rules: bool = True, show_prediction: bool = False) -> Dict[str, Any]:
    """
    SPC计算的便捷函数
    
    Args:
        data: 二维数组数据
        chart_type: 图表类型
        subgroup_size: 子组大小
        confidence_level: 置信水平
        show_rules: 是否显示判异规则
        show_prediction: 是否显示预测区间
    
    Returns:
        包含图表数据、统计结果、控制限、异常点的字典
    """
    calculator = SPCCalculator(data, chart_type, subgroup_size, confidence_level)
    result = calculator.calculate()
    
    return {
        "chart_type": result.chart_type,
        "chart_data": result.chart_data,
        "statistics": result.statistics,
        "control_limits": result.control_limits,
        "anomalies": result.anomalies,
        "rules_violations": result.rules_violations if show_rules else [],
        "prediction_intervals": {}  # 预测区间（后续扩展）
    }