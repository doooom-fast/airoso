import json,sys,os
for w in sys.argv[1:]:
    def J(f):
        p=os.path.join(w,'data',f); return json.load(open(p)) if os.path.exists(p) else None
    k=J('kn5_ground_check.full.json')
    print('==', w.split('/')[-1])
    print(' kgc fail', k['fail'], k['seating'], k['road_over_ground'])
    e=J('edge_smoothness.json'); print(' edge', json.dumps(e)[:500])
    t=J('kn5_textures.json'); print(' tex', json.dumps(t)[:400])
    h=J('house_seat_check.json'); print(' house', h['verdict'], h['buildings'], h.get('show_m_min'))
    a=J('audit.json'); print(' audit', {x:a.get(x) for x in ('road_verts','curb_verts','wall_verts','hard_total','verdict')})
