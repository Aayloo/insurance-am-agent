"""编排器：A → B → C → D 一次完整流水线。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from . import __version__
from .agents import a_data, b_research, c_allocation, d_gate, d_report

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_portfolio.json"
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "examples" / "sample_report.md"
DEFAULT_AUDIT = Path(__file__).resolve().parent.parent / "examples" / "audit_log.json"


def run_pipeline(data_path: str | Path = DEFAULT_DATA) -> Dict[str, Any]:
    bundle = a_data.run(data_path)
    research = b_research.run(bundle)
    proposal = c_allocation.run(bundle)
    gate = d_gate.run(bundle, proposal)
    return {
        "bundle": bundle,
        "research": research,
        "proposal": proposal,
        "gate": gate,
        "version": __version__,
    }


def write_outputs(result: Dict[str, Any], report_path: str | Path, audit_path: str | Path) -> None:
    report_path = Path(report_path)
    audit_path = Path(audit_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    report = d_report.render(
        result["bundle"], result["research"], result["proposal"], result["gate"], result["version"]
    )
    report_path.write_text(report, encoding="utf-8")

    record = d_report.audit_record(
        result["bundle"], result["research"], result["proposal"], result["gate"], result["version"]
    )
    audit_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize(result: Dict[str, Any]) -> str:
    proposal = result["proposal"]
    gate = result["gate"]
    bundle = result["bundle"]
    return "\n".join(
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
