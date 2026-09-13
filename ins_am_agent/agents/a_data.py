"""A 层：数据与约束。

A1 取数、A2 校验（时点对齐与口径统一）、A3 约束清单。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..models import Constraints, Holding, Liability, MarketView

VALID_ASSET_CLASSES = {"rate_bond", "credit_bond", "equity", "alternative", "cash"}
REQUIRED_HOLDING_FIELDS = (
    "name",
    "asset_class",
    "weight",
    "duration",
    "yield_pct",
    "issuer",
    "liquidity_days",
    "valuation_date",
)
# 发行人类型：sovereign 主权与准主权、diversified 分散组合、
# single_name 单一主体（受集中度上限约束）、counterparty 交易对手
VALID_ISSUER_TYPES = {"sovereign", "diversified", "single_name", "counterparty"}
WEIGHT_TOLERANCE = 1e-6


def load_bundle(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_holdings(raw: Dict[str, Any]) -> List[Holding]:
    holdings: List[Holding] = []
    for item in raw.get("holdings", []):
        holdings.append(
            Holding(
                name=item["name"],
                asset_class=item["asset_class"],
                weight=float(item["weight"]),
                duration=float(item["duration"]),
                yield_pct=float(item["yield_pct"]),
                rating=item.get("rating", ""),
                issuer=item.get("issuer", ""),
                issuer_type=item.get("issuer_type", "diversified"),
                liquidity_days=int(item.get("liquidity_days", 0)),
                valuation_date=item.get("valuation_date", ""),
            )
        )
    return holdings


def build_liability(raw: Dict[str, Any]) -> Liability:
    node = raw["liability"]
    return Liability(
        duration=float(node["duration"]),
        cost_pct=float(node["cost_pct"]),
        annual_cashflow_pct=float(node["annual_cashflow_pct"]),
    )


def build_market(raw: Dict[str, Any]) -> MarketView:
    node = raw["market"]
    return MarketView(
        curve_10y=float(node["curve_10y"]),
        curve_slope=float(node["curve_slope"]),
        credit_spread_pct=float(node["credit_spread_pct"]),
        spread_percentile=int(node["spread_percentile"]),
        equity_dividend_yield=float(node["equity_dividend_yield"]),
        rate_shock_bp=int(node["rate_shock_bp"]),
    )


def build_constraints(raw: Dict[str, Any]) -> Constraints:
    node = raw["constraints"]
    return Constraints(
        equity_cap_pct=float(node["equity_cap_pct"]),
        alternative_cap_pct=float(node["alternative_cap_pct"]),
        single_issuer_cap_pct=float(node["single_issuer_cap_pct"]),
        min_liquidity_pct=float(node["min_liquidity_pct"]),
        duration_tolerance_years=float(node["duration_tolerance_years"]),
        max_turnover_pct=float(node["max_turnover_pct"]),
    )


def validate(raw: Dict[str, Any], holdings: List[Holding]) -> List[Dict[str, str]]:
    """A2：时点对齐、权重合计、必填字段、口径一致性检查。"""
    issues: List[Dict[str, str]] = []
    as_of = raw.get("as_of", "")
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
                    {
                        "level": "错误",
                        "item": item.name,
                        "detail": "缺少字段 {}".format(field),
                    }
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
            issues.append(
                {"level": "错误", "item": item.name, "detail": "信用债缺少内部评级"}
            )
        if item.issuer_type not in VALID_ISSUER_TYPES:
            issues.append(
                {
                    "level": "错误",
                    "item": item.name,
                    "detail": "未知发行人类型 {}".format(item.issuer_type),
                }
            )
        if item.weight > 0.05 + WEIGHT_TOLERANCE and item.issuer_type == "diversified" and item.asset_class == "credit_bond":
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

    return issues


def class_weights(holdings: List[Holding], weights: Dict[str, float] | None = None) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for item in holdings:
        value = item.weight if weights is None else weights.get(item.name, item.weight)
        result[item.asset_class] = result.get(item.asset_class, 0.0) + value
    return result


def max_single_name(holdings: List[Holding], weights: Dict[str, float] | None = None) -> Dict[str, float]:
    """单一主体集中度：只统计 issuer_type 为 single_name 的持仓。"""
    best = {"name": "", "weight": 0.0}
    for item in holdings:
        if item.issuer_type != "single_name":
            continue
        value = item.weight if weights is None else weights.get(item.name, item.weight)
        if value > best["weight"]:
            best = {"name": item.name, "weight": value}
    return best


def run(path: str | Path) -> Dict[str, Any]:
    raw = load_bundle(path)
    holdings = build_holdings(raw)
    quality = validate(raw, holdings)
    return {
        "raw": raw,
        "path": str(path),
        "as_of": raw.get("as_of", ""),
        "holdings": holdings,
        "liability": build_liability(raw),
        "market": build_market(raw),
        "constraints": build_constraints(raw),
        "quality": quality,
    }
