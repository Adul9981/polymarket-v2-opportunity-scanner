#!/usr/bin/env python3
"""Render complete per-match pre-match intelligence detail pages."""

from __future__ import annotations

import csv
import html
import io
import json
import os
import re
from pathlib import Path
from typing import Any


LABELS = {
    "overallMapWinrate": "总体地图胜率",
    "overallRoundWinrate": "总体回合胜率",
    "mapWinrate": "地图胜率",
    "roundWinrate": "逐图回合胜率",
    "pistolWinrate": "手枪局胜率",
    "pistolWinConversion": "手枪局胜转化",
    "pistolLossConversion": "手枪局负转化",
    "kills": "击杀",
    "deaths": "死亡",
    "assists": "助攻",
    "killsOverDeaths": "KD",
    "flashAssists": "闪光助攻",
    "damage": "伤害",
    "headshotRate": "爆头率",
    "openingKills": "首杀",
    "openingConversion": "首杀转化",
    "openingDeathConversion": "首死后转化",
    "awpKills": "AWP 击杀",
    "eliminationWinrate": "击杀回合胜率",
    "objectiveWinrate": "目标回合胜率",
    "utilityDamage": "道具伤害",
    "enemiesFlashed": "致盲敌人",
    "multiKillRounds": "多杀回合",
    "clutchRounds": "残局",
    "lurkKills": "潜伏击杀",
    "grenadesUsed": "投掷物使用",
    "firstToWin3Rounds": "先到 3 回合胜率",
    "firstToWin6Rounds": "先到 6 回合胜率",
    "firstToWin9Rounds": "先到 9 回合胜率",
    "firstToWin12Rounds": "先到 12 回合胜率",
    "roundsLost": "丢回合",
    "gold": "金币",
    "xp": "经验",
    "heroDamage": "英雄伤害",
    "heroHealing": "英雄治疗",
    "roshanKills": "肉山击杀",
    "towerKills": "推塔",
    "barracksKills": "兵营",
    "firstBlood": "一血",
    "firstTower": "首塔",
    "firstRoshan": "首个肉山",
    "firstBarracks": "首个兵营",
    "first5Kills": "前 5 击杀",
    "first10Kills": "前 10 击杀",
    "first15Kills": "前 15 击杀",
    "first20Kills": "前 20 击杀",
    "duration": "比赛时长",
    "killsDeathsAssists": "KDA",
    "killParticipation": "参团率",
    "creepScore": "补刀",
    "denies": "反补",
    "buildingDamage": "建筑伤害",
    "wardsPlaced": "插眼",
    "wardsDestroyed": "反眼",
    "campsStacked": "堆野",
    "stunDuration": "控制时长",
    "goldDiffAt15mins": "15 分钟经济差",
    "championDamage": "英雄伤害",
    "dragonKills": "小龙",
    "baronKills": "大龙",
    "heraldKills": "先锋",
    "turretKills": "推塔",
    "inhibitorKills": "水晶",
    "firstDragon": "首条小龙",
    "firstBaron": "首条大龙",
    "firstInhibitor": "首座水晶",
    "minionKills": "补刀",
    "heals": "治疗",
    "visionScore": "视野分",
    "crowdControlTime": "控制时间",
}


def esc(value: Any) -> str:
    if value is None or value == "":
        return ""
    return html.escape(str(value), quote=True)


def pct(value: Any, digits: int = 0) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def num(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
        if digits <= 0:
            return f"{number:.0f}"
        return f"{number:.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "-"


def stat_text(value: Any, *, suffix: str = "", scale: float = 1.0) -> str:
    if not isinstance(value, dict):
        return "-"
    if "avg" in value:
        avg_value = value.get("avg")
        try:
            avg_value = float(avg_value) * scale
        except (TypeError, ValueError):
            pass
        avg = num(avg_value) + suffix
        percentile = value.get("percentile")
        total = value.get("total")
        sample = value.get("sample_size")
        extras = []
        if percentile is not None:
            extras.append(f"P{num(percentile, 1)}")
        if total is not None:
            extras.append(f"总计 {num(total)}")
        if sample is not None:
            extras.append(f"样本 {num(sample, 0)}")
        return f"{avg}" + (f"（{' / '.join(extras)}）" if extras else "")
    if "average" in value:
        avg_value = value.get("average")
        try:
            avg_value = float(avg_value) * scale
        except (TypeError, ValueError):
            pass
        return f"{num(avg_value)}{suffix}（总计 {num(value.get('total'))}）"
    parts = []
    for key in ("all", "terrorists", "counterTerrorists", "radiant", "dire"):
        if key in value:
            parts.append(f"{key}: {stat_text(value[key], suffix=suffix, scale=scale)}")
    return "；".join(parts) or "-"


PERCENT_METRICS = {
    "mapWinrate",
    "overallMapWinrate",
    "overallRoundWinrate",
    "roundWinrate",
    "pistolWinrate",
    "pistolWinConversion",
    "pistolLossConversion",
    "openingConversion",
    "openingDeathConversion",
    "eliminationWinrate",
    "objectiveWinrate",
    "headshotRate",
    "firstBlood",
    "firstTower",
    "firstRoshan",
    "firstBarracks",
    "first5Kills",
    "first10Kills",
    "first15Kills",
    "first20Kills",
    "winRate",
}
FRACTION_METRICS = {"pickRate", "banRate", "killParticipation"}


def metric_stat_text(key: str, value: Any) -> str:
    if key in FRACTION_METRICS:
        return stat_text(value, suffix="%", scale=100.0)
    if key in PERCENT_METRICS:
        return stat_text(value, suffix="%")
    return stat_text(value)


def metric_label(key: str) -> str:
    label = LABELS.get(key, key)
    return f"{label} [{key}]" if label != key else key


def coverage_bits(row: dict[str, Any]) -> list[str]:
    coverage = row.get("intel_coverage") or {}
    bits = []
    labels = {
        "teams": "队伍",
        "players": "选手",
        "players_with_stats": "有近期统计选手",
        "recent_matches": "近期比赛",
        "h2h": "历史交锋",
        "map_pool": "地图池",
        "favorites": "常用英雄/武器",
        "squad_players": "名单",
        "injuries": "伤停",
        "lineups": "阵容",
        "tournament_matches": "赛事赛程",
        "pool_rows": "赛事地图/英雄池",
    }
    for key, label in labels.items():
        value = coverage.get(key)
        if value is not None:
            bits.append(f"{label} {int(float(value))}")
    return bits


def quality_items(row: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (label, state, detail) without inventing missing values."""
    items: list[tuple[str, str, str]] = []
    if row.get("oddin"):
        deep = row["oddin"]
        home = deep.get("home") or {}
        away = deep.get("away") or {}
        teams = (home, away)
        players = [player for team in teams for player in team.get("players") or []]
        stats_players = [player for player in players if player.get("metrics")]
        items.append(
            (
                "队伍统计",
                "ok" if all(team.get("metrics") for team in teams) else "partial",
                f"{sum(1 for team in teams if team.get('metrics'))}/2 队有统计",
            )
        )
        state = "ok" if len(stats_players) == len(players) and players else "partial"
        items.append(("选手统计", state, f"{len(stats_players)}/{len(players)} 人有近期统计"))
        pools = sum(len(team.get("map_pool") or team.get("favorites") or []) for team in teams)
        items.append(("地图/英雄池", "ok" if pools else "gap", f"{pools} 项"))
        recent = sum(len(team.get("recent_matches") or []) for team in teams)
        items.append(("近期比赛", "ok" if recent else "gap", f"{recent} 场"))
        h2h = len((deep.get("head_to_head") or {}).get("matches") or [])
        items.append(("历史交锋", "ok" if h2h else "gap", f"{h2h} 场"))
        tournament = deep.get("tournament") or {}
        matches = len(tournament.get("matches") or [])
        teams_count = len(tournament.get("teams") or [])
        items.append(("赛事名单/赛程", "ok" if teams_count and matches else "partial", f"{teams_count} 队 / {matches} 场"))
        standings = sum(
            len(block.get("standings") or [])
            for block in tournament.get("standings") or []
            if isinstance(block, dict)
        )
        items.append(("赛事积分榜", "ok" if standings else "gap", f"{standings} 行"))
        pools = len((tournament.get("stats") or {}).get("pools") or [])
        items.append(("赛事地图/英雄统计", "ok" if pools else "gap", f"{pools} 项"))
    elif row.get("lmt"):
        deep = row["lmt"]
        teams = (deep.get("home") or {}, deep.get("away") or {})
        squad = sum(len(team.get("squad") or []) for team in teams)
        items.append(("完整名单", "ok" if squad else "gap", f"{squad} 人"))
        lineups = sum(1 for team in teams if (team.get("usual_lineup") or {}).get("players"))
        items.append(("首发/近场首发", "ok" if lineups else "gap", f"{lineups}/2 队"))
        recent = sum(len(team.get("last_matches") or []) for team in teams)
        items.append(("近期比赛", "ok" if recent else "gap", f"{recent} 场"))
        injuries = sum(len(team.get("injuries") or []) for team in teams)
        items.append(("伤停", "ok" if injuries else "info", f"{injuries} 人"))
        tables = (deep.get("league") or {}).get("tables") or []
        rows = sum(len(table.get("rows") or []) for table in tables)
        items.append(("积分榜", "ok" if rows else "gap", f"{rows} 行"))
        h2h = len((deep.get("head_to_head") or {}).get("matches") or [])
        items.append(("历史交锋", "ok" if h2h else "gap", f"{h2h} 场"))
    return items


def quality_block(row: dict[str, Any]) -> str:
    items = quality_items(row)
    if not items:
        return ""
    chips = "".join(
        f'<span class="q-{esc(state)}">{esc(label)} <b>{esc(detail)}</b></span>'
        for label, state, detail in items
    )
    return f'<section class="panel quality"><h2>数据覆盖与缺口</h2><div>{chips}</div></section>'


def odds_block(row: dict[str, Any]) -> str:
    winner = row.get("winner_market") or {}
    outcomes = winner.get("outcomes") or []
    rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('name'))}</td>"
        f"<td>{pct(item.get('fair_probability'), 1)}</td>"
        f"<td>{num(item.get('decimal_odds'))}</td>"
        "</tr>"
        for item in outcomes
    )
    if not rows:
        return f'<p class="gap">{esc(row.get("market_state_label") or "主市场缺口")}</p>'
    return (
        '<table><thead><tr><th>结果</th><th>去水概率</th><th>十进制</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )


def match_result(item: dict[str, Any], team_id: Any = None) -> str:
    if team_id is None:
        return item.get("result") or item.get("team_result") or ""
    return item.get("team_result") or ""


def match_rows(matches: list[dict[str, Any]], team_id: Any = None) -> str:
    rows = []
    for item in matches:
        date = (
            str(item.get("planned_start") or "")[:10]
            or str(item.get("start") or "")[:10]
            or ((item.get("date") or {}).get("utc") or "")[:10]
            or "-"
        )
        home = (item.get("home") or {}).get("name") or item.get("home") or ""
        away = (item.get("away") or {}).get("name") or item.get("away") or ""
        raw_score = item.get("score")
        score = (
            raw_score.get("display")
            if isinstance(raw_score, dict)
            else raw_score
        ) or (
            f"{item.get('home_score', item.get('team_score', '-'))}:"
            f"{item.get('away_score', item.get('opponent_score', '-'))}"
        )
        if "None" in str(score):
            score = "待赛"
        result = match_result(item, team_id)
        if not result:
            result = (item.get("winner") or {}).get("name") or ""
        rows.append(
            "<tr>"
            f"<td>{esc(date)}</td>"
            f"<td>{esc(home)}</td>"
            f"<td>{esc(score)}</td>"
            f"<td>{esc(away)}</td>"
            f"<td>{esc(result)}</td>"
            "</tr>"
        )
    return (
        '<div class="scroll"><table><thead><tr><th>日期</th><th>主队</th><th>比分</th><th>客队</th><th>结果</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">暂无已结束比赛样本。</p>'
    )


def metrics_table(metrics: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{esc(metric_label(key))}</td>"
        f"<td>{esc(metric_stat_text(key, value))}</td>"
        "</tr>"
        for key, value in metrics.items()
        if key not in {"mapWinrate"}
    )
    return (
        '<div class="scroll"><table><thead><tr><th>指标</th><th>数值 / 百分位 / 样本</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
        if rows
        else '<p class="gap">暂无队伍统计。</p>'
    )


def favorites_table(favorites: list[dict[str, Any]], game: str) -> str:
    if not favorites:
        return '<p class="gap">暂无常用英雄 / 武器样本。</p>'
    rows = []
    for item in favorites:
        metrics = item.get("metrics") or {}
        values = []
        for key, value in metrics.items():
            values.append(f"{metric_label(key)} {metric_stat_text(key, value)}")
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td>{esc('；'.join(values) or '-')}</td>"
            "</tr>"
        )
    return (
        '<div class="scroll tall"><table><thead><tr><th>名称</th><th>完整指标</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def map_pool_table(team: dict[str, Any]) -> str:
    rows = []
    for item in team.get("map_pool") or []:
        rounds = item.get("rounds") or {}
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('name'))}</td>"
            f"<td>{esc(metric_stat_text('mapWinrate', item.get('win_rate') or {}))}</td>"
            f"<td>{esc(metric_stat_text('pickRate', item.get('pick_rate') or {}))}</td>"
            f"<td>{esc(metric_stat_text('banRate', item.get('ban_rate') or {}))}</td>"
            f"<td>{esc(metric_stat_text('roundWinrate', rounds.get('terrorists') or {}))}</td>"
            f"<td>{esc(metric_stat_text('roundWinrate', rounds.get('counterTerrorists') or {}))}</td>"
            "</tr>"
        )
    return (
        '<div class="scroll"><table><thead><tr>'
        "<th>地图</th><th>胜率</th><th>选用</th><th>禁用</th><th>T 方回合</th><th>CT 方回合</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">该队伍当前没有地图池样本。</p>'
    )


def player_block(player: dict[str, Any], game: str) -> str:
    metrics = player.get("metrics") or {}
    favorite_rows = favorites_table(player.get("favorites") or [], game)
    status = "有近期统计" if metrics else "仅有赛事名单，近期统计样本不足"
    return f"""
<details class="player" open>
  <summary>
    <b>{esc(player.get("nickname"))}</b>
    <span>{esc(player.get("real_name") or "")}</span>
    <em>{esc(player.get("role") or status)}</em>
  </summary>
  <div class="player-body">
    {metrics_table(metrics)}
    <h4>选手常用英雄 / 武器</h4>
    {favorite_rows}
  </div>
</details>"""


def standing_table(blocks: list[dict[str, Any]]) -> str:
    rows = []
    for block in blocks:
        for item in block.get("standings") or []:
            rows.append(
                "<tr>"
                f"<td>{esc(block.get('name'))}</td>"
                f"<td>{esc(item.get('rank'))}</td>"
                f"<td>{esc((item.get('team') or {}).get('name'))}</td>"
                f"<td>{esc(item.get('matchesWon'))}-{esc(item.get('matchesLost'))}</td>"
                f"<td>{esc(item.get('mapsWon'))}-{esc(item.get('mapsLost'))}</td>"
                f"<td>{esc(item.get('points'))}</td>"
                "</tr>"
            )
    return (
        '<div class="scroll"><table><thead><tr><th>阶段</th><th>#</th><th>队伍</th><th>系列赛</th><th>小局</th><th>积分</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">当前赛事阶段没有可用积分榜。</p>'
    )


def tournament_pool_table(pools: list[dict[str, Any]], game: str) -> str:
    rows = []
    for item in pools:
        entity = item.get("map") or item.get("hero") or item.get("champion") or {}
        picks = item.get("picks")
        wins = item.get("wins")
        win_rate = (
            f"{float(wins) / float(picks) * 100:.1f}%"
            if wins is not None and picks
            else "-"
        )
        side = ""
        if game == "csgo":
            t_rate = item.get("terroristsWinrateInPercent")
            ct_rate = item.get("counterTerroristsWinrateInPercent")
            side = (
                f"<td>{'-' if t_rate is None else f'{float(t_rate):.1f}%'}</td>"
                f"<td>{'-' if ct_rate is None else f'{float(ct_rate):.1f}%'}</td>"
            )
        else:
            side = f"<td>{win_rate}</td>"
        rows.append(
            "<tr>"
            f"<td>{esc(entity.get('name'))}</td>"
            f"<td>{esc(num(picks, 1))}</td>"
            f"<td>{esc(num(item.get('bans'), 1))}</td>"
            f"{side}"
            "</tr>"
        )
    extra = "<th>T 胜率</th><th>CT 胜率</th>" if game == "csgo" else "<th>胜率</th>"
    return (
        '<div class="scroll tall"><table><thead><tr><th>地图/英雄</th><th>选取</th><th>禁用</th>'
        f"{extra}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">当前赛事阶段没有地图/英雄统计样本。</p>'
    )


def roster_table(teams: list[dict[str, Any]]) -> str:
    rows = []
    for item in teams:
        team = item.get("team") or {}
        players = item.get("players") or []
        rows.append(
            "<tr>"
            f"<td>{esc(team.get('name'))}</td>"
            f"<td>{esc(len(players))}</td>"
            f"<td>{esc('、'.join(str(p.get('nickname') or '') for p in players))}</td>"
            "</tr>"
        )
    return (
        '<div class="scroll tall"><table><thead><tr><th>队伍</th><th>人数</th><th>赛事名单</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">当前赛事未提供队伍名单。</p>'
    )


def leaders_table(stats: dict[str, Any]) -> str:
    rows = []
    for kind, key in (("队伍", "best_teams"), ("选手", "best_players")):
        for item in stats.get(key) or []:
            subject = (
                (item.get("player") or {}).get("nickname")
                if kind == "选手"
                else (item.get("team") or {}).get("name")
            )
            rows.append(
                "<tr>"
                f"<td>{esc(kind)}</td>"
                f"<td>{esc(item.get('metric'))}</td>"
                f"<td>{esc(subject)}</td>"
                f"<td>{esc(num(item.get('value')))}</td>"
                "</tr>"
            )
    return (
        '<div class="scroll"><table><thead><tr><th>类别</th><th>指标</th><th>对象</th><th>数值</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">当前赛事阶段没有领先数据。</p>'
    )


def bracket_table(blocks: list[dict[str, Any]]) -> str:
    rows = []
    for block in blocks:
        for node in block.get("brackets") or []:
            rows.append(
                "<tr>"
                f"<td>{esc(block.get('name'))}</td>"
                f"<td>{esc(node.get('label') or '-')}</td>"
                f"<td>{esc((node.get('homeTeam') or {}).get('name'))}</td>"
                f"<td>{esc(node.get('homeScore'))}</td>"
                f"<td>{esc(node.get('awayScore'))}</td>"
                f"<td>{esc((node.get('awayTeam') or {}).get('name'))}</td>"
                "</tr>"
            )
    return (
        '<div class="scroll tall"><table><thead><tr><th>阶段</th><th>轮次</th><th>主队</th><th>比分</th><th>比分</th><th>客队</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        if rows
        else '<p class="gap">当前赛事阶段未提供淘汰赛对阵。</p>'
    )


def oddin_team(team: dict[str, Any], game: str) -> str:
    return f"""
<section class="team">
  <div class="team-head">
    <div>
      <h2>{esc(team.get("name"))}</h2>
      <p>地图胜率 {esc(metric_stat_text("mapWinrate", team.get("map_winrate") or {}))}</p>
    </div>
  </div>
  <h3>全部队伍统计</h3>
  {metrics_table(team.get("metrics") or {})}
  <h3>完整地图池</h3>
  {map_pool_table(team) if game == "csgo" else favorites_table(team.get("favorites") or [], game)}
  <h3>常用武器 / 英雄完整列表</h3>
  {favorites_table(team.get("favorites") or [], game) if game == "csgo" else '<p class="muted">已在上方英雄池完整展开。</p>'}
  <h3>近期比赛</h3>
  {match_rows(team.get("recent_matches") or [], team.get("id"))}
  <h3>选手完整数据 · {len(team.get("players") or [])} 人</h3>
  {''.join(player_block(player, game) for player in team.get("players") or [])}
</section>"""


def render_oddin(row: dict[str, Any]) -> str:
    deep = row["oddin"]
    game = str(deep.get("game") or "")
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    h2h = deep.get("head_to_head") or {}
    tournament = deep.get("tournament") or {}
    stats = tournament.get("stats") or {}
    metadata = tournament.get("metadata") or {}
    info = metadata.get("tournament") or {}
    gap_bits = []
    if not tournament.get("standings"):
        gap_bits.append("积分榜：当前赛事阶段未提供")
    if not tournament.get("brackets"):
        gap_bits.append("淘汰赛对阵：当前赛事阶段未提供")
    if not stats:
        gap_bits.append("赛事统计：数据源当前返回空")
    elif not stats.get("pools"):
        gap_bits.append("赛事地图/英雄池：当前赛事阶段无样本")
    roster_only = sum(
        1
        for team in (home, away)
        for player in team.get("players") or []
        if not player.get("has_recent_stats")
    )
    if roster_only:
        gap_bits.append(f"选手统计：{roster_only} 人只有赛事名单、没有近三个月个人样本")
    return f"""
<section class="pair">
  {oddin_team(home, game)}
  {oddin_team(away, game)}
</section>
<section class="panel">
  <h2>历史交锋</h2>
  {match_rows(h2h.get("matches") or [])}
</section>
<section class="panel">
  <h2>赛事总览 · {esc(info.get("name"))}</h2>
  <div class="facts">
    <span>主办 {esc(metadata.get("organizer") or "-")}</span>
    <span>地点 {esc(metadata.get("location") or "-")}</span>
    <span>奖金 {esc(metadata.get("prize_pool") or "-")}</span>
    <span>线下 {esc("是" if metadata.get("offline") else "否")}</span>
    <span>资格赛 {esc("是" if metadata.get("qualification") else "否")}</span>
  </div>
  <h3>全部赛事名单</h3>
  {roster_table(tournament.get("teams") or [])}
  <h3>全部赛事赛程</h3>
  {match_rows(tournament.get("matches") or [])}
  <h3>积分榜</h3>
  {standing_table(tournament.get("standings") or [])}
  <h3>赛事地图 / 英雄统计</h3>
  {tournament_pool_table(stats.get("pools") or [], game)}
  <h3>赛事领先数据</h3>
  {leaders_table(stats)}
  <h3>淘汰赛对阵</h3>
  {bracket_table(tournament.get("brackets") or [])}
  <h3>数据缺口</h3>
  {''.join(f'<p class="gap">{esc(bit)}</p>' for bit in gap_bits) or '<p class="muted">当前抓取范围内未发现结构性缺口。</p>'}
</section>"""


def lmt_team(team: dict[str, Any]) -> str:
    position = team.get("league_position") or {}
    lineup = team.get("usual_lineup") or {}
    lineup_rows = "".join(
        "<tr>"
        f"<td>{esc(player.get('shirt_number'))}</td>"
        f"<td>{esc(player.get('name'))}</td>"
        f"<td>{esc(player.get('position'))}</td>"
        f"<td>{esc(player.get('position_abbr'))}</td>"
        "</tr>"
        for player in lineup.get("players") or []
    )
    squad_rows = "".join(
        "<tr>"
        f"<td>{esc(player.get('shirt_number'))}</td>"
        f"<td>{esc(player.get('name'))}</td>"
        f"<td>{esc(player.get('fullname'))}</td>"
        f"<td>{esc(player.get('position'))}</td>"
        f"<td>{esc(player.get('age'))}</td>"
        f"<td>{esc(player.get('nationality'))}</td>"
        f"<td>{esc(player.get('preferred_foot'))}</td>"
        f"<td>{esc(player.get('height_cm'))}</td>"
        f"<td>{esc(player.get('weight_kg'))}</td>"
        f"<td>{esc(player.get('market_value'))}</td>"
        f"<td>{esc(str(player.get('member_since') or '')[:10])}</td>"
        "</tr>"
        for player in team.get("squad") or []
    )
    injury_rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('player'))}</td>"
        f"<td>{esc(item.get('position'))}</td>"
        f"<td>{esc(item.get('status'))}</td>"
        f"<td>{esc((item.get('start') or {}).get('utc'))}</td>"
        f"<td>{esc((item.get('end') or {}).get('utc'))}</td>"
        "</tr>"
        for item in team.get("injuries") or []
    )
    stat_rows = "".join(
        "<tr>"
        f"<td>{esc(metric_label(key))}</td>"
        f"<td>{esc(stat_text(value))}</td>"
        "</tr>"
        for key, value in (team.get("season_stats") or {}).items()
    )
    scorer_rows = "".join(
        "<tr>"
        f"<td>{esc(item.get('name'))}</td>"
        f"<td>{esc(item.get('position'))}</td>"
        f"<td>{esc(item.get('goals'))}</td>"
        f"<td>{esc(item.get('matches'))}</td>"
        f"<td>{esc(item.get('minutes'))}</td>"
        "</tr>"
        for item in team.get("top_scorers") or []
    )
    recent_rows = "".join(
        "<tr>"
        f"<td>{esc((item.get('date') or {}).get('utc') or item.get('date'))}</td>"
        f"<td>{esc((item.get('opponent') or {}).get('name'))}</td>"
        f"<td>{esc(item.get('score'))}</td>"
        f"<td>{esc(item.get('result'))}</td>"
        "</tr>"
        for item in team.get("last_matches") or []
    )
    manager = team.get("manager") or {}
    return f"""
<section class="team">
  <div class="team-head">
    <div>
      <h2>{esc(team.get("name"))}</h2>
      <p>排名 {esc(position.get("position") or "-")} ·
      {esc(position.get("wins") or 0)} 胜 {esc(position.get("draws") or 0)} 平
      {esc(position.get("losses") or 0)} 负 · {esc(position.get("points") or 0)} 分</p>
      <p>主教练 {esc(manager.get("name") or "-")} · 阵容状态 {esc(team.get("lineup_status") or "-")}</p>
    </div>
  </div>
  <h3>阵容 / 预计首发 · {esc(lineup.get("formation") or "阵型待定")}</h3>
  <div class="scroll"><table><thead><tr><th>号码</th><th>球员</th><th>位置</th><th>缩写</th></tr></thead><tbody>{lineup_rows}</tbody></table></div>
  <h3>伤停名单 · {len(team.get("injuries") or [])} 人</h3>
  <div class="scroll"><table><thead><tr><th>球员</th><th>位置</th><th>状态</th><th>开始</th><th>结束</th></tr></thead><tbody>{injury_rows or '<tr><td colspan="5">当前无伤停</td></tr>'}</tbody></table></div>
  <h3>完整报名名单 · {len(team.get("squad") or [])} 人</h3>
  <div class="scroll tall"><table><thead><tr><th>号码</th><th>球员</th><th>全名</th><th>位置</th><th>年龄</th><th>国籍</th><th>惯用脚</th><th>身高</th><th>体重</th><th>身价</th><th>入队</th></tr></thead><tbody>{squad_rows}</tbody></table></div>
  <h3>赛季统计 · {len(team.get("season_stats") or {})} 项</h3>
  <div class="scroll"><table><thead><tr><th>指标</th><th>场均 / 总计 / 场次</th></tr></thead><tbody>{stat_rows}</tbody></table></div>
  <h3>队内射手</h3>
  <div class="scroll"><table><thead><tr><th>球员</th><th>位置</th><th>进球</th><th>出场</th><th>分钟</th></tr></thead><tbody>{scorer_rows or '<tr><td colspan="5">暂无数据</td></tr>'}</tbody></table></div>
  <h3>最近比赛</h3>
  <div class="scroll"><table><thead><tr><th>日期</th><th>对手</th><th>比分</th><th>结果</th></tr></thead><tbody>{recent_rows}</tbody></table></div>
</section>"""


def render_lmt(row: dict[str, Any]) -> str:
    deep = row["lmt"]
    league = deep.get("league") or {}
    tables = league.get("tables") or []
    table_rows = []
    is_nba = any(
        item.get("win_pct") is not None
        for table in tables
        for item in table.get("rows") or []
    )
    for table in tables:
        for item in table.get("rows") or []:
            if is_nba:
                table_rows.append(
                    "<tr>"
                    f"<td>{esc(item.get('position'))}</td>"
                    f"<td>{esc((item.get('team') or {}).get('name'))}</td>"
                    f"<td>{esc(item.get('played'))}</td>"
                    f"<td>{esc(item.get('wins'))}</td>"
                    f"<td>{esc(item.get('losses'))}</td>"
                    f"<td>{pct(item.get('win_pct'), 1)}</td>"
                    f"<td>{esc(item.get('last_ten_wins'))}-{esc(item.get('last_ten_losses'))}</td>"
                    f"<td>{esc(item.get('home_wins'))}-{esc(item.get('home_losses'))}</td>"
                    f"<td>{esc(item.get('away_wins'))}-{esc(item.get('away_losses'))}</td>"
                    f"<td>{esc(item.get('streak'))}</td>"
                    "</tr>"
                )
            else:
                table_rows.append(
                    "<tr>"
                    f"<td>{esc(item.get('position'))}</td>"
                    f"<td>{esc((item.get('team') or {}).get('name'))}</td>"
                    f"<td>{esc(item.get('played'))}</td>"
                    f"<td>{esc(item.get('wins'))}</td>"
                    f"<td>{esc(item.get('draws'))}</td>"
                    f"<td>{esc(item.get('losses'))}</td>"
                    f"<td>{esc(item.get('goal_diff'))}</td>"
                    f"<td>{esc(item.get('points'))}</td>"
                    "</tr>"
                )
    h2h_rows = "".join(
        "<tr>"
        f"<td>{esc((item.get('date') or {}).get('utc'))}</td>"
        f"<td>{esc((item.get('home') or {}).get('name'))}</td>"
        f"<td>{esc((item.get('score') or {}).get('display'))}</td>"
        f"<td>{esc((item.get('away') or {}).get('name'))}</td>"
        "</tr>"
        for item in (deep.get("head_to_head") or {}).get("matches") or []
    )
    league_scorers = []
    for item in league.get("top_scorers") or []:
        player = item.get("player") or {}
        total = item.get("total") or {}
        league_scorers.append(
            "<tr>"
            f"<td>{esc(player.get('name'))}</td>"
            f"<td>{esc((player.get('position') or {}).get('name'))}</td>"
            f"<td>{esc(total.get('goals'))}</td>"
            f"<td>{esc(total.get('matches'))}</td>"
            f"<td>{esc(total.get('minutes_played'))}</td>"
            "</tr>"
        )
    return f"""
<section class="pair">
  {lmt_team(deep.get("home") or {})}
  {lmt_team(deep.get("away") or {})}
</section>
<section class="panel">
  <h2>历史交锋</h2>
  <div class="scroll"><table><thead><tr><th>日期</th><th>主队</th><th>比分</th><th>客队</th></tr></thead><tbody>{h2h_rows}</tbody></table></div>
  <h2>联赛积分榜</h2>
  <div class="scroll tall"><table><thead>
  {('<tr><th>#</th><th>队伍</th><th>赛</th><th>胜</th><th>负</th><th>胜率</th><th>近10</th><th>主场</th><th>客场</th><th>连续</th></tr>' if is_nba else '<tr><th>#</th><th>队伍</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>净胜</th><th>分</th></tr>')}
  </thead><tbody>{''.join(table_rows) if table_rows else '<tr><td colspan="10">当前数据源未提供积分榜</td></tr>'}</tbody></table></div>
  <h2>赛事射手榜</h2>
  <div class="scroll tall"><table><thead><tr><th>球员</th><th>位置</th><th>进球</th><th>出场</th><th>分钟</th></tr></thead><tbody>{''.join(league_scorers) if league_scorers else '<tr><td colspan="5">当前数据源未提供射手榜</td></tr>'}</tbody></table></div>
</section>"""


def render_page(row: dict[str, Any], snapshot: dict[str, Any]) -> str:
    bits = coverage_bits(row)
    body = render_oddin(row) if row.get("oddin") else render_lmt(row) if row.get("lmt") else '<p class="gap">本场暂无完整深包。</p>'
    title = f"{row.get('teams', ['', ''])[0]} vs {row.get('teams', ['', ''])[1]} · AI 赛前情报"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--blue:#0071e3;--green:#248a3d;--orange:#b45309}}
*{{box-sizing:border-box;margin:0;padding:0}} body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC",sans-serif;line-height:1.55}} a{{color:var(--blue);text-decoration:none}} .wrap{{max-width:1180px;margin:auto;padding:26px 18px 60px}}
.hero,.panel,.team{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;margin-top:12px;box-shadow:0 6px 22px rgba(0,0,0,.03)}} .hero h1{{font-size:30px;letter-spacing:-.03em}} .hero h1 span{{font-size:13px;color:var(--sub);margin:0 8px}} .meta,.facts,.coverage{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}} .meta span,.facts span,.coverage span{{font-size:11px;background:#f2f2f5;border-radius:999px;padding:4px 9px;color:var(--sub)}}
.quality>div{{display:flex;flex-wrap:wrap;gap:6px}} .quality span{{font-size:10px;border-radius:999px;padding:4px 8px;background:#f2f2f5;color:var(--sub)}} .quality span b{{margin-left:5px;color:var(--ink)}} .quality .q-ok{{background:#e9f7ed;color:#22683a}} .quality .q-partial{{background:#fff4df;color:#8a5b08}} .quality .q-gap{{background:#fdeaea;color:#9d2c26}} .quality .q-info{{background:#edf3fb;color:#315d9a}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start}} .team-head{{display:flex;justify-content:space-between;gap:10px}} h2{{font-size:20px;margin-bottom:7px}} h3{{font-size:13px;margin:16px 0 6px;color:#3a3a3c}} h4{{font-size:11px;margin:10px 0 5px;color:var(--sub)}}
table{{width:100%;border-collapse:collapse;font-size:10px}} th,td{{padding:6px 7px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{color:var(--sub);font-size:9px;text-transform:uppercase;letter-spacing:.04em}} .scroll{{overflow:auto}} .scroll.tall{{max-height:360px}} .muted,.gap{{color:var(--sub);font-size:11px;margin:6px 0}}
th{{cursor:pointer}} th:hover{{color:var(--ink)}}
.player{{border:1px solid var(--line);border-radius:12px;margin-top:7px;background:#fbfbfc}} .player>summary{{cursor:pointer;list-style:none;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr) auto;gap:8px;padding:9px 10px;align-items:center}} .player>summary::-webkit-details-marker{{display:none}} .player>summary b{{font-size:12px}} .player>summary span,.player>summary em{{font-size:9.5px;color:var(--sub);font-style:normal}} .player-body{{padding:0 10px 10px}}
.note{{font-size:10px;color:var(--sub);margin-top:16px}} @media(max-width:800px){{.pair{{grid-template-columns:1fr}}.hero h1{{font-size:24px}}}} @media print{{body{{background:#fff}}.panel,.team,.hero{{box-shadow:none;break-inside:avoid}}.scroll.tall{{max-height:none}}}}
</style>
</head>
<body><main class="wrap">
<section class="hero">
  <a href="intel_prematch.html">← 返回赛前情报总览</a>
  <h1>{esc(row.get("teams", ["", ""])[0])}<span>vs</span>{esc(row.get("teams", ["", ""])[1])}</h1>
  <div class="meta"><span>{esc(row.get("sport_short"))}</span><span>{esc(row.get("league"))}</span><span>{esc(row.get("start_at_bj"))}</span><span>{esc(row.get("format"))}</span><span>{esc(row.get("status"))}</span><span>生成 {esc(snapshot.get("generated_at_bj"))}</span></div>
  <div class="coverage">{''.join(f'<span>{esc(bit)}</span>' for bit in bits)}</div>
  <div class="meta">
    <a href="{esc(row.get("detail_json_url") or "intel_prematch.json")}" download>下载完整 JSON</a>
    <a href="{esc(row.get("detail_csv_url") or "")}" download>下载指标 CSV</a>
    <a href="javascript:window.print()">打印 / 另存为 PDF</a>
  </div>
  <p class="note">所有表格支持点击表头排序；完整原始字段以 JSON 为准。</p>
</section>
{quality_block(row)}
<section class="panel"><h2>赛前市场共识</h2>{odds_block(row)}<p class="note">十进制赔率与去水概率只作赛前市场参考；完整底层 JSON 可从总览页进入。</p></section>
{body}
<p class="note">名单与近期统计来自本场页面下发的结构化数据。最近首发、训练名单或赛事 roster 不等同于已确认的本场官方首发；缺失字段保持为空并标记样本不足。</p>
</main>
<script>
(() => {{
  function valueOf(text) {{
    const cleaned = String(text).replace(/,/g, '').replace('%', '');
    const number = Number.parseFloat(cleaned);
    return Number.isFinite(number) ? number : String(text).toLowerCase();
  }}
  document.querySelectorAll('table').forEach(table => {{
    const head = table.tHead;
    const body = table.tBodies[0];
    if (!head || !body || head.rows.length !== 1) return;
    [...head.rows[0].cells].forEach((cell, index) => {{
      let asc = true;
      cell.addEventListener('click', () => {{
        const rows = [...body.rows];
        rows.sort((a, b) => {{
          const av = valueOf((a.cells[index] || {{}}).textContent || '');
          const bv = valueOf((b.cells[index] || {{}}).textContent || '');
          if (typeof av === 'number' && typeof bv === 'number') return asc ? av - bv : bv - av;
          return asc ? String(av).localeCompare(String(bv), 'zh-CN') : String(bv).localeCompare(String(av), 'zh-CN');
        }});
        rows.forEach(row => body.appendChild(row));
        asc = !asc;
      }});
    }});
  }});
}})();
</script>
</body></html>"""


def _base_name(row: dict[str, Any]) -> str:
    raw = str(row.get("fixture_slug") or row.get("id") or "match")
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", raw).strip("-")
    return f"intel_prematch_detail_{row.get('sport', 'match')}_{safe}"


def filename_for(row: dict[str, Any]) -> str:
    return f"{_base_name(row)}.html"


def json_filename_for(row: dict[str, Any]) -> str:
    return f"{_base_name(row)}.json"


def csv_filename_for(row: dict[str, Any]) -> str:
    return f"{_base_name(row)}.csv"


def _flatten_metric_rows(
    metrics: dict[str, Any],
    *,
    section: str,
    team: str = "",
    player: str = "",
) -> list[dict[str, Any]]:
    rows = []
    for key, value in metrics.items():
        if not isinstance(value, dict):
            continue
        if "avg" in value or "average" in value or "total" in value:
            rows.append(
                {
                    "section": section,
                    "team": team,
                    "player": player,
                    "metric": key,
                    "group": "",
                    "avg": value.get("avg", value.get("average")),
                    "percentile": value.get("percentile"),
                    "total": value.get("total"),
                    "sample_size": value.get("sample_size"),
                }
            )
            continue
        for group, nested in value.items():
            if not isinstance(nested, dict):
                continue
            rows.append(
                {
                    "section": section,
                    "team": team,
                    "player": player,
                    "metric": key,
                    "group": group,
                    "avg": nested.get("avg", nested.get("average")),
                    "percentile": nested.get("percentile"),
                    "total": nested.get("total"),
                    "sample_size": nested.get("sample_size"),
                }
            )
    return rows


def export_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if row.get("oddin"):
        deep = row["oddin"]
        for side in ("home", "away"):
            team = deep.get(side) or {}
            team_name = team.get("name") or ""
            rows.extend(_flatten_metric_rows(team.get("metrics") or {}, section="team_metric", team=team_name))
            for player in team.get("players") or []:
                rows.extend(
                    _flatten_metric_rows(
                        player.get("metrics") or {},
                        section="player_metric",
                        team=team_name,
                        player=player.get("nickname") or "",
                    )
                )
            for item in team.get("map_pool") or []:
                rows.append(
                    {
                        "section": "map_pool",
                        "team": team_name,
                        "entity": item.get("name"),
                        "metric": "win_rate",
                        "avg": (item.get("win_rate") or {}).get("avg"),
                        "percentile": (item.get("win_rate") or {}).get("percentile"),
                        "total": (item.get("win_rate") or {}).get("total"),
                    }
                )
            for item in team.get("favorites") or []:
                for metric, value in (item.get("metrics") or {}).items():
                    rows.append(
                        {
                            "section": "team_favorite",
                            "team": team_name,
                            "entity": item.get("name"),
                            "metric": metric,
                            "avg": (value or {}).get("avg"),
                            "percentile": (value or {}).get("percentile"),
                            "total": (value or {}).get("total"),
                        }
                    )
        for item in (deep.get("head_to_head") or {}).get("matches") or []:
            rows.append(
                {
                    "section": "head_to_head",
                    "entity": f"{(item.get('home') or {}).get('name')} vs {(item.get('away') or {}).get('name')}",
                    "metric": "score",
                    "value": (item.get("score") or {}).get("display") if isinstance(item.get("score"), dict) else item.get("score"),
                    "date": item.get("planned_start") or "",
                }
            )
        stats = (deep.get("tournament") or {}).get("stats") or {}
        for kind, key in (("tournament_best_team", "best_teams"), ("tournament_best_player", "best_players")):
            for item in stats.get(key) or []:
                subject = (
                    (item.get("player") or {}).get("nickname")
                    if kind.endswith("player")
                    else (item.get("team") or {}).get("name")
                )
                rows.append(
                    {
                        "section": kind,
                        "entity": subject,
                        "metric": item.get("metric"),
                        "value": item.get("value"),
                    }
                )
    elif row.get("lmt"):
        deep = row["lmt"]
        for side in ("home", "away"):
            team = deep.get(side) or {}
            team_name = team.get("name") or ""
            rows.extend(_flatten_metric_rows(team.get("season_stats") or {}, section="season_metric", team=team_name))
            for player in team.get("squad") or []:
                rows.append(
                    {
                        "section": "squad",
                        "team": team_name,
                        "player": player.get("name"),
                        "metric": "profile",
                        "value": json.dumps(player, ensure_ascii=False),
                    }
                )
            for item in team.get("injuries") or []:
                rows.append(
                    {
                        "section": "injury",
                        "team": team_name,
                        "player": item.get("player"),
                        "metric": item.get("status"),
                        "value": item.get("comment"),
                    }
                )
    return rows


def render_csv(row: dict[str, Any]) -> str:
    columns = [
        "section",
        "team",
        "player",
        "entity",
        "metric",
        "group",
        "avg",
        "percentile",
        "total",
        "sample_size",
        "value",
        "date",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for item in export_rows(row):
        writer.writerow(item)
    return buffer.getvalue()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_detail(
    row: dict[str, Any],
    output_dir: str | Path,
    snapshot: dict[str, Any],
) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    html_name = filename_for(row)
    json_name = json_filename_for(row)
    csv_name = csv_filename_for(row)
    row["detail_url"] = html_name
    row["detail_json_url"] = json_name
    row["detail_csv_url"] = csv_name
    _atomic_write(output / html_name, render_page(row, snapshot))
    _atomic_write(
        output / json_name,
        json.dumps(row, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write(output / csv_name, render_csv(row))
    return html_name


def cleanup_stale(output_dir: str | Path, keep: set[str]) -> int:
    output = Path(output_dir)
    if not output.exists():
        return 0
    removed = 0
    for path in output.glob("intel_prematch_detail_*"):
        if path.suffix not in {".html", ".json", ".csv"} or path.name in keep:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed
