"""L0 平台底座：配置驱动的流水线执行器。

流水线定义（``pipeline.yaml``）说明「跑哪些阶段、按什么顺序、用哪个组件」；
本模块只负责解析、校验、按顺序调用注册表里的组件，不含任何业务判断。

阶段契约：``fn(ctx, **params) -> Any``，返回值写入 ``ctx[stage.id]``。
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Mapping, Optional, Union

from .miniyaml import load as load_yaml
from .registry import Registry, RegistryError, default_registry

_VAR_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")


class PipelineError(ValueError):
    """流水线定义不合法，或阶段执行失败。"""


def load_pipeline(path: Union[str, os.PathLike]) -> Dict[str, Any]:
    """读取并校验流水线定义。任何结构问题都会在这里抛出，而不是留到执行时。"""
    spec = load_yaml(str(path))
    if not isinstance(spec, dict):
        raise PipelineError("流水线定义必须是映射（key: value）结构")

    raw_stages = spec.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise PipelineError("流水线必须包含至少一个阶段（stages）")

    stages: List[Dict[str, Any]] = []
    seen = set()
    for position, stage in enumerate(raw_stages, 1):
        if not isinstance(stage, dict):
            raise PipelineError("第 {} 个阶段必须是映射".format(position))
        stage_id = stage.get("id")
        uses = stage.get("uses")
        if not stage_id or not uses:
            raise PipelineError("第 {} 个阶段缺少 id 或 uses".format(position))
        if stage_id in seen:
            raise PipelineError("阶段 id 重复：{}".format(stage_id))
        seen.add(stage_id)
        kind, _dot, name = str(uses).partition(".")
        if not kind or not name:
            raise PipelineError("阶段 {} 的 uses 必须形如 kind.name：{}".format(stage_id, uses))
        params = stage.get("with") or {}
        if not isinstance(params, dict):
            raise PipelineError("阶段 {} 的 with 必须是映射".format(stage_id))
        stages.append({"id": stage_id, "kind": kind, "name": name, "params": params})

    variables = spec.get("vars") or {}
    if not isinstance(variables, dict):
        raise PipelineError("vars 必须是映射")

    return {
        "version": spec.get("version", 1),
        "name": spec.get("name", ""),
        "vars": variables,
        "stages": stages,
        "path": str(path),
    }


def _resolve_variables(value: Any, variables: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        whole = _VAR_PATTERN.fullmatch(value)
        if whole:
            key = whole.group(1)
            if key not in variables:
                raise PipelineError("未定义的变量：{}".format(key))
            return variables[key]

        def replace(match: "re.Match[str]") -> str:
            key = match.group(1)
            if key not in variables:
                raise PipelineError("未定义的变量：{}".format(key))
            return str(variables[key])

        return _VAR_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_resolve_variables(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_variables(item, variables) for key, item in value.items()}
    return value


def run_pipeline(
    spec: Union[str, os.PathLike, Dict[str, Any]],
    registry: Optional[Registry] = None,
    variables: Optional[Mapping[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """按定义执行流水线，返回阶段上下文。"""
    if isinstance(spec, (str, os.PathLike)):
        pipeline = load_pipeline(spec)
    else:
        pipeline = spec

    active_registry = registry or default_registry()
    merged_variables: Dict[str, Any] = dict(pipeline.get("vars") or {})
    merged_variables.update(variables or {})
    ctx: Dict[str, Any] = dict(context or {})

    executed: List[str] = []
    for stage in pipeline["stages"]:
        try:
            stage_fn = active_registry.resolve(stage["kind"], stage["name"])
        except RegistryError as error:
            raise PipelineError("阶段 {}：{}".format(stage["id"], error)) from None
        params = _resolve_variables(stage["params"], merged_variables)
        try:
            ctx[stage["id"]] = stage_fn(ctx, **params)
        except TypeError as error:
            raise PipelineError(
                "阶段 {}（{}.{}）参数不匹配：{}".format(
                    stage["id"], stage["kind"], stage["name"], error
                )
            ) from None
        executed.append(stage["id"])

    ctx["_pipeline"] = {
        "name": pipeline.get("name", ""),
        "path": pipeline.get("path", ""),
        "version": pipeline.get("version", 1),
        "executed": executed,
    }
    return ctx
