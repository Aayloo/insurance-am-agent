"""兼容层：A 层已拆分为 L1（数据与状态）与 L2（约束与政策）。

保留本模块只为旧导入路径不中断；新代码请直接用
``ins_am_agent.data_layer`` 与 ``ins_am_agent.policy``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data_layer.adapters import (  # noqa: F401  （兼容导出）
    VALID_ASSET_CLASSES,
    VALID_ISSUER_TYPES,
    build_holdings,
    build_liability,
    build_market,
    load_json_snapshot,
)
from ..data_layer.quality import run as run_quality
from ..models import Holding
from ..policy.loader import load_policy

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "config" / "constraints.yaml"


def class_weights(
    holdings: List[Holding], weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for item in holdings:
        value = item.weight if weights is None else weights.get(item.name, item.weight)
        result[item.asset_class] = result.get(item.asset_class, 0.0) + value
    return result


def max_single_name(
    holdings: List[Holding], weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """单一主体集中度：只统计 issuer_type 为 single_name 的持仓。"""
    best = {"name": "", "weight": 0.0}
    for item in holdings:
        if item.issuer_type != "single_name":
            continue
        value = item.weight if weights is None else weights.get(item.name, item.weight)
        if value > best["weight"]:
            best = {"name": item.name, "weight": value}
    return best


def validate(raw: Dict[str, Any], holdings: List[Holding]) -> List[Dict[str, str]]:
    """兼容包装：按旧签名校验一份原始数据。"""
    from ..data_layer.adapters import PortfolioSnapshot

    snapshot = PortfolioSnapshot(
        as_of=raw.get("as_of", ""),
        currency=raw.get("currency", ""),
        holdings=holdings,
        liability=build_liability(raw),
        market=build_market(raw),
        raw=raw,
        path="",
    )
    return run_quality(snapshot)


def run(path: str, policy_path: Optional[str] = None) -> Dict[str, Any]:
    """兼容包装：按旧形状返回 bundle（约束改由政策文件提供）。"""
    snapshot = load_json_snapshot(path)
    policy = load_policy(str(policy_path or DEFAULT_POLICY))
    return {
        "raw": snapshot.raw,
        "path": snapshot.path,
        "as_of": snapshot.as_of,
        "currency": snapshot.currency,
        "holdings": snapshot.holdings,
        "liability": snapshot.liability,
        "market": snapshot.market,
        "constraints": policy.constraints,
        "quality": run_quality(snapshot),
        "policy": policy,
    }
