"""L1 数据与状态：确定性合成历史。

回测需要多期数据，而真实持仓、精算与行情数据不能进公开仓库。所以这里用固定
种子的伪随机序列生成一段可复现的月度历史：同样的种子必然得到同样的历史，
测试和报告可以逐字复算。接入真实数据时替换本模块即可（见 SnapshotAdapter）。

生成的是「市场 + 负债 + 一篮子持仓权重」，资产的期间收益由回测引擎按
久期一阶近似计算（见 evaluation/backtest.py），本模块只负责市场状态的演化。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PERIODS = 24
DEFAULT_SEED = 20260831
DEFAULT_START = (2024, 9)

BASE_PORTFOLIO = Path(__file__).resolve().parents[2] / "data" / "sample_portfolio.json"

# 月度波动（百分数）：利率 18bp、利差 9bp、曲线斜率 8bp、权益 5.5%、另类 1.2%
# 口径参照常见机构对利率与权益月度波动的量级假设，保持在「像真实市场」的范围，
# 避免生成一条过于平滑、导致夏普虚高的历史。
RATE_VOL = 0.18
SLOPE_VOL = 0.08
SPREAD_VOL = 0.09
EQUITY_VOL = 5.5
ALTERNATIVE_VOL = 1.2


class _Deterministic:
    """极小的线性同余发生器：零依赖，且同一 seed 必然复现。"""

    def __init__(self, seed: int) -> None:
        self.state = seed % (2 ** 31)

    def unit(self) -> float:
        self.state = (1103515245 * self.state + 12345) % (2 ** 31)
        return self.state / float(2 ** 31)

    def symmetric(self) -> float:
        """近似正态的扰动：均值 0、标准差约 1，取值落在 [-3, 3]。

        三个均匀分布之和的均值是 1.5、标准差是 0.5，所以减去均值再除以 0.5
        即可归一。这样 ``vol`` 参数就真的是「一个标准差」，不会悄悄缩水三分之二。
        """
        return ((self.unit() + self.unit() + self.unit()) - 1.5) / 0.5

    def shift(self, value: float, vol: float, low: float, high: float) -> float:
        return min(high, max(low, value + vol * self.symmetric()))


def _month_label(year: int, month: int) -> str:
    last_day = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    return "{:04d}-{:02d}-{:02d}".format(year, month, last_day[month])


def _advance(year: int, month: int, step: int) -> tuple:
    index = year * 12 + (month - 1) + step
    return index // 12, index % 12 + 1


def _base_document(path: Optional[Path] = None) -> Dict[str, Any]:
    with open(str(path or BASE_PORTFOLIO), "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_history(
    periods: int = DEFAULT_PERIODS,
    seed: int = DEFAULT_SEED,
    start: tuple = DEFAULT_START,
    base_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """生成 ``periods`` 期月度快照；第一期就是样例组合的原始状态。"""
    if periods < 2:
        raise ValueError("回测至少需要 2 期历史")

    base = _base_document(base_path)
    rng = _Deterministic(seed)

    curve = float(base["market"]["curve_10y"])
    slope = float(base["market"]["curve_slope"])
    spread = float(base["market"]["credit_spread_pct"])
    equity_yield = float(base["market"]["equity_dividend_yield"])
    liability_duration = float(base["liability"]["duration"])
    liability_cost = float(base["liability"]["cost_pct"])
    weights = {item["name"]: float(item["weight"]) for item in base["holdings"]}

    year, month = start
    year, month = _advance(year, month, -periods)

    history: List[Dict[str, Any]] = []
    for _ in range(periods):
        year, month = _advance(year, month, 1)
        curve = rng.shift(curve, RATE_VOL, 1.5, 5.0)
        slope = rng.shift(slope, SLOPE_VOL, -0.9, 0.9)
        spread = rng.shift(spread, SPREAD_VOL, 0.5, 3.0)
        equity_yield = rng.shift(equity_yield, 0.12, 3.0, 7.5)
        liability_duration = rng.shift(liability_duration, 0.05, 7.5, 10.5)
        liability_cost = rng.shift(liability_cost, 0.02, 2.4, 4.2)

        holdings = []
        for item in base["holdings"]:
            entry = dict(item)
            entry["weight"] = round(weights[item["name"]], 8)
            drift = curve - float(base["market"]["curve_10y"])
            if item["asset_class"] == "credit_bond":
                drift += spread - float(base["market"]["credit_spread_pct"])
            entry["yield_pct"] = round(float(item["yield_pct"]) + drift, 4)
            entry["valuation_date"] = _month_label(year, month)
            holdings.append(entry)

        percentile = int(min(97, max(3, (spread - 0.5) / 2.5 * 100)))
        history.append(
            {
                "as_of": _month_label(year, month),
                "currency": base.get("currency", "CNY"),
                "note": "合成历史数据（固定种子可复现），仅用于回测演示，不含任何机构内部数据。",
                "liability": {
                    "duration": round(liability_duration, 4),
                    "cost_pct": round(liability_cost, 4),
                    "annual_cashflow_pct": float(base["liability"]["annual_cashflow_pct"]),
                },
                "market": {
                    "curve_10y": round(curve, 4),
                    "curve_slope": round(slope, 4),
                    "credit_spread_pct": round(spread, 4),
                    "spread_percentile": percentile,
                    "equity_dividend_yield": round(equity_yield, 4),
                    "rate_shock_bp": int(base["market"]["rate_shock_bp"]),
                    "equity_return_pct": round(0.6 + EQUITY_VOL * rng.symmetric(), 4),
                    "alternative_return_pct": round(0.4 + ALTERNATIVE_VOL * rng.symmetric(), 4),
                },
                "holdings": holdings,
            }
        )
    return history
