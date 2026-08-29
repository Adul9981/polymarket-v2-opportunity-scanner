#!/usr/bin/env python3
"""VPS -> GitHub Pages auto-publish: sync generated intel pages to danmu-intel repo.

服务器端：把 /opt/danmu-intel/reports/ 下生成的弹幕情报页同步到
站点仓库（.danmu_intel_site 对应 GitHub Adul9981/danmu-intel）并自动 push，
实现"服务器产出 -> 网站实时更新"。由 systemd timer 每 5 分钟触发（幂等：
无新文件不提交）。

首次需要 GitHub Deploy Key：~/.ssh/github_deploy（已生成），
公钥添加到 Adul9981/danmu-intel Settings -> Deploy keys（勾选写权限）。
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_favicon import inject_all as favicon_inject  # noqa: E402
from add_paywall import inject_all as paywall_inject  # noqa: E402
from add_paywall import page_key as paywall_page_key  # noqa: E402
from speedcard_consistency import check_page as speedcard_check  # noqa: E402
from add_site_nav import inject_all as nav_inject  # noqa: E402
from add_stats_track import inject_all as track_inject  # noqa: E402

ROOT = Path("/opt/danmu-intel")
REPORTS = ROOT / "reports"
REPO = ROOT / "site_repo"
KEY = Path.home() / ".ssh" / "github_deploy"
GIT_SSH = f"ssh -i {KEY} -o StrictHostKeyChecking=accept-new"
PATTERNS = ("intel_danmu_*.html", "intel_soop_*.html", "intel_profile_*.html", "intel_gray_*.html", "match_*.html", "case_*.html")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = GIT_SSH
    return subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True)


def regen_today_page(repo: Path) -> None:
    """Rebuild intel/today.html from latest scan + published pages (best effort).

    服务器每 5 分钟重建今日页：比赛节点（赛前/局中/复盘）一发布，
    今日页的"情报 →"入口自动出现，无需本地再跑一次（教训 2026-08-25：
    今日页曾依赖本地重建，服务器新节点上线后页面无入口）。
    """
    try:
        env = dict(os.environ)
        r = subprocess.run(
            [
                str(ROOT / ".venv" / "bin" / "python"),
                str(ROOT / "tools" / "update_site_today.py"),
                # 今日页按北京时间生成（教训 2026-08-26：UTC 日期会让
                # 北京已到次日时页面仍显示前一天）
                "--date", datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(hours=8))
                ).date().isoformat(),
                "--site-dir", str(repo),
            ],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"[publish] today page regen rc={r.returncode}: {r.stderr[-200:]}")
    except Exception as e:  # noqa: BLE001
        print(f"[publish] today page regen failed (non-fatal): {e}")


def rebuild_match_shells() -> int:
    """发布前重建全部比赛时间轴壳（2026-08-27 教训：节点生成后壳未更新，
    导致线上入口显示"暂未采集"——发布以 reports 为准重建壳，兜底防漏）。"""
    import vps_intel_pipeline as V

    V.REPORTS = REPORTS
    matches: list[dict] = []
    for p in (
        ROOT / "docs" / "data" / "intel" / "matches.json",
        ROOT / "data" / "matches_today.json",
    ):
        try:
            md = json.loads(p.read_text(encoding="utf-8"))
            matches += md.get("matches", [])
        except Exception:  # noqa: BLE001
            pass
    seen: set[str] = set()
    for m in matches:
        mid = m.get("id") or m.get("event_slug") or ""
        teams = m.get("teams", [])
        if not mid or len(teams) != 2 or mid in seen or m.get("intel_voided"):
            continue
        seen.add(mid)
        date = (m.get("start_time") or m.get("date") or "")[:10]
        max_games = V.format_of(m) if hasattr(V, "format_of") else 5
        try:
            V.build_timeline_shell(mid, teams, m.get("league", "-"), date, max_games)
        except Exception:  # noqa: BLE001
            pass
    print(f"[publish] rebuilt {len(seen)} match shells", flush=True)
    return len(seen)


def sync_game_status(repo: Path) -> None:
    """拉取 GitHub Actions 推送的 data 分支（小局状态 + 结算），落地供流水线/回填使用。

    2026-08-25：彻底摆脱本机——小局状态与结算改由云端每 5 分钟抓取，
    服务器发布时从 data 分支拉取（无需 Secret）。
    """
    try:
        env = dict(os.environ)
        env["GIT_SSH_COMMAND"] = GIT_SSH
        r = subprocess.run(
            ["git", "-C", str(repo), "fetch", "origin", "data:refs/remotes/origin/data"],
            env=env, capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"[publish] data branch fetch failed: {r.stderr[-200:]}")
            return
        for name, branch_path, dst in (
            ("game_status.json", "intel/game_status.json", ROOT / "data" / "game_status.json"),
            ("settlements.json", "intel/settlements.json", ROOT / "runtime" / "settlements.json"),
            ("matches_today.json", "data/matches_today.json", ROOT / "data" / "matches_today.json"),
            ("watchlist_events.json", "data/watchlist_events.json", ROOT / "runtime" / "watchlist_events.json"),
        ):
            r2 = subprocess.run(
                ["git", "-C", str(repo), "show", f"origin/data:{branch_path}"],
                env=env, capture_output=True, text=True, timeout=60,
            )
            if r2.returncode == 0 and r2.stdout.strip():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(r2.stdout, encoding="utf-8")
        print("[publish] game_status/settlements synced from cloud", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[publish] game_status sync failed (non-fatal): {e}")


def merge_settlements() -> None:
    """把云端结算合并进服务器 matches.json（结果回填，幂等）。"""
    try:
        src = ROOT / "runtime" / "settlements.json"
        mj = ROOT / "docs" / "data" / "intel" / "matches.json"
        if not src.exists() or not mj.exists():
            return
        s = json.loads(src.read_text(encoding="utf-8")).get("settlements", {})
        if not s:
            return
        d = json.loads(mj.read_text(encoding="utf-8"))
        ml = d.get("matches", [])
        by = {str(m.get("id") or m.get("slug") or ""): m for m in ml}
        # 2026-08-29：结算 slug 常等于 canonical 条目的 event_slug
        # （如 lol-tt-ig1 对应 id=lpl-tt-ig、event_slug=lol-tt-ig1）。
        # 只按 id/slug 匹配会漏 event_slug，导致每次发布重复追加结算条目
        # （教训：8-28 六场结算后 matches.json 出现双份 BRO-BFX/NAVI-paiN）。
        by_event = {str(m.get("event_slug") or ""): m for m in ml if m.get("event_slug")}
        added = 0
        for slug, v in s.items():
            m = by.get(slug) or by_event.get(slug)
            if m:
                if not m.get("event_slug"):
                    m["event_slug"] = slug  # 结算合并时补 event_slug（市场链接页依赖）
                    added += 1
                if not m.get("result_inferred"):
                    m["result_inferred"] = f"{v.get('winner')} 胜（Polymarket 结算）"
                    added += 1
                continue
            league = "LoL" if slug.startswith("lol-") else ("CS2" if slug.startswith("cs2-") else ("Dota2" if slug.startswith("dota2-") else "-"))
            ml.append({
                "id": slug, "slug": slug, "date": v.get("date", ""),
                "teams": v.get("teams", []), "league": league,
                "result_inferred": f"{v.get('winner')} 胜（Polymarket 结算）",
            })
            added += 1
        if added:
            d["matches"] = ml
            d["updated_at"] = datetime.date.today().isoformat()
            mj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[publish] merged {added} settlements into matches.json", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[publish] settlements merge failed (non-fatal): {e}")


def rebuild_history(repo: Path) -> None:
    """重建历史情报库页（本机离线后由服务器维护历史页新鲜度）。"""
    try:
        env = dict(os.environ)
        subprocess.run(
            [str(ROOT / ".venv" / "bin" / "python"),
             str(ROOT / "tools" / "build_history_index.py"),
             "--site-dir", str(repo)],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120,
        )
        print("[publish] history rebuilt", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[publish] history rebuild failed (non-fatal): {e}")


def finished_slugs() -> frozenset[str]:
    """已结束比赛的 slug 集合（settlements / 全小局 closed / matches.json 结果回填）。

    2026-08-26 产品规则：已结束比赛的实时情报对免费用户开放，付费墙按此判定。
    """
    out: set[str] = set()
    try:
        s = json.loads((ROOT / "runtime" / "settlements.json").read_text(encoding="utf-8"))
        out |= set((s.get("settlements") or {}).keys())
    except Exception:  # noqa: BLE001
        pass
    try:
        g = json.loads((ROOT / "data" / "game_status.json").read_text(encoding="utf-8"))
        for slug, gs in (g.get("games") or {}).items():
            if gs and all(bool(m.get("closed")) for m in gs.values()):
                out.add(slug)
    except Exception:  # noqa: BLE001
        pass
    try:
        d = json.loads((ROOT / "docs" / "data" / "intel" / "matches.json").read_text(encoding="utf-8"))
        for m in d.get("matches", []):
            if m.get("event_slug") and m.get("result_inferred"):
                out.add(str(m["event_slug"]))
    except Exception:  # noqa: BLE001
        pass
    return frozenset(out)


def finished_keys() -> frozenset[str]:
    """已结束比赛的文件名键集合（date|team1|team2，归一），兜底旧页无 slug 场景。"""
    out: set[str] = set()
    try:
        s = json.loads((ROOT / "runtime" / "settlements.json").read_text(encoding="utf-8"))
        for v in (s.get("settlements") or {}).values():
            teams = v.get("teams") or []
            if len(teams) == 2:
                from add_paywall import _norm_team
                out.add(f"{v.get('date')}|{'-'.join(sorted([_norm_team(teams[0]), _norm_team(teams[1])]))}")
    except Exception:  # noqa: BLE001
        pass
    try:
        d = json.loads((ROOT / "docs" / "data" / "intel" / "matches.json").read_text(encoding="utf-8"))
        for m in d.get("matches", []):
            teams = m.get("teams") or []
            if m.get("result_inferred") and len(teams) == 2:
                from add_paywall import _norm_team
                out.add(f"{m.get('date')}|{'-'.join(sorted([_norm_team(teams[0]), _norm_team(teams[1])]))}")
    except Exception:  # noqa: BLE001
        pass
    return frozenset(out)


def heartbeat(repo: Path) -> None:
    """空闲心跳：每 6 小时推一次提交，触发云端数据刷新兜底。

    GitHub Actions 定时器对新增工作流可能延迟/不触发（2026-08-25 实测 0 次
    schedule run），推送触发已兜底比赛时段；离线时段靠心跳保证每日清单刷新。
    """
    try:
        f = repo / "intel" / ".heartbeat"
        last = f.stat().st_mtime if f.exists() else 0
        if time.time() - last < 6 * 3600:
            return
        f.write_text(
            datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds") + "\n",
            encoding="utf-8",
        )
        print("[publish] heartbeat（云端数据刷新兜底）", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[publish] heartbeat failed (non-fatal): {e}")


def audit_site(repo: Path) -> int:
    """站点结构完整性审计：坏页面一律阻止发布。

    今日情报页是"网站架构与显示"头号防错对象（2026-08-25 用户定调）。
    检查：每页恰好 1 条导航 / 今日页无旧模板导航残留 / 实时页必须带付费墙 /
    嵌入脚本每页 ≤1。任何一项异常即阻止本次发布。
    """
    bad: list[tuple[str, str]] = []
    pro_re = re.compile(r"intel_danmu_.*_(pre|live|bp|g[1-9])(?:[_.].*)?\.html$", re.I)
    fslugs = finished_slugs()
    fkeys = finished_keys()
    for p in repo.rglob("*.html"):
        rel = str(p.relative_to(repo))
        t = p.read_text(encoding="utf-8", errors="ignore")
        n = len(re.findall(r"<nav[^>]*>", t))
        if n != 1:
            bad.append((rel, f"nav={n}"))
        if t.count('location.search.indexOf("embed=1")') > 1:
            bad.append((rel, "embed>1"))
        if rel == "intel/today.html" and 'class="inner"' in t:
            bad.append((rel, "旧模板导航残留"))
        m = re.search(
            r"(?:slug[=：]\s*)?((?:lol|cs2|dota2?)-[a-z0-9][a-z0-9-]*-\d{4}-\d{2}-\d{2})",
            t,
            re.I,
        )
        pk = paywall_page_key(p.name)
        finished = bool(
            (m and m.group(1).lower() in fslugs) or (pk and pk in fkeys)
        )
        if pro_re.search(p.name) and not finished and "danmu_member_v1" not in t:
            bad.append((rel, "缺付费墙"))
        if "核心情报速览" in t:
            bad_cats = speedcard_check(t)
            if bad_cats:
                bad.append((rel, f"速览卡与正文不一致:{bad_cats}"))
    if bad:
        print(f"[publish] SITE AUDIT FAIL: {len(bad)} 项异常，阻止本次发布")
        for x in bad[:15]:
            print("   ", x)
    return len(bad)


def main() -> int:
    if not KEY.exists():
        print("[publish] no deploy key, skip")
        return 1
    if not REPO.exists():
        print("[publish] cloning site repo...")
        env = dict(os.environ)
        env["GIT_SSH_COMMAND"] = GIT_SSH
        r = subprocess.run(
            ["git", "clone", "git@github.com:Adul9981/danmu-intel.git", str(REPO)],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            print(f"[publish] clone failed: {r.stderr[-300:]}")
            return 1

    # 2026-08-27 教训：site_repo 曾卡在残留 interactive rebase 导致发布连续
    # push 失败（rc=128）、线上停更数小时——发布前先清理残留 rebase 状态
    if (REPO / ".git" / "rebase-merge").exists() or (REPO / ".git" / "rebase-apply").exists():
        git(REPO, "rebase", "--abort", "-q")
        print("[publish] 清理残留 rebase 状态", flush=True)
    # 2026-08-27 教训：site_repo 反复出现游离 HEAD（no branch）导致
    # commit/push 全部异常、线上停更——发布前必须确保在 main 分支
    cur = git(REPO, "branch", "--show-current").stdout.strip()
    if cur != "main":
        git(REPO, "checkout", "-f", "main", "-q")
        print(f"[publish] 切回 main 分支（原状态 {cur or 'detached'}）", flush=True)
    # 优先 rebase 保留远端（本地站点 push）提交；冲突时回退到远端基线
    # （reports 是数据源，重新注入即可），避免双端互相覆盖（教训 2026-08-25）
    git(REPO, "fetch", "origin", "-q")
    if git(REPO, "rebase", "origin/main", "-q").returncode != 0:
        git(REPO, "rebase", "--abort", "-q")
        git(REPO, "reset", "--hard", "origin/main", "-q")
    sync_game_status(REPO)
    # 速览卡 ↔ 正文一致性：先修源（reports）再复制，保证修复持久化，
    # 避免"复制未修源 -> 每次发布都重复 LLM 改写"（2026-08-26 固化）。
    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"),
         str(ROOT / "tools" / "speedcard_consistency.py"),
         "--fix", "--dir", str(REPORTS)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600,
    )
    target = REPO / "intel"
    target.mkdir(parents=True, exist_ok=True)
    rebuild_match_shells()  # 2026-08-27：节点生成后壳必须最新（防线上入口缺失）
    copied = 0
    for pattern in PATTERNS:
        for f in REPORTS.glob(pattern):
            shutil.copy2(f, target / f.name)
            copied += 1
    # 先重建今日页，再统一注入导航/favicon——保证今日页用同一套导航
    # （教训 2026-08-25：注入在前、重建在后会把生成器旧导航重新推上线）
    regen_today_page(REPO)
    merge_settlements()
    # 队伍情报库自动沉淀（2026-08-26 用户定稿）：每场结算后自动把弹幕统计
    # 合并进 teams.json + TEAM_PROFILES.md（幂等，runtime/accumulated_matches.json 防重复）
    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"),
         str(ROOT / "tools" / "accumulate_team_intel.py"),
         "--root", str(ROOT)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=180,
    )
    rebuild_history(REPO)
    # 首页今日区块（2026-08-27：首页与今日页一致展示比赛+进展）
    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"),
         str(ROOT / "tools" / "build_home_today.py"),
         "--site-dir", str(REPO)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    # 清理未进行的 G5 孤儿页（系列 3-1/2-0 结束，G5 从未开打）。
    # 教训 2026-08-26：KT 3-2 BRO 打到 G5，g5_bp 是真节点，曾被无条件误删——
    # 现在只清理"结果明确未打到 G5"的比赛页。
    reached_g5: set[str] = set()
    try:
        md = json.loads((ROOT / "docs" / "data" / "intel" / "matches.json").read_text(encoding="utf-8"))
        for m in md.get("matches", []):
            r = (m.get("result_inferred") or "").replace(" ", "")
            if "3:2" in r or "3-2" in r:
                if m.get("event_slug"):
                    reached_g5.add(str(m["event_slug"]))
    except Exception:  # noqa: BLE001
        pass
    for p in (REPO / "intel").glob("intel_danmu_*_g5_*.html"):
        if reached_g5:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
                if any(s in txt for s in reached_g5):
                    continue  # 系列打到 G5，保留真节点
            except OSError:
                pass
        try:
            p.unlink()
            print(f"[publish] 清理未进行 G5 页: {p.name}", flush=True)
        except OSError:
            pass
    nav_inject(REPO)
    favicon_inject(REPO)
    track_inject(REPO)
    # 实时/赛前节点页必须带付费墙（Pro 层），否则实时情报免费可见
    paywall_inject(REPO / "intel", finished_slugs(), finished_keys())
    # 速览卡 ↔ 正文一致性：自动修复 + 审计门禁（2026-08-26 最高规则）
    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"),
         str(ROOT / "tools" / "speedcard_consistency.py"),
         "--fix", "--dir", str(REPO / "intel")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600,
    )
    if audit_site(REPO) > 0:
        return 2

    git(REPO, "add", "-A")
    status = git(REPO, "status", "--porcelain").stdout.strip()
    if not status:
        heartbeat(REPO)
        git(REPO, "add", "-A")
        status = git(REPO, "status", "--porcelain").stdout.strip()
        if not status:
            print(f"[publish] {datetime.datetime.now():%F %T} nothing changed")
            return 0
    git(REPO, "commit", "-m", f"auto publish intel pages {datetime.date.today()}", "-q")
    r = git(REPO, "push", "-q")
    print(f"[publish] {datetime.datetime.now():%F %T} pushed {copied} report files rc={r.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
