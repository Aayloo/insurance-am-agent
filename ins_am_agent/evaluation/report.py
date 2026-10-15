"""评估层：回测报告与审计记录。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

ASSET_LABELS = {
    "rate_bond": "利率债",
    "credit_bond": "信用债",
    "equity": "权益",
    "alternative": "另类",
    "cash": "现金类",
}


def _percent(value: float, digits: int = 2) -> str:
    return "{:+.{digits}f}%".format(value * 100, digits=digits)


def render_markdown(result: Dict[str, Any], policy, version: str) -> str:
    metrics = result["metrics"]
    baseline = result["baseline_metrics"]
    window = result["window"]
    lines = [
        "# 走查式回测报告（合成数据）",
        "",
        "> 每期完整跑一遍「研究 → 配置 → 闸门」，收益按久期一阶近似估算。",
        "> 数据为固定种子的合成序列，可逐字复算；不构成投资建议，也不代表可实现收益。",
        "",
        "| 项目 | 内容 |",
        "| --- | --- |",
        "| 回测区间 | {} → {}（{} 期，{} 个收益期）|".format(
            window["start"], window["end"], window["periods"], window["return_periods"]
        ),
        "| 引擎版本 | {} |".format(version),
        "| 历史指纹 | {} |".format(result["history_fingerprint"]),
        "| 政策版本 / 生效日 | {} / {} |".format(policy.fingerprint, policy.effective_date),
        "",
        "## 一、策略 vs 不调仓基准",
        "",
        "| 指标 | 调仓策略 | 不调仓基准 |",
        "| --- | --- | --- |",
        "| 累计收益 | {} | {} |".format(
            _percent(metrics["total_return"]), _percent(baseline["total_return"])
        ),
        "| 年化收益 | {} | {} |".format(
            _percent(metrics["annualized_return"]), _percent(baseline["annualized_return"])
        ),
        "| 年化波动 | {:.2f}% | {:.2f}% |".format(
            metrics["annualized_vol"] * 100, baseline["annualized_vol"] * 100
        ),
        "| 最大回撤 | {:.2f}% | {:.2f}% |".format(
            metrics["max_drawdown"] * 100, baseline["max_drawdown"] * 100
        ),
        "| 夏普（无风险 0）| {:.2f} | {:.2f} |".format(metrics["sharpe"], baseline["sharpe"]),
        "| 胜率 | {:.1f}% | {:.1f}% |".format(
            metrics["win_rate"] * 100, baseline["win_rate"] * 100
        ),
        "",
        "**超额累计收益（策略 − 基准）：{}**".format(_percent(result["excess_total_return"])),
        "",
        "> 读法：只在「扣掉成本后仍然更好」时，这套调仓逻辑才算证明了价值；否则它只是一套更贵的执行方式。",
        "",
        "## 二、成本与换手",
        "",
        "| 项目 | 数值 |",
        "| --- | --- |",
        "| 累计单边换手 | {:.1f}% |".format(result["turnover_total_pct"]),
        "| 累计交易成本 | {:.1f}bp |".format(result["cost_total_bp"]),
        "| 平均每期成本 | {:.1f}bp |".format(result["cost_total_bp"] / max(1, window["periods"])),
        "",
        "## 三、久期缺口与闸门",
        "",
        "| 指标 | 调仓策略 | 不调仓基准 |",
        "| --- | --- | --- |",
        "| 平均久期缺口 | {:+.2f} 年 | {:+.2f} 年 |".format(
            result["duration_gap_mean"], result["baseline_duration_gap_mean"]
        ),
        "| 最大绝对缺口 | {:.2f} 年 | {:.2f} 年 |".format(
            result["duration_gap_max_abs"], result["baseline_duration_gap_max_abs"]
        ),
    ]
    for status, count in sorted(result["gate_counts"].items()):
        lines.append("| 闸门结论「{}」| {} 期 |".format(status, count))
    lines.append("")

    lines.append("## 四、收益归因（按资产类别，累计贡献）")
    lines.append("")
    lines.append("| 资产类别 | 累计贡献 |")
    lines.append("| --- | --- |")
    for asset_class, contribution in sorted(
        result["attribution"].items(), key=lambda pair: -abs(pair[1])
    ):
        lines.append(
            "| {} | {} |".format(ASSET_LABELS.get(asset_class, asset_class), _percent(contribution))
        )
    lines.append("")

    lines.append("## 五、逐期明细")
    lines.append("")
    lines.append(
        "| 数据时点 | 策略收益 | 基准收益 | 策略净值 | 基准净值 | 换手 | 成本 | 策略缺口 | 基准缺口 | 闸门 |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in result["periods"]:
        lines.append(
            "| {} | {} | {} | {:.4f} | {:.4f} | {:.2f}% | {:.1f}bp | {:+.2f} | {:+.2f} | {} |".format(
                row["as_of"],
                _percent(row["net_return"]),
                _percent(row["baseline_return"]),
                row["nav"],
                row["baseline_nav"],
                row["turnover_pct"],
                row["cost_bp"],
                row["duration_gap"],
                row["baseline_duration_gap"],
                row["gate_status"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def audit_record(result: Dict[str, Any], policy, version: str) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "backtest",
        "version": version,
        "window": result["window"],
        "history_fingerprint": result["history_fingerprint"],
        "policy": {
            "fingerprint": policy.fingerprint,
            "effective_date": policy.effective_date,
            "path": policy.path,
        },
        "metrics": result["metrics"],
        "baseline_metrics": result["baseline_metrics"],
        "excess_total_return": result["excess_total_return"],
        "turnover_total_pct": result["turnover_total_pct"],
        "cost_total_bp": result["cost_total_bp"],
        "gate_counts": result["gate_counts"],
    }
