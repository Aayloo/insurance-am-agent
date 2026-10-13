"""L2 约束与政策：政策对象。

一次运行里，约束只应有**一个**来源：政策文件。``Policy`` 把约束值、每条闸门
规则的归属与处置方式、治理口径（谁签批、谁下单）冻结成一个不可变对象，
并带上文件指纹——审计时能证明「这一期用的是哪一版政策」。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..models import Constraints

STATUS_PASS = "通过"
STATUS_NOTICE = "提示"
STATUS_DOWNSIZE = "降规模"
STATUS_ESCALATE = "升级审批"
STATUS_REJECT = "否决"

VALID_STATUSES = (STATUS_PASS, STATUS_NOTICE, STATUS_DOWNSIZE, STATUS_ESCALATE, STATUS_REJECT)


@dataclass(frozen=True)
class PolicyRule:
    """一条闸门规则的政策元数据（不含计算逻辑）。"""

    key: str
    label: str = ""
    owner: str = ""
    on_breach: str = ""
    limit: str = ""
    source: str = ""


@dataclass(frozen=True)
class Policy:
    constraints: Constraints
    rules: Dict[str, PolicyRule] = field(default_factory=dict)
    governance: Dict[str, str] = field(default_factory=dict)
    effective_date: str = ""
    applies_to: str = ""
    source_note: str = ""
    path: str = ""
    fingerprint: str = ""

    def rule(self, key: str) -> Optional[PolicyRule]:
        return self.rules.get(key)

    def owner_of(self, key: str, default: str = "") -> str:
        rule = self.rules.get(key)
        return rule.owner if rule and rule.owner else default

    def on_breach_of(self, key: str, default: str = "") -> str:
        rule = self.rules.get(key)
        return rule.on_breach if rule and rule.on_breach else default

    def governance_of(self, key: str, default: str = "") -> str:
        return self.governance.get(key, default)
