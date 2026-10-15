"""评估层：收益与风险指标（零依赖）。

只做最基础、口径明确的几项：累计收益、年化收益、年化波动、最大回撤、夏普。
不引入第三方统计库，保证任何环境都能逐字复算。
"""

from __future__ import annotations

from math import sqrt
from typing import Dict, List, Sequence

PERIODS_PER_YEAR = 12


def stdev(values: Sequence[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    # 全常数序列直接返回 0：不同 Python 版本对 sum/count 的舍入不同，
    # 常数序列算出来的均值可能不是精确值，会让方差变成极小正数，
    # 进而在夏普里被放大成天文数字（3.9 与 3.13 的表现就不一致）。
    if all(value == values[0] for value in values):
        return 0.0
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    if variance <= 0:
        return 0.0
    return sqrt(variance)


def nav_from_returns(returns: Sequence[float], start: float = 1.0) -> List[float]:
    nav = [start]
    for value in returns:
        nav.append(nav[-1] * (1.0 + value))
    return nav


def total_return(nav: Sequence[float]) -> float:
    if len(nav) < 2 or nav[0] == 0:
        return 0.0
    return nav[-1] / nav[0] - 1.0


def annualized_return(nav: Sequence[float], periods_per_year: int = PERIODS_PER_YEAR) -> float:
    periods = len(nav) - 1
    if periods <= 0:
        return 0.0
    growth = nav[-1] / nav[0]
    if growth <= 0:
        return -1.0
    return growth ** (float(periods_per_year) / periods) - 1.0


def annualized_vol(returns: Sequence[float], periods_per_year: int = PERIODS_PER_YEAR) -> float:
    return stdev(returns) * sqrt(periods_per_year)


def max_drawdown(nav: Sequence[float]) -> float:
    peak = nav[0] if nav else 0.0
    worst = 0.0
    for value in nav:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst


def sharpe(
    returns: Sequence[float],
    periods_per_year: int = PERIODS_PER_YEAR,
    risk_free: float = 0.0,
) -> float:
    if not returns:
        return 0.0
    excess = [value - risk_free / periods_per_year for value in returns]
    deviation = stdev(excess)
    if deviation == 0:
        return 0.0
    return (sum(excess) / len(excess)) / deviation * sqrt(periods_per_year)


def summarize(returns: Sequence[float], nav: Sequence[float]) -> Dict[str, float]:
    """把一条收益序列压成几个可直接写进报告的指标。"""
    return {
        "periods": float(len(returns)),
        "total_return": total_return(nav),
        "annualized_return": annualized_return(nav),
        "annualized_vol": annualized_vol(returns),
        "max_drawdown": max_drawdown(nav),
        "sharpe": sharpe(returns),
        "win_rate": (sum(1 for value in returns if value > 0) / len(returns)) if returns else 0.0,
    }
