"""L1 数据与状态：质量校验。

时点对齐、权重合计、必填字段、口径一致性。产出结构化问题清单（级别 / 项目 /
说明），直接进报告与审计，不做任何静默修补。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .adapters import (
    REQUIRED_HOLDING_FIELDS,
    VALID_ASSET_CLASSES,
    VALID_ISSUER_TYPES,
    PortfolioSnapshot,
)

WEIGHT_TOLERANCE = 1e-6
SINGLE_NAME_WATCH_PCT = 0.05


def run(snapshot: PortfolioSnapshot) -> List[Dict[str, str]]:
    """返回问题清单；空列表表示数据可用。"""
    issues: List[Dict[str, str]] = []
    as_of = snapshot.as_of
    holdings = snapshot.holdings
    total_weight = sum(item.weight for item in holdings)

    if abs(total_weight - 1.0) > WEIGHT_TOLERANCE:
        issues.append(
            {
                "level": "错误",
                "item": "权重合计",
                "detail": "合计 {:.4f}，不等于 1.0".format(total_weight),
            }
        )

    for item in holdings:
        for field in REQUIRED_HOLDING_FIELDS:
            if not getattr(item, field, "") and getattr(item, field, 0) != 0:
                issues.append(
                    {"level": "错误", "item": item.name, "detail": "缺少字段 {}".format(field)}
                )
        if item.asset_class not in VALID_ASSET_CLASSES:
            issues.append(
                {
                    "level": "错误",
                    "item": item.name,
                    "detail": "未知资产类别 {}".format(item.asset_class),
                }
            )
        if item.weight < 0:
            issues.append({"level": "错误", "item": item.name, "detail": "权重为负"})
        if item.asset_class == "credit_bond" and not item.rating:
            issues.append({"level": "错误", "item": item.name, "detail": "信用债缺少内部评级"})
        if item.issuer_type not in VALID_ISSUER_TYPES:
            issues.append(
                {
                    "level": "错误",
                    "item": item.name,
                    "detail": "未知发行人类型 {}".format(item.issuer_type),
                }
            )
        if (
            item.weight > SINGLE_NAME_WATCH_PCT + WEIGHT_TOLERANCE
            and item.issuer_type == "diversified"
            and item.asset_class == "credit_bond"
        ):
            issues.append(
                {
                    "level": "提示",
                    "item": item.name,
                    "detail": "信用债标记为分散组合但权重较高，请确认是否需要按单一主体管理",
                }
            )
        if as_of and item.valuation_date != as_of:
            issues.append(
                {
                    "level": "提示",
                    "item": item.name,
                    "detail": "估值日 {} 与数据时点 {} 不一致，需确认".format(
                        item.valuation_date, as_of
                    ),
                }
            )

    if "constraints" in snapshot.raw:
        issues.append(
            {
                "level": "提示",
                "item": "数据文件",
                "detail": "数据文件中的 constraints 已不再生效，约束统一由政策文件提供，请移除该项",
            }
        )

    return issues
