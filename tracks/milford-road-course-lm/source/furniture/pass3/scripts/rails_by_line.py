"""seat_built per W-beam LINE (ledger 0082 pass 3): each 0.5 m cell of the visual rail meshes, its top over the highest built
ground, grouped by the nearest config line (g1..g4).   python rails_by_line.py <workshop> [track.config.json]"""
import sys, json, math, numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import seat_built as sb
from pathlib import Path
ws=Path(sys.argv[1]); cfgp=Path(sys.argv[2]) if len(sys.argv)>2 else ws/'track.config.json'
V,T,furn=sb.read(ws/'data/track.obj'); G=sb.Ground(V,T)
# which ground object is highest under a G1 cell
cl=json.loads((ws/'data/centerline.local.json').read_text()); o=cl['origin']
phi=math.radians(o['lat']); ml=111412.84*math.cos(phi)-93.5*math.cos(3*phi); mt=111132.954-559.822*math.cos(2*phi)
cfg=json.loads(cfgp.read_text())
lines=[(r['key'],r['kind'],np.array([((p[0]-o['lon'])*ml,(p[1]-o['lat'])*mt) for p in r['polyline_lonlat']])) for r in cfg['scenery']['bespoke']['rails']]
P=np.array(cl['points_xyz_m'])[:,[0,2]]; S=np.r_[0,np.cumsum(np.hypot(*np.diff(P,axis=0).T))]
from collections import defaultdict
agg=defaultdict(list)
for name,(cls,idx) in furn.items():
    if cls!='wbeam': continue
    Q=V[sorted(idx)]; cells={}
    for x,y,z in Q:
        k=(int(math.floor(x/0.5)),int(math.floor(z/0.5))); lo,hi=cells.get(k,(y,y)); cells[k]=(min(lo,y),max(hi,y))
    for (i,j),(lo,hi) in cells.items():
        x,z=(i+.5)*.5,(j+.5)*.5; g=G.height(x,z)
        if g is None: continue
        best=None
        for key,k,L in lines:
            if k!='wbeam': continue
            a,b=L[:-1],L[1:]; d=b-a; t=np.clip(((np.array([x,z])-a)*d).sum(1)/(d*d).sum(1),0,1); dist=np.hypot(*(a+t[:,None]*d-[x,z]).T).min()
            if best is None or dist<best[0]: best=(dist,key)
        agg[best[1]].append((hi-g,lo-g,x,z))
for key,v in sorted(agg.items()):
    v=np.array(v); print(key,len(v),'exposed p5/50/95',np.percentile(v[:,0],[5,50,95]).round(2),'buried(<0.6)',int((v[:,0]<0.6).sum()))
    if key.startswith('g1'):
        k=np.argmin(v[:,0]); print('   worst at',v[k].round(2))
