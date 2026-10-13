"""L2 政策装载测试：单一来源、严格校验、fail closed。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ins_am_agent.policy.loader import PolicyError, load_policy  # noqa: E402
from ins_am_agent.platform.miniyaml import MiniYamlError, loads  # noqa: E402

POLICY_PATH = ROOT / "config" / "constraints.yaml"
DATA_PATH = ROOT / "data" / "sample_portfolio.json"


class MiniYamlTest(unittest.TestCase):
    def test_parses_nested_mapping_and_sequence_of_mappings(self):
        text = (
            "name: \"示例\"\n"
            "vars:\n"
            "  data: \"a.json\"\n"
            "stages:\n"
            "  - id: one\n"
            "    uses: data.json\n"
            "  - id: two\n"
            "    uses: data.quality\n"
        )
        document = loads(text)
        self.assertEqual(document["name"], "示例")
        self.assertEqual(document["vars"]["data"], "a.json")
        self.assertEqual([stage["id"] for stage in document["stages"]], ["one", "two"])
        self.assertEqual(document["stages"][1]["uses"], "data.quality")

    def test_parses_inline_sequence_and_scalars(self):
        document = loads("analysts: [macro, credit]\ncap: 20.0\nflag: true\nempty: null\n")
        self.assertEqual(document["analysts"], ["macro", "credit"])
        self.assertEqual(document["cap"], 20.0)
        self.assertIs(document["flag"], True)
        self.assertIsNone(document["empty"])

    def test_rejects_tab_indentation(self):
        with self.assertRaises(MiniYamlError):
            loads("a:\n\tb: 1\n")

    def test_rejects_unknown_syntax(self):
        for text in ("a: &anchor 1\n", "key: {a: 1}\n", "---\na: 1\n"):
            with self.assertRaises(MiniYamlError):
                loads(text)

    def test_rejects_duplicate_key(self):
        with self.assertRaises(MiniYamlError):
            loads("a: 1\na: 2\n")


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(str(POLICY_PATH))

    def test_loads_real_policy(self):
        self.assertEqual(self.policy.effective_date, "2026-08-31")
        self.assertEqual(self.policy.constraints.equity_cap_pct, 20.0)
        self.assertEqual(self.policy.constraints.max_turnover_pct, 15.0)
        self.assertTrue(self.policy.fingerprint)

    def test_exposes_rule_metadata(self):
        self.assertEqual(self.policy.rule("duration_gap").on_breach, "升级审批")
        self.assertIn("投委会", self.policy.owner_of("duration_gap"))
        self.assertEqual(self.policy.governance_of("order_execution"), "人工执行，Agent 不接触交易接口")

    def test_data_file_holds_no_constraints(self):
        """约束只能有一个来源：数据文件里不该再出现 constraints。"""
        with open(DATA_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertNotIn("constraints", raw)

    def test_requires_effective_date(self):
        with self.assertRaises(PolicyError):
            load_policy("in-memory.yaml", document={"constraints": {}})

    def test_requires_all_constraint_fields(self):
        with self.assertRaises(PolicyError):
            load_policy(
                "in-memory.yaml",
                document={"effective_date": "2026-01-01", "constraints": {"equity_cap_pct": 20.0}},
            )

    def test_rejects_unknown_rule_key(self):
        document = loads(POLICY_PATH.read_text(encoding="utf-8"))
        document["rules"]["not_a_rule"] = {"owner": "x"}
        with self.assertRaises(PolicyError):
            load_policy("in-memory.yaml", document=document)

    def test_rejects_invalid_on_breach(self):
        document = loads(POLICY_PATH.read_text(encoding="utf-8"))
        document["rules"]["equity_cap"]["on_breach"] = "随便写"
        with self.assertRaises(PolicyError):
            load_policy("in-memory.yaml", document=document)

    def test_rejects_non_numeric_limit(self):
        document = loads(POLICY_PATH.read_text(encoding="utf-8"))
        document["constraints"]["equity_cap_pct"] = "二十"
        with self.assertRaises(PolicyError):
            load_policy("in-memory.yaml", document=document)


if __name__ == "__main__":
    unittest.main()
