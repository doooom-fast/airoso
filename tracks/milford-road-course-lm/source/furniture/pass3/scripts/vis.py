"""Line of sight from the driver's eye (1.1 m over the lap's centreline [invented: a seated driver]) to each building's
roof edge, through the 2017 lidar surface (ground g_fill + chm): visible if any lap point within REACH sees any of its
corners' tops. The 2017 canopy is lower than 2022's (the woods grew), so this over-reads visibility, never under."""
import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
d=np.load(VEG_READ+'/veg.npz'); E0,N0=int(d['E0']),int(d['N0'])
G=d['g_fill'].astype(float); S=G+d['chm'].astype(float)
W=AIROSO+'/tracks/milford-road-course-lm'
P=np.array(json.load(open(W+'/data/centerline.local.json'))['points_xyz_m'])[::7]
def zs(e,n,A): 
    i=np.clip((e-E0).astype(int),0,A.shape[1]-1); j=np.clip((n-N0).astype(int),0,A.shape[0]-1); return A[j,i]
B=json.load(open(sys.argv[1])); REACH=float(sys.argv[2]) if len(sys.argv)>2 else 400
eyeg=zs(P[:,0],P[:,2],G)+1.1
for b in B:
    C=np.array(b['corners']); top=b['h90']
    # targets: corners pulled 1 m inside + centre, at roof top over their ground
    cen=C.mean(0); T=np.vstack([cen+(c-cen)*0.9 for c in C]+[cen])
    tz=zs(T[:,0],T[:,1],G)+top-0.3
    best=0; nvis=0
    for k,(pe,pn) in enumerate(P[:,[0,2]]):
        for t,z in zip(T,tz):
            D=math.hypot(t[0]-pe,t[1]-pn)
            if D>REACH or D<5: continue
            s=np.arange(2,D-3,1.0)/D; ee=pe+(t[0]-pe)*s; nn=pn+(t[1]-pn)*s
            ray=eyeg[k]+(z-eyeg[k])*s
            if np.all(zs(ee,nn,S)<ray): nvis+=1; break
    b['vis_lap_pts']=nvis; b['vis_of']=len(P)
    print(b['id'],b['e'],b['n'],'h',b['h50'],'d',b.get('d_edge'),'visible from',nvis,'/',len(P),'lap points')
json.dump(B,open(sys.argv[1],'w'),indent=1)
