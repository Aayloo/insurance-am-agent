"""受支持的 YAML 子集解析器。

本项目坚持零第三方依赖，而策略文件与流水线定义需要人类可读、可写注释，
因此这里实现一个**严格**的 YAML 子集解析器：只接受下列语法，遇到任何
不支持的写法直接报错（fail closed），不做静默降级。

支持：
  - 注释（#，可整行也可行尾）与空行
  - 以空格缩进表示的嵌套映射
  - 映射组成的序列（- key: value）
  - 行内序列（[a, b, c]）
  - 标量：整数、浮点、布尔、null、单双引号或裸字符串

不支持（遇到即抛 MiniYamlError）：
  - 制表符缩进
  - 锚点与别名（& / *）
  - 多行标量（| / >）
  - 行内映射（{}）
  - 文档分隔符（---）

接入 PyYAML 的项目可以直接换成 yaml.safe_load；本模块的存在只是为了让
「零依赖」这个卖点成立。
"""

from __future__ import annotations

from typing import Any, List, Tuple


class MiniYamlError(ValueError):
    """解析失败：带上行号，便于定位策略文件里的写法问题。"""


_Line = Tuple[int, str, int]  # (indent, text, lineno)


def _strip_comment(raw: str) -> str:
    quote = ""
    for index, char in enumerate(raw):
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            continue
        if char == "#" and (index == 0 or raw[index - 1] in " \t"):
            return raw[:index]
    return raw


def _is_mapping_entry(text: str) -> bool:
    """判断一段文本是否形如 key: 或 key: value。"""
    head, sep, _rest = text.partition(":")
    if not sep:
        return False
    if not head or head != head.strip():
        return False
    if any(char in head for char in "[]{}\"'"):
        return False
    return True


def _split_flow(body: str) -> List[str]:
    parts: List[str] = []
    depth = 0
    quote = ""
    current = ""
    for char in body:
        if quote:
            current += char
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            current += char
            continue
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def _scalar(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    if text.startswith("&") or text.startswith("*"):
        raise MiniYamlError("不支持锚点与别名（& / *）")
    if text.startswith("{"):
        raise MiniYamlError("不支持行内映射（{}）写法")
    if text.startswith("[") and text.endswith("]"):
        body = text[1:-1].strip()
        if not body:
            return []
        return [_scalar(part) for part in _split_flow(body)]
    if text.startswith('"') or text.startswith("'"):
        if len(text) < 2 or text[-1] != text[0]:
            raise MiniYamlError("引号未闭合：{}".format(text))
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("null", "~"):
        return None
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _tokenize(text: str) -> List[_Line]:
    lines: List[_Line] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        leading = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise MiniYamlError("第 {} 行：不支持制表符缩进，请改用空格".format(lineno))
        if raw.lstrip().startswith("---"):
            raise MiniYamlError("第 {} 行：不支持文档分隔符（---）".format(lineno))
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        body = stripped.strip()
        if body.startswith("&") or body.startswith("*"):
            raise MiniYamlError("第 {} 行：不支持锚点与别名".format(lineno))
        if body in ("|", ">") or body.startswith("| ") or body.startswith("> "):
            raise MiniYamlError("第 {} 行：不支持多行标量".format(lineno))
        if body.startswith("- ") and _is_mapping_entry(body[2:]):
            # 把 ‘‘- key: value’’ 拆成序列项 + 嵌套映射，后续逻辑只需处理一种形状
            lines.append((indent, "-", lineno))
            lines.append((indent + 2, body[2:].strip(), lineno))
            continue
        lines.append((indent, body, lineno))
    return lines


def _parse_block(lines: List[_Line], index: int, indent: int) -> Tuple[Any, int]:
    if index >= len(lines):
        return None, index
    if lines[index][1] == "-":
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: List[_Line], index: int, indent: int) -> Tuple[Any, int]:
    result = {}
    while index < len(lines):
        line_indent, text, lineno = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise MiniYamlError(
                "第 {} 行：缩进超出预期（{} > {}）".format(lineno, line_indent, indent)
            )
        if not _is_mapping_entry(text):
            raise MiniYamlError("第 {} 行：不是合法的键值对：{}".format(lineno, text))
        key, _sep, rest = text.partition(":")
        key = key.strip()
        if key in result:
            raise MiniYamlError("第 {} 行：键重复：{}".format(lineno, key))
        rest = rest.strip()
        if rest:
            result[key] = _scalar(rest)
            index += 1
            continue
        index += 1
        if index < len(lines) and lines[index][0] > indent:
            result[key], index = _parse_block(lines, index, lines[index][0])
        else:
            result[key] = None
    return result, index


def _parse_sequence(lines: List[_Line], index: int, indent: int) -> Tuple[Any, int]:
    items = []
    while index < len(lines):
        line_indent, text, lineno = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise MiniYamlError("第 {} 行：缩进超出预期".format(lineno))
        if text != "-" and not text.startswith("- "):
            break
        body = text[2:].strip() if text.startswith("- ") else ""
        if body:
            items.append(_scalar(body))
            index += 1
            continue
        index += 1
        if index < len(lines) and lines[index][0] > indent:
            value, index = _parse_block(lines, index, lines[index][0])
        else:
            value = None
        items.append(value)
    return items, index


def loads(text: str) -> Any:
    """解析 YAML 子集文本；失败时抛 MiniYamlError。"""
    lines = _tokenize(text)
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise MiniYamlError("第 {} 行：无法归入任何层级".format(lines[index][2]))
    return value


def load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return loads(handle.read())
