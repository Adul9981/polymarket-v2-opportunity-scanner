#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大模型直连客户端（极简架构 · 固定提示词 + 数据 -> 结论）。

2026-08-30 用户定稿（朋友建议落地）：不依赖服务器上的 Codex agent，
项目内直接调 DeepSeek API；固定提示词见 prompts/intel_full.md。
"""

import json
import os
import re
import urllib.request
from pathlib import Path

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def deepseek_key() -> str:
    """从环境变量或 Codex 配置读取 DeepSeek API key（与 speedcard 同源）。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    cfg = Path.home() / ".codex" / "config.toml"
    if cfg.exists():
        try:
            m = re.search(
                r'experimental_bearer_token\s*=\s*"([^"]+)"',
                cfg.read_text(encoding="utf-8"),
            )
            if m:
                return m.group(1)
        except OSError:
            pass
    return ""


def chat(
    system: str,
    user: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 4000,
    json_mode: bool = True,
) -> str | None:
    """直连 DeepSeek：system（固定提示词）+ user（当次数据）-> 返回文本/JSON 字符串。

    失败（密钥无效/网络/超时）返回 None，调用方降级（不阻塞发布）。
    """
    key = deepseek_key()
    if not key:
        print("[llm_client] 无 DeepSeek key（config.toml / DEEPSEEK_API_KEY）", flush=True)
        return None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        print(f"[llm_client] API 调用失败: {e}", flush=True)
        return None


def parse_json(text: str | None) -> dict | None:
    """解析 LLM 返回（容忍 ```json 包裹或首尾空白）。"""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        d = json.loads(t)
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        # 尝试截取第一个 { 到最后一个 }
        try:
            s, e = t.index("{"), t.rindex("}")
            d = json.loads(t[s:e + 1])
            return d if isinstance(d, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None


if __name__ == "__main__":
    import sys
    sys = sys  # noqa: PLW0127
    r = chat("你是测试助手", "回复 OK 两个字母", json_mode=False)
    print("RESULT:", r)
