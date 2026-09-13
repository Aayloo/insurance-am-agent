"""命令行入口：python -m ins_am_agent --out examples/sample_report.md"""

from __future__ import annotations

import argparse
import sys

from .orchestrator import DEFAULT_AUDIT, DEFAULT_DATA, DEFAULT_REPORT, run_pipeline, summarize, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ins-am-agent",
        description="保险资管 Multi-Agent 框架：A 数据与约束 → B 投研 → C 配置 → D 闸门与报告",
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="组合与约束数据文件（JSON）")
    parser.add_argument("--out", default=str(DEFAULT_REPORT), help="报告输出路径（Markdown）")
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT), help="审计日志输出路径（JSON）")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = run_pipeline(args.data)
    write_outputs(result, args.out, args.audit)
    print(summarize(result))
    print("")
    print("报告：" + str(args.out))
    print("审计日志：" + str(args.audit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
