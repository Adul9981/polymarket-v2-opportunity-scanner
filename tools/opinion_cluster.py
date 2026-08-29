#!/usr/bin/env python3
"""弹幕意见聚类与归因（2026-08-26 用户定稿，情报加工层）。

把"表述不同但意见相同"的弹幕合并成意见簇，做归因，输出结论性内容。
只归纳给定样本，禁止编造；条数 = 该意见在样本中命中数；理由带时间锚点。

用法：
  python3 tools/opinion_cluster.py --match lol-drxc-foxy-2026-08-25 \
      --input <slice.jsonl> --teams "Kiwoom DRX Challengers,BNK FearX Youth" \
      [--out opinion_clusters.json] [--even]

--even：全窗口均匀采样（长窗口/整场复盘用，避免只取前 N 条导致结论偏向前期；
  教训 2026-08-26：整场 10,952 条弹幕只取前 500 条，结论停在系列前期与赛果矛盾）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path


def deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        cfg = Path.home() / ".codex" / "config.toml"
        if cfg.exists():
            m = re.search(
                r'experimental_bearer_token\s*=\s*"([^"]+)"',
                cfg.read_text(encoding="utf-8"),
            )
            if m:
                return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return ""


def load_samples(path: Path, cap: int = 500, even: bool = False) -> list[dict]:
    """读取切片并清洗/去重/采样（去 emote/URL）。

    even=False：取前 cap 条；even=True：全量去重后按时间均匀取 cap 条。
    """
    seen: set[str] = set()
    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = str(r.get("text") or r.get("message") or "")
                t = re.sub(r"\[emote:[^\]]*\]", "", text)
                t = re.sub(r"https?://\S+", "", t)
                t = re.sub(r"\s+", " ", t).strip()
                if len(t) < 3 or t in seen:
                    continue
                seen.add(t)
                ts = r.get("unixtime") or r.get("ts") or ""
                rows.append({"t": t[:120], "ts": ts})
    except OSError:
        pass
    if not even or len(rows) <= cap:
        return rows[:cap]
    rows.sort(key=lambda r: str(r.get("ts") or ""))
    step = len(rows) / cap
    return [rows[int(i * step)] for i in range(cap)]


def call_llm(prompt: str) -> dict:
    key = deepseek_key()
    if not key:
        raise RuntimeError("no deepseek key")
    body = json.dumps(
        {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电竞弹幕意见聚类分析师。把弹幕样本中'表述不同但对象+立场相同'的"
                        "意见合并成簇，做归因，输出结论。规则：只归纳给定样本，禁止编造弹幕/计数；"
                        "条数=该意见在样本中的命中数（可小于等于样本数）；理由必须来自样本内容并带"
                        "时间锚点；反讽/玩梗不算正向意见；输出 JSON。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 3200,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    content = r["choices"][0]["message"]["content"]
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 容错：取首个 { 到最后一个 } 之间的内容
        i, j = content.find("{"), content.rfind("}")
        if i >= 0 and j > i:
            return json.loads(content[i:j + 1])
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--teams", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--even", action="store_true", help="全窗口均匀采样（整场复盘用）")
    args = ap.parse_args()

    samples = load_samples(Path(args.input), even=args.even)
    if not samples:
        print(json.dumps({"clusters": [], "conclusion": "样本不足（无有效弹幕）"}, ensure_ascii=False, indent=2))
        return 0
    def fmt_ts(ts) -> str:
        try:
            return time.strftime("%H:%M", time.gmtime(float(ts)))
        except (ValueError, TypeError):
            return str(ts)

    sample_lines = "\n".join(f"- [{fmt_ts(s['ts'])}] {s['t']}" for s in samples[:400])
    prompt = (
        f"比赛：{args.match}（{args.teams or '未知对阵'}）\n"
        f"弹幕样本（{len(samples[:400])} 条，时间戳为 UTC HH:MM）：\n{sample_lines}\n\n"
        f"请输出 JSON：{{\"clusters\": [{{\"object\": \"队伍/选手/BP/盘口/局势\", "
        f"\"stance\": \"看好|看衰|质疑|中性\", \"count\": 命中数, "
        f"\"window_utc\": [\"起\",\"止\"], "
        f"\"reasons\": [{{\"cause\": \"归因\", \"hits\": 次数, \"anchors\": [\"HH:MM\"]}}], "
        f"\"samples\": [\"≤3 条代表样本\"]}}], "
        f"\"conclusion\": \"一句话情报含义（弹幕口径）\"}}。"
        f"输出约束（必须遵守）：cluster 数量 ≤6；每个 cluster 的 samples ≤2 条、"
        f"reasons ≤3 条、每个 reason 的 anchors ≤3 个；总输出 ≤700 字；"
        f"只输出 JSON，不要任何额外说明或代码块。"
    )
    try:
        result = call_llm(prompt)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": f"聚类失败: {e}"}, ensure_ascii=False))
        return 1
    result.setdefault("clusters", [])
    result.setdefault("conclusion", "")
    for c in result["clusters"]:
        c["samples"] = (c.get("samples") or [])[:3]
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
