"""评估层：走查式回测（walk-forward）。

每一期都完整跑一遍「L3 研究与质询 → L4 配置引擎 → L5 闸门」，得到目标权重；
再按当期市场变动计算资产收益，组合收益 = 权重 × 收益 − 交易成本。
同时跑一条**不调仓基准**（初始权重买入持有），用来回答最关键的那个问题：
这套调仓逻辑比「什么都不做」好多少。

收益模型是**久期一阶近似**：票息按月计提，价格变化 = −久期 × 利率变动；
信用债另外叠加利差变动，权益与另类用当期给定的期间收益。不含凸性、违约、
税费与真实成交价差，所以它只能用于比较相对表现，不代表可实现收益。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence

from ..agents import c_allocation, d_gate
from ..data_layer import adapters, quality
from ..models import Holding, MarketView
from . import metrics

COST_TO_DECIMAL = 10000.0


def instrument_returns(
    holdings: Sequence[Holding], market: MarketView, previous: MarketView
) -> Dict[str, float]:
    """按久期一阶近似估算本期各资产的收益率（小数）。"""
    rate_change = (market.curve_10y - previous.curve_10y) / 100.0
    spread_change = (market.credit_spread_pct - previous.credit_spread_pct) / 100.0
    result: Dict[str, float] = {}
    for item in holdings:
        carry = item.yield_pct / 100.0 / 12.0
        if item.asset_class == "rate_bond":
            price = -item.duration * rate_change
        elif item.asset_class == "credit_bond":
            price = -item.duration * (rate_change + spread_change)
        elif item.asset_class == "equity":
            price = market.equity_return_pct / 100.0
        elif item.asset_class == "alternative":
            price = market.alternative_return_pct / 100.0 - 0.5 * item.duration * rate_change
        else:
            price = 0.0
        result[item.name] = carry + price
    return result


def _bundle(raw: Dict[str, Any], policy) -> Dict[str, Any]:
    snapshot = adapters.snapshot_from_raw(raw)
    return {
        "raw": snapshot.raw,
        "path": "data/synthetic_history",
        "as_of": snapshot.as_of,
        "currency": snapshot.currency,
        "holdings": snapshot.holdings,
        "liability": snapshot.liability,
        "market": snapshot.market,
        "constraints": policy.constraints,
        "quality": quality.run(snapshot),
        "policy": policy,
    }


def _drift(weights: Dict[str, float], returns: Dict[str, float]) -> Dict[str, float]:
    """权重随价格漂移后重新归一（期间不调仓时的自然结果）。"""
    grown = {name: weights[name] * (1.0 + returns.get(name, 0.0)) for name in weights}
    total = sum(grown.values())
    if total <= 0:
        return dict(weights)
    return {name: value / total for name, value in grown.items()}


def walk_forward(
    history: Sequence[Dict[str, Any]],
    policy,
    include_gate: bool = True,
) -> Dict[str, Any]:
    """逐期回测；返回净值、基准净值、归因、闸门统计与指标。"""
    if len(history) < 2:
        raise ValueError("回测至少需要 2 期历史")

    baseline_weights = {item["name"]: float(item["weight"]) for item in history[0]["holdings"]}
    weights = dict(baseline_weights)
    baseline = dict(baseline_weights)

    rows: List[Dict[str, Any]] = []
    strategy_returns: List[float] = []
    baseline_returns: List[float] = []
    attribution: Dict[str, float] = {}
    gate_counts: Dict[str, int] = {}
    turnover_total = 0.0
    cost_total_bp = 0.0
    gap_values: List[float] = []
    baseline_gap_values: List[float] = []

    previous_market: Optional[MarketView] = None
    pending_cost = 0.0

    for index, period in enumerate(history):
        raw = json.loads(json.dumps(period))
        for item in raw["holdings"]:
            item["weight"] = weights.get(item["name"], float(item["weight"]))
        bundle = _bundle(raw, policy)
        proposal = c_allocation.run(bundle)
        gate = d_gate.run(bundle, proposal) if include_gate else None

        if index == 0:
            # 起点：按首期建议建仓，成本计入下一期
            pending_cost = proposal.cost_bp / COST_TO_DECIMAL
            turnover_total += proposal.turnover_pct
            cost_total_bp += proposal.cost_bp
            weights = dict(proposal.targets)
            previous_market = bundle["market"]
            if gate is not None:
                gate_counts[gate.status] = gate_counts.get(gate.status, 0) + 1
            continue

        returns = instrument_returns(bundle["holdings"], bundle["market"], previous_market)
        gross = sum(weights[name] * returns.get(name, 0.0) for name in weights)
        net = gross - pending_cost
        base_gross = sum(baseline[name] * returns.get(name, 0.0) for name in baseline)
        duration_of = {item.name: item.duration for item in bundle["holdings"]}
        baseline_duration = sum(baseline[name] * duration_of[name] for name in baseline)
        baseline_gap = baseline_duration - proposal.liability_duration

        strategy_returns.append(net)
        baseline_returns.append(base_gross)

        for item in bundle["holdings"]:
            contribution = weights[item.name] * returns.get(item.name, 0.0)
            attribution[item.asset_class] = attribution.get(item.asset_class, 0.0) + contribution

        drifted = _drift(weights, returns)
        baseline = _drift(baseline, returns)

        gap = proposal.duration_after - proposal.liability_duration
        gap_values.append(gap)
        baseline_gap_values.append(baseline_gap)
        rows.append(
            {
                "as_of": bundle["as_of"],
                "gross_return": gross,
                "net_return": net,
                "baseline_return": base_gross,
                "nav": None,
                "baseline_nav": None,
                "turnover_pct": proposal.turnover_pct,
                "cost_bp": pending_cost * COST_TO_DECIMAL,
                "duration_gap": gap,
                "baseline_duration_gap": baseline_gap,
                "liability_duration": proposal.liability_duration,
                "gate_status": gate.status if gate is not None else "未启用",
                "quality_issues": len(bundle["quality"]),
            }
        )

        pending_cost = proposal.cost_bp / COST_TO_DECIMAL
        turnover_total += proposal.turnover_pct
        cost_total_bp += proposal.cost_bp
        weights = dict(proposal.targets)
        previous_market = bundle["market"]
        if gate is not None:
            gate_counts[gate.status] = gate_counts.get(gate.status, 0) + 1

    nav = metrics.nav_from_returns(strategy_returns)
    baseline_nav = metrics.nav_from_returns(baseline_returns)
    for position, row in enumerate(rows):
        row["nav"] = nav[position + 1]
        row["baseline_nav"] = baseline_nav[position + 1]

    payload = json.dumps(history, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {
        "periods": rows,
        "nav": nav,
        "baseline_nav": baseline_nav,
        "returns": strategy_returns,
        "baseline_returns": baseline_returns,
        "metrics": metrics.summarize(strategy_returns, nav),
        "baseline_metrics": metrics.summarize(baseline_returns, baseline_nav),
        "excess_total_return": metrics.total_return(nav) - metrics.total_return(baseline_nav),
        "attribution": attribution,
        "gate_counts": gate_counts,
        "turnover_total_pct": round(turnover_total, 4),
        "cost_total_bp": round(cost_total_bp, 4),
        "duration_gap_mean": (sum(gap_values) / len(gap_values)) if gap_values else 0.0,
        "duration_gap_max_abs": max((abs(value) for value in gap_values), default=0.0),
        "baseline_duration_gap_mean": (
            sum(baseline_gap_values) / len(baseline_gap_values) if baseline_gap_values else 0.0
        ),
        "baseline_duration_gap_max_abs": max(
            (abs(value) for value in baseline_gap_values), default=0.0
        ),
        "window": {
            "start": history[0]["as_of"],
            "end": history[-1]["as_of"],
            "periods": len(history),
            "return_periods": len(strategy_returns),
        },
        "history_fingerprint": hashlib.sha256(payload).hexdigest()[:12],
    }
