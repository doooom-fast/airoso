# the body of tools/ship_track.sh author_race_planned_gate, word for word (the chain runs it inline)
import json,os,sys
data=sys.argv[1]; bad=[]
for lid in sys.argv[2:]:
    p=os.path.join(data,'no_route.%s.planned.json'%lid)
    if not os.path.exists(p):
        bad.append(lid+': no planned verdict (data/no_route.%s.planned.json missing)'%lid); continue
    r=json.load(open(p,encoding='utf-8'))
    if not isinstance(r,dict):
        bad.append(lid+': the planned verdict is not a no_route report'); continue
    print('  %-9s planned: %s  leak_cells %s  blocked %s  forbidden_reached %s  spawns_unreached %s  reached %s m2'%(lid,
          'FAIL' if r.get('fail') else 'PASS', r.get('leak_cells'), len(r.get('blocked') or []),
          len(r.get('forbidden_reached') or []), len(r.get('spawns_unreached') or []), r.get('reached_m2')))
    if r.get('fail') is not False or (r.get('leak_cells') or 0)>0 or r.get('blocked') or r.get('forbidden_reached') or r.get('spawns_unreached'):
        bad.append(lid+': planned no_route FAIL')
if bad: raise SystemExit('PLANNED no_route: '+'; '.join(bad))
