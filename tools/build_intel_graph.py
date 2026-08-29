#!/usr/bin/env python3
"""构建弹幕情报库关系图谱（graph.json）：从各实体文件推导关联边。

节点类型：league/team/player/champion/composition/match/gray_signal/bp_signal/alias/report
边类型：contains/plays_for/in_match/anchored_by/counters/pairs_with/in_composition/uses/
        sampled_in/at_match/refers_to/official_result/report

用法：python3 tools/build_intel_graph.py
输出：docs/data/intel/graph.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"


def load(name: str) -> dict:
    return json.loads((INTEL / name).read_text(encoding="utf-8"))


def main() -> int:
    matches = load("matches.json")["matches"]
    teams = load("teams.json")["teams"]
    players = load("players.json")["players"]
    leagues = load("leagues.json")["leagues"]
    champions = load("champions.json")["champions"]
    comps = load("compositions.json")["compositions"]
    gray = load("gray_signals.json")["records"]
    bp = load("bp_signals.json")["records"]
    aliases = load("aliases.json")["aliases"]
    official = json.loads((INTEL / "official" / "official_matches.json").read_text(encoding="utf-8"))["matches"]

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid: str, ntype: str, label: str, sub: str = "") -> None:
        nodes.setdefault(nid, {"id": nid, "type": ntype, "label": label, "sub": sub})

    def edge(f: str, t: str, etype: str) -> None:
        if f in nodes and t in nodes:
            edges.append({"from": f, "to": t, "type": etype})

    for l in leagues:
        node(l["id"], "league", l.get("name", l["id"]), l.get("gray_risk", ""))
    for t in teams:
        node(t["id"], "team", t.get("name", t["id"]), (t.get("danmu") or {}).get("tone", ""))
        if t.get("league"):
            # 联赛 id 可能带空格/大小写差异，尽力匹配
            lid = str(t["league"]).lower().replace(" ", "_")
            if lid in nodes:
                edge(lid, t["id"], "contains")
    for p in players:
        node(p["id"], "player", p.get("name") or p["id"], f"{p.get('role','?')} · {p.get('team','?')}")
        if p.get("team"):
            tid = str(p["team"]).split("(")[0].strip().lower().replace(" ", "_")
            if tid in nodes:
                edge(p["id"], tid, "plays_for")
    for c in champions:
        node(c["id"], "champion", c.get("name", c["id"]), " / ".join(c.get("roles", [])))
        for a in c.get("anchors", []):
            if a.get("player_id") and a["player_id"] in nodes:
                edge(c["id"], a["player_id"], "anchored_by")
            elif a.get("team") and a["team"] in nodes:
                edge(c["id"], a["team"], "anchored_by")
            if a.get("match_id") and a["match_id"] in nodes:
                edge(c["id"], a["match_id"], "at_match")
        for k in c.get("counters", []):
            if k.get("vs") in nodes:
                edge(c["id"], k["vs"], "counters")
        for p in c.get("pairing", []) + c.get("pairing_needs", []):
            for w in str(p.get("with", "")).split("|"):
                w = w.strip()
                if w in nodes:
                    edge(c["id"], w, "pairs_with")
        for tf in c.get("team_fit", []):
            if tf.get("team_id") in nodes:
                edge(tf["team_id"], c["id"], "uses")
    for co in comps:
        node(co["id"], "composition", co.get("name", co["id"]), " / ".join(co.get("type", [])))
        for ch in co.get("core", []):
            if ch in nodes:
                edge(ch, co["id"], "in_composition")
        for t in co.get("teams", []):
            if t.get("team_id") in nodes:
                edge(t["team_id"], co["id"], "uses")
        for s in co.get("samples", []):
            if s.get("match_id") in nodes:
                edge(co["id"], s["match_id"], "sampled_in")
    for m in matches:
        node(m["id"], "match", m.get("id", ""), (m.get("result_inferred") or "")[:60])
        for t in m.get("teams", []):
            tid = str(t).lower()
            if tid in nodes:
                edge(tid, m["id"], "in_match")
        for r in (m.get("data") or {}).get("reports", []) or m.get("reports", []):
            rid = r.replace("reports/", "").replace(".html", "")
            node(rid, "report", r, m.get("id", ""))
            edge(m["id"], rid, "report")
    for g in gray:
        node(g["id"], "gray_signal", g.get("match", g["id"]), f"{g.get('severity','')} · {g.get('count','')} 条")
        mid = g.get("match_id") or g.get("id", "")
        if mid in nodes and mid != g["id"]:
            edge(mid, g["id"], "at_match")
    for b in bp:
        node(b["id"], "bp_signal", b.get("match", b["id"]), (b.get("bp_point") or "")[:50])
        mid = b.get("match_id") or ""
        if mid in nodes and mid != b["id"]:
            edge(b["match_id"], b["id"], "at_match")
    for a in aliases:
        if a.get("official"):
            node("alias_" + a["alias"], "alias", a["alias"], f"→ {a['official']} · {a.get('confidence','')}")
            edge("alias_" + a["alias"], a["official"], "refers_to")
    for o in official:
        mid = o.get("match_id", "")
        if mid in nodes:
            node("official_" + mid, "official", mid, (o.get("result") or "")[:50])
            edge(mid, "official_" + mid, "official_result")

    graph = {
        "schema_version": "1.0",
        "description": "弹幕情报库关系图谱（自动生成，勿手改）",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    (INTEL / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
