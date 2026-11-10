"""Split a roof segment into height tiers (2 m grid cells assigned by height), and give each tier its minimum-area
rectangle and its measured median / p10 / p90 roof height over the lidar ground."""
import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull
d=np.load(VEG_READ+'/veg.npz'); chm=d['chm'].astype(float); E0=N0=-1400
ny,nx=chm.shape; C=chm[:ny//2*2,:nx//2*2].reshape(ny//2,2,nx//2,2).max(axis=(1,3))
GF=d['g_fill'].astype(float)[:ny//2*2,:nx//2*2].reshape(ny//2,2,nx//2,2).mean(axis=(1,3))   # the lidar ground under each 2 m cell (absolute, NAVD88 m)
Z0=316.26   # data/centerline.local.json origin elev_m: the scene's y = 0 (the lap's lidar ground minus its local y, median 316.26 m)
lab=np.load('bldAll_lab.npy'); B={b['id']:b for b in json.load(open('bldAll.json'))}
O=dict(lon=-83.66362827905016,lat=42.56999810653583); mlon,mlat=82107.23577351798,111084.36697075465
def rect(pts):
    pts4=np.concatenate([pts+[dx,dy] for dx in (-1,1) for dy in (-1,1)]); hull=pts4[ConvexHull(pts4).vertices]; best=None
    for i in range(len(hull)):
        dx,dy=hull[(i+1)%len(hull)]-hull[i]; th=math.atan2(dy,dx); cs,sn=math.cos(th),math.sin(th)
        Rm=np.array([[cs,sn],[-sn,cs]]); q=pts4@Rm.T; lo,hi=q.min(0),q.max(0); A=np.prod(hi-lo)
        if best is None or A<best[0]: best=(A,lo,hi,Rm)
    A,lo,hi,Rm=best; return np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])@Rm, A
spec=json.loads(sys.argv[1]); SPLIT_FILL=float(sys.argv[sys.argv.index('--split')+1]) if '--split' in sys.argv else None   # {"id": [cut, cut, ...]}
out=[]
for sid,cuts in spec.items():
    # a list cuts on the height over the ground; {"z": [...]} (ledger 0082 pass 4) on the roof's ELEVATION in the scene frame,
    # for a complex on sloping ground whose roofs are level at their own elevations
    Q=(C+GF-Z0) if isinstance(cuts,dict) else C
    cuts=cuts["z"] if isinstance(cuts,dict) else cuts
    m=lab==int(sid); h=C*m; edges=[-1e9]+cuts+[1e9]
    for t in range(len(edges)-1):
        mt=m&(Q>edges[t])&(Q<=edges[t+1]); mt=ndi.binary_opening(mt,iterations=1) if len(cuts) else mt
        lt,nl=ndi.label(mt)
        pieces=[lt==k for k in range(1,nl+1)]
        while pieces:
            mk=pieces.pop()
            if mk.sum()*4<60: continue
            jj,ii=np.nonzero(mk); pts=np.c_[E0+2*ii+1.0,N0+2*jj+1.0]; R,A=rect(pts); hh=C[mk]
            if SPLIT_FILL and mk.sum()*4/A<SPLIT_FILL and mk.sum()*4>=4*60:
                # (ledger 0082 pass 4, opt-in --split) an L- or T-shaped roof fills its box poorly: cut it across its box's long
                # axis where the fewest cells cross (between its 20 % and 80 % along), and box each half
                ax=R[1]-R[0] if np.hypot(*(R[1]-R[0]))>=np.hypot(*(R[2]-R[1])) else R[2]-R[1]; ax=ax/np.hypot(*ax)
                al=pts@ax; lo_,hi_=np.percentile(al,20),np.percentile(al,80)
                bins=np.arange(lo_,hi_+2,2.0); cnt=np.histogram(al,bins)[0]
                cut=bins[int(np.argmin(cnt))]+1.0
                sel=np.zeros_like(mk); sel[jj[al<cut],ii[al<cut]]=True
                pieces+= [sel, mk&~sel]; continue
            out.append(dict(src=int(sid),tier=t,cells=int(mk.sum()),area_m2=int(mk.sum()*4),fill=round(mk.sum()*4/A,2),
              h10=round(float(np.percentile(hh,10)),2),h50=round(float(np.median(hh)),2),h90=round(float(np.percentile(hh,90)),2),
              roof_z_local_m=round(float(np.median((C+GF)[mk]))-Z0,2),ground_z_local_m=[round(float(GF[mk].min())-Z0,2),round(float(GF[mk].max())-Z0,2)],
              corners_en=[[round(float(x),1),round(float(y),1)] for x,y in R],
              footprint_lonlat=[[round(O['lon']+x/mlon,7),round(O['lat']+y/mlat,7)] for x,y in R]))
for o in out: print({k:v for k,v in o.items() if k!='footprint_lonlat'})
json.dump(out,open('tiers.json','w'),indent=1)
