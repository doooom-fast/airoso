"""In-game drive gate — read AC's shared memory while a lap happens, judge it (REALISM.md §7).

The offline ``drive_test`` sweeps wheel paths over built triangles; THIS is its in-sim twin: it
watches a real car on the real installed track and scores the lap. Gate scope agreed with Kevin
2026-07-28 (see memory `ac-has-no-ai-lines`):

  1. lap completes            (graphics.completedLaps increments, iLastTime > 0)
  2. car stays on the surface (physics.numberOfTyresOut — catches mesh holes like ledger 0017)
  3. no unexplained contact   (physics.carDamage delta on a clean lap = invisible wall/prop)
  4. speed and smoothness     (profile recorded; the envelope comparison lands with R4)

AC publishes ``acpmf_physics`` / ``acpmf_graphics`` / ``acpmf_static`` as memory-mapped files —
readable at sim rate from plain Python ``mmap`` (tagname), no game-side code (struct layout:
fleet/reference/RESEARCH.md §B6). The harness ATTACHES to whatever session is running — Kevin
driving, or AI once ``write_ai_line`` output is proven — so the same gate covers both. It never
replaces Kevin's drive; it decides whether a build is worth it.

    python -m scripts.ac.ac_drive_test --attach                 # wait for a session, record 1 lap
    python -m scripts.ac.ac_drive_test --attach --laps 3 --out project/data/
    python -m scripts.ac.ac_drive_test --snapshot-race-ini      # save CM's race.ini as a template

Offsets are the classic AC (not ACC) pages; ``normalizedCarPosition`` is validated at runtime
(must be 0..1) and dropped from the report if the build disagrees.
"""

from __future__ import annotations

import argparse
import json
import mmap
import struct
import time
from pathlib import Path

PHYS = {"packetId": (0, "<i"), "gas": (4, "<f"), "brake": (8, "<f"), "gear": (16, "<i"),
        "rpms": (20, "<i"), "speedKmh": (28, "<f"), "heading": (208, "<f"),
        "carDamage": (224, "<5f"), "numberOfTyresOut": (244, "<i")}
GRAPH = {"packetId": (0, "<i"), "status": (4, "<i"), "session": (8, "<i"),
         "completedLaps": (132, "<i"), "position": (136, "<i"), "iCurrentTime": (140, "<i"),
         "iLastTime": (144, "<i"), "iBestTime": (148, "<i"), "sessionTimeLeft": (152, "<f"),
         "distanceTraveled": (156, "<f"), "isInPit": (160, "<i"),
         "normalizedCarPosition": (248, "<f")}
STATUS = {0: "OFF", 1: "REPLAY", 2: "LIVE", 3: "PAUSE"}


class Page:
    def __init__(self, tag: str, size: int):
        self.mm = mmap.mmap(-1, size, tagname=tag)

    def read(self, fields: dict) -> dict:
        out = {}
        for name, (off, fmt) in fields.items():
            v = struct.unpack_from(fmt, self.mm, off)
            out[name] = v[0] if len(v) == 1 else list(v)
        return out

    def wstr(self, off: int, nch: int) -> str:
        raw = self.mm[off:off + nch * 2]
        return raw.decode("utf-16-le", "replace").split("\x00")[0]


def attach(timeout_s: float):
    """Wait until AC exists and its physics packetId is advancing; return (phys, graph, static)."""
    t0 = time.time()
    while True:
        try:
            p = Page("acpmf_physics", 512)
            g = Page("acpmf_graphics", 512)
            s = Page("acpmf_static", 512)
            a = p.read({"packetId": PHYS["packetId"]})["packetId"]
            time.sleep(0.3)
            if p.read({"packetId": PHYS["packetId"]})["packetId"] != a:
                return p, g, s
        except (OSError, ValueError):
            pass
        if time.time() - t0 > timeout_s:
            raise TimeoutError("no live AC session appeared (launch the sim, enter the track)")
        time.sleep(1.0)


def record(laps_wanted: int, max_s: float, hz: float, out_dir: Path) -> dict:
    p, g, s = attach(max_s)
    track = s.wstr(134, 33)
    car = s.wstr(68, 33)
    print(f"attached: {car} @ {track}  (waiting for LIVE laps; ctrl-c stops early)")

    rows, events = [], []
    laps_done = 0
    lap_times = []
    base_damage = None
    norm_ok = True
    tyres_streak_start = None
    worst_streak = 0.0
    t0 = time.time()
    last_g = g.read(GRAPH)
    period = 1.0 / hz
    try:
        while time.time() - t0 < max_s:
            ph = p.read(PHYS)
            gr = g.read(GRAPH)
            t = time.time() - t0
            if gr["status"] == 2:                                        # LIVE only
                dmg = sum(ph["carDamage"])
                if base_damage is None:
                    base_damage = dmg
                if not (0.0 <= gr["normalizedCarPosition"] <= 1.0):
                    norm_ok = False
                out_n = ph["numberOfTyresOut"]
                if out_n > 2:
                    tyres_streak_start = tyres_streak_start or t
                else:
                    if tyres_streak_start is not None:
                        worst_streak = max(worst_streak, t - tyres_streak_start)
                        tyres_streak_start = None
                if dmg - (base_damage or 0.0) > 0.5 and not any(e["kind"] == "damage" for e in events):
                    events.append({"kind": "damage", "t": round(t, 2),
                                   "delta": round(dmg - base_damage, 2),
                                   "pos": round(gr["normalizedCarPosition"], 4)})
                if gr["completedLaps"] > last_g["completedLaps"]:
                    laps_done += gr["completedLaps"] - last_g["completedLaps"]
                    lap_times.append(gr["iLastTime"])
                    print(f"  lap {gr['completedLaps']}: {gr['iLastTime'] / 1000:.3f} s")
                rows.append([round(t, 3), round(ph["speedKmh"], 1), round(ph["gas"], 3),
                             round(ph["brake"], 3), ph["gear"], out_n,
                             round(gr["normalizedCarPosition"], 5), gr["completedLaps"]])
            last_g = gr
            if laps_wanted and laps_done >= laps_wanted:
                break
            time.sleep(period)
    except KeyboardInterrupt:
        print("  (stopped)")
    if tyres_streak_start is not None:
        worst_streak = max(worst_streak, (time.time() - t0) - tyres_streak_start)

    speeds = [r[1] for r in rows if r[1] > 1]
    gate = {
        "lap_completes": laps_done >= 1 and any(lt > 0 for lt in lap_times),
        "stays_on_surface": worst_streak <= 1.0,
        "no_unexplained_contact": not any(e["kind"] == "damage" for e in events),
        "speed_recorded": bool(speeds),
    }
    report = {
        "track": track, "car": car, "laps": laps_done,
        "lap_times_ms": lap_times, "samples": len(rows),
        "speed_kmh": {"min": min(speeds) if speeds else None,
                      "max": max(speeds) if speeds else None,
                      "avg": round(sum(speeds) / len(speeds), 1) if speeds else None},
        "worst_tyres_out_streak_s": round(worst_streak, 2),
        "events": events,
        "normalizedCarPosition_valid": norm_ok,
        "gate": gate, "PASS": all(gate.values()),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"ac_drive_test_{track or 'unknown'}"
    (out_dir / f"{stem}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    with open(out_dir / f"{stem}.csv", "w", encoding="ascii") as f:
        f.write("t,speed_kmh,gas,brake,gear,tyres_out,norm_pos,laps\n")
        f.writelines(",".join(map(str, r)) + "\n" for r in rows)
    return report


def snapshot_race_ini(out_dir: Path) -> None:
    """Save the launcher's current race.ini — the template future auto-launch will patch."""
    src = Path.home() / "Documents" / "Assetto Corsa" / "cfg" / "race.ini"
    if not src.exists():
        print(f"not found: {src} (start any session once so CM writes it)")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "race.ini.template"
    dst.write_bytes(src.read_bytes())
    print(f"saved {src} -> {dst}")


def main() -> None:
    ap = argparse.ArgumentParser(description="In-game drive gate over AC shared memory.")
    ap.add_argument("--attach", action="store_true", help="attach to a running/soon session")
    ap.add_argument("--laps", type=int, default=1, help="stop after N completed laps (0 = run to timeout)")
    ap.add_argument("--max-s", type=float, default=900.0)
    ap.add_argument("--hz", type=float, default=20.0)
    ap.add_argument("--out", type=Path, default=Path("."))
    ap.add_argument("--snapshot-race-ini", action="store_true")
    args = ap.parse_args()

    if args.snapshot_race_ini:
        snapshot_race_ini(args.out)
        return
    if not args.attach:
        print("nothing to do: pass --attach (record a session) or --snapshot-race-ini")
        return
    r = record(args.laps, args.max_s, args.hz, args.out)
    print(json.dumps({k: r[k] for k in ("track", "car", "laps", "speed_kmh",
                                        "worst_tyres_out_streak_s", "gate", "PASS")}, indent=1))
    print("PASS" if r["PASS"] else "FAIL", "— offline verdict only; the drive itself is the gate")


if __name__ == "__main__":
    main()
