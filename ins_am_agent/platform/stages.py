"""L0 平台底座：内置阶段的接线层。

每个阶段都是 ``(ctx, **params) -> value`` 的纯函数：业务逻辑仍在各层实现，
这里只做「从上下文取输入、把输出放回上下文」。换实现 = 换注册表里的一项。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .. import __version__
from ..agents import b_research, c_allocation, d_gate, d_report
from ..data_layer import adapters, quality, state as state_layer, synthetic
from ..evaluation import backtest as backtest_layer
from ..evaluation import report as backtest_report
from ..policy import loader as policy_loader
from .registry import Registry


def load_snapshot(ctx: Dict[str, Any], path: str) -> Any:
    """读取数据源，产出组合快照（L1）。"""
    return adapters.load_json_snapshot(path)


def check_quality(ctx: Dict[str, Any]) -> List[Dict[str, str]]:
    """数据质量校验（L1）。"""
    return quality.run(ctx["snapshot"])


def load_policy(ctx: Dict[str, Any], path: str) -> Any:
    """装载约束与政策（L2）——约束的唯一来源。"""
    return policy_loader.load_policy(path)


def assemble_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """把快照、质量报告与政策装配成本次运行的输入包（bundle）。"""
    snapshot = ctx["snapshot"]
    policy = ctx["policy"]
    return {
        "raw": snapshot.raw,
        "path": snapshot.path,
        "as_of": snapshot.as_of,
        "currency": snapshot.currency,
        "holdings": snapshot.holdings,
        "liability": snapshot.liability,
        "market": snapshot.market,
        "constraints": policy.constraints,
        "quality": list(ctx.get("quality") or []),
        "policy": policy,
    }


def run_research(
    ctx: Dict[str, Any],
    analysts: Optional[List[str]] = None,
    challenger: str = "conflict_rules",
) -> Dict[str, Any]:
    """投研团队并行出观点 + 交叉质询（L3）。"""
    return b_research.run_team(ctx["bundle"], analysts=analysts, challenger=challenger)


def run_allocation(ctx: Dict[str, Any], engine: str = "rule_based") -> Any:
    """配置求解（L4）。当前只有规则实现，求解器可替换。"""
    if engine != "rule_based":
        raise ValueError("未知配置引擎：{}".format(engine))
    return c_allocation.run(ctx["bundle"])


def apply_state(ctx: Dict[str, Any]) -> Any:
    """把目标权重落到组合状态上，形成可追溯的调仓流水（L1）。"""
    proposal = ctx["proposal"]
    current = state_layer.PortfolioState.from_snapshot(ctx["snapshot"])
    updated = current.apply(proposal.targets, reasons=proposal.reasons)
    ctx["bundle"]["state_after"] = updated
    return updated


def run_gate(ctx: Dict[str, Any]) -> Any:
    """风控与合规闸门（L5）。"""
    return d_gate.run(ctx["bundle"], ctx["proposal"])


def render_report(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """报告与审计留痕（L5）。"""
    bundle = ctx["bundle"]
    research = ctx["research"]
    proposal = ctx["proposal"]
    gate = ctx["gate"]
    return {
        "report": d_report.render(bundle, research, proposal, gate, __version__),
        "audit": d_report.audit_record(bundle, research, proposal, gate, __version__),
    }


def build_synthetic_history(ctx: Dict[str, Any], periods: int = 24, seed: int = 20260831) -> Any:
    """生成确定性合成历史（L1）——回测输入，可逐字复算。"""
    return synthetic.build_history(periods=periods, seed=seed)


def load_history_file(ctx: Dict[str, Any], path: str) -> Any:
    """读取历史数据文件（L1）：{"periods": [...]}，用于接真实多期数据。"""
    return adapters.load_json_history(path)


def run_backtest(ctx: Dict[str, Any], include_gate: bool = True) -> Dict[str, Any]:
    """走查式回测（评估层）：逐期跑研究 → 配置 → 闸门，并与不调仓基准对照。"""
    return backtest_layer.walk_forward(ctx["history"], ctx["policy"], include_gate=include_gate)


def render_backtest(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """回测报告与审计记录。"""
    result = ctx["backtest"]
    policy = ctx["policy"]
    return {
        "report": backtest_report.render_markdown(result, policy, __version__),
        "audit": backtest_report.audit_record(result, policy, __version__),
    }


BUILTIN_STAGES = (
    ("data", "json", load_snapshot),
    ("data", "quality", check_quality),
    ("data", "synthetic", build_synthetic_history),
    ("data", "history_file", load_history_file),
    ("policy", "file", load_policy),
    ("context", "assemble", assemble_context),
    ("research", "team", run_research),
    ("allocation", "rule_based", run_allocation),
    ("portfolio", "state", apply_state),
    ("gate", "compliance", run_gate),
    ("report", "markdown", render_report),
    ("backtest", "walk_forward", run_backtest),
    ("report", "backtest", render_backtest),
)


def register_builtin_stages(registry: Registry) -> Registry:
    for kind, name, fn in BUILTIN_STAGES:
        registry.register(kind, name, fn)
    return registry
