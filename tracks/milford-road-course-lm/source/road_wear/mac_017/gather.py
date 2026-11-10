"""The gate column for one workshop: python gather.py <workshop> [<log>]"""
import json, re, sys
from pathlib import Path
W = Path(sys.argv[1]); log = Path(sys.argv[2]).read_text(errors="replace") if len(sys.argv) > 2 else ""
d = lambda f: json.loads((W / "data" / f).read_text()) if (W / "data" / f).exists() else None
dt = d("drive_test.json")["layouts"]["full"]
print("drive_test:", "FAIL" if dt["fail"] else "PASS", {k: dt[k] for k in ("soft_top_in_lane", "obstruction_stations", "daylight_gaps",
      "excursion_drops", "undrivable_corners", "severe_steps", "steps_per_km", "kinks_per_km", "floating_furniture")})
au = d("audit.json")
print("audit_mesh:", {k: au[k] for k in au if re.match(r"^[A-K]_", k) and not isinstance(au[k], (dict, list))}, "road_verts", au["road_verts"], "curb_verts", au["curb_verts"])
kg = d("kn5_ground_check.full.json")
print("kn5_ground:", "FAIL" if kg["fail"] else "PASS", kg["seating"]["walls"], kg["road_over_ground"], "double_sheet", kg["double_sheet_cells"])
kt = d("kn5_textures.json")["kn5s"][0]
print("kn5_textures:", "PASS" if kt["ok"] else "FAIL", kt["bytes"], "B", kt["textures_embedded"], "textures", kt["materials"], "materials", kt["maps"], "maps; missing", len(kt["missing"]))
hs = d("house_seat_check.json")
print("house_seat:", hs["verdict"], hs["buildings"], "buildings, contact", hs["contact_m"])
es = d("edge_smoothness.json")
le = es["lane_edge"]
print("edge_smoothness:", es.get("verdict", es.get("pass")), "lane L d2 p99", le["left"]["d2_m"]["p99"], "resid p99", le["left"]["resid_m"]["p99"],
      "R d2 p99", le["right"]["d2_m"]["p99"], "resid p99", le["right"]["resid_m"]["p99"])
for pat in (r"kn5 verification passed[^\n]*", r"verify_kn5 --inis[^\n]*\n[^\n]*", r"\[treefx\] \d+ trees[^\n]*", r"\[grassfx\][^\n]*",
            r"SHIP OK[^\n]*", r"GATES:[^\n]*", r"NOT INSTALLED[^\n]*", r"^exit \d+"):
    for m in re.findall(pat, log, re.M):
        print("log:", m.replace("\n", " | ")[:300])
rw = d("road_wear_check.json")
if rw:
    for k, r in rw["rows"].items():
        print("road_wear", k, "PASS" if r["pass"] else "FAIL", {kk: vv for kk, vv in r.items() if kk not in ("pass", "profile", "materials")})
