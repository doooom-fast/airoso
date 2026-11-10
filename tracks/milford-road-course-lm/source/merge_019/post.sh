#!/bin/bash
# After the 0.1.9 build (Milford, ledger 0082 "Milford 0.1.9"): the key log lines, every gate row side by side with 0.1.7 (b17)
# and 0.1.8 (b018's kept records), road_wear, veg_verify, seat_built, the three-way kn5 comparison and mesh_diff -> <run>.post.txt
set -u
S=/private/tmp/claude-501/-Volumes-Drive-codex-airoso/830ae195-8db3-403c-a5ba-24f3f0c17f6d/scratchpad/sys
F=$S/work/mf019; N=$1; A=$S/wt-mf019; W=$F/$N; PY=/Volumes/Drive/codex/airoso/.venv/bin/python; T=$A/tracks/milford-road-course-lm/source
B17=$S/work/roadtex/b17; B18=$F/b018_rec
mkdir -p $B18; ln -sfn $S/work/furniture/records/b018 $B18/data; [ -e $F/b018_rec.log ] || ln -s $S/work/furniture/b018.log $F/b018_rec.log   # gate_table reads <ws>.log
K17=$B17/build/milford_road_course.kn5; K18=$S/work/furniture/records/b018/milford_road_course.kn5; K19=$W/build/milford_road_course.kn5
{
echo "== $N ($A @ $(git -C $A rev-parse --short HEAD))"; grep -E "^(quiet|head|exit|end)" $F/$N.log
grep -E "SHIP OK|FAIL|FATAL|\[treefx\] (planted|[0-9]+ trees)|\[grassfx\].*rectangles|block mpg_|f1_nw_screen|\[reseat\]|\[road_wear\]|PASS" $F/$N.log | head -120
echo "== gate_table (0.1.7 b17 | 0.1.8 b018 | 0.1.9 $N)"; (cd $F && $PY $T/furniture/gate_table.py $B17 $B18 $W 2>&1)
echo "== road_wear_check (0.1.7 | 0.1.9)"; for w in $B17 $W; do $PY -c "import json,sys; d=json.load(open(sys.argv[1])); print({k:(v if not isinstance(v,(list,dict)) else (v.get('pass', v.get('ok')) if isinstance(v,dict) else len(v))) for k,v in d.items()})" $w/data/road_wear_check.json; done
echo "== kn5 bytes"; ls -l $K17 $K18 $K19
echo "== veg_verify"; $PY $T/vegetation/scripts/veg_verify.py $W --json $F/$N.veg_verify.json 2>&1 | tail -12
echo "== seat_built"; $PY $T/furniture/pass3/scripts/seat_built.py $W --json $F/$N.seat_built.json 2>&1 | tail -30
echo "== rails_by_line"; $PY $T/furniture/pass3/scripts/rails_by_line.py $W 2>&1 | tail -8
echo "== compare_019 (positions = 0.1.8, road-wear UVs + materials = 0.1.7, textures = 0.1.7)"; (cd $A && $PY $T/merge_019/compare_019.py $K17 $K18 $K19 --json $F/$N.compare_019.json 2>&1 | tail -60)
echo "== mesh_diff 0.1.8 -> 0.1.9"; $PY $T/vegetation/scripts/mesh_diff.py $K18 $K19 --json $F/mesh_diff_b018_$N.json 2>&1 | tail -40
echo "== mesh_diff 0.1.7 -> 0.1.9"; $PY $T/vegetation/scripts/mesh_diff.py $K17 $K19 --json $F/mesh_diff_b17_$N.json 2>&1 | tail -40
} > $F/$N.post.txt 2>&1
mkdir -p $F/records/$N; cp $W/data/*.json $F/records/$N/ 2>/dev/null; cp $F/$N.log $F/records/$N/
echo done
