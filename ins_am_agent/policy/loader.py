"""L2 约束与政策：装载器。

政策文件（``config/constraints.yaml``）是约束的**唯一来源**：数据文件只放数据，
代码只读政策对象。任何字段缺失或取值非法都在装载阶段报错（fail closed），
不允许默默用默认值兜底——限额这种东西，静默兜底比报错危险得多。
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping, Optional

from ..models import Constraints
from ..platform.miniyaml import MiniYamlError, load as load_yaml
from .model import VALID_STATUSES, Policy, PolicyRule

REQUIRED_CONSTRAINT_FIELDS = (
    "equity_cap_pct",
    "alternative_cap_pct",
    "single_issuer_cap_pct",
    "min_liquidity_pct",
    "duration_tolerance_years",
    "max_turnover_pct",
)

# 闸门规则键：D 层按这些键取「归属」与「触限处置」，不再硬编码
KNOWN_RULE_KEYS = (
    "equity_cap",
    "alternative_cap",
    "single_issuer_cap",
    "liquidity_floor",
    "duration_gap",
    "turnover_cap",
    "yield_over_cost",
)


class PolicyError(ValueError):
    """政策文件缺失、结构错误或取值非法。"""


def _as_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError("{} 必须是映射结构".format(where))
    return value


def _as_float(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError("{} 必须是数字，当前为 {!r}".format(where, value))
    return float(value)


def _build_constraints(document: Mapping[str, Any]) -> Constraints:
    node = _as_mapping(document.get("constraints"), "constraints")
    missing = [field for field in REQUIRED_CONSTRAINT_FIELDS if field not in node]
    if missing:
        raise PolicyError("constraints 缺少字段：{}".format("、".join(missing)))
    return Constraints(
        equity_cap_pct=_as_float(node["equity_cap_pct"], "constraints.equity_cap_pct"),
        alternative_cap_pct=_as_float(
            node["alternative_cap_pct"], "constraints.alternative_cap_pct"
        ),
        single_issuer_cap_pct=_as_float(
            node["single_issuer_cap_pct"], "constraints.single_issuer_cap_pct"
        ),
        min_liquidity_pct=_as_float(node["min_liquidity_pct"], "constraints.min_liquidity_pct"),
        duration_tolerance_years=_as_float(
            node["duration_tolerance_years"], "constraints.duration_tolerance_years"
        ),
        max_turnover_pct=_as_float(node["max_turnover_pct"], "constraints.max_turnover_pct"),
    )


def _build_rules(document: Mapping[str, Any]) -> Dict[str, PolicyRule]:
    node = document.get("rules") or {}
    node = _as_mapping(node, "rules")
    unknown = [key for key in node if key not in KNOWN_RULE_KEYS]
    if unknown:
        raise PolicyError(
            "rules 包含未知规则：{}；已知规则：{}".format(
                "、".join(unknown), "、".join(KNOWN_RULE_KEYS)
            )
        )
    rules: Dict[str, PolicyRule] = {}
    for key, raw in node.items():
        entry = _as_mapping(raw, "rules.{}".format(key))
        on_breach = str(entry.get("on_breach", "") or "")
        if on_breach and on_breach not in VALID_STATUSES:
            raise PolicyError(
                "rules.{}.on_breach 必须是 {} 之一，当前为 {!r}".format(
                    key, "、".join(VALID_STATUSES), on_breach
                )
            )
        rules[key] = PolicyRule(
            key=key,
            label=str(entry.get("label", "") or ""),
            owner=str(entry.get("owner", "") or ""),
            on_breach=on_breach,
            limit=str(entry.get("limit", "") or ""),
            source=str(entry.get("source", "") or ""),
        )
    return rules


def _fingerprint(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:12]


def load_policy(path: str, document: Optional[Mapping[str, Any]] = None) -> Policy:
    """装载政策文件；缺少生效期或约束字段直接报错。"""
    fingerprint = ""
    if document is None:
        try:
            loaded = load_yaml(str(path))
        except MiniYamlError as error:
            raise PolicyError("政策文件解析失败：{}".format(error)) from None
        except FileNotFoundError:
            raise PolicyError("找不到政策文件：{}".format(path)) from None
        document = _as_mapping(loaded, "政策文件根节点")
        fingerprint = _fingerprint(str(path))

    effective_date = str(document.get("effective_date", "") or "")
    if not effective_date:
        raise PolicyError("政策文件必须写明 effective_date（约束从哪一天起生效）")

    governance_node = _as_mapping(document.get("governance") or {}, "governance")
    governance = {str(key): str(value) for key, value in governance_node.items()}

    return Policy(
        constraints=_build_constraints(document),
        rules=_build_rules(document),
        governance=governance,
        effective_date=effective_date,
        applies_to=str(document.get("applies_to", "") or ""),
        source_note=str(document.get("source", "") or ""),
        path=str(path),
        fingerprint=fingerprint,
    )
