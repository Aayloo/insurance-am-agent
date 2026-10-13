"""L0 平台测试：流水线定义驱动执行，档位切换只改配置。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ins_am_agent.orchestrator import DEFAULT_PIPELINE, run_pipeline  # noqa: E402
from ins_am_agent.platform.pipeline import (  # noqa: E402
    PipelineError,
    load_pipeline,
    run_pipeline as run_spec,
)

DATA = (ROOT / "data" / "sample_portfolio.json").as_posix()
POLICY = (ROOT / "config" / "constraints.yaml").as_posix()

PIPELINE_TEMPLATE = """\
version: 1
name: "测试流水线"
vars:
  data: "{data}"
  policy: "{policy}"
stages:
  - id: snapshot
    uses: data.json
    with:
      path: "${{data}}"
  - id: quality
    uses: data.quality
  - id: policy
    uses: policy.file
    with:
      path: "${{policy}}"
  - id: bundle
    uses: context.assemble
  - id: research
    uses: research.team
    with:
      analysts: {analysts}
  - id: proposal
    uses: allocation.rule_based
  - id: position
    uses: portfolio.state
  - id: gate
    uses: gate.compliance
  - id: report
    uses: report.markdown
"""


def write_pipeline(text: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    handle.write(text)
    handle.close()
    return Path(handle.name)


class DefaultPipelineTest(unittest.TestCase):
    def test_default_pipeline_has_expected_stages(self):
        spec = load_pipeline(str(DEFAULT_PIPELINE))
        self.assertEqual(
            [stage["id"] for stage in spec["stages"]],
            [
                "snapshot",
                "quality",
                "policy",
                "bundle",
                "research",
                "proposal",
                "position",
                "gate",
                "report",
            ],
        )

    def test_pipeline_records_execution_trace(self):
        result = run_pipeline()
        self.assertEqual(len(result["pipeline"]["executed"]), 9)
        self.assertEqual(result["pipeline"]["name"], "保险资管配置建议 · 完整档")


class ConfigurablePipelineTest(unittest.TestCase):
    def test_starter_tier_runs_with_two_analysts(self):
        """起步档：只跑宏观与信用两个研究员，不需要改代码。"""
        path = write_pipeline(
            PIPELINE_TEMPLATE.format(data=DATA, policy=POLICY, analysts="[macro, credit]")
        )
        result = run_pipeline(pipeline_path=path)
        self.assertEqual([item.agent_id for item in result["research"]["opinions"]], ["B1", "B2"])
        self.assertEqual(result["research"]["analysts"], ["macro", "credit"])
        self.assertTrue(result["report"])

    def test_unknown_analyst_fails_closed(self):
        path = write_pipeline(
            PIPELINE_TEMPLATE.format(data=DATA, policy=POLICY, analysts="[macro, options]")
        )
        with self.assertRaises(ValueError):
            run_pipeline(pipeline_path=path)

    def test_unknown_component_fails_closed(self):
        path = write_pipeline(
            """\
version: 1
vars:
  data: "{data}"
stages:
  - id: snapshot
    uses: data.not_registered
    with:
      path: "${{data}}"
""".format(
                data=DATA
            )
        )
        with self.assertRaises(PipelineError):
            run_spec(str(path))

    def test_undefined_variable_fails_closed(self):
        path = write_pipeline(
            """\
version: 1
stages:
  - id: snapshot
    uses: data.json
    with:
      path: "${missing}"
"""
        )
        with self.assertRaises(PipelineError):
            run_spec(str(path))

    def test_duplicate_stage_id_fails_closed(self):
        path = write_pipeline(
            """\
version: 1
stages:
  - id: snapshot
    uses: data.json
    with:
      path: "{data}"
  - id: snapshot
    uses: data.quality
""".format(
                data=DATA
            )
        )
        with self.assertRaises(PipelineError):
            run_spec(str(path))


if __name__ == "__main__":
    unittest.main()
