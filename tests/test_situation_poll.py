"""比赛局势卡 60s 实时轮询脚本回归（2026-10-31 固化）。

教训：GitHub Pages 给每个页面固定 Cache-Control: max-age=600（10 分钟，平台值改不了），
浏览器在 10 分钟内用本地缓存不重新请求 -> 节点页「比赛局势」胜率看似冻结（实为缓存）。
修复：给比赛局势卡加稳定 DOM id（#situation-card），进行中的 bp/mid 节点注入 60s 轮询
脚本（fetch 自身页面 + cache:no-store 绕过浏览器缓存，只替换卡这一小块）；end 节点冻结、
不注入。

2026-10-31 追加单调守卫：胜率块带 data-sit-ts（unix 秒），脚本比较新旧卡时间戳，
新卡 <= 当前则跳过——GitHub CDN 多 edge 节点清理不同步会让时间戳"回跳"，守卫杜绝之。
同时弃用 ?sit= 查询参数（实测 GitHub CDN 对查询字符串不区分缓存键，?sit= 无效）。

本测试锁定：id 稳定存在；bp/mid 注入脚本、end 不注入；胜率块带 unix 时间戳；
脚本带防重入守卫、单调守卫（新卡不更新则跳过）、且不再用 ?sit=。
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import render_node_page as R
import refresh_situation

_STATS = {"win_signal": {"pct_a": 55, "total": 90, "threshold": 10, "basis": "recent"}}
_DATA = {"progress_line": "x", "top_signals": []}


def _render(gphase: str) -> str:
    return R.render(
        _DATA, _STATS,
        teams=["A", "B"], date="2026-10-31", gi=2, gphase=gphase,
        slug_id="cs2-a-b-2026-10-31", max_games=3,
    )


def test_situation_card_has_stable_id():
    card = R.situation_card(_STATS, None, ["A", "B"])
    assert 'id="situation-card"' in card
    assert 'class="card"' in card


def test_bp_mid_inject_poll_script():
    for ph in ("bp", "mid"):
        h = _render(ph)
        assert 'id="situation-card"' in h
        assert "__sitPoll" in h          # 脚本注入
        assert "no-store" in h            # 禁用本地缓存（绕过浏览器 10min 缓存）
        assert "data-sit-ts" in h         # 胜率块带 unix 时间戳供单调守卫比较


def test_end_freezes_no_script():
    h = _render("end")
    assert 'id="situation-card"' in h
    assert "__sitPoll" not in h           # end 节点冻结，不轮询


def test_poll_script_guarded_and_monotonic():
    s = R.situation_poll_script()
    assert "window.__sitPoll" in s        # 防重入守卫
    assert "setInterval" in s             # 周期轮询
    assert "data-sit-ts" in s             # 单调守卫读取胜率 unix 时间戳
    assert "data-rat-ts" in s             # 2026-11-01：同时读评分 unix 时间戳
    assert "Math.max" in s                # 新鲜度 = max(胜率, 评分)，任一更新即换卡
    assert "tNew <= tCur" in s            # 新卡不更新则跳过（防 CDN 多节点回跳）
    assert "getElementById" in s          # 替换 #situation-card
    assert "?sit=" not in s               # 2026-10-31 弃用：GitHub CDN 对查询串不区分缓存键


def test_win_block_emits_unix_ts():
    ws = {"pct_a": 55, "total": 90, "threshold": 10, "basis": "recent"}
    blk = R.situation_win_block(ws, ["A", "B"])
    assert 'data-sit-ts="' in blk
    assert "胜率更新于 " in blk           # 展示用北京时间不变


def test_ratings_block_emits_unix_ts():
    # 2026-11-01：评分块带 data-rat-ts，胜率冻结但评分更新时守卫仍判"更新"（max 口径）
    ratings = {
        "game": {"num": 1, "name": "第1局"},
        "fetched_at_utc": "2026-11-01T12:00:00Z",
        "players": [{"name": "P1", "score": 9.9, "count": 100, "team_id": "1", "team": "A"}],
    }
    blk = R.situation_ratings_block(ratings, ["A", "B"])
    assert 'data-rat-ts="' in blk
    assert "评分更新于 " in blk           # 北京时间更新时间戳（与胜率块对齐）
    assert "北京时间" in blk


def test_ratings_block_empty_no_ts():
    # 暂无评分分支（初始渲染）不带 data-rat-ts，tsOf 对缺失属性按 0 处理，不误判
    blk = R.situation_ratings_block(None, ["A", "B"])
    assert "data-rat-ts" not in blk
    assert "暂未获取到虎扑选手评分" in blk


def test_page_backward_compat_no_script_by_default():
    # 其它 page() 调用（3 元组、无 extra_html）不受影响：无 id、无脚本
    from intel_html import page
    html = page("t", "s", [("1", "段", "<p>x</p>")], "footer")
    assert 'id="situation-card"' not in html
    assert "__sitPoll" not in html


# --------------------------------------------------------------------------- 回填 _ensure_poll

_OLD_CARD = (
    '<div class="card"><h2><span class="no">2</span>比赛局势</h2>'
    '<h3>两队胜率</h3>' + R._WIN_BEGIN + 'x' + R._WIN_END
    + '<h3>队员评分</h3>' + R._RAT_BEGIN + 'y' + R._RAT_END
    + '</div>'
)


def _old_page() -> str:
    return (
        '<!DOCTYPE html><html><head></head><body>'
        '<div class="card"><h2><span class="no">1</span>BP</h2></div>'
        + _OLD_CARD
        + '<div class="card"><h2><span class="no">3</span>方向</h2></div>'
        '</body></html>'
    )


def test_ensure_poll_adds_id_and_script_to_old_page():
    html, changed = refresh_situation._ensure_poll(_old_page())
    assert changed is True
    assert 'id="situation-card"' in html
    assert "__sitPoll" in html
    assert html.count('id="situation-card"') == 1  # 只第 2 张卡被加 id


def test_ensure_poll_idempotent_on_new_page():
    html, _ = refresh_situation._ensure_poll(_old_page())
    html2, changed2 = refresh_situation._ensure_poll(html)
    assert changed2 is False
    assert html2 == html


def test_ensure_poll_skips_when_no_card_anchor():
    # 占位页（无 <div class="card"> 比赛局势锚点）不注入脚本、不加 id
    html = '<!DOCTYPE html><html><body><section><h2>比赛局势（系统注入）</h2></section></body></html>'
    out, changed = refresh_situation._ensure_poll(html)
    assert changed is False
    assert "__sitPoll" not in out
    assert 'id="situation-card"' not in out


# ----------------------------------------------------------------- 旧脚本升级（2026-10-31）

_OLD_SITPOLL = """<script>
(function () {
  if (window.__sitPoll) return;
  window.__sitPoll = true;
  var base = window.location.href.split("#")[0].split("?")[0];
  function swap() {
    fetch(base + "?sit=" + Date.now(), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        if (!html) return;
        var doc = new DOMParser().parseFromString(html, "text/html");
        var fresh = doc.getElementById("situation-card");
        var cur = document.getElementById("situation-card");
        if (fresh && cur) cur.outerHTML = fresh.outerHTML;
      })
      .catch(function () {});
  }
  setInterval(swap, 60000);
})();
</script>"""


def _old_page_with_old_script() -> str:
    return (
        '<!DOCTYPE html><html><head></head><body>'
        + _OLD_CARD
        + _OLD_SITPOLL
        + '</body></html>'
    )


def test_ensure_poll_upgrades_old_sitscript():
    html, changed = refresh_situation._ensure_poll(_old_page_with_old_script())
    assert changed is True
    assert "?sit=" not in html            # 旧 ?sit= 版被升级掉
    assert "data-sit-ts" in html          # 新脚本含单调守卫读取时间戳
    assert "tNew <= tCur" in html


def test_ensure_poll_new_script_idempotent():
    html, changed = refresh_situation._ensure_poll(_old_page_with_old_script())
    assert changed is True
    html2, changed2 = refresh_situation._ensure_poll(html)
    assert changed2 is False               # 已是新版，不再改动
    assert html2 == html
