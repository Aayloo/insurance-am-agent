"""L5 治理与交付：报告生成（D3）与留痕、评估（D5）。

治理口径（谁签批、谁下单、谁负责）来自政策文件，不在代码里硬编码；
留痕同时记录输入指纹、政策指纹与组合状态指纹，保证结论可复现。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

CLASS_LABELS = {
    "rate_bond": "利率债",
    "credit_bond": "信用债",
    "equity": "权益",
    "alternative": "另类",
    "cash": "现金类",
}

# 政策文件缺失时的兜底治理口径；正常情况下以 policy.governance 为准
DEFAULT_GOVERNANCE = {
    "decision_owner": "投资经理与投委会承担决策责任，Agent 只出建议",
    "sign_off": "投资经理、风控合规、投委会",
    "order_execution": "人工执行，Agent 不接触交易接口",
}

SIGN_OFF_ACTIONS = {
    "投资经理": "确认调整理由与执行节奏",
    "风控合规": "确认例外事项与后续压回计划",
    "投委会": "就超出容忍度的久期缺口作出决议",
}

LAYER_STEPS = ["L1 数据与状态", "L2 约束与政策", "L3 投研", "L4 配置引擎", "L5 治理与交付"]


def input_fingerprint(bundle: Dict[str, Any]) -> str:
    payload = json.dumps(bundle["raw"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def display_path(path: str) -> str:
    """报告中只展示仓库内相对路径，避免泄露本地绝对路径。"""
    candidate = Path(path)
    try:
        root = Path(__file__).resolve().parents[2]
        return candidate.resolve().relative_to(root).as_posix()
    except Exception:
        return candidate.name


def _policy(bundle: Dict[str, Any]):
    return bundle.get("policy")


def _governance(bundle: Dict[str, Any], key: str) -> str:
    policy = _policy(bundle)
    if policy is not None:
        value = policy.governance_of(key, "")
        if value:
            return value
    return DEFAULT_GOVERNANCE.get(key, "")


def _sign_off_lines(bundle: Dict[str, Any]) -> List[str]:
    roles = [role.strip() for role in _governance(bundle, "sign_off").split("、") if role.strip()]
    if not roles:
        return []
    return [
        "{}. {}：{}。".format(index, role, SIGN_OFF_ACTIONS.get(role, "确认本期结论与后续动作"))
        for index, role in enumerate(roles, 1)
    ]


def render(bundle: Dict[str, Any], research: Dict[str, Any], proposal, gate, version: str) -> str:
    holdings = bundle["holdings"]
    constraints = bundle["constraints"]
    market = bundle["market"]
    liability = bundle["liability"]
    policy = _policy(bundle)
    state = bundle.get("state_after")
    lines = []

    lines.append("# 保险资管配置建议书（示例输出）")
    lines.append("")
    lines.append("> 本文件由 `insurance-am-agent` 自动生成，用于演示 L0→L5 流水线。")
    lines.append("> 所有数值为合成样例数据与示意限额，不构成监管口径或投资建议。")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 数据时点 | {} |".format(bundle["as_of"]))
    lines.append("| 负债久期 / 成本 | {:.1f} 年 / {:.2f}% |".format(liability.duration, liability.cost_pct))
    lines.append("| 10 年利率 / 期限利差 | {:.2f}% / {:+.2f}% |".format(market.curve_10y, market.curve_slope))
    lines.append("| 版本 / 输入指纹 | {} / {} |".format(version, input_fingerprint(bundle)))
    if policy is not None:
        lines.append(
            "| 政策版本 / 生效日 | {} / {} |".format(policy.fingerprint, policy.effective_date)
        )
    lines.append("")

    lines.append("## 一、数据与约束（L1 数据与状态 · L2 约束与政策）")
    lines.append("")
    if bundle["quality"]:
        lines.append("| 级别 | 项目 | 说明 |")
        lines.append("| --- | --- | --- |")
        for issue in bundle["quality"]:
            lines.append("| {} | {} | {} |".format(issue["level"], issue["item"], issue["detail"]))
    else:
        lines.append("数据校验通过，无异常项。")
    lines.append("")
    lines.append("| 约束 | 取值 |")
    lines.append("| --- | --- |")
    lines.append("| 权益上限 | {:.1f}% |".format(constraints.equity_cap_pct))
    lines.append("| 另类上限 | {:.1f}% |".format(constraints.alternative_cap_pct))
    lines.append("| 单一主体上限 | {:.1f}% |".format(constraints.single_issuer_cap_pct))
    lines.append("| 流动性下限 | {:.1f}% |".format(constraints.min_liquidity_pct))
    lines.append("| 久期缺口容忍度 | ±{:.1f} 年 |".format(constraints.duration_tolerance_years))
    lines.append("| 单期换手上限 | {:.1f}% |".format(constraints.max_turnover_pct))
    lines.append("")

    lines.append("## 二、投研团队观点（L3 投研）")
    lines.append("")
    lines.append("| Agent | 议题 | 结论 | 方向 | 证据 | 置信度 | 失效条件 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for opinion in research["opinions"]:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                opinion.agent_id,
                opinion.topic,
                opinion.stance,
                opinion.direction,
                opinion.evidence,
                opinion.confidence,
                opinion.invalid_if,
            )
        )
    lines.append("")
    challenge = research["challenge"]
    lines.append("### 交叉质询（{} 轮后收敛）".format(challenge["rounds"]))
    lines.append("")
    if challenge["disagreements"]:
        lines.append("| 分歧点 | 一方 | 另一方 | 影响 |")
        lines.append("| --- | --- | --- | --- |")
        for row in challenge["disagreements"]:
            lines.append(
                "| {} | {} | {} | {} |".format(row["issue"], row["side_a"], row["side_b"], row["impact"])
            )
    else:
        lines.append("本轮无明显方向性分歧。")
    lines.append("")

    lines.append("## 三、配置建议与压力测试（L4 配置引擎）")
    lines.append("")
    lines.append(
        "久期：调整前 {:.2f} 年 → 调整后 {:.2f} 年（负债久期 {:.1f} 年）；"
        "换手 {:.2f}%，估算成本 {:.2f}bp。".format(
            proposal.duration_before,
            proposal.duration_after,
            proposal.liability_duration,
            proposal.turnover_pct,
            proposal.cost_bp,
        )
    )
    lines.append("")
    lines.append(
        "收益率：调整前 {:.2f}% → 调整后 {:.2f}%，相对负债成本 {:.2f}% 的利差 {:+.2f}%。".format(
            proposal.yield_before,
            proposal.yield_after,
            proposal.liability_cost_pct,
            proposal.yield_after - proposal.liability_cost_pct,
        )
    )
    lines.append("")
    lines.append("| 资产 | 类别 | 当前权重 | 目标权重 | 调整 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in holdings:
        current = proposal.current[item.name] * 100
        target = proposal.targets[item.name] * 100
        delta = target - current
        if abs(delta) < 0.005:
            continue
        lines.append(
            "| {} | {} | {:.2f}% | {:.2f}% | {:+.2f}pp |".format(
                item.name,
                CLASS_LABELS.get(item.asset_class, item.asset_class),
                current,
                target,
                delta,
            )
        )
    lines.append("")
    lines.append("**调整理由**")
    lines.append("")
    for reason in proposal.reasons:
        lines.append("- {}".format(reason))
    lines.append("")
    lines.append("**压力测试**")
    lines.append("")
    lines.append("| 情景 | 组合影响 | 说明 |")
    lines.append("| --- | --- | --- |")
    for row in proposal.stress_tests:
        lines.append(
            "| {} | {:+.2f}% | {} |".format(row["scenario"], row["impact_pct"], row["note"])
        )
    lines.append("")

    lines.append("## 四、闸门结论与签批（L5 治理与交付）")
    lines.append("")
    lines.append("**闸门结论：{}** —— {}".format(gate.status, gate.summary))
    lines.append("")
    lines.append("| 校验项 | 限额 | 实际 | 结论 | 责任 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in gate.items:
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                item.rule, item.limit, item.actual, item.status, item.owner
            )
        )
    lines.append("")
    lines.append("**待人工签批事项**")
    lines.append("")
    for line in _sign_off_lines(bundle):
        lines.append(line)
    lines.append("")
    lines.append("> {}".format(_governance(bundle, "order_execution")))
    lines.append("")

    lines.append("## 五、留痕")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 生成时间（UTC） | {} |".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
    lines.append("| 引擎版本 | {} |".format(version))
    lines.append("| 输入指纹 | {} |".format(input_fingerprint(bundle)))
    lines.append("| 数据文件 | `{}` |".format(display_path(bundle["path"])))
    if policy is not None:
        lines.append(
            "| 政策文件 / 指纹 / 生效日 | `{}` / {} / {} |".format(
                display_path(policy.path), policy.fingerprint, policy.effective_date
            )
        )
    if state is not None:
        lines.append(
            "| 组合状态指纹 / 调仓笔数 | {} / {} |".format(
                state.fingerprint(), len(state.latest_trades())
            )
        )
    lines.append("")
    return "\n".join(lines)


def audit_record(
    bundle: Dict[str, Any], research: Dict[str, Any], proposal, gate, version: str
) -> Dict[str, Any]:
    policy = _policy(bundle)
    state = bundle.get("state_after")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": version,
        "input_fingerprint": input_fingerprint(bundle),
        "data_path": display_path(bundle["path"]),
        "as_of": bundle["as_of"],
        "steps": list(LAYER_STEPS),
        "policy": {
            "path": display_path(policy.path) if policy is not None else "",
            "fingerprint": policy.fingerprint if policy is not None else "",
            "effective_date": policy.effective_date if policy is not None else "",
        },
        "analysts": list(research.get("analysts") or [item.agent_id for item in research["opinions"]]),
        "opinions": [opinion.agent_id for opinion in research["opinions"]],
        "disagreements": len(research["challenge"]["disagreements"]),
        "duration_gap_after": round(proposal.duration_after - proposal.liability_duration, 4),
        "turnover_pct": proposal.turnover_pct,
        "state_fingerprint": state.fingerprint() if state is not None else "",
        "trade_count": len(state.latest_trades()) if state is not None else 0,
        "gate_status": gate.status,
        "gate_items": [
            {"rule": item.rule, "actual": item.actual, "status": item.status} for item in gate.items
        ],
    }
