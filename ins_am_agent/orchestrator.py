"""编排器：读取流水线定义并执行。

阶段顺序、启用哪些研究员、用哪个配置引擎都由 ``pipeline.yaml`` 决定；
本模块只负责把结果整理成稳定结构并写出文件。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from . import __version__
from .platform.pipeline import run_pipeline as run_pipeline_spec

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PIPELINE = ROOT / "pipeline.yaml"
DEFAULT_DATA = ROOT / "data" / "sample_portfolio.json"
DEFAULT_POLICY = ROOT / "config" / "constraints.yaml"
DEFAULT_REPORT = ROOT / "examples" / "sample_report.md"
DEFAULT_AUDIT = ROOT / "examples" / "audit_log.json"


def load_result(
    pipeline_path: Optional[Union[str, Path]] = None,
    data_path: Optional[Union[str, Path]] = None,
    policy_path: Optional[Union[str, Path]] = None,
    variables: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """按流水线定义跑一次，返回整理后的结果。"""
    context = run_pipeline_spec(
        str(pipeline_path or DEFAULT_PIPELINE),
        variables={
            "data": str(data_path or DEFAULT_DATA),
            "policy": str(policy_path or DEFAULT_POLICY),
            **dict(variables or {}),
        },
    )
    report = context.get("report") or {}
    return {
        "bundle": context.get("bundle"),
        "research": context.get("research"),
        "proposal": context.get("proposal"),
        "gate": context.get("gate"),
        "policy": context.get("policy"),
        "position": context.get("position"),
        "report": report.get("report", ""),
        "audit": report.get("audit", {}),
        "pipeline": context.get("_pipeline", {}),
        "context": context,
        "version": __version__,
    }


def run_pipeline(
    data_path: Optional[Union[str, Path]] = None,
    policy_path: Optional[Union[str, Path]] = None,
    pipeline_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """向后兼容入口：默认跑完整档流水线。"""
    return load_result(pipeline_path=pipeline_path, data_path=data_path, policy_path=policy_path)


def write_outputs(
    result: Dict[str, Any],
    report_path: Union[str, Path] = DEFAULT_REPORT,
    audit_path: Union[str, Path] = DEFAULT_AUDIT,
) -> None:
    report_path = Path(report_path)
    audit_path = Path(audit_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result["report"], encoding="utf-8")
    audit_path.write_text(
        json.dumps(result["audit"], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def summarize(result: Dict[str, Any]) -> str:
    proposal = result["proposal"]
    gate = result["gate"]
    bundle = result["bundle"]
    policy = result.get("policy")
    pipeline = result.get("pipeline") or {}
    lines = [
        "流水线：{}（阶段 {} 个）".format(pipeline.get("name") or "未命名", len(pipeline.get("executed", []))),
    ]
    if policy is not None:
        lines.append(
            "政策：生效日 {}，指纹 {}".format(policy.effective_date, policy.fingerprint)
        )
    lines.extend(
        [
            "数据时点：{}（质量问题 {} 项）".format(bundle["as_of"], len(bundle["quality"])),
            "投研观点：{} 条，分歧点 {} 个".format(
                len(result["research"]["opinions"]),
                len(result["research"]["challenge"]["disagreements"]),
            ),
            "久期：{:.2f} → {:.2f} 年（负债 {:.1f} 年，缺口 {:+.2f} 年）".format(
                proposal.duration_before,
                proposal.duration_after,
                proposal.liability_duration,
                proposal.duration_after - proposal.liability_duration,
            ),
            "换手：{:.2f}%（估算成本 {:.2f}bp）".format(proposal.turnover_pct, proposal.cost_bp),
            "闸门结论：{} —— {}".format(gate.status, gate.summary),
        ]
    )
    return "\n".join(lines)
