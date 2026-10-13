"""命令行入口。

    python -m ins_am_agent
    python -m ins_am_agent --pipeline pipeline.yaml --policy config/constraints.yaml
    python -m ins_am_agent --list-components
"""

from __future__ import annotations

import argparse
import sys

from .orchestrator import (
    DEFAULT_AUDIT,
    DEFAULT_DATA,
    DEFAULT_PIPELINE,
    DEFAULT_POLICY,
    DEFAULT_REPORT,
    load_result,
    summarize,
    write_outputs,
)
from .platform.registry import default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ins-am-agent",
        description="保险资管 Multi-Agent 框架：L0 平台底座 → L1 数据与状态 → L2 约束与政策 → L3 投研 → L4 配置引擎 → L5 治理",
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="组合数据文件（JSON，只放数据）")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="约束与政策文件（YAML，约束唯一来源）")
    parser.add_argument("--pipeline", default=str(DEFAULT_PIPELINE), help="流水线定义（YAML）")
    parser.add_argument("--out", default=str(DEFAULT_REPORT), help="报告输出路径（Markdown）")
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT), help="审计日志输出路径（JSON）")
    parser.add_argument(
        "--list-components",
        action="store_true",
        help="列出注册表里可用的组件（kind.name），不跑流水线",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_components:
        for kind, names in default_registry().describe().items():
            print("{}: {}".format(kind, "、".join(names)))
        return 0

    result = load_result(
        pipeline_path=args.pipeline, data_path=args.data, policy_path=args.policy
    )
    write_outputs(result, args.out, args.audit)
    print(summarize(result))
    print("")
    print("报告：" + str(args.out))
    print("审计日志：" + str(args.audit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
