"""D 层闸门：风控与合规校验（D1）与例外处理（D2）。

闸门只做"通过 / 提示 / 降规模 / 升级审批 / 否决"的判断，
不做投资决策；最终决议仍由人签批。
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..models import GateItem, GateResult

STATUS_ORDER = ("通过", "提示", "降规模", "升级审批", "否决")


def _worst(statuses: List[str]) -> str:
    worst = "通过"
    for status in statuses:
        if STATUS_ORDER.index(status) > STATUS_ORDER.index(worst):
            worst = status
    return worst


def run(bundle: Dict[str, Any], proposal) -> GateResult:
    holdings = bundle["holdings"]
    constraints = bundle["constraints"]
    items: List[GateItem] = []

    targets = proposal.targets
    current = proposal.current

    def class_total(asset_class: str, weights: Dict[str, float]) -> float:
        return sum(
            weights.get(item.name, item.weight)
            for item in holdings
            if item.asset_class == asset_class
        )

    # 1) 权益上限
    equity = class_total("equity", targets) * 100
    if equity > constraints.equity_cap_pct + 1e-6:
        equity_status = "降规模"
    elif abs(equity - constraints.equity_cap_pct) < 1e-6:
        equity_status = "提示"
    else:
        equity_status = "通过"
    items.append(
        GateItem(
            rule="权益类资产上限",
            limit="{:.1f}%".format(constraints.equity_cap_pct),
            actual="{:.1f}%".format(equity),
            status=equity_status,
            owner="合规 Agent 初筛 · 风控复核",
        )
    )

    # 2) 另类资产上限
    alternative = class_total("alternative", targets) * 100
    items.append(
        GateItem(
            rule="另类资产上限",
            limit="{:.1f}%".format(constraints.alternative_cap_pct),
            actual="{:.1f}%".format(alternative),
            status="通过" if alternative <= constraints.alternative_cap_pct + 1e-6 else "降规模",
            owner="合规 Agent 初筛",
        )
    )

    # 3) 单一主体集中度（只统计 issuer_type 为 single_name 的持仓，同时看存量与目标）
    single_name_holdings = [item for item in holdings if item.issuer_type == "single_name"]
    current_best = max(single_name_holdings, key=lambda item: current.get(item.name, 0.0), default=None)
    target_best = max(single_name_holdings, key=lambda item: targets.get(item.name, 0.0), default=None)
    current_peak = 0.0 if current_best is None else current.get(current_best.name, 0.0) * 100
    target_peak = 0.0 if target_best is None else targets.get(target_best.name, 0.0) * 100
    cap_single = constraints.single_issuer_cap_pct
    if target_best is None:
        single_status = "通过"
        note = "无单一主体敞口"
    elif current_peak > cap_single + 1e-6 and target_peak <= cap_single + 1e-6:
        single_status = "降规模"
        note = "{}({}%) 存量超限，本期目标已压回".format(current_best.name, round(current_peak, 1))
    elif target_peak > cap_single + 1e-6:
        single_status = "否决"
        note = "{}({}%) 仍超限".format(target_best.name, round(target_peak, 1))
    else:
        single_status = "通过"
        note = "最大单一主体 {}%".format(round(target_peak, 1))
    items.append(
        GateItem(
            rule="单一主体集中度",
            limit="{:.1f}%".format(cap_single),
            actual=note,
            status=single_status,
            owner="风控 Agent 初筛",
        )
    )

    # 4) 流动性下限
    liquidity = class_total("cash", targets) * 100
    if liquidity < constraints.min_liquidity_pct - 1e-6:
        liquidity_status = "否决"
    elif liquidity < constraints.min_liquidity_pct + 1.0:
        liquidity_status = "提示"
    else:
        liquidity_status = "通过"
    items.append(
        GateItem(
            rule="流动性下限",
            limit="{:.1f}%".format(constraints.min_liquidity_pct),
            actual="{:.1f}%".format(liquidity),
            status=liquidity_status,
            owner="风控 Agent 初筛",
        )
    )

    # 5) 久期缺口
    gap = proposal.duration_after - proposal.liability_duration
    tolerance = constraints.duration_tolerance_years
    if abs(gap) <= tolerance:
        gap_status = "通过"
    else:
        gap_status = "升级审批"
    items.append(
        GateItem(
            rule="久期缺口容忍度",
            limit="±{:.1f} 年".format(tolerance),
            actual="{:+.2f} 年".format(gap),
            status=gap_status,
            owner="ALM Agent 测算 · 投委会审批",
        )
    )

    # 6) 换手上限
    items.append(
        GateItem(
            rule="单期换手上限",
            limit="{:.1f}%".format(constraints.max_turnover_pct),
            actual="{:.2f}%".format(proposal.turnover_pct),
            status="通过" if proposal.turnover_pct <= constraints.max_turnover_pct else "升级审批",
            owner="投资经理复核",
        )
    )

    # 7) 收益覆盖负债成本（保险特有：投资收益需覆盖刚性负债成本）
    spread = proposal.yield_after - proposal.liability_cost_pct
    items.append(
        GateItem(
            rule="收益与负债成本利差",
            limit="≥ 0（负债成本 {:.2f}%）".format(proposal.liability_cost_pct),
            actual="{:+.2f}%".format(spread),
            status="通过" if spread >= 0 else "提示",
            owner="投资经理与精算复核",
        )
    )

    status = _worst([item.status for item in items])
    summary_map = {
        "通过": "全部校验通过，可提交签批",
        "提示": "校验通过，但存在需关注事项",
        "降规模": "存在超限项，需先压回或降低规模",
        "升级审批": "存在超出授权范围的事项，需上会审批",
        "否决": "存在硬约束冲突，本期方案不可执行",
    }
    return GateResult(status=status, summary=summary_map[status], items=items)
