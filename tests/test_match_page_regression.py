"""Regression tests for match-detail page intel linking (AGENTS 防错规则 12).

Guards against the "intel page exists but detail page shows 暂无" class of
errors: report-name construction must match real file names (hyphenated team
slugs), and every referenced node/report page must exist in the site.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SITE_INTEL = ROOT / ".danmu_intel_site" / "intel"


def report_name(teams: list[str], date: str) -> str:
    slug = "-".join(str(t).replace(" ", "") for t in teams)
    return f"intel_danmu_{slug}_{date}.html"


@pytest.mark.parametrize(
    "match_id, teams, date",
    [
        ("2026-08-22_we_lgd", ["WE", "LGD"], "2026-08-22"),
        ("2026-08-22_gen_dk", ["GEN", "DK"], "2026-08-22"),
        ("2026-08-21_bro_bfx", ["BRO", "BFX"], "2026-08-21"),
        ("2026-08-21_sk_th", ["SK", "TH"], "2026-08-21"),
    ],
)
def test_report_name_matches_site_file(match_id: str, teams: list[str], date: str) -> None:
    name = report_name(teams, date)
    assert (SITE_INTEL / name).exists(), (
        f"{match_id}: expected report page {name} to exist in site intel/ "
        "(hyphenated team slug linking)"
    )


def test_matches_json_team_order_consistent() -> None:
    data = json.loads((ROOT / "docs/data/intel/matches.json").read_text(encoding="utf-8"))
    for m in data.get("matches", []):
        if m.get("event_slug") and m.get("teams"):
            assert len(m["teams"]) == 2, f"{m['id']}: teams must be 2 for slug linking"


def test_generated_shell_references_existing_pages() -> None:
    for shell in SITE_INTEL.glob("match_*.html"):
        text = shell.read_text(encoding="utf-8")
        for name in ("node_g1_", "intel_danmu_", "match_", "closed_loop_", "intel_soop_"):
            for ref in [ln for ln in text.split('"') if name in ln and ln.endswith(".html")]:
                assert (SITE_INTEL / ref).exists(), f"{shell.name}: broken ref {ref}"
