"""C 层：配置决策。

C1 久期缺口、C2 情景与压力测试、C3 组合优化、C4 成本与偏离理由。
所有数值均由确定性算法给出，单期调仓受换手额度约束。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..models import Holding, Proposal

PER_TRADE_LIMIT = 0.05
TURNOVER_USAGE = 0.7
TRANSACTION_COST_BP = 8.0
EQUITY_SHOCK_PCT = 20.0
SPREAD_SHOCK_BP = 50


def weighted_duration(holdings: List[Holding], weights: Dict[str, float]) -> float:
    return sum(weights.get(item.name, item.weight) * item.duration for item in holdings)


def weighted_yield(holdings: List[Holding], weights: Dict[str, float]) -> float:
    return sum(weights.get(item.name, item.weight) * item.yield_pct for item in holdings)


def _rate_bond_duration(holdings: List[Holding]) -> float:
    names = [item for item in holdings if item.asset_class == "rate_bond"]
    if not names:
        return 0.0
    total = sum(item.weight for item in names)
    if total <= 0:
        return 0.0
    return sum(item.weight * item.duration for item in names) / total


def _rebalance(
    holdings: List[Holding], liability_duration: float, constraints, market
) -> Tuple[Dict[str, float], List[str], float]:
    targets: Dict[str, float] = {item.name: item.weight for item in holdings}
    reasons: List[str] = []

    rate_names = [item.name for item in holdings if item.asset_class == "rate_bond"]
    cash_names = [item.name for item in holdings if item.asset_class == "cash"]
    credit_names = [item.name for item in holdings if item.asset_class == "credit_bond"]
    bucket = rate_names or [holdings[0].name]

    def to_bucket(amount: float) -> None:
        if amount <= 0:
            return
        share = amount / len(bucket)
        for name in bucket:
            targets[name] += share

    # 1) 权益与另类超限部分压回，转入利率债
    for asset_class, cap_pct in (
        ("equity", constraints.equity_cap_pct),
        ("alternative", constraints.alternative_cap_pct),
    ):
        total = sum(targets[item.name] for item in holdings if item.asset_class == asset_class)
        cap = cap_pct / 100
        if total <= cap + 1e-9:
            continue
        excess = total - cap
        for item in holdings:
            if item.asset_class != asset_class:
                continue
            cut = targets[item.name] * (excess / total)
            targets[item.name] -= cut
        to_bucket(excess)
        reasons.append(
            "{} 超内部上限 {:.1f}%，按比例压回并转入利率债 {:.1f}%".format(
                asset_class, cap_pct, excess * 100
            )
        )

    # 2) 单一主体超限压回（仅限 issuer_type 为 single_name 的持仓）
    cap_single = constraints.single_issuer_cap_pct / 100
    for item in holdings:
        if item.issuer_type != "single_name":
            continue
        if targets[item.name] > cap_single + 1e-9:
            cut = targets[item.name] - cap_single
            targets[item.name] -= cut
            to_bucket(cut)
            reasons.append(
                "{} 作为单一主体敞口 {:.1f}% 超过上限 {:.1f}%，压回至上限后转入利率债".format(
                    item.name, (targets[item.name] + cut) * 100, constraints.single_issuer_cap_pct
                )
            )

    # 3) 流动性下限
    floor = constraints.min_liquidity_pct / 100
    cash_total = sum(targets[name] for name in cash_names)
    if cash_names and cash_total < floor - 1e-9:
        need = floor - cash_total
        for name in rate_names:
            take = min(need, targets[name])
            targets[name] -= take
            targets[cash_names[0]] += take
            need -= take
            if need <= 1e-9:
                break
        reasons.append("现金类低于流动性下限，从利率债补回至 {:.1f}%".format(floor * 100))

    # 4) 拉长久期：优先动用超过下限的现金，其次调整信用债
    budget = constraints.max_turnover_pct / 100 * TURNOVER_USAGE
    used = 0.0
    gap = weighted_duration(holdings, targets) - liability_duration
    target_duration_level = _rate_bond_duration(holdings) or 8.5
    cash_total = sum(targets[name] for name in cash_names)
    movable_cash = max(0.0, cash_total - floor)

    for name in cash_names + credit_names:
        if used >= budget - 1e-9:
            break
        if gap >= -constraints.duration_tolerance_years:
            break
        item = next(node for node in holdings if node.name == name)
        gain = target_duration_level - item.duration
        if gain <= 0:
            continue
        room = min(PER_TRADE_LIMIT, budget - used, targets[name])
        if item.asset_class == "cash":
            room = min(room, movable_cash)
        if room <= 1e-9:
            continue
        needed = (-gap - constraints.duration_tolerance_years) / gain
        amount = min(room, needed)
        targets[name] -= amount
        to_bucket(amount)
        used += amount
        if item.asset_class == "cash":
            movable_cash -= amount
        gap = weighted_duration(holdings, targets) - liability_duration
        reasons.append(
            "从 {} 调出 {:.1f}% 转入利率债，用于收敛久期缺口".format(name, amount * 100)
        )

    return targets, reasons, used


def _stress_tests(holdings: List[Holding], targets: Dict[str, float], market) -> List[Dict[str, object]]:
    rate_shock = market.rate_shock_bp / 10000.0
    rate_impact = -sum(
        targets.get(item.name, item.weight) * item.duration * rate_shock for item in holdings
    )

    spread_shock = SPREAD_SHOCK_BP / 10000.0
    credit_impact = -sum(
        targets.get(item.name, item.weight) * item.duration * spread_shock
        for item in holdings
        if item.asset_class == "credit_bond"
    )

    equity_shock = EQUITY_SHOCK_PCT / 100.0
    equity_impact = -sum(
        targets.get(item.name, item.weight) * equity_shock
        for item in holdings
        if item.asset_class == "equity"
    )

    return [
        {
            "scenario": "利率上行 {}bp".format(market.rate_shock_bp),
            "impact_pct": round(rate_impact * 100, 2),
            "note": "按修正久期近似估算，未计凸性",
        },
        {
            "scenario": "信用利差走阔 {}bp".format(SPREAD_SHOCK_BP),
            "impact_pct": round(credit_impact * 100, 2),
            "note": "仅作用于信用债敞口",
        },
        {
            "scenario": "权益回撤 {:.0f}%".format(EQUITY_SHOCK_PCT),
            "impact_pct": round(equity_impact * 100, 2),
            "note": "仅作用于权益敞口",
        },
    ]


def run(bundle: Dict[str, Any]) -> Proposal:
    holdings: List[Holding] = bundle["holdings"]
    liability = bundle["liability"]
    constraints = bundle["constraints"]
    market = bundle["market"]

    current = {item.name: item.weight for item in holdings}
    targets, reasons, _used = _rebalance(holdings, liability.duration, constraints, market)

    turnover = 0.5 * sum(abs(targets[item.name] - current[item.name]) for item in holdings)
    duration_before = weighted_duration(holdings, current)
    duration_after = weighted_duration(holdings, targets)

    return Proposal(
        targets=targets,
        current=current,
        duration_before=duration_before,
        duration_after=duration_after,
        liability_duration=liability.duration,
        turnover_pct=round(turnover * 100, 2),
        cost_bp=round(turnover * TRANSACTION_COST_BP, 2),
        yield_before=weighted_yield(holdings, current),
        yield_after=weighted_yield(holdings, targets),
        liability_cost_pct=liability.cost_pct,
        reasons=reasons,
        stress_tests=_stress_tests(holdings, targets, market),
    )
