#!/usr/bin/env python3
"""Extract trade-relevant intel from Huya danmaku JSONL.

Reads ts/nick/text JSONL (from tools/fetch_huya_danmu.py) and outputs a
structured intel JSON + Chinese summary covering:
  - teams / players sentiment (pos/neg counts + samples)
  - odds & numbers discussion (让分/人头/盘口 digits)
  - match situation clues (score, resources, comeback talk)
  - gray signals (直播间灰话：接单/假赛/买 etc., flagged as risk only)
  - danmaku density bursts (high-activity minutes = likely key game moments;
    trade-relevant: correlated with price moves)

Usage:
  python3 tools/danmu_intel.py --input docs/data/danmu/shuoshuo/2026-08-17_323444.jsonl \
      --out runtime/danmu_intel.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


TEAMS = {
    "KC": ["kc", "karmine"],
    "GX": ["gx", "giantx"],
    "TH": ["th", "heratics"],
    "Navi": ["navi", "natus"],
    "T1": ["t1"],
    "DK": ["dk", "dplus", "damwon", "dwg"],
    "DNS": ["dns", "dnsoop"],
    "KT": ["kt"],
    "HLE": ["hle", "hanwha"],
    "GEN": ["gen", "geng"],
    "WBG": ["wbg", "微博"],
    "LNG": ["lng", "李宁"],
    "WE": ["we", "西安we"],
    "EDG": ["edg"],
    "BLG": ["blg"],
    "TES": ["tes"],
    "IG": ["ig", "invictus"],
    # CS2 (EWC/IEM/BLAST/Major) — 2026-08-19 新增
    "Vitality": ["vitality", "小蜜蜂"],
    "Spirit": ["spirit", "绿龙"],
    "G2": ["g2"],
    "NAVI": ["navi", "natus"],
    "FaZe": ["faze", "法泽"],
    "MOUZ": ["mouz", "老鼠"],
    "Liquid": ["liquid", "液体"],
    "FURIA": ["furia", "黑豹"],
    "MongolZ": ["mongolz", "蒙古"],
    "EF": ["eternal fire", "永恒之火"],
    "Astra": ["astra"],
    "AG": ["ag"],
    "白鲨": ["白鲨"],
    "情久": ["情久"],
    "EP": ["ep"],
    # Dota2 (TI2026) — 2026-08-20 新增
    "Iron Wing": ["iron wing", "ironwing", "1w", "铁翼"],
    # Team Spirit shares an English tag with the CS2 roster; Chinese Dota2
    # audiences commonly use “雪碧”, which is unambiguous in this feed.
    "Spirit": ["spirit", "绿龙", "雪碧", "team spirit"],
}

PLAYERS = {
    "Canna": ["canna", "金东河"],
    "Oscar": ["奥斯卡", "oscar"],
    "Poby": ["poby"],
    "Hype": ["hype"],
    "Guma": ["姑妈", "guma", "gumayusi"],
    "Mithy": ["mithy"],
    "Faker": ["faker", "飞科", "老李"],
    "Chovy": ["chovy", "超威"],
    "Zeus": ["zeus", "宙斯"],
    # CS2 — 2026-08-19 新增
    "Niko": ["niko", "尼公子"],
    "Apex": ["apex", "apex"],
    "Zywoo": ["zywoo", "载物"],
    "donk": ["donk"],
    "m0NESY": ["m0nesy", "小孩哥"],
    "Twistzz": ["twistzz"],
    "ropz": ["ropz"],
    "sh1ro": ["sh1ro", "西若"],
    # Dota2 TI2026: Iron Wing vs Team Spirit
    "Pure": ["pure", "普洱"],
    "bzm": ["bzm", "泽马"],
    "33": ["33"],
    "Ari": ["ari"],
    "Whitemon": ["whitemon"],
    "Yatoro": ["yatoro", "亚托罗", "雨神"],
    "Larl": ["larl", "拉尔"],
    "Collapse": ["collapse", "崩溃哥", "崩溃"],
    "not me": ["not me", "notme"],
    "rue": ["rue"],
}

# ---- 选手 -> 队伍（供"比赛局势"胜率把选手表态折算进队伍）----
# 2026-10-19 起这只是【静态兜底】：主源是虎扑每小局首发阵容（player_teams 参数，
# 由 vps_intel_pipeline.fetch_lineup / refresh_situation / danmu_live_monitor 拉取后
# 注入 win_signal），动态优先覆盖本表；本表在阵容拉取失败/比赛未开时仍保证已知选手
# 可折算。队名用 TEAMS 规范 key（与 win_signal 的 teams 参数经 _canon_team 归一一致）。
# 未登记的选手不计入胜率（宁可漏计、不误配——防错 19）；转会/换队时同步更新并补回归。
PLAYER_TEAM = {
    # LoL（长期稳定）
    "Faker": "T1", "Guma": "T1",
    "Chovy": "GEN",
    # CS2
    "Zywoo": "Vitality", "Apex": "Vitality",
    "donk": "Spirit",
    # Dota2（Spirit 三核）
    "Yatoro": "Spirit", "Larl": "Spirit", "Collapse": "Spirit",
}

# 每个实体所属的游戏（跨游戏共享的实体标多个）。analyze() 按 game 过滤实体词表，
# 避免 Dota2 选手 "33" 在 LoL 弹幕里误命中 "33分钟"、LoL 的 Faker 漏进 CS2 等跨游戏泄漏。
GAMES = ("lol", "cs2", "dota2")
ENTITY_GAMES: dict[str, set[str]] = {
    # LoL 战队
    "KC": {"lol"}, "GX": {"lol"}, "TH": {"lol"}, "Navi": {"lol"}, "T1": {"lol"},
    "DK": {"lol"}, "DNS": {"lol"}, "KT": {"lol"}, "HLE": {"lol"}, "GEN": {"lol"}, "WBG": {"lol"},
    "LNG": {"lol"}, "WE": {"lol"}, "EDG": {"lol"}, "BLG": {"lol"}, "TES": {"lol"},
    "IG": {"lol"},
    # CS2 战队
    "Vitality": {"cs2"}, "Spirit": {"cs2", "dota2"}, "G2": {"cs2"}, "NAVI": {"cs2"},
    "FaZe": {"cs2"}, "MOUZ": {"cs2"}, "Liquid": {"cs2"}, "FURIA": {"cs2"},
    "MongolZ": {"cs2"}, "EF": {"cs2"}, "Astra": {"cs2"}, "AG": {"cs2"},
    "白鲨": {"cs2"}, "情久": {"cs2"}, "EP": {"cs2"},
    # Dota2 战队
    "Iron Wing": {"dota2"},
    # LoL 选手
    "Canna": {"lol"}, "Oscar": {"lol"}, "Poby": {"lol"}, "Hype": {"lol"},
    "Guma": {"lol"}, "Mithy": {"lol"}, "Faker": {"lol"}, "Chovy": {"lol"},
    "Zeus": {"lol"},
    # CS2 选手
    "Niko": {"cs2"}, "Apex": {"cs2"}, "Zywoo": {"cs2"}, "donk": {"cs2"},
    "m0NESY": {"cs2"}, "Twistzz": {"cs2"}, "ropz": {"cs2"}, "sh1ro": {"cs2"},
    # Dota2 选手
    "Pure": {"dota2"}, "bzm": {"dota2"}, "33": {"dota2"}, "Ari": {"dota2"},
    "Whitemon": {"dota2"}, "Yatoro": {"dota2"}, "Larl": {"dota2"},
    "Collapse": {"dota2"}, "not me": {"dota2"}, "rue": {"dota2"},
}


def _match_game(name: str, game: str | None) -> bool:
    """实体 name 是否属于 game（game 未知或实体未标注时不过滤，向后兼容）。"""
    if not game or game not in GAMES:
        return True
    tags = ENTITY_GAMES.get(name)
    return tags is None or game in tags

POSITIVE = [
    "无敌", "厉害", "牛逼", "nb", "可以", "稳", "有希望", "相信", "顶",
    "强", "猛",  # 单字歧义低，配合否定反转（"不强"→负面）
    # 阶段1 扩充：补常见夸赞词，此前大量正面弹幕被判成中性
    "不错", "帅", "起飞", "爆发", "爆种", "carry", "带飞", "大腿", "mvp", "血c",
]
NEGATIVE = [
    "懦夫", "垃圾", "拉胯", "发瘟", "废物", "离谱", "被压",
    "菜", "怂",  # 单字歧义低，配合否定反转（"不菜"→正面）
    # 阶段1：单字"放/送/坑"歧义过大（"放战歌/放心/保送/龙坑"），改为整词
    "放水", "送人头", "送分", "开送", "摆烂", "演员", "混子", "太坑", "坑了",
    "不行",  # 配合"吗/？"反问（"不行吗"→中性）
]
ODDS_KW = ["人头", "让分", "盘口", "赔率", "水位", "6.5", "7.5", "48", "700", "-6.5", "+6.5"]
GRAY_KW = [
    "假赛", "剧本", "菠菜", "买了", "卡盘", "送分", "故意", "操控", "收钱", "演了", "在演",
    # 韩文（SOOP/LCK CL 主体，2026-08-26 补：G4 曾 44 条韩文灰信号规则层报 0）
    "고의", "던지노", "던짐", "던졌", "던지네", "던지고", "지령", "조작", "대리",
    # 英文（Twitch）
    "throw", "rigged", "match fix", "selling", "int",
]
SITUATION_KW = [
    "龙魂", "大龙", "小龙", "经济", "翻盘", "一波", "2-0", "1-1", "2-1",
    "比分", "听牌", "推塔", "开龙", "团战", "优势", "落后", "gg",
    # Dota2
    "肉山", "打盾", "拿盾", "买活", "高地", "守高", "破路", "超级兵", "兵线",
    "塔防", "三路", "bkb", "圣剑",
]

# ---- 胜方向词（观众口径·非结论）：用于"比赛局势"两队伍胜率 ----
# 只统计"队伍名 + 胜方向词"同时出现的弹幕；"gg/ez" 等反讽/玩梗高发词刻意排除，
# 避免英文 Twitch 反讽与 LoL 赛后礼貌性 GG 污染（防错规则 14/16/17）。
WIN_KW = [
    "赢了", "拿下", "必胜", "稳了", "稳赢", "平推", "碾压", "血洗", "零封",
    "让一追", "让二追", "晋级", "出线", "夺冠", "拿下了", "锁了",
    "win", "wins", "won", "stomp", "sweep", "free win",
]
# 注意："冠军"不用（DK冠军=头衔易误判）；"抬走"是"把X抬走=X输"，归负向。
WIN_LOSE_KW = ["输了", "寄了", "g了", "被零封", "被碾压", "被血洗", "输了呀", "抬走", "抬走了"]

# ---- 阶段4：中性弹幕抢救（供 LLM 二次判定，回收规则层漏判情绪）----
SALVAGE_LIMIT = 40  # 抢救候选上限：控制喂给 LLM 的 token 成本

# 潜在情绪线索（关键词库未覆盖的口语/黑话/程度副词），仅用于给中性弹幕排优先级，
# 不据此下情绪结论——情绪判定交给 AI 层二次判定。
SALVAGE_CUE = (
    # 口语负面/失误（NEGATIVE 未收录）
    "拉了", "下饭", "白给", "崩了", "没了", "完了", "翻车", "掉链子",
    "麻了", "裂开", "惜败", "带不动", "carry不动", "抽象",
    # 口语正面/情绪
    "666", "泪目", "泪了",
    # 程度/惊讶副词（常伴评价）
    "太", "有点", "真", "居然", "竟然", "这么", "那么",
)

# ---- deep theme analysis (detailed, opinion-oriented) ----
THEMES = {
    "比赛局势": ["2-0", "1-1", "2-1", "gg", "一波", "翻盘", "龙魂", "暂停", "结束", "零封", "速通", "拿下", "赢了", "输了", "肉山", "打盾", "拿盾", "买活", "高地", "守高", "破路", "超级兵", "兵线", "塔防", "三路", "bkb", "圣剑"],
    "队伍打法/实力": ["阵容", "打法", "保枪", "放资源", "放龙", "控龙", "运营", "强开", "打架", "送分", "首败", "碾压", "菜", "强", "怂", "懦", "无敌", "四保一", "带线", "拉扯"],
    "选手表现": ["皇子", "发条", "蛇女", "打野", "中单", "上单", "下路", "辅助", "canna", "oscar", "奥斯卡", "samd", "姑妈", "guma", "poby", "hype", "pure", "bzm", "泽马", "whitemon", "yatoro", "亚托罗", "雨神", "larl", "拉尔", "collapse", "崩溃", "not me", "rue"],
    "BP/阵容": ["bp", "ban", "pick", "选", "英雄", "体系", "counter", "克制", "一号位", "二号位", "三号位", "四号位", "五号位"],
    "盘口/数字": ["盘", "人头", "让分", "6.5", "7.5", "48", "700", "收", "赔", "水位"],
    "集体质疑": ["假赛", "剧本", "菠菜", "买了", "卡盘", "送分", "故意", "操控", "收钱"],
}

VERDICT_POS = ["强", "猛", "无敌", "厉害", "稳", "有希望", "牛逼", "nb", "可以", "顶", "好", "不错", "帅", "起飞", "爆发", "carry", "mvp", "带飞", "大腿"]
VERDICT_NEG = ["菜", "怂", "懦", "垃圾", "废物", "离谱", "不行", "假", "演", "搞", "放水", "送人头", "送分", "开送", "摆烂", "混子"]


def esc(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


# 所有实体关键词（战队+选手）的小写集合，用于剥离虎牙"Faker："挂件前缀
ALL_ENTITY_KWS = {
    str(k).lower()
    for kws in list(TEAMS.values()) + list(PLAYERS.values())
    for k in kws
}

_PREFIX_RE = re.compile(r"^\s*([A-Za-z0-9一-鿿]{1,24})[：:]\s*")


def strip_entity_prefix(text: str) -> str:
    """去掉虎牙"Faker："这类挂件/表情前缀（挂件名=实体名，并非提及）。

    例："Faker：这把安妮太菜了" → "这把安妮太菜了"（不再误判为 Faker 提及）。
    仅当冒号前缀名是已知战队/选手时才剥离；真实提及不带冒号（"faker怎么不说话了"），
    故该规则安全，不会误伤真实提及。
    """
    m = _PREFIX_RE.match(text)
    if m and m.group(1).lower() in ALL_ENTITY_KWS:
        return text[m.end():]
    return text


NEGATION = ("不是", "没有", "不太", "不算", "不", "没", "别")


def _find_keyword(text: str, kws: list[str]) -> tuple[str, int] | None:
    """返回首个命中的 (关键词, 下标)；未命中返回 None。ASCII 大小写不敏感。"""
    t = text.lower()
    for k in kws:
        i = t.find(k.lower())
        if i != -1:
            return k, i
    return None


def _is_negated(text: str, idx: int) -> bool:
    """关键词紧邻否定词前缀（"不菜"/"没送"/"别强"）→ 情绪反转。"""
    before = text[max(0, idx - 3):idx]
    return bool(before) and any(before.endswith(w) for w in NEGATION)


def sentiment(text: str) -> str | None:
    """情绪判定（阶段1：否定反转 + 反问中性 + 整词匹配）。

    - "不菜/没送" → 正面；"不强/别怂" → 负面
    - "不行吗？" → 中性（反问，非负面陈述）
    """
    neg = _find_keyword(text, NEGATIVE)
    if neg is not None:
        kw, idx = neg
        after = text[idx + len(kw):idx + len(kw) + 2]
        if any(q in after for q in ("吗", "嘛", "？", "?")):
            return None  # 反问句，不算负面
        return "pos" if _is_negated(text, idx) else "neg"
    pos = _find_keyword(text, POSITIVE)
    if pos is not None:
        kw, idx = pos
        return "neg" if _is_negated(text, idx) else "pos"
    return None


def keyword_hit(text: str, keyword: str) -> bool:
    """Avoid matching short ASCII team codes inside unrelated words."""
    lowered = text.lower()
    kw = keyword.lower()
    if kw.isascii() and kw.isalnum() and len(kw) <= 3:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", lowered))
    return kw in lowered


def _ts_value(row: dict) -> float:
    """Normalize row timestamp to epoch seconds (huya numeric ts / soop string ts+unixtime)."""
    if row.get("unixtime"):
        return float(row["unixtime"])
    ts = row.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("+0800", "+08:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def tone_label(pos: int, neg: int, mentions: int | None = None) -> str:
    """实体情绪倾向标签（阶段2：小样本置信度阈值）。

    解决"正 0 / 负 1 就判负面"这类单条噪声问题：
    - mentions < 3 → "样本不足"（不妄下结论）
    - 情绪样本 < 2 → "观望"（有提及但无明确倾向）
    - 一边倒（≥2 倍且 ≥2 条）→ "正面"/"负面"
    - 其余 → "分歧"
    """
    if mentions is not None and mentions < 3:
        return "样本不足"
    sig = pos + neg
    if sig < 3:
        return "观望"
    if pos >= 2 * neg and pos >= 3:
        return "正面"
    if neg >= 2 * pos and neg >= 3:
        return "负面"
    return "分歧"


def _narrative_tone(pos: int, neg: int) -> str:
    """叙事桶/全局情绪：中性/正面/负面/分歧（带 ±2 死区，方向敏感）。"""
    if pos + neg < 2:
        return "中性"
    net = pos - neg
    if net >= 2:
        return "正面"
    if net <= -2:
        return "负面"
    return "分歧"


def _clean_sample(text: str) -> str:
    """样本清洗：去 emote 标记/URL，压缩空白，截断（供胜率样本审计）。"""
    t = re.sub(r"\[emote:[^\]]*\]", "", text)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120]


def _canon_team(name: str) -> str | None:
    """队伍名 -> TEAMS 规范 key（abbr/全称/别名命中即返回；未登记返回 None）。"""
    nl = (name or "").strip().lower()
    if not nl:
        return None
    for canon, kws in TEAMS.items():
        if nl == canon.lower() or nl in [k.lower() for k in kws]:
            return canon
    return None


def _team_keywords(name: str) -> list[str]:
    """把一个比赛队伍名（abbr/全称）解析成弹幕匹配关键词。

    优先查 TEAMS 规范词表（对 key 或其任一关键词大小写不敏感命中即用其关键词表）；
    未登记队伍（如世界赛入围赛新队）回退到名字本身小写，保证仍能匹配。
    """
    canon = _canon_team(name)
    if canon is not None:
        return TEAMS[canon]
    nl = (name or "").strip().lower()
    return [nl] if nl else []


def _player_entry(name: str) -> tuple[str | None, list[str]]:
    """选手名 -> (PLAYERS 规范 key 或 None, 弹幕关键词表)。

    按 PLAYERS 词表反向解析：命中规范 key 或任一别名（大小写不敏感）时返回该词表
    （含昵称），否则回退到名字本身——保证虎扑首发阵容里的官方名（如 Gumayusi）
    既能匹配官方名、也能匹配弹幕昵称（姑妈/guma）。
    """
    nl = (name or "").strip().lower()
    if not nl:
        return None, []
    for pname, kws in PLAYERS.items():
        if nl == pname.lower() or nl in [k.lower() for k in kws]:
            return pname, kws
    return None, [name.strip()]


def _team_player_keywords(team: str, game: str | None, player_teams: dict[str, str]) -> list[str]:
    """本场队伍 `team` 名下所有选手的弹幕关键词（供胜率折算）。

    player_teams = {选手名: 队伍名}，由静态 PLAYER_TEAM 与虎扑每小局首发阵容动态
    合并而来（动态优先，转会/换队时覆盖静态）。仅当选手归属队伍归一后 == `team`、
    且选手属于当前 game 时返回其关键词；未登记/跨游戏的选手不折算
    （宁可漏计、不误配——防错规则 19 禁跨联赛混源）。
    """
    canon = _canon_team(team)
    if canon is None:
        return []
    out: list[str] = []
    for pname, tname in player_teams.items():
        if _canon_team(tname) != canon:
            continue
        pkey, kws = _player_entry(pname)
        if not _match_game(pkey if pkey else pname, game):
            continue
        out.extend(kws)
    return out


def _count_signal(rows: list[dict], kws: dict[str, list[str]], a: str, b: str) -> tuple[int, int, list[str], list[str]]:
    """在给定行集合上做胜负方向计数，返回 (count_a, count_b, samples_a, samples_b)。

    同一弹幕同时命中"队伍名 + 胜方向词"才计该队一次；同时提及两队 / 未提任何一队 /
    无方向词 → 不计；反讽高频词（gg/ez）已排除。某队"输了/寄了/被零封"计给另一队。
    """
    count = {a: 0, b: 0}
    samples: dict[str, list[str]] = {a: [], b: []}
    for r in rows:
        text = strip_entity_prefix(r.get("text", r.get("message", "")))
        if not text:
            continue
        t = text.lower()
        hits_a = any(keyword_hit(t, k) for k in kws[a])
        hits_b = any(keyword_hit(t, k) for k in kws[b])
        if hits_a == hits_b:  # 都命中或都未命中 -> 归属歧义，不计
            continue
        has_win = any(k in t for k in WIN_KW)
        has_lose = any(k in t for k in WIN_LOSE_KW)
        if has_lose and has_win:
            # "被零封/被碾压/被血洗"含"零封/碾压/血洗"：负向更具体，优先判负
            has_win = False
        if has_win == has_lose:  # 都无方向 -> 不计
            continue
        side = a if hits_a else b  # 被提及的队伍
        if has_win:
            counted = side
        else:  # 某队"输了/寄了/被零封" -> 记给另一队
            counted = b if hits_a else a
        count[counted] += 1
        if len(samples[counted]) < 8:
            s = _clean_sample(text)
            if s:
                samples[counted].append(s)
    return count[a], count[b], samples[a], samples[b]


def win_signal(
    rows: list[dict],
    teams: list[str],
    threshold: int = 10,
    game: str | None = None,
    player_teams: dict[str, str] | None = None,
    window_seconds: int | None = 300,
) -> dict | None:
    """显式胜负弹幕计数 → 两队伍胜率（观众口径·非结论）。

    规则（防错 14/16/17）：同一弹幕同时命中"队伍名 + 胜方向词"才计该队一次；
    同时提及两队、或未提及任何一队、或无方向词 → 不计；反讽高频词（gg/ez）已排除。
    选手提名也折算进其所属队伍：player_teams 为静态 PLAYER_TEAM 与虎扑每小局首发
    阵容的动态合并（动态优先），跨游戏选手（game 过滤）不折算。

    近窗口口径（2026-10-19 定稿，防"前期优势累积盖过末段被翻盘"）：
    window_seconds>0 时只统计「最新窗口秒内」的胜负弹幕（反转立即反映）；
    近窗口样本 < threshold 时回退到整段累积；window_seconds<=0/None 或行无时间戳
    时退化为整段累积（向后兼容）。输出 basis 标记实际口径（recent/cumulative）。
    总计数 < threshold 时 pct 置 None、sample_status=insufficient，禁止硬算。
    """
    if len(teams) != 2:
        return None
    a, b = teams
    eff: dict[str, str] = dict(PLAYER_TEAM)
    if player_teams:
        eff.update(player_teams)
    kws = {
        a: _team_keywords(a) + _team_player_keywords(a, game, eff),
        b: _team_keywords(b) + _team_player_keywords(b, game, eff),
    }

    # 整段累积（回退口径）
    ca, cb, sa, sb = _count_signal(rows, kws, a, b)
    basis = "cumulative"

    # 近窗口口径：只保留最新 window_seconds 秒内的行；样本足够则优先
    if window_seconds and window_seconds > 0:
        ts_vals = [_ts_value(r) for r in rows]
        if any(v > 0 for v in ts_vals):
            max_ts = max(ts_vals)
            recent = [r for r, tv in zip(rows, ts_vals) if tv >= max_ts - window_seconds]
            ra, rb, rsa, rsb = _count_signal(recent, kws, a, b)
            if ra + rb >= threshold:
                ca, cb, sa, sb = ra, rb, rsa, rsb
                basis = "recent"

    total = ca + cb
    if total == 0 or total < threshold:
        return {
            "team_a": a, "team_b": b,
            "count_a": ca, "count_b": cb,
            "total": total,
            "pct_a": None, "pct_b": None,
            "sample_status": "insufficient",
            "samples_a": sa, "samples_b": sb,
            "threshold": threshold,
            "basis": basis,
            "window_seconds": window_seconds,
        }
    pa = round(ca / total * 100)
    return {
        "team_a": a, "team_b": b,
        "count_a": ca, "count_b": cb,
        "total": total,
        "pct_a": pa, "pct_b": 100 - pa,
        "sample_status": "ready",
        "samples_a": sa, "samples_b": sb,
        "threshold": threshold,
        "basis": basis,
        "window_seconds": window_seconds,
    }


def analyze(
    rows: list[dict],
    game: str | None = None,
    teams: list[str] | None = None,
    player_teams: dict[str, str] | None = None,
    window_seconds: int | None = 300,
) -> dict:
    # normalize platform fields: SOOP uses "message", huya uses "text"
    rows = [dict(r, text=r.get("text", r.get("message", ""))) for r in rows]
    # stripped = 去掉虎牙"Faker："挂件前缀后的正文；实体匹配与情绪都用它
    # sent = 预计算情绪；ts_val = 预计算时间戳（实体/密度/叙事共用，避免重复算）
    for r in rows:
        r["stripped"] = strip_entity_prefix(r["text"])
        r["sent"] = sentiment(r["stripped"])
        r["ts_val"] = _ts_value(r)
    # 未显式给 game 时，从记录里的 game 字段自动推断（采集阶段已打标签）
    if game is None:
        cnt = Counter(r.get("game") for r in rows if r.get("game"))
        if cnt:
            game = cnt.most_common(1)[0][0]

    def clean(text: str) -> str:
        """样本清洗（2026-08-26 精细度优化）：去 emote 标记/URL，压缩空白。
        避免 Twitch 表情符号与广告刷屏污染情报样本。"""
        t = re.sub(r"\[emote:[^\]]*\]", "", text)
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t[:120]

    if not rows:
        return {
            "meta": {
                "total": 0,
                "active_users": 0,
                "window_utc": ["等待首条弹幕", "等待首条弹幕"],
                "density_per_min": 0.0,
                "sample_status": "insufficient",
            },
            "teams": {},
            "players": {},
            "odds_discussion": {"count": 0, "samples": []},
            "situation": {"count": 0, "samples": []},
            "gray_signals": {"count": 0, "samples": []},
            "density_bursts": [],
            "narrative": {"consensus": {}, "timeline": [], "turning_points": []},
            "neutral_salvage": [],
            "top_users": [],
            "win_signal": win_signal([], teams or [], player_teams=player_teams, window_seconds=window_seconds) if teams else None,
        }
    ts = [r["ts_val"] for r in rows]
    t0, t1 = min(ts), max(ts)
    minutes = max((t1 - t0) / 60, 1)

    # density bursts by minute
    buckets: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[int(r["ts_val"] // 60)].append(r)
    counts = {k: len(v) for k, v in buckets.items()}
    if counts:
        vals = list(counts.values())
        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0
        def _burst(k: int, c: int) -> dict:
            rs = buckets[k]
            p = sum(1 for r in rs if r["sent"] == "pos")
            n = sum(1 for r in rs if r["sent"] == "neg")
            return {
                "minute_utc": datetime.datetime.fromtimestamp(k * 60, datetime.timezone.utc).strftime("%H:%M"),
                "minute": k,
                "count": c,
                "pos": p,
                "neg": n,
                "tone": _narrative_tone(p, n),
                "samples": [clean(x["text"]) for x in rs[:4] if clean(x["text"])],
            }

        bursts = [
            _burst(k, c)
            for k, c in sorted(counts.items(), key=lambda kv: -kv[1])
            if c >= max(mean + 2 * std, 6)
        ][:8]
    else:
        bursts = []

    # teams / players sentiment
    team_agg: dict[str, dict] = {}
    for name, kws in TEAMS.items():
        if not _match_game(name, game):
            continue
        hits = [r for r in rows if any(keyword_hit(r["stripped"], k) for k in kws)]
        if not hits:
            continue
        pos = sum(1 for r in hits if r["sent"] == "pos")
        neg = sum(1 for r in hits if r["sent"] == "neg")
        team_agg[name] = {
            "mentions": len(hits),
            "pos": pos,
            "neg": neg,
            "samples": [clean(r["stripped"]) for r in hits[:5] if clean(r["stripped"])],
        }

    player_agg: dict[str, dict] = {}
    for name, kws in PLAYERS.items():
        if not _match_game(name, game):
            continue
        hits = [r for r in rows if any(keyword_hit(r["stripped"], k) for k in kws)]
        if not hits:
            continue
        pos = sum(1 for r in hits if r["sent"] == "pos")
        neg = sum(1 for r in hits if r["sent"] == "neg")
        player_agg[name] = {
            "mentions": len(hits),
            "pos": pos,
            "neg": neg,
            "samples": [clean(r["stripped"]) for r in hits[:5] if clean(r["stripped"])],
        }

    odds = [r for r in rows if any(k in r["text"] for k in ODDS_KW)]
    gray = [r for r in rows if any(k in r["text"] for k in GRAY_KW)]
    situation = [r for r in rows if any(k in r["text"] for k in SITUATION_KW)]
    users = Counter(r.get("nick") or r.get("nickname") or r.get("user_id") or "?" for r in rows)

    # ---- 阶段2：比赛叙事（情绪时间轴 / 关键转折点 / 观众共识）----
    total_pos = sum(1 for r in rows if r["sent"] == "pos")
    total_neg = sum(1 for r in rows if r["sent"] == "neg")
    consensus = {
        "pos": total_pos,
        "neg": total_neg,
        "net": total_pos - total_neg,
        "tone": _narrative_tone(total_pos, total_neg),
    }

    # 情绪时间轴：整场切 5 段看走势（<10 分钟则整体 1 段）
    n_seg = 5 if minutes >= 25 else (3 if minutes >= 10 else 1)
    span = max(t1 - t0, 1.0)
    timeline = []
    for i in range(n_seg):
        lo = t0 + span * i / n_seg
        hi = t0 + span * (i + 1) / n_seg
        rs = [r for r in rows if r["ts_val"] >= lo and (i == n_seg - 1 or r["ts_val"] < hi)]
        p = sum(1 for r in rs if r["sent"] == "pos")
        n = sum(1 for r in rs if r["sent"] == "neg")
        timeline.append({
            "start_utc": datetime.datetime.fromtimestamp(lo, datetime.timezone.utc).strftime("%H:%M"),
            "count": len(rs),
            "pos": p,
            "neg": n,
            "net": p - n,
            "tone": _narrative_tone(p, n),
        })

    # 转折点：密度峰值分钟里情绪一边倒的（正面=高光/翻盘，负面=失误/送）
    turning = [
        {"minute_utc": b["minute_utc"], "count": b["count"], "tone": b["tone"],
         "pos": b["pos"], "neg": b["neg"],
         "sample": (b["samples"][0] if b["samples"] else "")}
        for b in bursts
        if b["tone"] in ("正面", "负面")
    ]

    narrative = {
        "consensus": consensus,
        "timeline": timeline,
        "turning_points": turning,
    }

    # ---- 阶段4：中性弹幕抢救候选（供 AI 层二次判定）----
    # 规则层 sentiment() 判 None 的中性弹幕占绝大多数（约 93%），其中夹着大量
    # 关键词库没覆盖到的真实情绪（黑话/口语/反讽/表情语义，如"666""这把拉了"）。
    # 规则层不硬猜，只按价值挑出至多 SALVAGE_LIMIT 条去重后的中性弹幕，交给
    # fast_intel_node / run_codex_report 的 LLM 二次判定；出现次数=观众共识信号。
    # 排序优先级：提及本局战队/选手 ＞ 出现次数多 ＞ 含潜在情绪线索。
    salvage_kws = [
        k
        for name, kwlist in list(TEAMS.items()) + list(PLAYERS.items())
        if _match_game(name, game)
        for k in kwlist
    ]
    salvage_agg: dict[str, dict] = {}
    for r in rows:
        if r["sent"] is not None:
            continue
        c = clean(r["stripped"])
        if not c:
            continue
        e = salvage_agg.setdefault(c, {"count": 0, "entity": False, "ts_val": r["ts_val"]})
        e["count"] += 1
        e["ts_val"] = min(e["ts_val"], r["ts_val"])
        if not e["entity"] and any(keyword_hit(c, k) for k in salvage_kws):
            e["entity"] = True
    salvage_items = sorted(
        salvage_agg.items(),
        key=lambda kv: (
            kv[1]["entity"],
            kv[1]["count"],
            any(x in kv[0] for x in SALVAGE_CUE),
            -kv[1]["ts_val"],
        ),
        reverse=True,
    )[:SALVAGE_LIMIT]
    neutral_salvage = [
        {
            "text": c,
            "count": e["count"],
            "entity": e["entity"],
            "minute_utc": datetime.datetime.fromtimestamp(
                e["ts_val"], datetime.timezone.utc
            ).strftime("%H:%M"),
        }
        for c, e in salvage_items
    ]

    return {
        "meta": {
            "total": len(rows),
            "active_users": len(users),
            "window_utc": [
                datetime.datetime.fromtimestamp(t0, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                datetime.datetime.fromtimestamp(t1, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            ],
            "density_per_min": round(len(rows) / minutes, 1),
            "sample_status": "ready",
        },
        "teams": team_agg,
        "players": player_agg,
        "odds_discussion": {"count": len(odds), "samples": [clean(r["text"]) for r in odds[:8] if clean(r["text"])]},
        "situation": {"count": len(situation), "samples": [clean(r["text"]) for r in situation[:8] if clean(r["text"])]},
        "gray_signals": {"count": len(gray), "samples": [clean(r["text"]) for r in gray[:8] if clean(r["text"])]},
        "density_bursts": bursts,
        "narrative": narrative,
        "neutral_salvage": neutral_salvage,
        "top_users": users.most_common(8),
        "win_signal": win_signal(rows, teams, game=game, player_teams=player_teams, window_seconds=window_seconds) if teams else None,
    }


def print_summary(intel: dict) -> None:
    m = intel["meta"]
    print(f"弹幕情报（{m['window_utc'][0]} ~ {m['window_utc'][1]}，{m['total']} 条，{m['active_users']} 人，{m['density_per_min']} 条/分）\n")
    print("== 队伍情绪 ==")
    for name, d in sorted(intel["teams"].items(), key=lambda kv: -kv[1]["mentions"]):
        print(f"  {name}: {tone_label(d['pos'], d['neg'], d['mentions'])} 提及{d['mentions']} 正{d['pos']}/负{d['neg']} | 例: {d['samples'][0][:40]}")
    print("\n== 选手状态 ==")
    for name, d in sorted(intel["players"].items(), key=lambda kv: -kv[1]["mentions"]):
        print(f"  {name}: {tone_label(d['pos'], d['neg'], d['mentions'])} 提及{d['mentions']} 正{d['pos']}/负{d['neg']} | 例: {d['samples'][0][:40]}")
    print(f"\n== 盘口/数字讨论（{intel['odds_discussion']['count']} 条）==")
    for s in intel["odds_discussion"]["samples"][:5]:
        print(f"  - {s[:50]}")
    print(f"\n== 局势线索（{intel['situation']['count']} 条）==")
    for s in intel["situation"]["samples"][:5]:
        print(f"  - {s[:50]}")
    print(f"\n== 灰信号（{intel['gray_signals']['count']} 条，仅风险提示）==")
    for s in intel["gray_signals"]["samples"][:5]:
        print(f"  - {s[:50]}")
    if intel["density_bursts"]:
        print(f"\n== 弹幕密度峰值（比赛关键时刻，与价格异动相关）==")
        for b in intel["density_bursts"][:5]:
            print(f"  {b['minute_utc']} UTC：{b['count']} 条 | {b['samples'][0][:40]}")
    n = intel.get("narrative") or {}
    if n.get("consensus") or n.get("timeline"):
        cons = n.get("consensus") or {}
        print(f"\n== 比赛叙事（阶段2）==")
        if cons.get("pos") or cons.get("neg"):
            print(f"  观众共识：{cons.get('tone', '中性')}（正 {cons.get('pos', 0)} / 负 {cons.get('neg', 0)}，净 {cons.get('net', 0):+d}）")
        tl = n.get("timeline") or []
        if len(tl) >= 2:
            print("  情绪走势：" + " → ".join(f"{b['tone']}({b['net']:+d})" for b in tl))
        for t in (n.get("turning_points") or [])[:4]:
            print(f"  转折 {t['minute_utc']} {t['tone']}（{t['count']}条）{t['sample'][:30]}")
    ns = intel.get("neutral_salvage") or []
    if ns:
        print(f"\n== 中性弹幕抢救候选（{len(ns)} 条，供 AI 二次判定）==")
        for s in ns[:5]:
            print(f"  ×{s.get('count', 1)} {s.get('text', '')[:40]}")


def _print_win_signal(ws: dict) -> None:
    """打印两队伍胜率信号（观众口径·非结论）。"""
    a, b = ws["team_a"], ws["team_b"]
    if ws.get("sample_status") == "insufficient":
        print(f"\n== 比赛局势·胜率 == 样本不足（{ws['total']} 条 < 阈值 {ws['threshold']}，不硬算）")
        return
    print(f"\n== 比赛局势·胜率（观众口径·非结论）== {a} {ws['pct_a']}% : {ws['pct_b']}% {b}（共 {ws['total']} 条）")


def analyze_deep(rows: list[dict]) -> dict:
    """Theme-grouped, assertion-oriented deep analysis (no raw danmaku stream)."""
    rows = [dict(r, text=r.get("text", r.get("message", ""))) for r in rows]
    themed: dict[str, list[str]] = {t: [] for t in THEMES}
    for r in rows:
        t = r["text"]
        for theme, kws in THEMES.items():
            if any(k.lower() in t.lower() for k in kws):
                themed[theme].append(t)
                break

    def dedup(items: list[str], limit: int = 8) -> list[str]:
        seen: list[str] = []
        for x in items:
            x2 = x.strip()
            if not x2 or x2 in seen or any(x2 in s or s in x2 for s in seen):
                continue
            seen.append(x2)
            if len(seen) >= limit:
                break
        return seen

    themes_out = {t: {"count": len(v), "samples": dedup(v)} for t, v in themed.items()}

    # assertion extraction: object + verdict
    objs = ["KC", "GX", "TH", "Navi", "T1", "皇子", "发条", "打野", "中单", "上单", "下路",
            "Canna", "Oscar", "奥斯卡", "samd", "姑妈", "Poby", "Hype", "阵容", "LEC",
            "Iron Wing", "IW", "Spirit", "雪碧", "Pure", "bzm", "泽马", "33", "Ari", "Whitemon",
            "Yatoro", "亚托罗", "雨神", "Larl", "拉尔", "Collapse", "崩溃", "not me", "rue"]
    assertions: list[tuple[str, str, int]] = []
    counter: dict[tuple[str, str], int] = {}
    for r in rows:
        t = r["text"]
        for o in objs:
            if o.lower() not in t.lower():
                continue
            for v in VERDICT_NEG:
                if v in t:
                    key = (o, "负面:" + v)
                    counter[key] = counter.get(key, 0) + 1
                    break
            else:
                for v in VERDICT_POS:
                    if v in t:
                        key = (o, "正面:" + v)
                        counter[key] = counter.get(key, 0) + 1
                        break
    for (o, v), c in sorted(counter.items(), key=lambda kv: -kv[1]):
        assertions.append((o, v, c))

    # key event timeline: burst minutes with dominant theme
    buckets: dict[int, list[str]] = {}
    for r in rows:
        buckets.setdefault(int(r["ts"] // 60), []).append(r["text"])
    events = []
    for minute, texts in sorted(buckets.items()):
        if len(texts) < 6:
            continue
        theme_count = {}
        for t in texts:
            for theme, kws in THEMES.items():
                if any(k.lower() in t.lower() for k in kws):
                    theme_count[theme] = theme_count.get(theme, 0) + 1
                    break
        top = max(theme_count, key=theme_count.get) if theme_count else "其他"
        import datetime as _dt
        events.append({
            "minute_utc": _dt.datetime.fromtimestamp(minute * 60, _dt.timezone.utc).strftime("%H:%M"),
            "count": len(texts),
            "theme": top,
            "sample": texts[0][:40],
        })

    return {"themes": themes_out, "assertions": assertions[:16], "events": events[-10:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="弹幕 -> 交易情报提炼")
    parser.add_argument("--input", required=True, help="JSONL 弹幕文件")
    parser.add_argument("--out", default=None, help="情报 JSON 输出路径（可选）")
    parser.add_argument("--game", default="", help="游戏标签 lol/cs2/dota2（可选；未给则按记录 game 字段自动推断）")
    parser.add_argument("--teams", default="", help="两个比赛队伍（逗号分隔，如 KC,MVK），用于计算胜率")
    parser.add_argument("--players", default="", help="首发阵容 JSON 文件路径（{选手名: 队伍名}，虎扑每小局阵容）")
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    teams = [t.strip() for t in args.teams.split(",") if t.strip()] if args.teams else None
    player_teams: dict[str, str] | None = None
    if args.players:
        try:
            player_teams = json.loads(Path(args.players).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            player_teams = None
    intel = analyze(rows, game=args.game or None, teams=teams, player_teams=player_teams)
    print_summary(intel)
    if intel.get("win_signal"):
        _print_win_signal(intel["win_signal"])
    if args.out:
        Path(args.out).write_text(json.dumps(intel, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n已保存：{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
