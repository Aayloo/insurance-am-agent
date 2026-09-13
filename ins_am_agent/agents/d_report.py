"""D 层输出：报告生成（D3）与留痕、评估（D5）。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

CLASS_LABELS = {
    "rate_bond": "利率债",
    "credit_bond": "信用债",
    "equity": "权益",
    "alternative": "另类",
    "cash": "现金类",
}


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


def render(bundle: Dict[str, Any], research: Dict[str, Any], proposal, gate, version: str) -> str:
    holdings = bundle["holdings"]
    constraints = bundle["constraints"]
    market = bundle["market"]
    liability = bundle["liability"]
    lines = []

    lines.append("# 保险资管配置建议书（示例输出）")
    lines.append("")
    lines.append("> 本文件由 `insurance-am-agent` 自动生成，用于演示 A→B→C→D 流水线。")
    lines.append("> 所有数值为合成样例数据与示意限额，不构成监管口径或投资建议。")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 数据时点 | {} |".format(bundle["as_of"]))
    lines.append("| 负债久期 / 成本 | {:.1f} 年 / {:.2f}% |".format(liability.duration, liability.cost_pct))
    lines.append("| 10 年利率 / 期限利差 | {:.2f}% / {:+.2f}% |".format(market.curve_10y, market.curve_slope))
    lines.append("| 版本 / 输入指纹 | {} / {} |".format(version, input_fingerprint(bundle)))
    lines.append("")

    lines.append("## 一、A 层：数据质量与约束清单")
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

    lines.append("## 二、B 层：投研团队观点")
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
    lines.append("### B5 交叉质询（{} 轮后收敛）".format(challenge["rounds"]))
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

    lines.append("## 三、C 层：配置建议与压力测试")
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

    lines.append("## 四、D 层：闸门结论与签批")
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
    lines.append("1. 投资经理：确认调整理由与执行节奏。")
    lines.append("2. 风控与合规：确认例外事项与后续压回计划。")
    lines.append("3. 投委会：就超出容忍度的久期缺口作出决议。")
    lines.append("")
    lines.append("> 下单与交收由人工完成，Agent 不接触交易接口。")
    lines.append("")

    lines.append("## 五、留痕")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("| --- | --- |")
    lines.append("| 生成时间（UTC） | {} |".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
    lines.append("| 引擎版本 | {} |".format(version))
    lines.append("| 输入指纹 | {} |".format(input_fingerprint(bundle)))
    lines.append("| 数据文件 | `{}` |".format(display_path(bundle["path"])))
    lines.append("")
    return "\n".join(lines)


def audit_record(bundle: Dict[str, Any], research: Dict[str, Any], proposal, gate, version: str) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": version,
        "input_fingerprint": input_fingerprint(bundle),
        "data_path": display_path(bundle["path"]),
        "as_of": bundle["as_of"],
        "steps": ["A", "B", "C", "D"],
        "opinions": [opinion.agent_id for opinion in research["opinions"]],
        "disagreements": len(research["challenge"]["disagreements"]),
        "duration_gap_after": round(proposal.duration_after - proposal.liability_duration, 4),
        "turnover_pct": proposal.turnover_pct,
        "gate_status": gate.status,
        "gate_items": [
            {"rule": item.rule, "actual": item.actual, "status": item.status} for item in gate.items
        ],
    }
