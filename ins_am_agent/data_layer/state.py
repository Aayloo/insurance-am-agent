"""L1 数据与状态：组合状态。

资管的核心是**有状态的组合**：持仓、成本基线、调仓流水必须可追溯。
本模块让「目标权重」落成一条可审计的调仓记录，也是后续回测与归因的挂点。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .adapters import PortfolioSnapshot

WEIGHT_EPSILON = 1e-9


@dataclass(frozen=True)
class Trade:
    """一笔调仓：从原权重调到目标权重。"""

    name: str
    from_weight: float
    to_weight: float

    @property
    def delta(self) -> float:
        return self.to_weight - self.from_weight


@dataclass
class PortfolioState:
    """组合在某一时点的状态；``apply`` 返回新状态，不修改原对象。"""

    as_of: str
    weights: Dict[str, float]
    trades: List[Trade] = field(default_factory=list)
    version: int = 0

    @classmethod
    def from_snapshot(cls, snapshot: PortfolioSnapshot) -> "PortfolioState":
        return cls(as_of=snapshot.as_of, weights={item.name: item.weight for item in snapshot.holdings})

    def apply(
        self,
        targets: Dict[str, float],
        reasons: Optional[Sequence[str]] = None,
    ) -> "PortfolioState":
        """按目标权重生成新状态，并记录本次调仓流水。"""
        new_weights: Dict[str, float] = {}
        for name, weight in self.weights.items():
            new_weights[name] = float(targets.get(name, weight))
        new_trades: List[Trade] = []
        for name in self.weights:
            before = self.weights[name]
            after = new_weights[name]
            if abs(after - before) > WEIGHT_EPSILON:
                new_trades.append(Trade(name=name, from_weight=before, to_weight=after))
        return PortfolioState(
            as_of=self.as_of,
            weights=new_weights,
            trades=list(self.trades) + new_trades,
            version=self.version + 1,
        )

    def turnover_pct(self) -> float:
        """单边换手（%）：与配置引擎的换手口径保持一致。"""
        moved = sum(abs(trade.delta) for trade in self.trades)
        return round(0.5 * moved * 100, 4)

    def latest_trades(self) -> List[Trade]:
        return [trade for trade in self.trades if abs(trade.delta) > WEIGHT_EPSILON]

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"as_of": self.as_of, "weights": self.weights}, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:12]
