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


# 控制图常数表(子组大小 n=2~25)
# 来源: Western Electric Rules 标准常数表
# 字段: d2, d3, D3, D4, c4, A2, A3, B3, B4
CONTROL_CHART_CONSTANTS = {
    2:  (1.128, 0.853, 0.000, 3.267, 0.7979, 1.880, 2.224, 0.000, 3.267),
    3:  (1.693, 0.888, 0.000, 2.574, 0.8862, 1.023, 1.266, 0.000, 2.568),
    4:  (2.059, 0.880, 0.000, 2.282, 0.9213, 0.729, 0.855, 0.000, 2.266),
    5:  (2.326, 0.864, 0.000, 2.114, 0.9400, 0.577, 0.658, 0.000, 2.089),
    6:  (2.534, 0.848, 0.000, 2.004, 0.9515, 0.483, 0.544, 0.030, 1.970),
    7:  (2.704, 0.833, 0.076, 1.924, 0.9594, 0.419, 0.469, 0.118, 1.882),
    8:  (2.847, 0.820, 0.136, 1.864, 0.9650, 0.373, 0.415, 0.185, 1.815),
    9:  (2.970, 0.808, 0.184, 1.816, 0.9693, 0.337, 0.373, 0.239, 1.761),
    10: (3.078, 0.797, 0.223, 1.777, 0.9727, 0.308, 0.340, 0.284, 1.716),
    11: (3.173, 0.787, 0.256, 1.744, 0.9754, 0.285, 0.313, 0.329, 1.671),
    12: (3.258, 0.778, 0.283, 1.717, 0.9776, 0.266, 0.291, 0.367, 1.633),
    13: (3.336, 0.770, 0.307, 1.693, 0.9794, 0.249, 0.272, 0.401, 1.599),
    14: (3.407, 0.763, 0.328, 1.672, 0.9810, 0.235, 0.256, 0.431, 1.568),
    15: (3.472, 0.755, 0.388, 1.612, 0.9823, 0.223, 0.242, 0.544, 1.456),
    16: (3.532, 0.749, 0.399, 1.601, 0.9835, 0.212, 0.230, 0.561, 1.439),
    17: (3.588, 0.743, 0.415, 1.585, 0.9845, 0.203, 0.220, 0.581, 1.419),
    18: (3.640, 0.738, 0.429, 1.571, 0.9854, 0.194, 0.210, 0.599, 1.401),
    19: (3.689, 0.733, 0.443, 1.557, 0.9863, 0.187, 0.202, 0.616, 1.384),
    20: (3.735, 0.729, 0.459, 1.540, 0.9869, 0.180, 0.194, 0.621, 1.380),
    21: (3.778, 0.724, 0.469, 1.531, 0.9876, 0.174, 0.187, 0.636, 1.364),
    22: (3.819, 0.720, 0.478, 1.522, 0.9882, 0.168, 0.181, 0.648, 1.352),
    23: (3.858, 0.717, 0.487, 1.513, 0.9887, 0.163, 0.175, 0.659, 1.341),
    24: (3.895, 0.714, 0.496, 1.504, 0.9892, 0.158, 0.170, 0.669, 1.331),
    25: (3.931, 0.709, 0.504, 1.496, 0.9896, 0.153, 0.164, 0.681, 1.319),
}


def _interpolate_constants(n: float, n1: int, n2: int) -> tuple:
    """
    对缺失的 n 值进行线性插值计算常数。
    当 n 落在常数表两个相邻值之间时使用。
    """
    c1 = CONTROL_CHART_CONSTANTS[n1]
    c2 = CONTROL_CHART_CONSTANTS[n2]
    ratio = (n - n1) / (n2 - n1)
    return tuple(c1[i] + (c2[i] - c1[i]) * ratio for i in range(9))


def _estimate_constants(n: float) -> tuple:
    """
    对 n > 25 的情况使用经验公式估算常数。
    近似公式:
      d2 ≈ 1 + 2.66 * log10(n)
      c4 ≈ 1 - 1 / (2n)
      A2 ≈ 3 / (d2 * sqrt(n))
      D3 ≈ max(0, 1 - 3 * d3/d2), D4 ≈ 1 + 3 * d3/d2
    """
    d2 = 1.0 + 2.66 * np.log10(n)
    c4 = 1.0 - 1.0 / (2.0 * n)
    A2 = 3.0 / (d2 * np.sqrt(n))
    # d3/d2 近似值随 n 增大趋于 0.3
    d3_d2_approx = max(0.28, 0.3 - 0.01 * (n - 25))
    d3 = d2 * d3_d2_approx
    D3 = max(0.0, 1.0 - 3.0 * d3 / d2)
    D4 = 1.0 + 3.0 * d3 / d2
    A3 = 3.0 / (c4 * np.sqrt(n))
    B3 = max(0.0, 1.0 - 3.0 * d3 / (d2 * c4))
    B4 = 1.0 + 3.0 * d3 / (d2 * c4)
    return (d2, d3, D3, D4, c4, A2, A3, B3, B4)


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
        self.data = data  # 保留原始二维列表,支持不均匀数组(末组可能不足subgroup_size)
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
        """获取控制图常数，支持 n=1 和 n>25 的边界情况"""
        n = self.subgroup_size

        # n=1: 单值数据只能用于 I-MR 图
        if n == 1:
            # d2=1.128 是 n=2 的值；极差=0，此时 sigma 由移动极差估计
            d2, d3, D3, D4 = 1.128, 0.853, 0.0, 3.267
            c4, A2, A3, B3, B4 = 0.0, 0.0, 0.0, 0.0, 0.0
        elif n in CONTROL_CHART_CONSTANTS:
            d2, d3, D3, D4, c4, A2, A3, B3, B4 = CONTROL_CHART_CONSTANTS[n]
        elif 2 <= n <= 25:
            # 在 2~25 范围内插值
            n1 = max(2, n - 1)
            n2 = min(25, n + 1)
            # 找到两侧最近的已知点
            keys = sorted(k for k in CONTROL_CHART_CONSTANTS if n1 <= k <= n2)
            if not keys:
                n1, n2 = 2, 3
                for k in sorted(CONTROL_CHART_CONSTANTS.keys()):
                    if k <= n:
                        n1 = k
                    if k >= n and n2 is None:
                        n2 = k
                        break
            else:
                n1, n2 = min(keys), max(keys)
            d2, d3, D3, D4, c4, A2, A3, B3, B4 = _interpolate_constants(n, n1, n2)
        else:
            # n > 25: 使用经验公式估算
            d2, d3, D3, D4, c4, A2, A3, B3, B4 = _estimate_constants(n)

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
        """X̄-R 控制图(均值-极差)"""
        data = self.data
        n = self.subgroup_size

        # 计算子组均值和极差(支持不均匀数组)
        group_means = [float(np.mean(group)) for group in data]
        group_ranges = [float(np.max(group) - np.min(group)) for group in data]

        # 计算总体统计量
        x_double_bar = np.mean(group_means)  # 总均值
        r_bar = np.mean(group_ranges)  # 平均极差

        # 计算控制限
        d2 = self.constants["d2"]
        D3, D4 = self.constants["D3"], self.constants["D4"]
        A2 = self.constants["A2"]

        sigma_x = r_bar / d2

        # X̄图控制限(均值图)
        UCL_X = x_double_bar + A2 * r_bar
        LCL_X = x_double_bar - A2 * r_bar
        CL_X = x_double_bar

        # R图控制限(极差图)
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
        flat_data = np.array([x for group in data for x in group], dtype=float)
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
                "data": group_means,
                "ucl": float(UCL_X),
                "lcl": float(LCL_X),
                "cl": float(CL_X),
                "unit": "均值"
            },
            "range": {
                "labels": [f"组{i+1}" for i in range(len(group_ranges))],
                "data": group_ranges,
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
        """X̄-S 控制图(均值-标准差)"""
        data = self.data
        n = self.subgroup_size

        # 计算子组均值和标准差(支持不均匀数组)
        group_means = [float(np.mean(group)) for group in data]
        group_stds = [float(np.std(group, ddof=1)) if len(group) > 1 else 0.0 for group in data]

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
        flat_data = np.array([x for group in data for x in group], dtype=float)
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
                "data": group_means,
                "ucl": float(UCL_X),
                "lcl": float(LCL_X),
                "cl": float(CL_X),
                "unit": "均值"
            },
            "std": {
                "labels": [f"组{i+1}" for i in range(len(group_stds))],
                "data": group_stds,
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
        """I-MR 控制图(单值-移动极差)"""
        # I-MR图将所有数据展平为一维
        data = np.array([x for group in self.data for x in group], dtype=float)

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
        """p 控制图(不合格品率)"""
        data = self.data
        n = self.subgroup_size  # 子组大小

        # 每行是一个子组,第一列是不合格品数(支持不均匀数组)
        defectives = np.array([group[0] if len(group) >= 1 else 0 for group in data], dtype=float)

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
        """np 控制图(不合格品数)"""
        # 将所有数据展平为一维
        data = np.array([x for group in self.data for x in group], dtype=float)
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
        """c 控制图(缺陷数)"""
        # 将所有数据展平为一维
        data = np.array([x for group in self.data for x in group], dtype=float)

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
        """u 控制图(单位缺陷数)"""
        data = self.data
        n = self.subgroup_size

        # 每行是一个子组,第一列是缺陷数(支持不均匀数组)
        defects = np.array([group[0] if len(group) >= 1 else 0 for group in data], dtype=float)
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
        # 将所有数据展平为一维
        data = np.array([x for group in self.data for x in group], dtype=float)

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
        # 将所有数据展平为一维
        data = np.array([x for group in self.data for x in group], dtype=float)

        mean = np.mean(data)
        std = np.std(data, ddof=1)

        # 添加趋势线(线性回归)
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
        """西格玛规则检测(判异规则)"""
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
        "data_values": data,  # 原始分组数据，供前端展示
        "statistics": result.statistics,
        "control_limits": result.control_limits,
        "anomalies": result.anomalies,
        "rules_violations": result.rules_violations if show_rules else [],
        "prediction_intervals": {}  # 预测区间(后续扩展)
    }