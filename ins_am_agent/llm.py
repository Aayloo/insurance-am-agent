"""可选 LLM 接口。

设计原则：数字由代码算，语言由模型组织。
本模块默认关闭；只有显式配置环境变量后才会调用外部模型，
且任何异常都会回退到确定性文本，不影响流水线运行。

    export INS_AM_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
    export INS_AM_LLM_API_KEY="..."
    export INS_AM_LLM_MODEL="gpt-5"
"""

from __future__ import annotations

import json
import os
import urllib.request

ENDPOINT_ENV = "INS_AM_LLM_ENDPOINT"
API_KEY_ENV = "INS_AM_LLM_API_KEY"
MODEL_ENV = "INS_AM_LLM_MODEL"

SYSTEM_PROMPT = (
    "你是保险资管投研助手。只允许基于给定的事实与数字组织语言，"
    "不得引入任何新数字，不得给出下单指令。输出中文，语气克制。"
)


def is_enabled() -> bool:
    return bool(os.environ.get(ENDPOINT_ENV) and os.environ.get(API_KEY_ENV))


def polish(text: str, instruction: str = "压缩为三句话，保留所有数字") -> str:
    """可选：对确定性生成的文字做润色；未配置或失败时原样返回。"""
    if not is_enabled() or not text.strip():
        return text
    endpoint = os.environ[ENDPOINT_ENV]
    payload = {
        "model": os.environ.get(MODEL_ENV, "gpt-5"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction + "\n\n" + text},
        ],
        "temperature": 0,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(os.environ[API_KEY_ENV]),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return text
