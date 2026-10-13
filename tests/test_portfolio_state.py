"""L1 组合状态测试：调仓流水、换手口径、状态指纹。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ins_am_agent.data_layer.adapters import load_json_snapshot  # noqa: E402
from ins_am_agent.data_layer.state import PortfolioState  # noqa: E402

DATA = ROOT / "data" / "sample_portfolio.json"


class PortfolioStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = load_json_snapshot(str(DATA))
        cls.initial = PortfolioState.from_snapshot(cls.snapshot)

    def test_snapshot_becomes_state(self):
        self.assertEqual(self.initial.version, 0)
        self.assertEqual(len(self.initial.weights), len(self.snapshot.holdings))
        self.assertAlmostEqual(sum(self.initial.weights.values()), 1.0, places=6)

    def test_apply_records_trades_and_bumps_version(self):
        targets = dict(self.initial.weights)
        first = next(iter(targets))
        targets[first] -= 0.04
        second = list(targets)[1]
        targets[second] += 0.04
        updated = self.initial.apply(targets)
        self.assertEqual(updated.version, 1)
        self.assertEqual(len(updated.latest_trades()), 2)
        self.assertAlmostEqual(updated.turnover_pct(), 4.0, places=6)
        self.assertAlmostEqual(sum(updated.weights.values()), 1.0, places=6)

    def test_apply_is_pure(self):
        before = dict(self.initial.weights)
        self.initial.apply({name: value for name, value in before.items()})
        self.assertEqual(self.initial.weights, before)
        self.assertEqual(self.initial.version, 0)

    def test_fingerprint_is_stable_and_moves_with_weights(self):
        self.assertEqual(self.initial.fingerprint(), self.initial.fingerprint())
        targets = dict(self.initial.weights)
        first = next(iter(targets))
        targets[first] = targets[first] - 0.02
        second = list(targets)[1]
        targets[second] = targets[second] + 0.02
        self.assertNotEqual(self.initial.apply(targets).fingerprint(), self.initial.fingerprint())


if __name__ == "__main__":
    unittest.main()
