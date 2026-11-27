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

import argparse
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
from add_assistant import inject_all as assistant_inject  # noqa: E402
from add_paywall import inject_all as paywall_inject  # noqa: E402
from add_paywall import page_key as paywall_page_key  # noqa: E402
from add_site_nav import inject_all as nav_inject  # noqa: E402
from add_stats_track import inject_all as track_inject  # noqa: E402
import analytics_publish  # noqa: E402
import build_site_search as site_search  # noqa: E402

ROOT = Path("/opt/danmu-intel")
REPORTS = ROOT / "reports"
REPO = ROOT / "site_repo"
WEBROOT = Path("/var/www/danmu-pulse")
FREE_MODE_FLAG = ROOT / "runtime" / "free_mode.flag"
KEY = Path.home() / ".ssh" / "github_deploy"
GIT_SSH = f"ssh -i {KEY} -o StrictHostKeyChecking=accept-new"
PATTERNS = (
    "intel_danmu_*.html",
    "intel_soop_*.html",
    "intel_prematch*",
    "intel_help.html",
    "assistant.*",
    "match_*.html",
    "case_*.html",
)
PATTERN_WORKSPACE = (
    ROOT / "pattern-decision" / "live" / "reports" / "pattern_decision_workspace.html"
)
PATTERN_ATLAS = ROOT / "pattern-decision" / "live" / "reports" / "pattern_atlas.html"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = GIT_SSH
    return subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True)


def free_mode() -> bool:
    """2026-09-08 全公开模式：runtime/free_mode.flag 存在 = 会员系统关闭、全员公开。
    删除 flag 即恢复付费墙（free=False 重新注入）。"""
    try:
        return FREE_MODE_FLAG.exists()
    except OSError:
        return False


def serve_webroot(repo: Path, webroot: Path) -> int:
    """把审计通过后的站点目录同步到 nginx webroot（秒级直出，2026-09-02 M1）。

    同步规则：repo 为源（含注入后的 nav/favicon/打点/付费墙），webroot 为镜像；
    删除 webroot 中已不存在的旧项（含被清理的 G5 页），保证一致性。
    """
    try:
        if not repo.exists():
            print(f"[publish] serve_webroot: 源目录不存在 {repo}", flush=True)
            return 0
        webroot.mkdir(parents=True, exist_ok=True)
        # 清理 webroot 中 repo 已删除的旧项
        for item in webroot.iterdir():
            if item.name == ".git":
                continue
            if not (repo / item.name).exists():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
        # 同步 repo -> webroot（全量复制，同机本地，5 分钟一次可接受）
        for item in repo.iterdir():
            if item.name == ".git":
                continue
            dst = webroot / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        # 2026-09-02 M3：为已上线节点的状态文件补 published_at（SLA 四段时间戳）
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        for stf in (ROOT / "runtime" / "vps_intel").glob("*_g*.json"):
            if "_intel" in stf.name or "fail" in stf.name:
                continue
            try:
                d = json.loads(stf.read_text(encoding="utf-8"))
                rp = d.get("report", "")
                if rp and Path(rp).exists() and (webroot / "intel" / Path(rp).name).exists():
                    # 2026-09-02 修复：只补首次发布（published_at=快报上线时刻），
                    # 禁止每次循环覆盖（历史节点曾被刷成当前时间，失真）
                    if "published_at" not in d:
                        d["published_at"] = now
                    stf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
        print(f"[publish] served webroot {webroot}", flush=True)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[publish] serve_webroot failed: {e}", flush=True)
        return 0


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


def build_situation_json() -> None:
    """跑 build_situation_page.py 生成 data/situation_live.json（规则层实时局势）。

    独立「比赛局势」页（match_situation.html）的实时数据源：胜率=累积弹幕口径、
    评分=虎扑按小局实时。与情报页比赛局势栏（refresh_situation.py 注入节点页）互不干扰。
    """
    try:
        env = dict(os.environ)
        subprocess.run(
            [str(ROOT / ".venv" / "bin" / "python"),
             str(ROOT / "tools" / "build_situation_page.py"), "--once"],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[publish] situation json build failed (non-fatal): {e}")


def copy_situation_files(repo: Path) -> int:
    """把比赛局势页 + 数据 JSON 同步进站点仓库（静态页幂等覆盖，JSON 每轮最新）。"""
    n = 0
    target = repo / "intel"
    target.mkdir(parents=True, exist_ok=True)
    src_page = ROOT / "tools" / "templates" / "match_situation.html"
    if src_page.exists():
        shutil.copy2(src_page, target / "match_situation.html")
        n += 1
    src_json = ROOT / "data" / "situation_live.json"
    if src_json.exists():
        shutil.copy2(src_json, target / "situation_live.json")
        n += 1
    if n:
        print(f"[publish] situation page/json synced ({n} files)", flush=True)
    return n


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


MIRROR_MIN_INTERVAL = 600  # 镜像推送最小间隔（秒，2026-10-11 固化）
_MIRROR_STATE = ROOT / "runtime" / "vps_mirror_last_push.txt"
# "每轮必变"的易变文件：实时刷新页的统计计数、空闲心跳。
# 它们单独变化不构成"站点内容变化"，不值得每次都触发 GitHub Pages 重建。
_VOLATILE_NAMES = ("intel_danmu_live_vps_",)
_VOLATILE_EXACT = (".heartbeat", "situation_live.json")


def volatile_path(p: str) -> bool:
    """改动是否属于易变文件（实时页/心跳）。"""
    name = Path(p).name
    return name in _VOLATILE_EXACT or any(name.startswith(v) for v in _VOLATILE_NAMES)


def _last_mirror_push() -> float:
    try:
        return float(_MIRROR_STATE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0.0


def _mark_mirror_push() -> None:
    try:
        _MIRROR_STATE.parent.mkdir(parents=True, exist_ok=True)
        _MIRROR_STATE.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def _clear_stale_index_lock(repo: Path) -> None:
    """发布前清理陈旧 .git/index.lock。

    教训 2026-10-26：git add/commit 被中断会留下 0 字节 index.lock，之后每次
    git add 都因锁存在而失败（rc!=0）；脚本又不查 add/commit 返回码，导致每分钟
    "pushed rc=0" 假成功、线上停更 4+ 小时。site_repo 只被本 oneshot 脚本触碰，
    发布起点（fetch/rebase 已完成）残留的锁必为陈旧，直接删除兜底。
    """
    lock = repo / ".git" / "index.lock"
    try:
        if lock.exists():
            lock.unlink()
            print("[publish] 清理陈旧 index.lock", flush=True)
    except OSError as e:  # noqa: BLE001
        print(f"[publish] WARN: 清理 index.lock 失败 {e}", flush=True)


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
    pro_re = re.compile(
        r"(?:intel_danmu_.*_(pre|live|bp|g[1-9])(?:[_.].*)?|intel_profile_.*)\.html$",
        re.I,
    )
    fslugs = finished_slugs()
    fkeys = finished_keys()
    # 2026-08-30：测试/隐藏残留文件不参与审计、不随发布上线
    # （教训：VPS 上 test_nav/权限测试遗留的 test space.html / .wtest_* 等
    # 文件导致 SITE AUDIT FAIL，发布被卡数小时，今日/历史页全部停更）。
    test_re = re.compile(r"(^|[\\/])[._]?(test|wtest|zz_site_test|permtest|tmp_test)", re.I)
    for p in repo.rglob("*.html"):
        if p.name.startswith("._"):
            continue
        rel = str(p.relative_to(repo))
        if test_re.search(rel):
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[publish] audit skip non-utf8 file: {rel}", flush=True)
            continue
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
        if not free_mode() and pro_re.search(p.name) and not finished and "danmu_member_v1" not in t:
            bad.append((rel, "缺付费墙"))
    # 2026-09-02 M3：格式门禁（非阻塞）——旧格式/结构异常仅告警，不卡发布
    fmt_bad = 0
    for p in (repo / "intel").glob("intel_danmu_*_g*.html"):
        s = p.read_text(encoding="utf-8", errors="ignore")
        if "核心情报速览" in s or not re.search(r'class="no">\d+</span>', s):
            fmt_bad += 1
    if fmt_bad:
        print(f"[publish] WARN: {fmt_bad} 页仍为旧格式/结构异常（非阻塞，仅告警）", flush=True)
    if bad:
        print(f"[publish] SITE AUDIT FAIL: {len(bad)} 项异常，阻止本次发布")
        for x in bad[:15]:
            print("   ", x)
    return len(bad)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="发布弹幕情报到站点（nginx 直出 + GitHub Pages 镜像）")
    ap.add_argument("--no-mirror", action="store_true",
                    help="跳过 GitHub Pages 镜像 push（仅同步 nginx webroot）")
    ap.add_argument("--no-serve", action="store_true",
                    help="跳过 nginx webroot 同步（仅推 GitHub Pages 镜像）")
    args = ap.parse_args(argv)

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
    target = REPO / "intel"
    target.mkdir(parents=True, exist_ok=True)
    for stale in target.glob("intel_prematch_detail_*"):
        if stale.is_file():
            stale.unlink(missing_ok=True)
    analytics_publish.prepare_release(ROOT, REPORTS, target)
    rebuild_match_shells()  # 2026-08-27：节点生成后壳必须最新（防线上入口缺失）
    build_situation_json()  # 独立比赛局势页的实时数据（规则层，零 AI）
    copy_situation_files(REPO)  # 局势页 + situation_live.json 进站点仓库
    copied = 0
    for pattern in PATTERNS:
        for f in REPORTS.glob(pattern):
            shutil.copy2(f, target / f.name)
            copied += 1
    # The repository reset above restores the previously published workspace.
    # Always reinstall the VPS-built page so publishing cannot roll it back.
    if PATTERN_WORKSPACE.exists():
        shutil.copy2(PATTERN_WORKSPACE, target / PATTERN_WORKSPACE.name)
        copied += 1
    else:
        print(f"[publish] WARN: pattern workspace missing: {PATTERN_WORKSPACE}", flush=True)
    if PATTERN_ATLAS.exists():
        shutil.copy2(PATTERN_ATLAS, target / PATTERN_ATLAS.name)
        copied += 1
    else:
        print(f"[publish] WARN: pattern atlas missing: {PATTERN_ATLAS}", flush=True)
    # 先重建今日页，再统一注入导航/favicon——保证今日页用同一套导航
    # （教训 2026-08-25：注入在前、重建在后会把生成器旧导航重新推上线）
    regen_today_page(REPO)
    merge_settlements()
    # 2026-10-24 用户定稿：不再生成/发布四维画像库、地图战绩、灰信号·验证闭环三个特征页（省算力）。
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
    # 2026-09-02 修复：保留依据 = runtime/vps_intel 的 g5 状态文件（真实 G5 节点），
    # 不再依赖 matches.json 文字比分（教训：NSEA-DNSC / KT.C-DRX.C / KT-BRO 真 G5
    # 页面曾因 result_inferred 无 "3:2" 字样被误删）。
    reached_g5_reports: set[str] = set()
    for stf in (ROOT / "runtime" / "vps_intel").glob("*_g5_*.json"):
        if "_intel" in stf.name or "fail" in stf.name:
            continue
        try:
            rp = json.loads(stf.read_text(encoding="utf-8")).get("report", "")
            if rp:
                reached_g5_reports.add(Path(rp).name)
        except Exception:  # noqa: BLE001
            pass
    for p in (REPO / "intel").glob("intel_danmu_*_g5_*.html"):
        if p.name in reached_g5_reports:
            continue
        try:
            p.unlink()
            print(f"[publish] 清理未进行 G5 页: {p.name}", flush=True)
        except OSError:
            pass
    search_counts = site_search.build_all(REPO)
    print(f"[publish] site search rebuilt: {search_counts}", flush=True)
    nav_inject(REPO)
    favicon_inject(REPO)
    track_inject(REPO)
    assistant_inject(REPO)
    # 实时/赛前节点页必须带付费墙（Pro 层），否则实时情报免费可见
    paywall_inject(REPO / "intel", finished_slugs(), finished_keys(), free=free_mode())
    if audit_site(REPO) > 0:
        return 2

    # nginx 直出（2026-09-02 M1）：审计通过后同步 webroot，秒级上线
    if not args.no_serve:
        serve_webroot(REPO, WEBROOT)
    if args.no_mirror:
        print(f"[publish] {datetime.datetime.now():%F %T} mirror skipped (--no-mirror)")
        return 0

    _clear_stale_index_lock(REPO)
    r_add = git(REPO, "add", "-A")
    if r_add.returncode != 0:
        print(f"[publish] {datetime.datetime.now():%F %T} WARN: git add 失败 rc={r_add.returncode}: {r_add.stderr.strip()[-200:]}")
        return 3
    status = git(REPO, "status", "--porcelain").stdout.strip()
    if not status:
        heartbeat(REPO)
        r_add = git(REPO, "add", "-A")
        if r_add.returncode != 0:
            print(f"[publish] {datetime.datetime.now():%F %T} WARN: git add 失败 rc={r_add.returncode}: {r_add.stderr.strip()[-200:]}")
            return 3
        status = git(REPO, "status", "--porcelain").stdout.strip()
        if not status:
            print(f"[publish] {datetime.datetime.now():%F %T} nothing changed")
            return 0
    # 镜像推送节流（2026-10-11）：仅"实时页/心跳"这类每轮必变的文件变化时，
    # 最多每 MIRROR_MIN_INTERVAL 秒推一次。原因：GitHub Pages 每次推送都会重建，
    # 而 GitHub 侧的 jekyll 容器偶发拉取超时（与我们仓库无关），
    # 一分钟一推会把偶发失败放大成天天收失败邮件。nginx 直出不受影响（仍每分钟最新）。
    changed = [ln[3:].strip().strip('"') for ln in status.splitlines()]
    if changed and all(volatile_path(p) for p in changed):
        _last = _last_mirror_push()
        if _last and (time.time() - _last) < MIRROR_MIN_INTERVAL:
            print(
                f"[publish] {datetime.datetime.now():%F %T} 镜像推送节流：仅实时页变化，"
                f"{int(MIRROR_MIN_INTERVAL - (time.time() - _last))}s 后再推"
            )
            return 0
    r_commit = git(REPO, "commit", "-m", f"auto publish intel pages {datetime.date.today()}", "-q")
    if r_commit.returncode != 0:
        print(f"[publish] {datetime.datetime.now():%F %T} WARN: git commit 失败 rc={r_commit.returncode}: {r_commit.stderr.strip()[-200:]}")
        return 3
    r = git(REPO, "push", "-q")
    if r.returncode == 0:
        _mark_mirror_push()
    print(f"[publish] {datetime.datetime.now():%F %T} pushed {copied} report files rc={r.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
