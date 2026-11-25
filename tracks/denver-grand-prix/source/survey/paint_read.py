"""Road paint read off an orthophoto: the first reader of PLAN section 4b's paint inventory.

    python3 paint_read.py <image.png> <out.json> [--overlay out.jpg] [--lidar points.npz]

The image carries its georeference in a sidecar (drapp_mosaic.py's bbox json, or tools/naip_crop.py's corners json); it
is loaded through the aerial engine (scripts.aerial.engine.ortho.Ortho: the CRS from the sidecar, a local ENU frame)
and its luminance channels through scripts.aerial.engine.channels. Nothing is placed by eye and nothing is drawn where
no pixel is.

Method. Paint is a thin mark brighter than the asphalt on both sides of it:
  1. white: the luminance top-hat over TOPHAT_M (a mark narrower than that stands out of its background) at least
     WHITE_TOP over a background darker than PAVE_LUM_MAX; yellow: the same on the yellow axis ((r+g)/2 - b);
  2. only on the roadway: flooded outward from the OSM street lines (OSM says where to look, never where anything is)
     within WINDOW_M over ground that is dark (under PAVE_LUM_MAX) and has asphalt's colour (the engine's yellow axis,
     thin marks removed, under ROAD_YEL_MAX: lawn, mulch and concrete are yellower), opened by LEAK_M; what stands on it
     (vehicles, islands up to HOLE_M2) is filled and what is not asphalt there is counted as covered;
  2b. white marks are split by thickness (an opening THICK_M wide) so a lane line and the stop bar it runs into are two
     marks; a yellow mark wider than DOUBLE_W_MIN is a double line (the two lines are not resolved separately at 3 inches);
  3. connected marks, each measured by its own principal axis: length, width (area / length), bearing, a centre line
     sampled every STEP_M across its width (so a curved line stays curved);
  4. a mark with pavement on one side only is a kerb or a slab edge, not paint, and is dropped (counted); so is a mark
     with rough ground beside it (branches over grass, a planter): paint under a tree's shadow can be lost this way;
  5. classes by measured shape alone: line (thin, long), dash (thin, short), block (0.3-1.0 m wide, 1-5 m long: a
     crosswalk bar or a stop-bar piece), bar (0.3-1.0 m wide, longer), symbol (anything else small: arrows, legends;
     the type is NOT read);
  6. blocks side by side at one spacing become a crosswalk (its outline, bar count, bar size and spacing measured);
     dashes end to end on one line become a broken line (dash and gap measured).
  7. with --lidar (ept_box.py's points, a different sensor and year): a mark with no ground return within LIDAR_GROUND_R is
     not on the ground (a roof the colour of asphalt) and is dropped; and each mark is checked against the returns that
     land on it: paint returns far more of the laser than asphalt, so 'lidar_confirms' is true when at least LIDAR_MIN_N
     ground returns on the mark average LIDAR_DLOG over the roadway's median log-intensity, false when they do not, and
     absent when too few returns landed on it to say. This is the independent reading (law L5); it places nothing.
Every threshold is [invented] tuning of a colour reader and is written into the output; the image is the measurement.
Vehicles and deep shadow hide paint: marks are reported as read, a hidden stretch is simply absent, and the share of the
window that is too dark or covered is reported so absence is not read as "none".
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4))
sys.path.insert(0, ROOT)
from scripts.aerial.engine.ortho import Ortho  # noqa: E402
from scripts.aerial.engine import channels  # noqa: E402

T = os.path.join(ROOT, 'tracks', 'denver-grand-prix')
ORIGIN = (-104.9849, 39.7401)
P = {'TOPHAT_M': 1.4, 'WHITE_TOP': 22.0, 'WHITE_SAT_MAX': 0.16, 'YEL_TOP': 16.0, 'PAVE_LUM_MAX': 165.0, 'SHADOW_LUM': 45.0,
     'WINDOW_M': 16.0, 'LANE_M': 3.5, 'SIDE_ALLOW_M': 4.5, 'TEX_MAX': 9.0, 'ROAD_YEL_MAX': 6.0, 'LEAK_M': 2.4, 'SIDE_SMOOTH_MIN': 0.5, 'VEH_DLUM': 38.0, 'HOLE_M2': 90.0, 'THICK_M': 0.34, 'DOUBLE_W_MIN': 0.27, 'SIDE_DIFF_MAX': 22.0, 'STEP_M': 0.5, 'MIN_AREA_M2': 0.08, 'SIDE_M': 0.28, 'LINE_W_MAX': 0.33, 'DASH_L_MAX': 4.6,
     'BLOCK_W': (0.33, 1.05), 'BLOCK_L': (1.0, 5.2), 'CW_GAP_MAX': 3.0, 'LIDAR_GROUND_R': 0.75, 'LIDAR_MIN_N': 3, 'LIDAR_DLOG': 1.0, 'CW_MIN_BARS': 3}


def osm_lines(ortho):
    o = json.load(open(os.path.join(T, 'source', 'osm.json')))
    out = []
    for w in o['ways']:
        hw = w['tags'].get('highway')
        if hw in (None, 'service', 'footway', 'cycleway', 'path', 'steps', 'pedestrian', 'construction', 'proposed'):
            continue
        ll = np.array([o['nodes'][str(n)] for n in w['nodes']])
        e, n = ortho.lonlat_to_en(ll[:, 0], ll[:, 1]); x, y = ortho.en_to_px(e, n)
        if ((x > -200) & (x < ortho.W + 200) & (y > -200) & (y < ortho.H + 200)).any():
            out.append((w, np.stack([x, y], 1)))
    return out


def window(ortho, lines, gsd):
    """where to look: a band about each OSM street line as wide as its tagged lanes allow (lanes x LANE_M each side of the
    line, plus SIDE_ALLOW_M for parking, a bike lane and the line being off-centre; WINDOW_M when untagged, and never more),
    and a disc of WINDOW_M + 2 at every node where streets meet (turning radii, corner islands). OSM says where to look,
    never where anything is. The pilot's flat WINDOW_M band reached 7 m into roofs and plazas beside a two-lane street."""
    im = Image.new('L', (ortho.W, ortho.H), 0); d = ImageDraw.Draw(im); seen = {}
    for w, xy in lines:
        try:
            half = min(P['WINDOW_M'], float(w['tags']['lanes']) * P['LANE_M'] / (1.0 if w['tags'].get('oneway') == 'yes' else 1.0) / 2 + P['SIDE_ALLOW_M'])
        except (KeyError, ValueError):
            half = P['WINDOW_M']
        d.line([tuple(p) for p in xy], fill=255, width=int(2 * half / gsd))
        for n, p in zip(w['nodes'], xy):
            seen.setdefault(n, []).append(tuple(p))
    r = (P['WINDOW_M'] + 2.0) / gsd
    for n, ps in seen.items():
        if len(ps) >= 2:
            x, y = ps[0]; d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return np.asarray(im) > 0


def measure(ys, xs, gsd):
    """one mark: principal axis, length, width, a centre line every STEP_M"""
    pts = np.stack([xs, ys], 1).astype(float); c = pts.mean(0); q = pts - c
    if len(pts) < 3:
        return None
    w, v = np.linalg.eigh(np.cov(q.T)); ax = v[:, 1]; t = q @ ax; u = q @ v[:, 0]
    L = (t.max() - t.min() + 1) * gsd; area = len(pts) * gsd * gsd
    nb = max(1, int(round(L / P['STEP_M']))); edges = np.linspace(t.min(), t.max() + 1e-6, nb + 1); cl = []; wid = []
    for a, b in zip(edges, edges[1:]):
        m = (t >= a) & (t <= b)
        if m.any():
            um = np.median(u[m]); cl.append(c + ax * (a + b) / 2 + v[:, 0] * um); wid.append((u[m].max() - u[m].min() + 1) * gsd)
    cl = np.array(cl)
    path = float(np.hypot(*np.diff(cl, axis=0).T).sum()) * gsd + P['STEP_M'] if len(cl) > 1 else L
    return {'c': c, 'ax': ax, 'L': max(L, path), 'W': area / max(L, path, 1e-6), 'Wmed': float(np.median(wid)), 'area': area, 'cl': cl,
            'bearing': (math.degrees(math.atan2(ax[0], -ax[1])) % 180.0), 'ends': (c + ax * t.min(), c + ax * t.max())}


def read(image, lidar=None, corridor=None, prepare=None):
    """corridor: an optional callable ortho -> bool mask; the roadway is only looked for inside it (the lap survey's band)."""
    ortho = Ortho.load(image, origin=ORIGIN); gsd = float(np.mean(ortho.gsd))
    # prepare: an optional callable ortho -> {'mask_out': bool mask no mark is read on, 'road_extra': bool mask added to the
    # roadway (painted surfaces that do not have asphalt's colour)}; it may rewrite ortho.rgb (the lap survey's shadow gain)
    prep = prepare(ortho) if prepare is not None else {}
    rgb = ortho.rgb
    ch = channels.compute(rgb, gsd, {'line_width_m': P['TOPHAT_M'], 'line_amp': 1.0})
    lum = ch['lum']; k = max(3, int(round(P['TOPHAT_M'] / gsd)) | 1)
    bg = ndimage.grey_opening(ndimage.gaussian_filter(lum, 0.6), size=(k, k)); top = lum - bg
    yel = ndimage.gaussian_filter(ch['yel'], 0.6); ybg = ndimage.grey_opening(yel, size=(k, k)); ytop = yel - ybg
    lines = osm_lines(ortho); win0 = window(ortho, lines, gsd)
    if corridor is not None:
        win0 = win0 & corridor(ortho)
    # the roadway: flooded from the OSM lines over ground that is dark and has asphalt's colour (not yellower than
    # ROAD_YEL_MAX on the engine's yellow axis, thin marks removed first: lawn, mulch and concrete are all yellower)
    texs = ndimage.gaussian_filter(ch['tex'], 2.0)
    yroad = ndimage.gaussian_filter(ybg, 0.3 / gsd)
    free = win0 & (yroad < P['ROAD_YEL_MAX']) & (bg < P['PAVE_LUM_MAX'])
    f = 4 if gsd < 0.15 else 1
    def small(m_):
        return m_[::f, ::f]
    def big_(m_):
        o_ = np.kron(m_, np.ones((f, f), bool))[:ortho.H, :ortho.W] if f > 1 else m_
        return np.pad(o_, ((0, ortho.H - o_.shape[0]), (0, ortho.W - o_.shape[1]))) if o_.shape != (ortho.H, ortho.W) else o_
    seed = Image.new('L', (ortho.W, ortho.H), 0); dd = ImageDraw.Draw(seed)
    for _, xy in lines:
        dd.line([tuple(q) for q in xy], fill=255, width=max(3, int(3.0 / gsd)))
    seed = np.asarray(seed) > 0
    r_ = max(1, int(round(P['LEAK_M'] / 2 / gsd / f))); yy, xx = np.mgrid[-r_:r_ + 1, -r_:r_ + 1]; disk = (yy * yy + xx * xx) <= r_ * r_
    fs = ndimage.binary_opening(small(free), structure=disk)
    lab, n = ndimage.label(fs)
    core = np.isin(lab, np.unique(lab[small(seed) & (lab > 0)]))
    hl, hn = ndimage.label(~core)                                             # what stands on the road: vehicles, crosswalk blocks, islands
    sizes = ndimage.sum(np.ones_like(hl), hl, range(hn + 1)) * (gsd * f) ** 2
    fill = sizes < P['HOLE_M2']; fill[0] = False
    fill[np.unique(np.concatenate([hl[0], hl[-1], hl[:, 0], hl[:, -1]]))] = False
    win = big_(core | fill[hl]) & win0
    if prep.get('road_extra') is not None:
        win = win | (prep['road_extra'] & win0)
    smooth = win & (texs < P['TEX_MAX']) & (bg < P['PAVE_LUM_MAX'])
    sg = 6.0 / gsd / f; w_ = ndimage.gaussian_filter(smooth[::f, ::f].astype(np.float32), sg)
    rm = ndimage.gaussian_filter((lum * smooth)[::f, ::f], sg) / np.maximum(w_, 1e-3)
    roadmean = np.kron(rm, np.ones((f, f), np.float32))[:ortho.H, :ortho.W]
    if roadmean.shape != lum.shape:
        roadmean = np.pad(roadmean, ((0, ortho.H - roadmean.shape[0]), (0, ortho.W - roadmean.shape[1])), mode='edge')
    bsat = ndimage.gaussian_filter(ch['sat'], 0.4 / gsd)
    covered = win & ((bg >= P['PAVE_LUM_MAX']) | (np.abs(bg - roadmean) > P['VEH_DLUM']) | ((bsat > 0.25) & (bg > 75)))
    if prep.get('road_extra') is not None:
        covered = covered & ~prep['road_extra']
    covered = ndimage.binary_opening(covered, iterations=max(1, int(0.5 / gsd)))       # vehicles and the like, not thin paint
    covered_d = ndimage.binary_dilation(covered, iterations=max(1, int(0.25 / gsd)))
    yellow = win & (ytop >= P['YEL_TOP']) & (top >= 4) & (bg < P['PAVE_LUM_MAX'])
    white = win & (top >= np.maximum(P['WHITE_TOP'], 0.22 * bg)) & (ch['sat'] <= P['WHITE_SAT_MAX']) & (bg < P['PAVE_LUM_MAX']) & ~yellow
    if prep.get('mask_out') is not None:
        white = white & ~prep['mask_out']; yellow = yellow & ~prep['mask_out']
    marks = []; dropped = {'small': 0, 'kerb_or_edge': 0, 'wide': 0, 'on_a_vehicle': 0, 'rough_ground_beside': 0}
    side_px = P['SIDE_M'] / gsd
    if gsd < 0.15:
        tk = max(1, int(round(P['THICK_M'] / gsd / 2)))
        thick = ndimage.binary_dilation(ndimage.binary_opening(white, structure=np.ones((2 * tk + 1, 2 * tk + 1))), iterations=1) & white
        thin = white & ~thick
    else:
        thick, thin = np.zeros_like(white), white
    for colour, mask in (('white', thin), ('white', thick), ('yellow', yellow)):
        lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            ys, xs = np.nonzero(lab[sl] == i); ys = ys + sl[0].start; xs = xs + sl[1].start
            if len(ys) * gsd * gsd < P['MIN_AREA_M2']:
                dropped['small'] += 1; continue
            m = measure(ys, xs, gsd)
            if m is None:
                continue
            if m['W'] > 1.3 and m['L'] > 1.6:                    # a vehicle roof, a slab: not a mark
                dropped['wide'] += 1; continue
            if covered_d[ys, xs].mean() > 0.3:
                dropped['on_a_vehicle'] += 1; continue
            # pavement on both sides? sample the background luminance SIDE_M off the centre line, each side
            nrm = np.array([-m['ax'][1], m['ax'][0]]); off = (m['Wmed'] / 2 / gsd + side_px)
            a = m['cl'] + nrm * off; b = m['cl'] - nrm * off
            la = channels.sample(lum, a[:, 0], a[:, 1]); lb = channels.sample(lum, b[:, 0], b[:, 1])
            ta = channels.sample(ch['tex'], a[:, 0], a[:, 1]); tb = channels.sample(ch['tex'], b[:, 0], b[:, 1])
            core = channels.sample(lum, m['cl'][:, 0], m['cl'][:, 1])
            sa, sb = float(np.median(la)), float(np.median(lb))
            fa = float(np.mean((ta < P['TEX_MAX'] + 4) & (la < P['PAVE_LUM_MAX']))); fb = float(np.mean((tb < P['TEX_MAX'] + 4) & (lb < P['PAVE_LUM_MAX'])))
            if min(fa, fb) < P['SIDE_SMOOTH_MIN']:
                dropped['rough_ground_beside'] += 1; continue
            if (max(sa, sb) > P['PAVE_LUM_MAX'] or abs(sa - sb) > P['SIDE_DIFF_MAX']
                    or min(float(np.median(core)) - sa, float(np.median(core)) - sb) < 0.5 * P['WHITE_TOP'] * (colour == 'white')):
                dropped['kerb_or_edge'] += 1; continue
            m['pix'] = (ys, xs)
            m.update(colour=colour, side_lum=[round(sa), round(sb)], lum=round(float(np.median(core))),
                     shadow=bool(max(sa, sb) < P['SHADOW_LUM']), tex=round(float(max(np.median(ta), np.median(tb))), 1))
            marks.append(m)
    for m in marks:
        w, L = m['W'], m['L']
        m['double'] = bool(m['colour'] == 'yellow' and m['Wmed'] >= P['DOUBLE_W_MIN'] + 0.076 and L > 2.0)
        if (w <= P['LINE_W_MAX'] or m['double']) and L > P['DASH_L_MAX']:
            m['kind'] = 'line'
        elif w <= P['LINE_W_MAX'] and L >= 0.45 and L / max(w, 1e-6) > 2.5:
            m['kind'] = 'dash'
        elif P['BLOCK_W'][0] < w <= P['BLOCK_W'][1] and P['BLOCK_L'][0] <= L <= P['BLOCK_L'][1]:
            m['kind'] = 'block'
        elif P['BLOCK_W'][0] < w <= P['BLOCK_W'][1] and L > P['BLOCK_L'][1]:
            m['kind'] = 'bar'
        else:
            m['kind'] = 'symbol'
    if lidar is not None:
        Lz = np.load(lidar); g = Lz['cls'] == 2
        e_, n_ = ortho.lonlat_to_en(Lz['lon'][g], Lz['lat'][g]); px, py = ortho.en_to_px(e_, n_)
        xi = np.round(px).astype(int); yi = np.round(py).astype(int); ok = (xi >= 0) & (xi < ortho.W) & (yi >= 0) & (yi < ortho.H)
        xi, yi = xi[ok], yi[ok]; li = np.log1p(Lz['intensity'][g][ok].astype(float))
        idr = np.zeros((ortho.H, ortho.W), np.int32)
        for k_, m in enumerate(marks, 1):
            idr[m['pix']] = k_
        idr = ndimage.grey_dilation(idr, size=(3, 3))
        gr = np.zeros((ortho.H, ortho.W), bool); gr[yi, xi] = True
        gnear = ndimage.binary_dilation(gr, iterations=int(P['LIDAR_GROUND_R'] / gsd))
        hit = idr[yi, xi]; onroad = win[yi, xi] & (ndimage.binary_dilation(idr > 0, iterations=int(0.45 / gsd))[yi, xi] == 0)
        ref = float(np.median(li[onroad])) if onroad.any() else float('nan')
        kept = []; dropped['not_on_lidar_ground'] = 0
        for k_, m in enumerate(marks, 1):
            if not gnear[m['pix']].any():
                dropped['not_on_lidar_ground'] += 1; continue
            v = li[hit == k_]; m['lidar_n'] = int(len(v))
            if len(v) >= P['LIDAR_MIN_N']:
                m['lidar_dlog'] = round(float(v.mean() - ref), 2); m['lidar_confirms'] = bool(v.mean() - ref >= P['LIDAR_DLOG'])
            kept.append(m)
        marks = kept
    dark = win & (lum < P['SHADOW_LUM'])
    stats = {'gsd_m': round(gsd, 4), 'roadway_m2': round(float(win.sum()) * gsd * gsd), 'roadway_in_shadow_share': round(float(dark.sum()) / max(win.sum(), 1), 3),
             'roadway_covered_share': round(float(covered.sum()) / max(win.sum(), 1), 3), 'dropped': dropped}
    return ortho, gsd, marks, stats, (white, yellow, win, covered, dark, top, ytop)


def group(marks, gsd):
    """crosswalks from blocks; broken lines from dashes. Returns items (dicts in pixel space) and the marks left single."""
    used = set(); items = []
    blocks = [i for i, m in enumerate(marks) if m['kind'] == 'block']
    # crosswalk: blocks with one bearing (within 12 deg), centres spaced along the axis ACROSS their length, gaps <= CW_GAP_MAX
    for i in blocks:
        if i in used:
            continue
        grp = [i]; used.add(i); grew = True
        while grew:
            grew = False
            for j in blocks:
                if j in used:
                    continue
                for g in grp:
                    a, b = marks[g], marks[j]
                    db = abs((a['bearing'] - b['bearing'] + 90) % 180 - 90)
                    d = (b['c'] - a['c']) * gsd; along = abs(d @ a['ax']); across = abs(d @ np.array([-a['ax'][1], a['ax'][0]]))
                    if db < 12 and across <= P['CW_GAP_MAX'] and along <= 0.6 * max(a['L'], b['L']) and across > 0.5:
                        grp.append(j); used.add(j); grew = True; break
        if len(grp) >= P['CW_MIN_BARS']:
            items.append({'class': 'crosswalk', 'members': grp})
        else:
            for g in grp:
                used.discard(g)
    used_cw = set(g for it in items for g in it['members'])
    dashes = [i for i, m in enumerate(marks) if m['kind'] == 'dash' and i not in used_cw]; usedd = set()
    for i in sorted(dashes, key=lambda k: marks[k]['c'][0]):
        if i in usedd:
            continue
        chain = [i]; usedd.add(i); grew = True
        while grew:
            grew = False
            for j in dashes:
                if j in usedd or marks[j]['colour'] != marks[i]['colour']:
                    continue
                for g in (chain[0], chain[-1]):
                    a, b = marks[g], marks[j]
                    db = abs((a['bearing'] - b['bearing'] + 90) % 180 - 90)
                    d = (b['c'] - a['c']) * gsd; along = abs(d @ a['ax']); across = abs(d @ np.array([-a['ax'][1], a['ax'][0]]))
                    gap = along - (a['L'] + b['L']) / 2
                    if db < 8 and across < 0.35 + 0.02 * along and 0.5 < gap < 14.0:
                        (chain.append(j) if g == chain[-1] else chain.insert(0, j)); usedd.add(j); grew = True; break
        if len(chain) >= 2:
            items.append({'class': 'broken_line', 'members': chain})
        else:
            usedd.discard(i)
    left = [i for i in range(len(marks)) if i not in used_cw and i not in usedd]
    return items, left


def emit(ortho, gsd, marks, items, left, stats, image):
    def ll(p):
        lon, lat = ortho.px_to_lonlat(np.atleast_2d(p)[:, 0], np.atleast_2d(p)[:, 1])
        return [[round(float(a), 7), round(float(b), 7)] for a, b in zip(lon, lat)]
    def lid(ms):
        if not any('lidar_n' in m for m in ms):
            return {}
        c = [m['lidar_confirms'] for m in ms if 'lidar_confirms' in m]
        o_ = {'lidar_returns_on_it': int(sum(m.get('lidar_n', 0) for m in ms))}
        if c:
            o_['lidar_confirms'] = bool(np.mean(c) >= 0.5); o_['lidar_parts_confirmed'] = f'{sum(c)} of {len(c)}'
        return o_
    out = []
    for it in items:
        ms = [marks[i] for i in it['members']]
        if it['class'] == 'crosswalk':
            ax = ms[0]['ax']; nrm = np.array([-ax[1], ax[0]]); cs = np.array([m['c'] for m in ms]); o = np.argsort(cs @ nrm); ms = [ms[k] for k in o]; cs = cs[o]
            sp = np.diff(cs @ nrm) * gsd; ends = np.array([e for m in ms for e in m['ends']])
            ta, tb = (ends @ ax).min(), (ends @ ax).max(); na, nb_ = (cs @ nrm).min() - ms[0]['W'] / 2 / gsd, (cs @ nrm).max() + ms[-1]['W'] / 2 / gsd
            ring = [ax * ta + nrm * na, ax * tb + nrm * na, ax * tb + nrm * nb_, ax * ta + nrm * nb_]
            out.append({'class': 'crosswalk', 'type': 'bars (continental / ladder; a pair of edge lines is not looked for)', 'colour': ms[0]['colour'],
                        'bars': len(ms), 'bar_length_m': round(float(np.median([m['L'] for m in ms])), 2), 'bar_width_m': round(float(np.median([m['W'] for m in ms])), 2),
                        'bar_spacing_m': round(float(np.median(sp)), 2), 'bar_spacing_max_m': round(float(sp.max()), 2),
                        'bar_bearing_deg': round(float(np.median([m['bearing'] for m in ms])), 1), 'outline_lonlat': ll(np.array(ring)),
                        'bars_lonlat': [ll(np.array(m['ends'])) for m in ms], 'in_shadow': bool(np.mean([m['shadow'] for m in ms]) > 0.5), **lid(ms)})
        else:
            ax0 = ms[0]['ax']; ms.sort(key=lambda m: float(m['c'] @ ax0)); gaps = []
            for a, b in zip(ms, ms[1:]):
                gaps.append(abs(float((b['c'] - a['c']) @ a['ax'])) * gsd - (a['L'] + b['L']) / 2)
            out.append({'class': 'line', 'pattern': 'broken', 'colour': ms[0]['colour'], 'width_m': round(float(np.median([m['W'] for m in ms])), 2),
                        'dashes': len(ms), 'dash_m': round(float(np.median([m['L'] for m in ms])), 2), 'gap_m': round(float(np.median(gaps)), 2),
                        'gap_max_m': round(float(max(gaps)), 2), 'length_m': round(float(np.hypot(*((ms[-1]['c'] - ms[0]['c']) * gsd))) + ms[0]['L'], 1),
                        'bearing_deg': round(float(np.median([m['bearing'] for m in ms])), 1), 'dashes_lonlat': [ll(np.array(m['ends'])) for m in ms], **lid(ms)})
    for i in left:
        m = marks[i]
        if m['kind'] in ('line', 'dash'):
            out.append({'class': 'line', 'pattern': ('double solid' if m.get('double') else 'solid') if m['kind'] == 'line' else 'single dash or fragment', 'colour': m['colour'], 'width_m': round(m['W'], 2),
                        'length_m': round(m['L'], 1), 'bearing_deg': round(m['bearing'], 1), 'line_lonlat': ll(m['cl']), 'in_shadow': m['shadow'], **lid([m])})
        elif m['kind'] in ('bar', 'block'):
            out.append({'class': 'bar', 'note': 'a transverse or lone bar: a stop bar, a yield line piece, or a crosswalk bar with no neighbours read',
                        'colour': m['colour'], 'width_m': round(m['W'], 2), 'length_m': round(m['L'], 1), 'bearing_deg': round(m['bearing'], 1),
                        'line_lonlat': ll(np.array(m['ends'])), 'in_shadow': m['shadow'], **lid([m])})
        else:
            out.append({'class': 'symbol', 'note': 'an arrow, a legend, a bike or bus mark, or clutter: the type is not read', 'colour': m['colour'],
                        'area_m2': round(m['area'], 2), 'length_m': round(m['L'], 1), 'width_m': round(m['W'], 2), 'bearing_deg': round(m['bearing'], 1),
                        'centre_lonlat': ll(m['c'])[0], **lid([m])})
    for k, it in enumerate(out):
        it['id'] = f'p{k:04d}'; it['grade'] = 'measured'
    return {'_doc': 'Road paint read off one orthophoto by paint_read.py (PLAN 4b). Positions are lon / lat (WGS84 as the image\'s georeference gives '
                    'them, NO registration shift applied). Every item is a mark the reader found; nothing is inferred between marks. See the '
                    'report beside this file for accuracy and for what could not be read.',
            'image': os.path.basename(image), 'georeference': ortho.describe(), 'thresholds_invented': {k: v for k, v in P.items()}, 'stats': stats,
            'counts': {c: sum(1 for it in out if it['class'] == c) for c in ('line', 'crosswalk', 'bar', 'symbol')}, 'items': out}


def overlay(ortho, marks, items, left, path, scale=1.0, masks=None):
    im = Image.fromarray(ortho.rgb.astype(np.uint8)); d = ImageDraw.Draw(im)
    if masks is not None:                                    # the roadway's outline, thin
        edge = masks[2] & ~ndimage.binary_erosion(masks[2]); a = np.asarray(im).copy(); a[edge] = (255, 255, 255); im = Image.fromarray(a); d = ImageDraw.Draw(im)
    col = {'line': (0, 255, 255), 'dash': (0, 255, 255), 'bar': (255, 0, 255), 'block': (255, 0, 255), 'symbol': (255, 128, 0)}
    for i in left:
        m = marks[i]; c = (255, 255, 0) if (m['colour'] == 'yellow' and m['kind'] in ('line', 'dash')) else col[m['kind']]
        if m['kind'] == 'symbol':
            x, y = m['c']; d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=c, width=2)
        else:
            d.line([tuple(p) for p in (m['cl'] if len(m['cl']) > 1 else np.array(m['ends']))], fill=c, width=2)
    for it in items:
        ms = [marks[i] for i in it['members']]
        for m in ms:
            d.line([tuple(p) for p in m['ends']], fill=(0, 255, 0) if it['class'] == 'crosswalk' else (0, 160, 255), width=2)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im.save(path, quality=80)


if __name__ == '__main__':
    a = sys.argv
    ortho, gsd, marks, stats, masks = read(a[1], a[a.index('--lidar') + 1] if '--lidar' in a else None); items, left = group(marks, gsd)
    res = emit(ortho, gsd, marks, items, left, stats, a[1]); json.dump(res, open(a[2], 'w'), indent=1)
    stats.update({k: (float(v) if isinstance(v, np.floating) else v) for k, v in stats.items()})
    conf = [it.get('lidar_confirms') for it in res['items']]
    res['lidar_check'] = {'confirmed': conf.count(True), 'contradicted': conf.count(False), 'too_few_returns_to_say': conf.count(None)}
    json.dump(res, open(a[2], 'w'), indent=1)
    print(res['counts'], stats, res['lidar_check'])
    if '--overlay' in a:
        overlay(ortho, marks, items, left, a[a.index('--overlay') + 1], masks=masks)
