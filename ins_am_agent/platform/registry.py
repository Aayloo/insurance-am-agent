"""L0 平台底座：组件注册表。

流水线里的每一步都按 ``kind.name`` 寻址，而不是被直接 import。这样
「加一个研究员」「换一个求解器」「加一条闸门规则」都只需要注册 + 改配置，
不需要动编排代码——这正是平台与脚本的分界。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class RegistryError(KeyError):
    """找不到组件，或重复注册。"""


class Registry:
    """按类别（kind）组织的组件表。"""

    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Callable[..., Any]]] = {}

    def register(
        self, kind: str, name: str, fn: Callable[..., Any], *, replace: bool = False
    ) -> Callable[..., Any]:
        bucket = self._items.setdefault(kind, {})
        if name in bucket and not replace:
            raise RegistryError("组件已存在：{}.{}（如需覆盖请传 replace=True）".format(kind, name))
        bucket[name] = fn
        return fn

    def resolve(self, kind: str, name: str) -> Callable[..., Any]:
        bucket = self._items.get(kind)
        if not bucket or name not in bucket:
            available = ", ".join(sorted(bucket)) if bucket else "（该类暂无组件）"
            raise RegistryError(
                "未知组件：{}.{}；该类可用组件：{}".format(kind, name, available)
            )
        return bucket[name]

    def names(self, kind: str) -> List[str]:
        return sorted(self._items.get(kind, {}))

    def describe(self) -> Dict[str, List[str]]:
        return {kind: sorted(bucket) for kind, bucket in sorted(self._items.items())}


_DEFAULT: Optional[Registry] = None


def default_registry() -> Registry:
    """内置组件注册表；惰性构建以避免循环导入。"""
    global _DEFAULT
    if _DEFAULT is None:
        from .stages import register_builtin_stages

        registry = Registry()
        register_builtin_stages(registry)
        _DEFAULT = registry
    return _DEFAULT
