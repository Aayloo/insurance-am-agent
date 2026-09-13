"""数据结构定义。

设计原则：所有金额、比例、久期、收益率都由确定性代码计算，
LLM 只参与文字组织，不参与数值计算。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Holding:
    name: str
    asset_class: str
    weight: float
    duration: float
    yield_pct: float
    rating: str
    issuer: str
    issuer_type: str
    liquidity_days: int
    valuation_date: str


@dataclass
class Liability:
    duration: float
    cost_pct: float
    annual_cashflow_pct: float


@dataclass
class MarketView:
    curve_10y: float
    curve_slope: float
    credit_spread_pct: float
    spread_percentile: int
    equity_dividend_yield: float
    rate_shock_bp: int


@dataclass
class Constraints:
    equity_cap_pct: float
    alternative_cap_pct: float
    single_issuer_cap_pct: float
    min_liquidity_pct: float
    duration_tolerance_years: float
    max_turnover_pct: float


@dataclass
class Opinion:
    agent_id: str
    topic: str
    stance: str
    direction: str
    evidence: str
    confidence: str
    invalid_if: str


@dataclass
class GateItem:
    rule: str
    limit: str
    actual: str
    status: str
    owner: str


@dataclass
class GateResult:
    status: str
    summary: str
    items: List[GateItem]


@dataclass
class Proposal:
    targets: Dict[str, float]
    current: Dict[str, float]
    duration_before: float
    duration_after: float
    liability_duration: float
    turnover_pct: float
    cost_bp: float
    yield_before: float
    yield_after: float
    liability_cost_pct: float
    reasons: List[str]
    stress_tests: List[Dict[str, object]]
