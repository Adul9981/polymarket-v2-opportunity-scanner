import sys
from pathlib import Path
sys.path.insert(0, "/opt/danmu-intel/tools")
from vps_intel_pipeline import REPORTS, SLICE_DIR, STATE_DIR, fast_intel_node, slice_rows

SLUG="lol-kt-bro2-2026-08-26"; TEAMS=["KT Rolster","HANJIN BRION"]; DATE="2026-08-26"
FILES=sorted(Path("/opt/danmu-intel/docs/data/danmu").glob("*/*.jsonl"))
nodes=[
 (1,"bp","2026-08-26T07:53:00+00:00","2026-08-26T08:28:00+00:00","",5),
 (1,"mid","2026-08-26T08:08:00+00:00","2026-08-26T08:40:00+00:00","",5),
 (1,"end","2026-08-26T08:30:00+00:00","2026-08-26T09:10:00+00:00","est",5),
 (2,"bp","2026-08-26T08:58:00+00:00","2026-08-26T09:28:00+00:00","",5),
]
for gi,gp,frm,to,eb,mg in nodes:
    rep=REPORTS/f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g{gi}_{gp}.html"
    st=STATE_DIR/f"{SLUG}_g{gi}_{gp}.json"; sf=SLICE_DIR/f"{SLUG}_g{gi}_{gp}.jsonl"
    for p in (rep,st,sf):
        try: p.unlink()
        except OSError: pass
    n=slice_rows(frm,FILES,sf,to)
    ij=STATE_DIR/f"{SLUG}_g{gi}_{gp}_intel.json"
    rc,so,se=fast_intel_node(SLUG,TEAMS,DATE,gi,gp,ij,sf,end_basis=eb,max_games=mg)
    ok=rep.exists() and "</body>" in rep.read_text(encoding="utf-8",errors="ignore")
    sec=0
    if ok:
        import re
        t=rep.read_text(encoding="utf-8",errors="ignore")
        sec=len(re.findall(r"<h2[^>]*><span class=\"no\">\d+</span>",t))
    print(f"G{gi} {gp}: slice={n} rc={rc} complete={ok} sections={sec} {so}",flush=True)
