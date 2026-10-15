"""L1 合成历史 + 评估层测试：可复现、指标口径、策略与基准对照。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ins_am_agent.data_layer.synthetic import build_history  # noqa: E402
from ins_am_agent.evaluation import backtest, metrics  # noqa: E402
from ins_am_agent.orchestrator import load_result  # noqa: E402
from ins_am_agent.policy.loader import load_policy  # noqa: E402

POLICY = ROOT / "config" / "constraints.yaml"
BACKTEST_PIPELINE = ROOT / "pipeline.backtest.yaml"


class SyntheticHistoryTest(unittest.TestCase):
    def test_same_seed_reproduces_same_history(self):
        first = build_history(periods=6, seed=42)
        second = build_history(periods=6, seed=42)
        self.assertEqual(first, second)

    def test_different_seed_changes_history(self):
        self.assertNotEqual(build_history(periods=6, seed=42), build_history(periods=6, seed=43))

    def test_periods_are_well_formed(self):
        history = build_history(periods=6, seed=7)
        self.assertEqual(len(history), 6)
        for period in history:
            self.assertIn("as_of", period)
            self.assertIn("market", period)
            self.assertIn("liability", period)
            total = sum(item["weight"] for item in period["holdings"])
            self.assertAlmostEqual(total, 1.0, places=6)

    def test_rejects_too_short_horizon(self):
        with self.assertRaises(ValueError):
            build_history(periods=1)


class MetricsTest(unittest.TestCase):
    def test_nav_and_total_return(self):
        nav = metrics.nav_from_returns([0.10, -0.10])
        self.assertAlmostEqual(nav[-1], 1.1 * 0.9, places=10)
        self.assertAlmostEqual(metrics.total_return(nav), 0.99 - 1.0, places=10)

    def test_max_drawdown(self):
        self.assertAlmostEqual(metrics.max_drawdown([1.0, 1.2, 0.9, 1.1]), -0.25, places=10)
        self.assertAlmostEqual(metrics.max_drawdown([1.0, 1.1, 1.2]), 0.0, places=10)

    def test_annualized_return_of_one_year_of_doubling(self):
        nav = [1.0] + [1.0 * (2.0 ** (1.0 / 12.0)) ** month for month in range(1, 13)]
        self.assertAlmostEqual(metrics.annualized_return(nav), 1.0, places=6)

    def test_volatility_is_zero_for_flat_series(self):
        self.assertAlmostEqual(metrics.annualized_vol([0.01] * 24), 0.0, places=12)
        self.assertAlmostEqual(metrics.sharpe([0.01] * 24), 0.0, places=12)


class WalkForwardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy(str(POLICY))
        cls.history = build_history(periods=12, seed=20260831)
        cls.result = backtest.walk_forward(cls.history, cls.policy)

    def test_shape_of_result(self):
        result = self.result
        self.assertEqual(len(result["periods"]), len(self.history) - 1)
        self.assertEqual(len(result["nav"]), len(self.history))
        self.assertEqual(len(result["returns"]), len(self.history) - 1)
        self.assertEqual(result["window"]["periods"], len(self.history))

    def test_metrics_are_in_sane_ranges(self):
        result = self.result
        self.assertLessEqual(result["metrics"]["max_drawdown"], 0.0)
        self.assertGreater(result["metrics"]["annualized_vol"], 0.0)
        self.assertGreaterEqual(result["cost_total_bp"], 0.0)
        self.assertGreater(result["turnover_total_pct"], 0.0)

    def test_strategy_reduces_duration_gap_versus_baseline(self):
        """策略的价值主张是收敛久期缺口，这一条必须成立。"""
        result = self.result
        self.assertLess(
            abs(result["duration_gap_mean"]), abs(result["baseline_duration_gap_mean"])
        )
        self.assertLessEqual(
            result["duration_gap_max_abs"], result["baseline_duration_gap_max_abs"]
        )

    def test_attribution_equals_gross_returns(self):
        result = self.result
        total = sum(result["attribution"].values())
        gross = sum(row["gross_return"] for row in result["periods"])
        self.assertAlmostEqual(total, gross, places=10)

    def test_backtest_is_reproducible(self):
        again = backtest.walk_forward(build_history(periods=12, seed=20260831), self.policy)
        self.assertEqual(again["nav"], self.result["nav"])
        self.assertEqual(again["history_fingerprint"], self.result["history_fingerprint"])

    def test_gate_can_be_switched_off(self):
        without_gate = backtest.walk_forward(self.history, self.policy, include_gate=False)
        self.assertEqual(without_gate["gate_counts"], {})
        self.assertEqual(without_gate["metrics"], self.result["metrics"])

    def test_rejects_short_history(self):
        with self.assertRaises(ValueError):
            backtest.walk_forward(self.history[:1], self.policy)


class BacktestPipelineTest(unittest.TestCase):
    def test_pipeline_produces_report_and_audit(self):
        result = load_result(pipeline_path=BACKTEST_PIPELINE)
        self.assertIn("走查式回测报告", result["report"])
        self.assertEqual(result["audit"]["kind"], "backtest")
        self.assertIn("policy", result["audit"])
        self.assertTrue(result["audit"]["history_fingerprint"])
        self.assertTrue(result["pipeline"]["executed"])


if __name__ == "__main__":
    unittest.main()
