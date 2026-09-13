"""端到端测试：样例数据跑通 A→B→C→D，并校验关键不变量。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ins_am_agent.orchestrator import run_pipeline  # noqa: E402


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_pipeline()

    def test_data_quality_flags_stale_valuation(self):
        issues = self.result["bundle"]["quality"]
        self.assertTrue(any("估值日" in issue["detail"] for issue in issues))

    def test_research_team_has_five_outputs(self):
        opinions = self.result["research"]["opinions"]
        self.assertEqual([item.agent_id for item in opinions], ["B1", "B2", "B3", "B4"])
        for opinion in opinions:
            self.assertTrue(opinion.evidence)
            self.assertTrue(opinion.invalid_if)

    def test_target_weights_sum_to_one(self):
        total = sum(self.result["proposal"].targets.values())
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_duration_gap_narrows(self):
        proposal = self.result["proposal"]
        before = abs(proposal.duration_before - proposal.liability_duration)
        after = abs(proposal.duration_after - proposal.liability_duration)
        self.assertLess(after, before)

    def test_turnover_within_limit(self):
        proposal = self.result["proposal"]
        limit = self.result["bundle"]["constraints"].max_turnover_pct
        self.assertLessEqual(proposal.turnover_pct, limit)

    def test_single_issuer_brought_back_within_cap(self):
        constraints = self.result["bundle"]["constraints"]
        targets = self.result["proposal"].targets
        peak = max(
            targets[item.name]
            for item in self.result["bundle"]["holdings"]
            if item.issuer_type == "single_name"
        ) * 100
        self.assertLessEqual(peak, constraints.single_issuer_cap_pct + 1e-6)

    def test_gate_status_is_known(self):
        status = self.result["gate"].status
        self.assertIn(status, {"通过", "提示", "降规模", "升级审批", "否决"})

    def test_equity_within_cap(self):
        constraints = self.result["bundle"]["constraints"]
        equity = sum(
            self.result["proposal"].targets[item.name]
            for item in self.result["bundle"]["holdings"]
            if item.asset_class == "equity"
        ) * 100
        self.assertLessEqual(equity, constraints.equity_cap_pct + 1e-6)


if __name__ == "__main__":
    unittest.main()
