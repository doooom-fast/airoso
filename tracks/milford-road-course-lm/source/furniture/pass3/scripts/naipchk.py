import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
O=dict(lon=-83.66362827905016,lat=42.56999810653583); mlon,mlat=82107.23577351798,111084.36697075465
LON0,LAT0,LON1,LAT1=-83.67,42.56050328638498,-83.657,42.57949671361502
A=np.asarray(Image.open(AIROSO+'/tracks/milford-road-course/source/naip_2022_mrc.jpg')).astype(float)
Hp,Wp=A.shape[:2]
W=AIROSO+'/tracks/milford-road-course-lm'
c=json.load(open(W+'/data/centerline.local.json')); P=np.array(c['points_xyz_m']); wd=np.array(c['widths_m']); T=cKDTree(P[:,[0,2]])
B=json.load(open(sys.argv[1])); lab=np.load(sys.argv[1].replace('.json','_lab.npy'))
E0=N0=-1400
for b in B:
    jj,ii=np.nonzero(lab==b['id']); ee=E0+2*ii+1.0; nn=N0+2*jj+1.0
    px=((O['lon']+ee/mlon-LON0)/(LON1-LON0)*Wp).astype(int); py=((LAT1-(O['lat']+nn/mlat))/(LAT1-LAT0)*Hp).astype(int)
    ok=(px>=0)&(px<Wp)&(py>=0)&(py<Hp)
    b['naip_cov']=round(float(ok.mean()),2)
    if ok.sum()>5:
        rgb=A[py[ok],px[ok]]; g=rgb[:,1]-(rgb[:,0]+rgb[:,2])/2
        b['naip_green']=round(float(np.median(g)),1); b['naip_lum']=round(float(np.median(rgb.mean(1))),0)
    d,i=T.query(np.c_[ee,nn]); b['d_edge']=round(float((d-wd[i]/2).min()),1)
json.dump(B,open(sys.argv[1],'w'),indent=1)
for b in sorted(B,key=lambda b:b['d_edge']):
    if b['d_edge']<400: print({k:v for k,v in b.items() if k not in('corners',)})
