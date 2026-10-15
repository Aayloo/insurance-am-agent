"""L1 数据与状态：数据适配器。

适配器把外部数据源（JSON 文件、行情接口、精算系统、会计系统）归一成
``PortfolioSnapshot``。接入真实流程时新增一个 adapter 并注册到平台即可，
下游各层不需要改动。

注意：数据文件只放数据。约束与政策属于 L2，见 ``config/constraints.yaml``。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from ..models import Holding, Liability, MarketView

# 资产类别：利率债 / 信用债 / 权益 / 另类 / 现金类
VALID_ASSET_CLASSES = {"rate_bond", "credit_bond", "equity", "alternative", "cash"}
# 发行人类型：sovereign 主权与准主权、diversified 分散组合、
# single_name 单一主体（受集中度上限约束）、counterparty 交易对手
VALID_ISSUER_TYPES = {"sovereign", "diversified", "single_name", "counterparty"}

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


@dataclass
class PortfolioSnapshot:
    """某一时点的组合快照：持仓 + 负债 + 市场。"""

    as_of: str
    currency: str
    holdings: List[Holding]
    liability: Liability
    market: MarketView
    raw: Dict[str, Any] = field(default_factory=dict)
    path: str = ""


class SnapshotAdapter(Protocol):
    """数据适配器协议：任何数据源都要能产出快照。"""

    name: str

    def load(self, path: str) -> PortfolioSnapshot:  # pragma: no cover - 协议
        ...


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
        equity_return_pct=float(node.get("equity_return_pct", 0.0)),
        alternative_return_pct=float(node.get("alternative_return_pct", 0.0)),
    )


def load_json_history(path: str) -> List[Dict[str, Any]]:
    """读取多期快照序列（回测输入）：{"periods": [ ...单期数据结构... ]}"""
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    periods = document.get("periods")
    if not isinstance(periods, list) or not periods:
        raise ValueError("历史数据文件必须包含非空的 periods 数组：{}".format(path))
    return periods


def load_json_snapshot(path: str) -> PortfolioSnapshot:
    """从 JSON 文件读取快照（零依赖的默认适配器）。"""
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return snapshot_from_raw(raw, path=str(path))


def snapshot_from_raw(raw: Dict[str, Any], path: str = "") -> PortfolioSnapshot:
    """把一份原始数据字典装配成快照（回测逐期复用同一入口）。"""
    return PortfolioSnapshot(
        as_of=raw.get("as_of", ""),
        currency=raw.get("currency", ""),
        holdings=build_holdings(raw),
        liability=build_liability(raw),
        market=build_market(raw),
        raw=raw,
        path=path,
    )


class JsonSnapshotAdapter:
    """JSON 文件适配器；注册名为 ``data.json``。"""

    name = "json"

    def load(self, path: str) -> PortfolioSnapshot:
        return load_json_snapshot(path)
