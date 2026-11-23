"""horizon.3dep13.json against the plan-grade study: the skyline by bearing (horizon.plan-grade.json) and the peak table
the plan printed (PLAN section 3, typed in below as it stood on 2026-11-23). Prints; writes horizon.compare.json."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
new = json.load(open(os.path.join(H, 'horizon.3dep13.json'))); old = json.load(open(os.path.join(H, 'horizon.plan-grade.json')))
S, SC = 'Denver GP start (Colfax/Sherman)', 'Sand Creek origin'
# PLAN section 3's table: (bearing, km, altitude or None = hidden)
PLAN = {'Pikes Peak': ((182.9, 100.2, 1.14), (185.7, 105.7, None)), 'Mt Morrison': ((248.5, 21.5, 1.93), (242.8, 28.5, 1.46)),
        'Mt Blue Sky (Evans)': ((253.5, 58.8, 2.38), (250.6, 65.5, 2.11)), 'Green Mtn (Lakewood)': ((254.6, 17.2, 1.46), (246.1, 24.0, 1.06)),
        'Mestaaehehe Mtn': ((261.2, 44.0, 2.25), (256.4, 50.3, 1.95)), 'Lookout Mtn': ((267.8, 21.7, 1.67), (257.5, 27.7, 1.32)),
        'North Table Mtn': ((284.3, 19.5, 1.03), (269.2, 24.2, 0.86)), 'James Peak': ((281.9, 61.5, 2.00), (276.6, 65.9, 1.85)),
        'South Arapaho Peak': ((299.3, 64.9, 1.92), (293.3, 67.4, 1.85)), 'Bear Peak': ((312.9, 36.1, 1.35), (301.4, 37.2, 1.34)),
        'Longs Peak': ((317.1, 78.5, 1.65), (311.7, 78.7, 1.67))}
out = {'_doc': 'horizon.3dep13.json minus the plan-grade study. skyline: per site, over the bearings both files hold. peaks: against '
               'PLAN section 3 as printed. Written by compare.py.', 'skyline': {}, 'peaks': []}
for s in new['sites']:
    o = {r[0]: r for r in old['sites'][s]}
    d = [(r[0], round(r[1] - o[r[0]][1], 3), r[2], o[r[0]][2]) for r in new['sites'][s] if r[0] in o]
    big = [x for x in d if abs(x[1]) > 0.1]
    out['skyline'][s] = {'bearings': len(d), 'mean_diff_deg': round(sum(x[1] for x in d) / len(d), 3),
                         'max_abs_diff_deg': max(abs(x[1]) for x in d), 'bearings_over_0.1_deg': len(big),
                         'over_0.1_deg': [{'bearing': b, 'diff_deg': dv, 'cell_km_3dep': round(a / 1000, 1), 'cell_km_plan': round(c / 1000, 1)} for b, dv, a, c in big]}
    print(f"{s}: {len(d)} bearings, mean {out['skyline'][s]['mean_diff_deg']:+.3f}, max |diff| {out['skyline'][s]['max_abs_diff_deg']:.2f}, {len(big)} over 0.1 deg")
for name, (a, b) in PLAN.items():
    for site, (pb, pk, pa) in ((S, a), (SC, b)):
        v = new['peaks'][site][name]
        row = {'peak': name, 'site': site, 'plan': {'bearing': pb, 'km': pk, 'alt': pa, 'visible': pa is not None},
               '3dep': {'bearing': v['bearing_deg'], 'nominal_bearing': v['nominal_bearing_deg'], 'km': v['distance_km'], 'alt': v['altitude_deg'], 'visible': v['visible'], 'clearance': v['clearance_deg']},
               'alt_diff_deg': None if pa is None else round(v['altitude_deg'] - pa, 3), 'visibility_changed': v['visible'] != (pa is not None)}
        row['changed_over_0.1'] = bool(row['visibility_changed'] or (row['alt_diff_deg'] is not None and abs(row['alt_diff_deg']) > 0.1))
        out['peaks'].append(row)
        print(f"  {name:22s} {site[:12]:12s} plan {pb:6.1f} {pk:6.1f} km {'hidden' if pa is None else f'{pa:.2f}':>6s} | 3dep {v['bearing_deg']:7.2f} (nominal {v['nominal_bearing_deg']:7.2f}) {v['distance_km']:6.1f} km "
              f"{v['altitude_deg']:.2f} {'vis' if v['visible'] else 'hid'} ({v['clearance_deg']:+.2f}) {'  <-- CHANGED' if row['changed_over_0.1'] else ''}")
json.dump(out, open(os.path.join(H, 'horizon.compare.json'), 'w'), indent=1)
