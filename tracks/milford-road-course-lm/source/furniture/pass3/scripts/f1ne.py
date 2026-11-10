"""F1's north-east end, which pass 2's 45 m read did not reach: the canopy-free 2-6 m returns along F1's direction past its
built NE end, off the vegetation read's every-return file (veg_canopy.npz: every non-ground return over 2 m; nothing
downloaded). Per 4 m bin along: the median plan position, the p90 top, the returns, the single-pulse share."""
import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
from scipy.spatial import cKDTree
C=np.load(VEG_READ+'/veg_canopy.npz')
e,n,h,rn,nr=C['e'].astype(float),C['n'].astype(float),C['hag'].astype(float),C['rn'],C['nr']
a=np.array([-205.0,439.0]); b=np.array([-20.0,540.0])   # along F1's own direction (its built NE leg), well past its end
u=(b-a)/np.linalg.norm(b-a); L=np.linalg.norm(b-a); nrm=np.array([-u[1],u[0]])
q=np.c_[e,n]-a; al=q@u; off=q@nrm
sel=(al>=0)&(al<=L)&(np.abs(off)<14)
T=cKDTree(np.c_[e[h>7],n[h>7]])
canopy=np.array([len(x)>0 for x in T.query_ball_point(np.c_[e[sel],n[sel]],r=1.5)]) if sel.sum() else np.zeros(0,bool)
idx=np.nonzero(sel)[0][~canopy]
idx=idx[(h[idx]>=2.0)&(h[idx]<=6.0)]
print('seeds',len(idx))
rows=[]
for k in range(int(L//4)):
    m=idx[(al[idx]>=4*k)&(al[idx]<4*k+4)]
    if len(m)<3: rows.append(dict(bin=k,al=4*k+2,n=int(len(m)))); continue
    o=off[m]; om=np.median(o); near=m[np.abs(o-om)<0.9]
    if len(near)<3: rows.append(dict(bin=k,al=4*k+2,n=int(len(m)),near=int(len(near)))); continue
    p=a+u*(4*k+2)+nrm*np.median(off[near])
    rows.append(dict(bin=k,al=4*k+2,n=int(len(m)),near=int(len(near)),off=round(float(np.median(off[near])),2),sd=round(float(np.std(off[near])),2),
        top90=round(float(np.percentile(h[near],90)),2),top=round(float(h[near].max()),2),single=round(float(np.mean(nr[near]==1)),2),e=round(float(p[0]),1),nn=round(float(p[1]),1)))
for r in rows: print(r)
json.dump(rows,open('f1ne_bins.json','w'))
