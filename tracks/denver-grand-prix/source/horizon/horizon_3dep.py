"""The horizon study of horizon_study.py re-run on USGS 3DEP 1/3 arc-second (about 10 m cells), PLAN section 3.

Same three sites, same peaks (read out of horizon_study.py, not copied), same eye height, curvature and refraction, same
"local maximum within about 600 m of the nominal summit" rule. What differs: the DEM (seven 1 x 1 degree GeoTIFFs,
bare earth, NAVD88), the ray step (10 m near, 0.05 % of distance far, where the plan-grade study stepped 120 m / 0.4 %),
and the reach: rays stop at DMAX_M = 112 km (the tiles cover bearing 180-335 from all three sites that far; the
plan-grade file's farthest skyline cell in that arc is 102 km).

    python3 horizon_3dep.py tiles <dir>     # prints the seven tile URLs to fetch into <dir> (about 2.8 GB; NOT in git)
    python3 horizon_3dep.py <dir>           # reads <dir>/USGS_13_*.tif, writes horizon.3dep13.json beside this file

Needs numpy and rasterio (reading only). No network in the study itself.
"""
import ast, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TILES = ['n39w105', 'n39w106', 'n40w105', 'n40w106', 'n40w107', 'n41w106', 'n41w107']     # named by their NW corner
URL = 'https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/13/TIFF/current/{t}/USGS_13_{t}.tif'
R = 6371000.0; K = 0.13; EYE = 1.2; DMAX_M = 112000.0; B0, B1, STEP = 180.0, 335.0, 0.5

if len(sys.argv) > 2 and sys.argv[1] == 'tiles':
    for t in TILES:
        print(URL.format(t=t), '->', os.path.join(sys.argv[2], f'USGS_13_{t}.tif'))
    sys.exit(0)


def constants():
    """SITES and PEAKS as horizon_study.py declares them (that module reads its DEM at import, so it is parsed)"""
    out = {}
    for node in ast.parse(open(os.path.join(HERE, 'horizon_study.py')).read()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', None) in ('SITES', 'PEAKS'):
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out['SITES'], out['PEAKS']


class Dem:
    def __init__(self, d):
        import rasterio
        self.t = {}; self.meta = {}
        for t in TILES:
            p = os.path.join(d, f'USGS_13_{t}.tif')
            with rasterio.open(p) as src:
                a = src.read(1); tr = src.transform
                self.meta[t] = {'file': os.path.basename(p), 'bytes': os.path.getsize(p), 'w': src.width, 'h': src.height,
                                'cell_deg': tr.a, 'crs': str(src.crs), 'nodata': src.nodata, 'url': URL.format(t=t)}
            a[a < -1000] = np.nan
            self.t[(int(t[1:3]), int(t[4:7]))] = (a, tr.c, tr.f, tr.a, -tr.e)        # lat of N edge, lon of W edge (positive west)

    def elev(self, lon, lat):
        lon = np.atleast_1d(np.asarray(lon, float)); lat = np.atleast_1d(np.asarray(lat, float))
        out = np.full(lon.shape, np.nan)
        kn = np.ceil(lat).astype(int); kw = np.ceil(-lon).astype(int)
        for (n, w), (a, x0, y0, dx, dy) in self.t.items():
            m = (kn == n) & (kw == w)
            if not m.any():
                continue
            fx = (lon[m] - x0) / dx - 0.5; fy = (y0 - lat[m]) / dy - 0.5              # cell centres
            ix = np.clip(np.floor(fx).astype(int), 0, a.shape[1] - 2); iy = np.clip(np.floor(fy).astype(int), 0, a.shape[0] - 2)
            tx = fx - ix; ty = fy - iy
            out[m] = (a[iy, ix] * (1 - tx) * (1 - ty) + a[iy, ix + 1] * tx * (1 - ty) + a[iy + 1, ix] * (1 - tx) * ty + a[iy + 1, ix + 1] * tx * ty)
        return out


def dest(lon, lat, brg, d):
    b = math.radians(brg); la = math.radians(lat); lo = math.radians(lon); a = d / R
    la2 = np.arcsin(math.sin(la) * np.cos(a) + math.cos(la) * np.sin(a) * math.cos(b))
    lo2 = lo + np.arctan2(math.sin(b) * np.sin(a) * math.cos(la), np.cos(a) - math.sin(la) * np.sin(la2))
    return np.degrees(lo2), np.degrees(la2)


def bearing_dist(lon, lat, lon2, lat2):
    la = math.radians(lat); la2 = math.radians(lat2); dl = math.radians(lon2 - lon)
    y = math.sin(dl) * math.cos(la2); x = math.cos(la) * math.sin(la2) - math.sin(la) * math.cos(la2) * math.cos(dl)
    a = math.sin((la2 - la) / 2) ** 2 + math.cos(la) * math.cos(la2) * math.sin(dl / 2) ** 2
    return (math.degrees(math.atan2(y, x)) + 360) % 360, 2 * R * math.asin(math.sqrt(a))


def steps(dmax):
    d = [300.0]
    while d[-1] < dmax:
        d.append(d[-1] + max(10.0, d[-1] * 0.0005))
    return np.array(d[:-1])


def ang(h0, h, d):
    return np.degrees(np.arctan2(h - h0 - d * d * (1 - K) / (2 * R), d))


def main(d):
    dem = Dem(d); SITES, PEAKS = constants(); D = steps(DMAX_M)
    res = {'_doc': 'Terrain skyline by bearing (deg true), %.1f deg steps, %.0f-%.0f: [bearing, altitude_deg above horizontal, distance_m of '
                   'the skyline-forming cell, its elevation_m], and every named peak from every site (bearing and distance to the DEM summit inside the box; blocked_below = the highest ground on that bearing up to 2.5 km short of it, with where it is; beyond_2km repeats that ignoring ground nearer than 2 km, so a bank beside the site does not decide a peak). Eye %.1f m over the DEM ground; '
                   'curvature with refraction k=%.2f; rays to %.0f km. DEM: USGS 3DEP 1/3 arc-second (about 10 m cells, bare earth, '
                   'NAVD88), the staged 1 x 1 degree tiles listed under "dem". Script: horizon_3dep.py beside this file. The plan-grade '
                   'study it replaces: horizon.plan-grade.json.' % (STEP, B0, B1, EYE, K, DMAX_M / 1000),
           'dem': dem.meta, 'sites': {}, 'peaks': {}, 'site_ground_m': {}}
    for s, (lo, la) in SITES.items():
        g = float(dem.elev(lo, la)[0]); h0 = g + EYE; res['site_ground_m'][s] = round(g, 2)
        sky = []
        for i in range(int((B1 - B0) / STEP) + 1):
            b = B0 + i * STEP
            e = dem.elev(*dest(lo, la, b, D)); a = ang(h0, e, D)
            if np.isnan(a).any():
                raise SystemExit(f'{s}: bearing {b} leaves the tiles at {D[np.isnan(a)][0] / 1000:.1f} km')
            k = int(np.argmax(a)); sky.append([b, round(float(a[k]), 3), int(D[k]), int(round(float(e[k])))])
        res['sites'][s] = sky
        pk = {}
        for name, (plo, pla) in PEAKS.items():
            b, dd = bearing_dist(lo, la, plo, pla)
            gx, gy = np.meshgrid(np.linspace(-0.008, 0.008, 161), np.linspace(-0.006, 0.006, 121))    # the same box, 10 m steps
            ez = dem.elev(plo + gx.ravel(), pla + gy.ravel())
            if np.isnan(ez).all():
                pk[name] = None; continue
            j = int(np.nanargmax(ez)); top = float(ez[j]); slo = plo + gx.ravel()[j]; sla = pla + gy.ravel()[j]
            b, dd = bearing_dist(lo, la, slo, sla)                                           # to the DEM's own summit
            ap = float(ang(h0, top, dd)); Dn = D[D < dd - 2500]
            en = dem.elev(*dest(lo, la, b, Dn)); an = ang(h0, en, Dn); kb = int(np.nanargmax(an)); bl = float(an[kb])
            blo, bla = dest(lo, la, b, Dn[kb:kb + 1])
            far = Dn >= 2000.0; kf = int(np.nanargmax(np.where(far, an, -90.0)))            # the same, ignoring ground nearer than 2 km
            pk[name] = {'bearing_deg': round(b, 2), 'distance_km': round(dd / 1000, 2), 'summit_dem_m': round(top, 1),
                        'summit_lon_lat': [round(slo, 5), round(sla, 5)], 'altitude_deg': round(ap, 3),
                        'nominal_bearing_deg': round(bearing_dist(lo, la, plo, pla)[0], 2),
                        'blocked_below_deg': round(bl, 3), 'visible': ap > bl, 'clearance_deg': round(ap - bl, 3),
                        'blocker': {'distance_km': round(float(Dn[kb]) / 1000, 2), 'elevation_m': round(float(en[kb]), 1),
                                    'lon_lat': [round(float(blo[0]), 5), round(float(bla[0]), 5)]},
                        'beyond_2km': {'blocked_below_deg': round(float(an[kf]), 3), 'visible': ap > float(an[kf]),
                                       'clearance_deg': round(ap - float(an[kf]), 3), 'blocker_distance_km': round(float(Dn[kf]) / 1000, 2),
                                       'blocker_elevation_m': round(float(en[kf]), 1)}}
        res['peaks'][s] = pk
        ds = sorted(r[2] for r in sky if 200 <= r[0] <= 330)
        print(f"\n== {s}  ground {g:.1f} m   skyline cells 200-330: {ds[0] / 1000:.1f} / {ds[len(ds) // 2] / 1000:.1f} / {ds[-1] / 1000:.1f} km; "
              f"highest {max(r[1] for r in sky):.2f} deg")
        for name, v in sorted(pk.items(), key=lambda kv: kv[1]['bearing_deg'] if kv[1] else 999):
            if v:
                print(f"{v['bearing_deg']:7.2f} deg  {name:22s} {v['distance_km']:6.1f} km  dem {v['summit_dem_m']:6.0f} m  alt {v['altitude_deg']:5.2f}  "
                      f"blocked-below {v['blocked_below_deg']:5.2f}  {'VISIBLE' if v['visible'] else 'hidden'} ({v['clearance_deg']:+.2f})  "
                      f"highest ground in front: {v['blocker']['elevation_m']:.0f} m at {v['blocker']['distance_km']:.1f} km"
                      + ('' if v['blocker']['distance_km'] >= 2 else f"; beyond 2 km: {v['beyond_2km']['blocked_below_deg']:.2f} ({v['beyond_2km']['clearance_deg']:+.2f}) at {v['beyond_2km']['blocker_distance_km']:.1f} km"))
    json.dump(res, open(os.path.join(HERE, 'horizon.3dep13.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main(sys.argv[1])
