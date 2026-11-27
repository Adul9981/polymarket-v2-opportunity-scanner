"""Regression checks for the read-only pattern decision workspace."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_pattern_decision_site as site  # noqa: E402


def test_dataset_counts_unique_training_matches():
    dataset = site.build_dataset(list(site.DEFAULT_SECTIONS), recent_days=1, recent_limit=1)
    training = dataset["training"]
    assert training
    assert dataset["stats"]["training_matches"] == len({row["slug"] for row in training})
    assert dataset["stats"]["training_matches"] < dataset["stats"]["training_samples"]


def test_workspace_uses_match_dedup_and_calibrated_rates():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "uniqueMatchMass" in template
    assert "betaRate" in template
    assert "count>=8" in template
    assert "按比赛去重" in template
    assert "相似度 ≠ 胜率" in template


def test_workspace_keeps_entry_band_constructive():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "entryStatus='等待回踩'" in template
    assert "未进区不追" in template
    assert "历史触达" in template


def test_workspace_foregrounds_actionable_trade_plan_and_simplifies_paths():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "renderTradeCallout" in template
    assert "推荐买哪边" in template
    assert "推荐价格" in template
    assert "第一止盈" in template
    assert "第二止盈" in template
    assert "失效 / 止损" in template
    assert "系统判断最终更可能取胜" in template
    assert "selectedContinuation" in template
    assert "默认只画首选延续" in template
    assert "candidates.forEach((c,i)=>{if(!c.future.length)return" not in template
    assert 'id="libraryCountInline"' in template


def test_workspace_exposes_countdown_and_manual_price_refresh():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "REFRESH_INTERVAL_MS=60000" in template
    assert 'id="refreshCountdown"' in template
    assert 'id="refreshNow"' in template
    assert "还有 '+remaining+' 秒自动刷新" in template
    assert "正在获取最新赔率" in template
    assert "startRefreshLoop" in template
    assert "setInterval(refreshLiveSnapshot,60000)" not in template


def test_workspace_splits_payload_into_cached_external_json(tmp_path):
    out = tmp_path / "pattern_decision_workspace.html"
    dataset = {
        "generated_at": "2026-11-27T20:00:00+08:00",
        "generated_date": "2026-11-27",
        "matches": [],
        "stats": {},
    }
    site.write_site(dataset, out, None, False)
    html = out.read_text(encoding="utf-8")
    payload = tmp_path / site.PAYLOAD_NAME
    assert payload.exists()
    assert (tmp_path / site.PAYLOAD_GZIP_NAME).exists()
    assert out.stat().st_size < 200_000
    assert "pattern_decision_payload.json?v=2026-11-27" in html
    assert "pattern_decision_payload.json.gz?v=2026-11-27" in html
    assert '<script id="pattern-data" type="application/json">null</script>' in html
    assert "async function loadData()" in html


def test_label_metadata_uses_plain_chinese_names():
    labels = site.label_meta()
    assert labels["A3_折价修复"]["title"] == "高位回撤修复"
    assert labels["B4_直线阴跌"]["title"] == "持续阴跌"
    assert labels["C1_中位震荡"]["title"] == "中线反复拉锯"
    assert labels["A3_折价修复"]["family"] == "反转结构"
    assert labels["B4_直线阴跌"]["family"] == "坠落结构"
    for meta in labels.values():
        public_text = " ".join(str(value) for value in meta.values())
        assert "A1" not in public_text
        assert "A2" not in public_text
        assert "A3" not in public_text
        assert "B1" not in public_text
        assert "B4" not in public_text
        assert "C2" not in public_text


def test_workspace_exposes_level_split_and_history_comparison():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "小局预测" in template
    assert "整场预测" in template
    assert "新版形态审计" in template
    assert "对比同类历史案例" in template
    assert "P1 观察版" in template
    assert "候选" in template


def test_live_snapshot_cannot_override_embedded_training_corpus():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "const corpusStats={" in template
    assert "training_matches:DATA.stats&&DATA.stats.training_matches" in template
    assert "snapshot.stats||{},corpusStats" in template
    assert "Never let an older snapshot overwrite" in template


def test_workspace_candidate_pool_uses_match_context_and_is_not_fixed_to_three():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "let MAX_CANDIDATES=12" in template
    assert "MAX_CANDIDATES=Math.max(12,PATTERN_LIBRARY_KEYS.length)" in template
    assert "function matchingPool()" in template
    assert "normalizedFormat(t.fmt)===format" in template
    assert "function uniqueMatchCount(rows)" in template
    assert "exactMatches>=12" in template
    assert "compatibleMatches>=12" in template
    assert "scope+=' / '+format+'扩样'" in template
    assert "含BO3/未知" in template
    assert "stageRows=rows.filter(t=>gameBucket(t.g)===bucket)" in template
    assert "uniqueMatchCount(stageRows)>=12" in template
    assert "poolByLabel" in template
    assert "本标签池 '+c.poolCount" in template
    assert "sampleEvidenceText(c)" in template
    assert "const fallbackMode=matched.formatFallback" in template
    assert "evidenceMode:fallbackMode||(coreLabels.has(lab)?'近邻匹配':'池内补样')" in template
    assert "function sampleEvidenceText(c)" in template
    assert "严格同制 '+c.exactMatches+' 场 → 兼容扩样 '+c.compatibleMatches+' 场" in template
    assert "function balancedEvidence(rows" in template
    assert "balancedEvidence(evidence,240,3,60)" in template
    assert "local=local.slice(0,60)" not in template
    assert "同制去重不足 12 场时" in template
    assert "return grouped.slice(0,MAX_CANDIDATES)" in template
    assert "可见前缀 '+visibleLabels" in template
    assert "赛后结果 '+outcomeLabels" in template


def test_vps_publisher_reinstalls_workspace_after_repo_reset():
    publisher = (ROOT / "tools" / "vps_publish.py").read_text(encoding="utf-8")
    assert 'PATTERN_WORKSPACE = (' in publisher
    assert '"pattern_decision_workspace.html"' in publisher
    assert 'shutil.copy2(PATTERN_WORKSPACE, target / PATTERN_WORKSPACE.name)' in publisher
    assert 'PATTERN_PAYLOAD = (' in publisher
    assert '"pattern_decision_payload.json"' in publisher
    assert 'shutil.copy2(PATTERN_PAYLOAD, target / PATTERN_PAYLOAD.name)' in publisher
    assert 'PATTERN_PAYLOAD_GZIP = (' in publisher
    assert '"pattern_decision_payload.json.gz"' in publisher
    assert 'shutil.copy2(PATTERN_PAYLOAD_GZIP, target / PATTERN_PAYLOAD_GZIP.name)' in publisher
    assert 'PATTERN_ATLAS =' in publisher
    assert '"pattern_atlas.html"' in publisher
    assert 'shutil.copy2(PATTERN_ATLAS, target / PATTERN_ATLAS.name)' in publisher


def test_training_rows_preserve_every_cooccurring_shape_label():
    training = []
    site.append_market_training(
        training,
        slug="fixture", sport="lol", fmt="BO3", level="game", game=1,
        raw={0: [(1000, 0.50), (1012, 0.44), (1020, 0.32), (1040, 0.18), (1085, 0.55), (1100, 1.0)]},
        teams={0: "Alpha"},
        summaries={0: {"labels": ["A1_V型极值反转", "A6_反弹确认", "A6_反弹确认"], "end": 1.0}},
        start=1000, end=1100,
    )
    assert training
    assert training[0]["lab"] == "未知"
    assert training[0]["labs"] == ["A1_V型极值反转", "A6_反弹确认"]
    assert all(row["ols"] == ["A1_V型极值反转", "A6_反弹确认"] for row in training)


def test_training_rows_do_not_name_a_candidate_from_a_future_outcome_label():
    training = []
    site.append_market_training(
        training,
        slug="future-label", sport="lol", fmt="BO3", level="game", game=1,
        raw={0: [(1000, 0.50), (1020, 0.54), (1040, 0.58), (1060, 0.64), (1080, 0.72), (1100, 1.0)]},
        teams={0: "Alpha"},
        summaries={0: {"labels": ["A2_中位U型反转"], "end": 1.0}},
        start=1000, end=1100,
    )
    assert training
    assert any(row["vls"] == [] for row in training)
    assert all(row["lab"] != "A2_中位U型反转" for row in training if row["vls"] == [])


def test_midline_oscillation_is_classified_from_the_visible_prefix():
    assert site.observable_shape_labels({"lo": 0.24, "hi": 0.76, "cr": 5}) == ["C1_中位震荡"]
    assert site.observable_shape_labels({"lo": 0.24, "hi": 0.86, "cr": 5}) == []
    assert site.observable_shape_labels({"lo": 0.18, "hi": 0.76, "cr": 5}) == []
    assert site.observable_shape_labels({"lo": 0.24, "hi": 0.76, "cr": 3}) == []


def test_visible_prefix_labels_cover_process_shapes_without_future_data():
    points = [
        (0, 0.50), (60, 0.34), (120, 0.28), (180, 0.44),
        (240, 0.30), (300, 0.52), (360, 0.72),
    ]
    labels = site.visible_prefix_labels(points, "game")
    assert "A5_W型双底" in labels
    assert "A7_强强对话错杀" in labels
    assert "C2_早期缩距/热门确立" in site.visible_prefix_labels(
        [(0, 0.38), (60, 0.28), (120, 0.42), (180, 0.72)], "game"
    )

    tail_collapse = [(0, 0.90), (60, 0.88), (120, 0.55), (180, 0.12), (240, 0.02)]
    assert "B1_尾盘崩塌" in site.visible_prefix_labels(tail_collapse, "game")
    assert "B1_尾盘崩塌" not in site.visible_prefix_labels(tail_collapse, "series")


def test_visible_prefix_labels_do_not_call_slow_deep_drop_a_v_reversal():
    slow = [(0, 0.50), (60, 0.08), (180, 0.12), (300, 0.20), (600, 0.35), (840, 0.75)]
    labels = site.visible_prefix_labels(slow, "game")
    assert "A1_V型极值反转" not in labels
    assert "A6_反弹确认" not in labels


def test_legacy_minute_filename_is_parsed_and_mirrored(tmp_path):
    import build_pattern_library as library

    slug = "lol-alpha-beta-2026-08-12"
    folder = tmp_path / slug
    folder.mkdir()
    rows = [
        {"timestamp": "2026-08-12T00:00:00Z", "market_slug": f"{slug}-moneyline", "side": "Alpha", "price": 0.42},
        {"timestamp": "2026-08-12T00:01:00Z", "market_slug": f"{slug}-moneyline", "side": "Alpha", "price": 0.25},
        {"timestamp": "2026-08-12T00:02:00Z", "market_slug": f"{slug}-moneyline", "side": "Alpha", "price": 0.45},
        {"timestamp": "2026-08-12T00:03:00Z", "market_slug": f"{slug}-moneyline", "side": "Alpha", "price": 1.0},
    ]
    (folder / "moneyline_alpha_price_1m.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    parts = library.parse_snapshot_dir(str(folder), slug)
    assert len(parts["series"]) == 1
    assert next(iter(parts["series"].values()))[0] == "Alpha"


def test_training_records_separate_visible_prefix_and_outcome_labels():
    training = []
    site.append_market_training(
        training,
        slug="prefix", sport="lol", fmt="BO3", level="game", game=1,
        raw={0: [(1000, 0.50), (1060, 0.24), (1120, 0.44), (1180, 0.28), (1240, 0.72), (1300, 1.0)]},
        teams={0: "Alpha"},
        summaries={0: {"labels": ["A2_中位U型反转"], "end": 1.0}},
        start=1000, end=1300,
    )
    assert training
    assert all("ols" in row and "vls" in row for row in training)
    assert all("A2_中位U型反转" in row["ols"] for row in training)
    assert any(
        label in row["vls"]
        for row in training
        for label in ("A5_W型双底", "C1_中位震荡", "C2_早期缩距/热门确立")
    )


def test_sparse_ten_minute_history_is_not_dropped_from_training():
    training = []
    site.append_market_training(
        training,
        slug="coarse", sport="lol", fmt="BO3", level="series", game=None,
        raw={0: [(1200, 0.42), (1800, 0.31), (2400, 1.0)]},
        teams={0: "Alpha"},
        summaries={0: {"labels": ["A2_中位U型反转"], "end": 1.0}},
        start=1000, end=2600,
    )
    assert training
    assert 50.0 in {row["cut"] for row in training}
    assert training[0]["gr"] == "10分钟级"
    assert training[0]["labs"] == ["A2_中位U型反转"]


def test_structure_event_cutoffs_keep_late_collapse_observable():
    points = [(1000, 0.90), (1060, 0.88), (1120, 0.70), (1180, 0.40), (1240, 0.12), (1300, 0.02), (1360, 0.01)]
    cutoffs = site.structure_event_cutoffs(points, 1000, 1360)
    assert 1300 in cutoffs
    training = []
    site.append_market_training(
        training,
        slug="late-collapse", sport="cs2", fmt="BO3", level="game", game=1,
        raw={0: points}, teams={0: "Alpha"},
        summaries={0: {"labels": ["B1_尾盘崩塌"], "end": 0.0}},
        start=1000, end=1360,
    )
    event_rows = [row for row in training if row.get("cut_src") == "event"]
    assert event_rows
    assert any("B1_尾盘崩塌" in row["vls"] for row in event_rows)


def test_pattern_inventory_covers_the_complete_decision_library():
    inventory = site.pattern_inventory([
        {"slug": "m1", "s": "lol", "l": "game", "lab": "A1_V型极值反转", "labs": ["A1_V型极值反转", "A6_反弹确认"]},
        {"slug": "m2", "s": "cs2", "l": "series", "lab": "A6_反弹确认", "labs": ["A6_反弹确认"]},
    ])
    assert len(inventory) == len(site.label_meta()) - 1
    by_label = {row["label"]: row for row in inventory}
    assert by_label["A1_V型极值反转"]["training_matches"] == 1
    assert by_label["A6_反弹确认"]["training_matches"] == 2
    assert by_label["A6_反弹确认"]["training_observations"] == 2


def test_workspace_exposes_library_coverage_not_just_visible_candidates():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "pattern_inventory" in template
    assert "function recordLabels(record)" in template
    assert "function renderPatternCoverage()" in template
    assert "总库 '+inventory.length+' 类" in template
    assert "当前池覆盖 '+available.size+' 类" in template
    assert "本池暂无证据" in template


def test_candidate_chart_names_both_sides_directly():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "蓝线 · '+esc(shortTeam(baseName,20))" in template
    assert "橙线 · '+esc(shortTeam(otherName,20))" in template
    assert "['结构偏向',shortTeam(dirName,18),fColor]" in template
    assert "candidate.useSelected?x:1-x" in template
    assert "toViewPoint=p=>[p[0],viewPrice(p[1]/100)*100]" in template
    assert "Math.max(candidate.buyLow,candidate.buyHigh)" in template
    assert "Y(candidate.target1*100)" in template
    assert "candidate.invalid*100" in template
    assert "右半边把历史同类路径统一换算到“" in template
    assert "['历史终点',endValue==null?'-':pct(endValue),fColor]" in template
    assert "['镜像终点',oppositeValue==null?'-':shortTeam(mirrorName,12)+' '+pct(oppositeValue),'#c26c00']" in template


def test_candidate_chart_keeps_observed_prices_in_raw_market_coordinates():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    candidate_chart = template.split("function candidateChart", 1)[1].split(
        "function patternInventory", 1
    )[0]
    # Current prices must never be mirrored into the candidate coordinate. The
    # left side of the chart has to match the main market chart exactly.
    assert "path.map(p=>[X(p[0]),Y(p[1])])" in candidate_chart
    assert "observed[i]={price:last[1],view:last[1]}" in candidate_chart
    assert "当前盘面 · 双方原始赔率" in candidate_chart
    assert "观察后 · 统一换算到候选方向坐标" in candidate_chart


def test_candidate_labels_only_use_shapes_visible_before_the_cutoff():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "function recordCandidateLabels(record)" in template
    assert "return uniqueText(record.vls)" in template
    assert "recordLabels(record)" in template
    assert "recordOutcomeLabels(record)" in template


def test_decision_states_buy_direction_sample_scope_and_weak_evidence_plainly():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "建议关注买入" in template
    assert "不是这两队历史交手样本" in template
    assert "样本不足，只报偏向后不生成买入建议" in template
    assert "方向倾向" in template
    assert "全库相似候选" in template
    assert "function aggregateDirection()" in template
    assert "综合方向" in template
    assert "结构分歧" in template
    assert "暂不硬选一个方向" in template


def test_workspace_first_builds_a_large_opening_cohort_then_splits_future_branches():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "function cohortContext()" in template
    assert "function cohortPrior(x)" in template
    assert "开盘基础样本池" in template
    assert "同开盘区间 / 相近观察时点" in template
    assert "function classifyFutureBranch" in template
    assert "守住并走强" in template
    assert "回踩后走强" in template
    assert "冲高后回落" in template
    assert "持续走弱" in template
    assert "基础池覆盖" in template
    assert "基础先验冲突" in template
    assert "条件观察 " in template
    assert "currentCohort=cohortContext();renderCohortSummary(currentCohort)" in template
    assert "pct(b.medianEnd*100)+'c" not in template
    assert "pct(rec.current*100)+'c" not in template


def test_future_shape_keeps_extrema_instead_of_uniform_summary_points():
    points = [(0, 50), (1, 80), (2, 50), (3, 20), (4, 50)]
    picked = site.shape_downsample(points, 4)
    assert picked[0] == points[0]
    assert picked[-1] == points[-1]
    assert (1, 80) in picked or (3, 20) in picked
    assert site.MAX_PUBLIC_POINTS >= 180


def test_snapshot_format_is_inferred_when_metadata_is_missing():
    assert site.infer_format({"game_winners": {"1": 0, "2": 0}}, {}) == "BO3"
    assert site.infer_format({"game_winners": {"1": 0, "2": 1, "3": 0, "4": 1, "5": 0}}, {}) == "BO5"
    assert site.infer_format({"game_winners": {"1": 1}}, {}) == "BO1"
    assert site.infer_format({"format": "BO5"}, {"format": "BO3"}) == "BO5"


def test_training_records_reference_real_minute_market_paths():
    dataset = site.build_dataset(list(site.DEFAULT_SECTIONS), recent_days=0, recent_limit=0)
    market_ids = {market["id"] for match in dataset["matches"] for market in match.get("markets", {}).values()}
    assert dataset["training"]
    for row in dataset["training"][:200]:
        assert row["mid"] in market_ids
        assert row["gr"] in {"1分钟级", "5分钟级", "10分钟级", "数据不足"}
        assert 0 <= row["cut"] <= 100


def test_candidate_evidence_chart_uses_real_paths_and_decision_levels():
    template = site.TEMPLATE.read_text(encoding="utf-8")
    assert "function candidateChart" in template
    assert "representatives" in template
    assert "25%–75% 区间" in template
    assert "双方真实价格路径" in template
    assert "建议买入区" in template
    assert "失效边界" in template
    assert "不使用固定摘要点" in template
