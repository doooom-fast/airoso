"""The aerial reading stage, end to end (ledger 0088). Opt-in: run it by hand or from a track's own tooling; nothing in
an existing build path calls it.

    python -m scripts.aerial.engine <engine.json | project-dir> [--out DIR] [--layout ID ...] [--no-stills]

A project dir is read for track.config.json ``aerial_engine`` (the same keys, inline); an engine.json path is the
config itself. Paths in it are relative to the config's folder; ``${VAR}`` and ``${VAR:-default}`` expand from the
environment (imagery and maps are not committed; their sidecars are).

THE CONFIG HOLDS ONLY DATA (a per-track file, e.g. tracks/<slug>/source/aerial-engine/engine.json):

  name                 the track's name
  image, georef        the orthophoto and its georeference (ortho.py: a GeoTIFF needs none; else a sidecar or a dict)
  origin_from          a centerline.local.json whose origin is the ENU frame (else ``origin_lonlat``, else the image's
                       centre)
  colours              channel overrides (channels.py DEFAULTS)
  edges                edge-finder settings: edge_kind surface | lines, score pave | grey, reach_m, weak, min_half_m,
                       ridge_min, rmin_m, passes
  route_mask           pave | between_lines (route.py)
  corridor_m           how tightly the guide holds the route line (route.py; default 8)
  band                 band.py overrides (valley, nb, min_depth, med_m, width)
  lidar                {"walls": [{"survey", "line"}], "register": "wall_top" | null}
  start_finish_px      the start / finish line on the AERIAL (pixel-centre coords): where a published lap starts
  maps                 {key: {file, ink {course, other}, drop_rows_above, sf_px, sf_close_px, spur_px, exclude_px,
                        labels, label_ink, register_to lidar | pavement, title}}
  sketches             {key: {file, stroke}}: a hand sketch's strokes (shape only, never direction)
  layouts              [{id, name, route: {maps: [keys]} | {sketch: key}, direction ccw | cw | direction_from: <id>,
                         published_length_m: [..], kerbs: true}]

OUTPUT (--out, default <config dir>/out): report.json (every number), pieces.json, per layout <id>.layout.json,
<id>.centerline.geojson, <id>.source.json (when exact), <id>_overall.jpg, <id>_zooms.jpg (clean stills).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from . import channels as chn
from . import edges as edg
from . import emit, geom, kerbs, maps, network, register, route, stills
from .ortho import Ortho

JOIN_IN_M, JOIN_OUT_M, JOIN_SMOOTH_M = 10.0, 25.0, 6.0
AGREE_M = 3.0           # a second map's line this far outside the measured road's edge is a different road
SF_ON_LAP_M = 15.0      # a start / finish further than this from a layout's lap is not on that layout
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand(v: str) -> str:
    return _VAR.sub(lambda m: os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else ""), v)


def load_config(arg: str):
    p = Path(arg)
    if p.is_dir():
        cfg = json.loads((p / "track.config.json").read_text(encoding="utf-8"))
        if "aerial_engine" not in cfg:
            raise SystemExit(f"[aerial-engine] {p}/track.config.json has no aerial_engine block (the stage is opt-in)")
        return cfg["aerial_engine"], p
    return json.loads(p.read_text(encoding="utf-8")), p.parent


def _path(base: Path, v):
    if v is None:
        return None
    v = expand(str(v))
    q = Path(v)
    return q if q.is_absolute() else (base / q).resolve()


def log(msg):
    print(f"[aerial-engine] {msg}", flush=True)


class Stage:
    def __init__(self, cfg: dict, base: Path, out: Path):
        self.cfg, self.base, self.out = cfg, base, out
        out.mkdir(parents=True, exist_ok=True)
        self.rep = {"_doc": "scripts.aerial.engine report (ledger 0088): every number the stage measured",
                    "name": cfg.get("name"), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # -- inputs ------------------------------------------------------------------------------------------------------
    def load_inputs(self):
        c = self.cfg
        origin = None
        if c.get("origin_from"):
            loc = json.loads(_path(self.base, c["origin_from"]).read_text(encoding="utf-8"))
            origin = (float(loc["origin"]["lon"]), float(loc["origin"]["lat"]))
        elif c.get("origin_lonlat"):
            origin = tuple(c["origin_lonlat"])
        georef = c.get("georef")
        if isinstance(georef, str):
            georef = _path(self.base, georef)
        self.o = Ortho.load(_path(self.base, c["image"]), georef, origin)
        log(f"image {self.o.desc['image']} {self.o.W}x{self.o.H} {self.o.desc['crs']} gsd {self.o.gsd[0]:.3f} m")
        self.walls = []
        for w in (c.get("lidar") or {}).get("walls", []):
            sv = register.lidar_wall_survey(_path(self.base, w["survey"]), _path(self.base, w["line"]))
            if abs(sv["origin"][0] - self.o.origin[0]) > 1e-9 or abs(sv["origin"][1] - self.o.origin[1]) > 1e-9:
                lon, lat = (sv["origin"][0] + sv["face"][:, 0] / self.o.m_lon, sv["origin"][1] + sv["face"][:, 1] / self.o.m_lat)
                sv["face"] = np.c_[self.o.lonlat_to_en(lon, lat)]
            self.walls.append(sv)
        reg = (c.get("lidar") or {}).get("register")
        self.rep["registration"] = None
        if reg == "wall_top" and self.walls:
            lum = self.o.rgb.mean(-1)
            offs, outs = [], []
            for sv in self.walls:
                offs.append(register.wall_top(self.o, lum, sv["face"], sv["outward"]))
                outs.append(sv["outward"])
            r = register.fit_shift(np.concatenate(offs), np.vstack(outs), float(np.mean(self.o.gsd)))
            r["feature"] = "wall_top: the wall's concrete top, road-side edge, against the lidar wall face"
            self.rep["registration"] = r
            if r["apply"]:
                self.o.set_shift(r["shift_en_m"])
            log(f"registration to lidar: shift {r['shift_en_m']} m (|{r['shift_m']}| m, sd {r['shift_sd_en_m']}), "
                f"residual rms {r['residual_m']['rms']} m, {'APPLIED' if r['apply'] else 'under a pixel: not applied'}")
        self.ch = chn.compute(self.o.rgb, float(np.mean(self.o.gsd)), c.get("colours"))
        self.pave = chn.pavement_mask(self.ch["pave"])
        self.free = route.free_mask(self.ch, self.pave, c.get("route_mask", "pave"))
        lid = []
        for sv in self.walls:
            F = sv["face"]
            lid.append(np.vstack([F, F[:1]]) if sv["closed"] else F)
        self.ctx = edg.Ctx(self.o, self.ch, lid, c.get("edges"))
        self.rep["image"] = self.o.describe()
        self._pave_dil = ndimage.binary_dilation(self.pave, iterations=max(1, int(round(1.0 / float(np.mean(self.o.gsd))))))

    def on_pave(self, P):
        px, py = self.o.en_to_px(P[:, 0], P[:, 1])
        xi = np.clip(np.rint(px).astype(int), 0, self.o.W - 1)
        yi = np.clip(np.rint(py).astype(int), 0, self.o.H - 1)
        inside = (px >= 0) & (py >= 0) & (px <= self.o.W - 1) & (py <= self.o.H - 1)
        return inside & self._pave_dil[yi, xi]

    def sf_en(self):
        """The start / finish: ``start_finish_px`` on the aerial, or ``start_finish_lonlat`` (the config's own)."""
        sf = self.cfg.get("start_finish_px")
        if sf:
            e, n = self.o.px_to_en(np.array([float(sf[0])]), np.array([float(sf[1])]))
            return np.array([e[0], n[0]])
        ll = self.cfg.get("start_finish_lonlat")
        if ll:
            e, n = self.o.lonlat_to_en(float(ll[0]), float(ll[1]))
            return np.array([float(e), float(n)])
        return None

    # -- route lines -------------------------------------------------------------------------------------------------
    def map_line(self, key: str):
        spec = self.cfg["maps"][key]
        m = maps.load(spec, _path(self.base, spec["file"]))
        A = maps.outer_contour(m["course"] | m["other"], close=2)
        if spec.get("register_to", "lidar") == "lidar" and self.walls:
            ref = geom.resample(np.vstack([sv["face"] for sv in self.walls]), 0.25, closed=self.walls[0]["closed"])
            ref_name = "the lidar wall face"
        else:
            ref = self._pavement_outline()
            ref_name = "the aerial's pavement outline"
        loop_px, loop_info = maps.course_loop(m, spec)
        sols = maps.fit_similarity(A, ref)
        sf = self.sf_en()

        def on_frac(z):
            return float(self.on_pave(geom.resample(maps.apply(z["T"], loop_px), 2.0, closed=True)).mean())

        def sf_miss(z):
            if sf is None or not spec.get("sf_px"):
                return None
            return float(np.hypot(*(maps.apply(z["T"], np.array(spec["sf_px"], float)) - sf)))
        z, near = maps.choose(sols, on_frac, sf_miss)
        aff = maps.affine_residual(A, ref, z["T"])
        line = geom.resample(maps.apply(z["T"], loop_px), 1.0, closed=True)
        want = self._direction_sign(spec.get("direction") or "ccw")
        if np.sign(geom.signed_area(line)) != want:
            line = line[::-1].copy()
        refits = []
        stretches = maps.off_pavement_stretches(line, self.on_pave)
        if stretches:
            med = route.medial_points(self.o, self.free)
            for a, b in stretches:
                c = line[(a + b) // 2]
                line2, info = maps.local_refit(line, med, c)
                if info is not None and info.get("refused"):
                    info["stretch_m"] = [int(a), int(b)]
                    refits.append(info)
                elif info is not None:
                    info["stretch_m"] = [int(a), int(b)]
                    info["off_pavement_before"] = round(float((~self.on_pave(line[a:b + 1])).mean()), 2)
                    info["off_pavement_after"] = round(float((~self.on_pave(line2[a:b + 1])).mean()), 2)
                    refits.append(info)
                    line = line2
        labels = maps.label_points(m, spec)
        lab_en = {k: maps.apply(z["T"], p) for k, p in labels.items()}
        rec = {"file": spec["file"], "title": spec.get("title"), "registered_to": ref_name,
               "outline_px": int(len(A)), "course_edges": loop_info,
               "chosen": {"det": z["det"], "handedness": "proper (unmirrored)" if z["det"] < 0 else "MIRRORED",
                          "angle_deg": round(z["angle_deg"], 2), "scale_m_per_px": round(z["scale_m_per_px"], 4),
                          "outline_rms_m": round(z["rms"], 2), "outline_p95_m": round(z["p95"], 2),
                          "course_on_pavement": round(z["on_pavement"], 3),
                          "sf_miss_m": None if z["sf_miss_m"] is None else round(z["sf_miss_m"], 1)},
               "affine": aff, "solutions_tried": len(sols),
               "near_equal_fits": [{"det": q["det"], "angle_deg": round(q["angle_deg"], 1), "rms": round(q["rms"], 2),
                                    "course_on_pavement": round(q["on_pavement"], 3),
                                    "sf_miss_m": None if q["sf_miss_m"] is None else round(q["sf_miss_m"], 1)} for q in near],
               "local_refits": refits, "line_m": round(geom.closed_len(line), 1)}
        log(f"map {key}: outline rms {z['rms']:.2f} m to {ref_name}, {rec['chosen']['handedness']}, course "
            f"{z['on_pavement'] * 100:.0f} % on pavement, S/F miss {rec['chosen']['sf_miss_m']} m, refits {len(refits)}")
        return line, lab_en, rec

    def _pavement_outline(self):
        lab, n = ndimage.label(self.pave)
        sizes = ndimage.sum(self.pave, lab, range(1, n + 1))
        big = ndimage.binary_fill_holes(lab == 1 + int(np.argmax(sizes)))
        y, x = np.nonzero(big & ~ndimage.binary_erosion(big))
        e, nn = self.o.px_to_en(x.astype(float), y.astype(float))
        return np.c_[e, nn]

    @staticmethod
    def _direction_sign(d):
        return 1 if d.lower() in ("ccw", "counter-clockwise", "anticlockwise") else -1

    def sketch_line(self, key: str):
        spec = self.cfg["sketches"][key]
        doc = json.loads(_path(self.base, spec["file"]).read_text(encoding="utf-8"))
        body = doc.get("data", doc)
        st = body["strokes"][int(spec.get("stroke", 0))]["pts"]
        pts = np.array(st, float).reshape(-1, 2)
        meta = {"corners_wnes": body["corners_wnes"], "image_w": body["image_w"], "image_h": body["image_h"]}
        f, _ = Ortho._georef(Path(spec["file"]), meta, int(body["image_w"]), int(body["image_h"]))
        lon, lat = f(pts[:, 0], pts[:, 1])
        e, n = self.o.lonlat_to_en(lon, lat)
        line = geom.resample(np.c_[e, n], 1.0, closed=True)
        return line, {"file": spec["file"], "stroke": int(spec.get("stroke", 0)), "drawn_m": round(geom.closed_len(line), 1),
                      "note": "a sketch gives SHAPE only (Kevin 2026-11-07: 'Do them as published, i just drew shape')"}

    # -- the run -----------------------------------------------------------------------------------------------------
    def run(self, only=None, do_stills=True):
        self.load_inputs()
        layouts = [L for L in self.cfg["layouts"] if not only or L["id"] in only]
        done = {}
        bodies = []
        self.rep["maps"], self.rep["sketches"], self.rep["layouts"] = {}, {}, []
        pieces = {}
        for L in layouts:
            log(f"layout {L['id']}: {L.get('name')}")
            labels = {}
            src = L["route"]
            if src.get("maps"):
                lines = []
                for k in src["maps"]:
                    line, lab, rec = self.map_line(k)
                    self.rep["maps"][k] = rec
                    lines.append(line)
                    labels[k] = (lab, line)
                line = lines[0]
                route_src = {"kind": "published map", "primary": src["maps"][0], "others": src["maps"][1:]}
            elif src.get("sketch"):
                line, rec = self.sketch_line(src["sketch"])
                self.rep["sketches"][src["sketch"]] = rec
                lines = [line]
                route_src = {"kind": "hand sketch (shape only)", "sketch": src["sketch"]}
            else:
                raise SystemExit(f"[aerial-engine] layout {L['id']}: no route source (a published map or a sketch): the "
                                 "stage does not guess a route")
            flip = None
            if L.get("direction_from"):
                ref = done[L["direction_from"]]["C"]
                flip = self._agrees(line, ref) < 0
                if flip:
                    line = line[::-1].copy()
                route_src["direction"] = f"as layout {L['direction_from']} runs on the stretches they share" + \
                    (" (the line was drawn the other way)" if flip else "")
            else:
                want = self._direction_sign(L.get("direction", "ccw"))
                if np.sign(geom.signed_area(line)) != want:
                    line = line[::-1].copy()
                route_src["direction"] = L.get("direction", "ccw") + " (as published)"
            G, ginfo = route.guide(self.o, self.free, line, True, float(self.cfg.get("corridor_m", 8.0)))
            route_src["guide"] = ginfo
            res = self._measure_layout(L, G, done)
            C, W, parts = res["C"], res["W"], res["parts"]
            # do the other maps draw the same route? each one's line read onto the MEASURED road: the share of it on
            # that road (within its measured half-width + AGREE_M), and the share of the road it covers
            agree = []
            for k, other in zip(route_src.get("others", []), lines[1:]):
                Lo = geom.resample(other, 1.0, closed=True)
                d, j = cKDTree(C).query(Lo)
                on = d <= W[j] / 2 + AGREE_M
                d2 = cKDTree(Lo).query(C)[0]
                cov = d2 <= W / 2 + AGREE_M
                agree.append({"map": k, "its_line_on_the_measured_road": round(float(on.mean()), 3),
                              "measured_road_covered_by_it": round(float(cov.mean()), 3),
                              "line_to_centre_m": geom.pct(d, 2), "off_road_m": int((~on).sum())})
                log(f"  map {k} vs {route_src['primary']}: {on.mean() * 100:.1f} % of its line on the measured road, "
                    f"which it covers {cov.mean() * 100:.1f} %")
            route_src["maps_agree"] = agree
            # start: the published S/F for a mapped lap; else where the layout first meets its reference
            sf = self.sf_en()
            i0, dsf = geom.nearest(C, sf) if sf is not None else (0, np.inf)
            if dsf <= SF_ON_LAP_M:
                start = {"kind": "the start / finish (start_finish_px / _lonlat)", "miss_m": round(dsf, 2)}
            elif L.get("direction_from") and res.get("first_shared") is not None:
                i0 = res["first_shared"]
                start = {"kind": f"the first station shared with {L['direction_from']}, in its order"}
            else:
                i0, start = 0, {"kind": "the guide's first station"}
            C = np.roll(C, -i0, axis=0)
            W = np.roll(W, -i0)
            Cm = geom.resample(C, 1.0, closed=True)
            s1 = geom.cumlen(np.vstack([C, C[:1]]))
            sm = geom.cumlen(Cm)
            Wm = np.interp(sm, s1[:-1], W)
            lap = geom.closed_len(Cm)
            pub = L.get("published_length_m")
            corners = self._corners(labels, Cm) if labels else {}
            lay = {"id": L["id"], "name": L.get("name"), "route": route_src, "start": start, "lap_m": round(lap, 1),
                   "published_length_m": pub,
                   "vs_published_m": [round(lap - p, 1) for p in pub] if pub else None,
                   "joins": res["joins"], "parts": [{k: v for k, v in p.items() if not k.startswith("_")} for p in parts],
                   "width_m": {"p10": round(float(np.percentile(Wm, 10)), 2), "p50": round(float(np.median(Wm)), 2),
                               "p90": round(float(np.percentile(Wm, 90)), 2)},
                   "corners": corners, "measure": res["report"]}
            if L.get("kerbs", True):
                lay["kerbs"] = self._kerbs(Cm, Wm)
            self.rep["layouts"].append(lay)
            done[L["id"]] = {"C": res["C"], "W": res["W"], "G": G, "m": res.get("m"), "summ": res.get("summ"),
                             "i0": int(i0), "parts": parts, "lay": lay}
            for p in parts:
                if p.get("_own"):
                    pieces[p["piece"]] = p["_own"]
            bodies.append({"id": L["id"], "centre_en_m": np.round(Cm, 2).tolist(),
                           "width_m_per_metre": np.round(Wm, 2).tolist(),
                           "frame": {"origin_lonlat": list(self.o.origin), "axes": "x = E, y = N, metres"}, "_lay": lay})
            emit.centerline_geojson(self.o, Cm, Wm, self.out / f"{L['id']}.centerline.geojson", self.cfg.get("name", ""),
                                    {"aerial_engine": {"layout": L["id"], "image": self.o.desc["image"],
                                                       "registration_shift_en_m": self.o.shift.round(3).tolist()}})
            # the source block's screenshot path is the project's own (build_aerial resolves it against the project
            # dir: the track folder whose data/centerline.local.json is origin_from), else absolute
            proj = _path(self.base, self.cfg["origin_from"]).parent.parent if self.cfg.get("origin_from") else None
            img_rel = os.path.relpath(self.o.desc["image"], proj) if proj else self.o.desc["image"]
            emit.source_block(self.o, Cm, Wm, img_rel, self.out / f"{L['id']}.source.json")
            if do_stills:
                stills.overall(self.o, Cm, self.out / f"{L['id']}_overall.jpg")
                stills.zooms(self.o, Cm, sm, self.out / f"{L['id']}_zooms.jpg")
            log(f"layout {L['id']}: lap {lap:.1f} m" + (f" (published {pub}: {lay['vs_published_m']})" if pub else ""))
        self._split_pieces(done, pieces)
        for b in bodies:
            lay = b.pop("_lay")
            (self.out / f"{b['id']}.layout.json").write_text(json.dumps({**b, **lay}, indent=1, default=_jd), encoding="utf-8")
        (self.out / "pieces.json").write_text(json.dumps({"pieces": pieces}, indent=1, default=_jd), encoding="utf-8")
        self.rep["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (self.out / "report.json").write_text(json.dumps(self.rep, indent=1, default=_jd), encoding="utf-8")
        log(f"-> {self.out}")
        return self.rep

    def _split_pieces(self, done, pieces):
        """A layout measured whole is cut into pieces where later layouts join or leave it; every layout's parts are
        then named by those pieces (a shared stretch lists the pieces it runs over)."""
        cuts = {}
        for lid, d in done.items():
            for p in d["parts"]:
                if p.get("_ref"):
                    base, ja, jb = p["_ref"]
                    cuts.setdefault(base, set()).update([ja, jb])
        for base, cs in cuts.items():
            d = done[base]
            if d.get("summ") is None:
                continue
            n = len(d["C"])
            i0 = d["i0"]
            cs = sorted(set(cs) | {i0})
            order = sorted(cs, key=lambda c: (c - i0) % n)
            names = []
            spans = {}
            for q, a in enumerate(order):
                b = order[(q + 1) % len(order)]
                idx = np.arange(a, a + ((b - a) % n or n) + 1) % n
                name = f"{base}.p{q + 1}"
                pieces[name] = self._piece_record(d["summ"], 0, 0, False, name, idx)
                spans[name] = (a, (b - a) % n or n)
                names.append(name)
            pieces.pop(f"{base}.all", None)
            d["lay"]["parts"] = [{"piece": nm, "kind": "measured", "length_m": pieces[nm]["length_m"]} for nm in names]
            for lid, dd in done.items():
                for p, pub in zip(dd["parts"], dd["lay"]["parts"]):
                    if p.get("_ref") and p["_ref"][0] == base:
                        _, ja, jb = p["_ref"]
                        L_ = (jb - ja) % n
                        pub["pieces"] = [nm for nm in names if (spans[nm][0] - ja) % n < L_]

    @staticmethod
    def _agrees(line, ref):
        """+1 if the line runs the way ``ref`` does where they lie together (within 6 m), -1 if against, 0 if apart."""
        T1, _ = geom.normals(line, closed=True)
        T2, _ = geom.normals(ref, closed=True)
        d, j = cKDTree(ref).query(line)
        near = d < 6.0
        if near.sum() < 10:
            return 0
        return int(np.sign(np.sum((T1[near] * T2[j[near]]).sum(1))))

    def _measure_layout(self, L, G, done):
        band_opts = self.cfg.get("band") or {}
        if not done:
            summ = network.measure_route(self.ctx, G, True, band_opts)
            if summ is None:
                raise SystemExit(f"[aerial-engine] layout {L['id']}: too few edges on one side to fit the lap")
            C, W = summ["C"], summ["W"]
            name = f"{L['id']}.all"
            part = {"piece": name, "kind": "measured", "length_m": round(geom.closed_len(C), 1),
                    "_own": self._piece_record(summ, 0, len(C) - 1, True, name)}
            return {"C": C, "W": W, "parts": [part], "joins": [], "report": summ["report"], "m": summ["m"], "summ": summ}
        prev = [d["C"] for d in done.values()]
        prev_W = [d["W"] for d in done.values()]
        prev_ids = list(done)
        who, at = network.shared_mask(G, prev, prev_W)
        n = len(G)
        # rotate so the walk starts at a change of ownership (never inside a run)
        ch = np.where(who != np.roll(who, 1))[0]
        r0 = int(ch[0]) if len(ch) else 0
        order = np.roll(np.arange(n), -r0)
        segs = []
        cur = [order[0]]
        for i in order[1:]:
            if who[i] == who[cur[-1]]:
                cur.append(i)
            else:
                segs.append(cur)
                cur = [i]
        segs.append(cur)
        parts, Cs, Ws = [], [], []
        first_shared = None
        reports = []
        ext = int(network.EXT_M / edg.STEP_M)
        for seg in segs:
            seg = np.array(seg)
            k = who[seg[0]]
            if k >= 0:
                Cp, Wp = prev[k], prev_W[k]
                ja = geom.nearest(Cp, G[seg[0]])[0]
                jb = geom.nearest(Cp, G[seg[-1]])[0]
                m_ = len(Cp)
                idx = np.arange(ja, jb + 1) if jb >= ja else np.r_[np.arange(ja, m_), np.arange(0, jb + 1)]
                if len(idx) > 0.9 * m_:      # the short way round is the other direction: not expected, refuse
                    raise SystemExit(f"[aerial-engine] layout {L['id']}: a shared stretch maps onto most of "
                                     f"{prev_ids[k]}'s lap; check the direction")
                Q, Wq = Cp[idx], Wp[idx]
                if first_shared is None:
                    first_shared = len(np.vstack(Cs)) if Cs else 0
                parts.append({"piece": f"{prev_ids[k]}@{ja * edg.STEP_M:.0f}-{jb * edg.STEP_M:.0f}", "kind": "shared",
                              "from_layout": prev_ids[k], "length_m": round(float(geom.cumlen(Q)[-1]), 1),
                              "_ref": (prev_ids[k], int(ja), int(jb))})
            else:
                ii = np.r_[np.arange(seg[0] - ext, seg[0]), seg, np.arange(seg[-1] + 1, seg[-1] + 1 + ext)] % n
                log(f"  own stretch {len(seg) * edg.STEP_M:.0f} m from guide station {seg[0] * edg.STEP_M:.0f}")
                summ = network.measure_route(self.ctx, G[ii], False, band_opts)
                name = f"{L['id']}.own{len([p for p in parts if p['kind'] != 'shared']) + 1}"
                if summ is None:
                    # too few edges on a side to fit: NOT measured. The guide is kept so the layout closes, and the
                    # stretch is reported as unmeasured, never as a measurement
                    Q = G[seg]
                    Wq = np.full(len(seg), np.nan)
                    reports.append({"piece": name, "unmeasured": "too few edges on one side to fit"})
                    parts.append({"piece": name, "kind": "UNMEASURED (guide only)",
                                  "length_m": round(float(geom.cumlen(Q)[-1]), 1)})
                    log(f"  {name}: UNMEASURED, too few edges on one side")
                else:
                    Cfull = summ["C"]
                    a = geom.nearest(Cfull, G[seg[0]])[0]
                    b = geom.nearest(Cfull, G[seg[-1]])[0]
                    Q, Wq = Cfull[a:b + 1], summ["W"][a:b + 1]
                    reports.append({"piece": name, **summ["report"]})
                    parts.append({"piece": name, "kind": "measured", "length_m": round(float(geom.cumlen(Q)[-1]), 1),
                                  "_own": self._piece_record(summ, a, b, False, name)})
            Cs.append(Q)
            Ws.append(Wq)
        joins = []
        for i in range(len(Cs)):
            A, B = Cs[i], Cs[(i + 1) % len(Cs)]
            joins.append({"after": parts[i]["piece"], "before": parts[(i + 1) % len(parts)]["piece"],
                          "gap_m": round(float(np.hypot(*(A[-1] - B[0]))), 2)})
        C = np.vstack(Cs)
        W = np.concatenate(Ws)
        if np.isnan(W).any():          # an unmeasured stretch: its width held from its measured neighbours, flagged
            ok = np.isfinite(W)
            W = np.interp(np.arange(len(W)), np.where(ok)[0], W[ok])
        keep = np.r_[True, np.hypot(*np.diff(C, axis=0).T) > 1e-6]
        C, W = C[keep], W[keep]
        Cr = geom.resample(C, edg.STEP_M, closed=True)
        s_old = geom.cumlen(np.vstack([C, C[:1]]))
        s_new = geom.cumlen(np.vstack([Cr, Cr[:1]]))
        W = np.interp(s_new[:-1] / s_new[-1] * s_old[-1], s_old[:-1], W)
        # every join between stretches measured apart steps by its gap: blended over JOIN_OUT_M round it (full
        # weight within JOIN_IN_M) towards a JOIN_SMOOTH_M gaussian of the line; the gap itself stays reported
        jpos = [geom.nearest(Cr, Q[0])[0] for Q in Cs]
        sr = s_new[:-1]
        total = s_new[-1]
        dj = np.full(len(Cr), np.inf)
        for j in jpos:
            d = np.abs(sr - sr[j])
            dj = np.minimum(dj, np.minimum(d, total - d))
        w = np.clip((JOIN_OUT_M - dj) / (JOIN_OUT_M - JOIN_IN_M), 0, 1)[:, None]
        Cr = Cr * (1 - w) + geom.smooth(Cr, JOIN_SMOOTH_M, edg.STEP_M, closed=True) * w
        fs = None
        if first_shared is not None:
            fs = geom.nearest(Cr, C[first_shared])[0]
        return {"C": Cr, "W": W, "parts": parts, "joins": joins, "report": {"own_stretches": reports}, "first_shared": fs}

    def _piece_record(self, summ, a, b, closed, name, idx=None):
        """A measured piece: stations a..b of a strip (``idx`` overrides, e.g. a range wrapping a closed lap)."""
        m = summ["m"]
        s = m["s"]
        if idx is None:
            idx = np.arange(a, b + 1)
        idx = np.asarray(idx)
        span = np.diff(s[idx])
        span = np.where(span < 0, edg.STEP_M, span)           # across a closed lap's seam
        rec = {"piece": name, "length_m": round(float(geom.closed_len(summ["C"]) if closed else span.sum()), 1)}
        for side, sgn in (("left", 1.0), ("right", -1.0)):
            o = m["sides"][side]
            st = o["status"][idx]
            use = np.isin(st, ("seen", "lidar"))
            res = (o["x"] - o["sp"](s))[idx][use & (st != "lidar")]
            inf = {}
            for why in ("opening", "weak", "shadow", "outlier"):
                rr = [(float(s[idx[p]]), float(s[idx[q]])) for p, q in geom.runs(st == why) if s[idx[q]] - s[idx[p]] >= 1.0]
                if rr:
                    inf[why] = [[round(x, 1), round(y, 1)] for x, y in rr]
            ev = {}
            for r, u in zip([o["raw"][i] for i in idx], use):
                if u and r is not None:
                    ev[r["type"]] = ev.get(r["type"], 0) + 1
            if (st == "lidar").any():
                ev["lidar"] = int((st == "lidar").sum())
            rec[side] = {"seen_fraction": round(float(use.mean()), 3), "residual_m": geom.pct(res),
                         "inferred_m": inf, "evidence": ev,
                         "edge_en_m": np.round(summ[side + "_E"][idx][::4], 2).tolist()}
        W = summ["W"][idx]
        rec["width_m"] = {"min": round(float(W.min()), 2), "p50": round(float(np.median(W)), 2), "max": round(float(W.max()), 2)}
        Cc = summ["C"][idx]
        sc = geom.cumlen(Cc)
        smm = np.arange(0, sc[-1] + 1e-9, 1.0)
        rec["centre_en_m"] = np.round(np.c_[np.interp(smm, sc, Cc[:, 0]), np.interp(smm, sc, Cc[:, 1])], 2).tolist()
        rec["width_m_per_metre"] = np.round(np.interp(smm, sc, W), 2).tolist()
        bi = summ.get("inferred_band")
        if bi is not None and bi[idx].any():
            rec["band_bridged_m"] = round(float(bi[idx].sum() * edg.STEP_M), 1)
        return rec

    def _corners(self, labels, Cm):
        """Each map label -> the map line's nearest point (the corner it names) -> that point's station on the lap.
        Labels are printed beside the line, so a station is good to a corner's length, not to an apex."""
        out = {}
        for key, (labs, line) in labels.items():
            for k, p in labs.items():
                j, dl = geom.nearest(line, p)
                s, d, _ = _station(Cm, line[j])
                out.setdefault(k.lstrip("T"), {})[key] = {"s_m": round(s, 1), "label_to_line_m": round(dl, 1),
                                                          "line_to_lap_m": round(d, 1)}
        return dict(sorted(out.items(), key=lambda kv: (len(kv[0]), kv[0])))

    def _kerbs(self, Cm, Wm):
        line = kerbs.Line(self.o, np.vstack([Cm, Cm[:1]]), np.r_[Wm, Wm[:1]])
        out = []
        for sgn, name in ((1, "left"), (-1, "right")):
            for a, b in kerbs.scan(line, sgn):
                m = kerbs.measure(line, sgn, a, b)
                if m:
                    out.append({"side": name, "candidate_s": [round(a, 1), round(b, 1)], **m})
        return {"runs": out, "total_m": round(sum(r["s1"] - r["s0"] for r in out), 1),
                "note": "candidates found by block rhythm and measured by the block reader (ledger 0081's rules); "
                        "a run is a candidate until seen on its straightened strip"}


def _station(L, p):
    s = geom.cumlen(L)
    d = np.hypot(*(L - np.asarray(p, float)).T)
    i = int(np.argmin(d))
    return float(s[i]), float(d[i]), i


def _jd(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if hasattr(o, "tolist"):
        return o.tolist()
    return str(o)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    cfg, base = load_config(argv.pop(0))
    out, only, do_stills = None, [], True
    while argv:
        a = argv.pop(0)
        if a == "--out":
            out = Path(argv.pop(0))
        elif a == "--layout":
            only.append(argv.pop(0))
        elif a == "--no-stills":
            do_stills = False
    Stage(cfg, base, out or (base / "out")).run(only or None, do_stills)


if __name__ == "__main__":
    main()
