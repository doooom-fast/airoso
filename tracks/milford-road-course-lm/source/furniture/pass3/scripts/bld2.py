"""roof segments on a 2 m grid (the max of each 2x2 block of the 1 m chm), for the sparser shallow nodes"""
import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull
d=np.load(VEG_READ+'/veg.npz')
E0,N0=int(d['E0']),int(d['N0']); chm=d['chm'].astype(float); multi=np.nan_to_num(d['multi'],nan=0); nf=d['n_first']
box=[float(x) for x in sys.argv[1:5]]; HMIN=float(sys.argv[5]); OUT=sys.argv[6]
ny,nx=chm.shape; ny2,nx2=ny//2,nx//2
c=chm[:ny2*2,:nx2*2].reshape(ny2,2,nx2,2)
C=c.max(axis=(1,3))
mu=multi[:ny2*2,:nx2*2].reshape(ny2,2,nx2,2).max(axis=(1,3))
has=C>HMIN
med=ndi.median_filter(C,3)
R=has&(np.abs(C-med)<0.35)&(mu<0.25)
R=ndi.binary_opening(R,iterations=1); R=ndi.binary_closing(R,iterations=1)&(C>HMIN-0.5); R=ndi.binary_fill_holes(R)
lab,n=ndi.label(R); out=[]
for k,sl in enumerate(ndi.find_objects(lab),1):
    m=lab[sl]==k; a=int(m.sum())*4
    if a<60: continue
    jj,ii=np.nonzero(m); ee=E0+2*(sl[1].start+ii)+1.0; nn=N0+2*(sl[0].start+jj)+1.0
    if not(box[0]<=ee.mean()<=box[2] and box[1]<=nn.mean()<=box[3]): continue
    h=C[sl][m]
    pts=np.c_[ee,nn]; pts4=np.concatenate([pts+[dx,dy] for dx in (-1,1) for dy in (-1,1)])
    hull=pts4[ConvexHull(pts4).vertices]; best=None
    for i in range(len(hull)):
        dx,dy=hull[(i+1)%len(hull)]-hull[i]; th=math.atan2(dy,dx); cs,sn=math.cos(th),math.sin(th)
        Rm=np.array([[cs,sn],[-sn,cs]]); q=pts4@Rm.T; lo,hi=q.min(0),q.max(0); A=np.prod(hi-lo)
        if best is None or A<best[0]: best=(A,lo,hi,Rm)
    A,lo,hi,Rm=best
    corners=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]])@Rm
    out.append(dict(id=k,area=a,e=round(float(ee.mean()),1),n=round(float(nn.mean()),1),L=round(float(hi[0]-lo[0]),1),W=round(float(hi[1]-lo[1]),1),
      fill=round(a/A,2),h10=round(float(np.percentile(h,10)),2),h50=round(float(np.median(h)),2),h90=round(float(np.percentile(h,90)),2),
      corners=[[round(float(x),1),round(float(y),1)] for x,y in corners]))
json.dump(out,open(OUT,'w'),indent=1)
for r in out: print({k:v for k,v in r.items() if k!='corners'})
np.save(OUT.replace('.json','_lab.npy'),lab)
