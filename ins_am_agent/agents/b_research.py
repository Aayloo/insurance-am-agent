"""B 层：投研团队。

B1 宏观与利率、B2 信用与利差、B3 权益与行业、B4 另类与流动性、
B5 交叉质询（挑战假设，输出分歧点而非继续辩论）。

本模块用确定性规则实现，便于复现与验收；
接入 LLM 时只需替换观点文字的组织方式，数值判断逻辑保持不变。
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..models import Opinion


def _macro_analyst(bundle: Dict[str, Any]) -> Opinion:
    market = bundle["market"]
    liability = bundle["liability"]
    inverted = market.curve_slope < 0
    stance = (
        "曲线小幅倒挂，长端利率相对负债成本仍有配置价值，倾向拉长久期"
        if inverted
        else "曲线陡峭，长端溢价较高，可继续拉长久期"
    )
    return Opinion(
        agent_id="B1",
        topic="宏观与利率",
        stance=stance,
        direction="加久期",
        evidence="10 年利率 {:.2f}%，期限利差 {:+.2f}%，负债久期 {:.1f} 年".format(
            market.curve_10y, market.curve_slope, liability.duration
        ),
        confidence="中",
        invalid_if="若通胀反弹或供给冲击推动长端上行超过 {}bp".format(market.rate_shock_bp),
    )


def _credit_analyst(bundle: Dict[str, Any]) -> Opinion:
    market = bundle["market"]
    narrow = market.spread_percentile < 30
    wide = market.spread_percentile > 70
    if narrow:
        stance = "信用利差处于历史偏低分位，性价比不足，不宜追加信用敞口"
        direction = "减信用"
    elif wide:
        stance = "信用利差处于历史偏高分位，可择机增配高评级信用"
        direction = "加信用"
    else:
        stance = "信用利差居中，维持现有信用敞口"
        direction = "维持"
    return Opinion(
        agent_id="B2",
        topic="信用与利差",
        stance=stance,
        direction=direction,
        evidence="信用利差 {:.2f}%，历史分位 {}%".format(
            market.credit_spread_pct, market.spread_percentile
        ),
        confidence="中",
        invalid_if="若出现超预期违约事件导致利差快速走阔，则转为防御",
    )


def _equity_analyst(bundle: Dict[str, Any]) -> Opinion:
    market = bundle["market"]
    constraints = bundle["constraints"]
    holdings = bundle["holdings"]
    equity_weight = sum(item.weight for item in holdings if item.asset_class == "equity")
    at_cap = equity_weight >= constraints.equity_cap_pct / 100 - 1e-9
    spread = market.equity_dividend_yield - market.curve_10y
    if spread > 0 and at_cap:
        stance = "股息率高于国债，相对吸引力仍在，但权益已达内部上限，只能做结构调整"
        direction = "维持"
    elif spread > 0:
        stance = "股息率高于国债，可适度增加高股息权益"
        direction = "加权益"
    else:
        stance = "股息率低于国债，权益吸引力有限"
        direction = "减权益"
    return Opinion(
        agent_id="B3",
        topic="权益与行业",
        stance=stance,
        direction=direction,
        evidence="股息率 {:.2f}%，与 10 年国债利差 {:+.2f}%，当前权益仓位 {:.1f}%".format(
            market.equity_dividend_yield, spread, equity_weight * 100
        ),
        confidence="中",
        invalid_if="若权益回撤超过 20% 或盈利预期大幅下调，则重新评估仓位",
    )


def _alternative_analyst(bundle: Dict[str, Any]) -> Opinion:
    holdings = bundle["holdings"]
    constraints = bundle["constraints"]
    cash_weight = sum(item.weight for item in holdings if item.asset_class == "cash")
    alternative_weight = sum(item.weight for item in holdings if item.asset_class == "alternative")
    illiquid_days = max(
        [item.liquidity_days for item in holdings if item.asset_class == "alternative"] or [0]
    )
    if cash_weight >= constraints.min_liquidity_pct / 100:
        stance = "流动性缓冲高于下限，可择机配置另类资产，但需控制变现周期"
        direction = "保留流动性"
    else:
        stance = "流动性低于下限，当期不再增加低流动性资产"
        direction = "保留流动性"
    return Opinion(
        agent_id="B4",
        topic="另类与流动性",
        stance=stance,
        direction=direction,
        evidence="现金类 {:.1f}%，另类 {:.1f}%，最长变现周期 {} 天".format(
            cash_weight * 100, alternative_weight * 100, illiquid_days
        ),
        confidence="高",
        invalid_if="若出现集中赔付或退保导致现金流缺口，则优先恢复流动性",
    )


CONFLICT_RULES = (
    ("加久期", "保留流动性", "拉长久期需要动用流动性，需明确当期调仓规模上限"),
    ("加权益", "维持", "权益观点与仓位上限约束存在冲突，只能通过结构调整实现"),
    ("加信用", "减信用", "信用敞口方向相反，需以利差分位与内部评级为准"),
)


def _challenger(opinions: List[Opinion]) -> Dict[str, Any]:
    disagreements = []
    directions = {item.direction: item for item in opinions}
    for left, right, impact in CONFLICT_RULES:
        if left in directions and right in directions:
            disagreements.append(
                {
                    "issue": "{} 与 {}".format(left, right),
                    "side_a": "{}（{}）".format(directions[left].agent_id, directions[left].stance),
                    "side_b": "{}（{}）".format(directions[right].agent_id, directions[right].stance),
                    "impact": impact,
                }
            )
    low_confidence = [item.agent_id for item in opinions if item.confidence == "低"]
    return {
        "rounds": 3,
        "disagreements": disagreements,
        "low_confidence": low_confidence,
    }


def run(bundle: Dict[str, Any]) -> Dict[str, Any]:
    opinions = [
        _macro_analyst(bundle),
        _credit_analyst(bundle),
        _equity_analyst(bundle),
        _alternative_analyst(bundle),
    ]
    return {
        "opinions": opinions,
        "challenge": _challenger(opinions),
    }
