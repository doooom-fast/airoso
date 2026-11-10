"""crop.py e0 n0 e1 n1 out.jpg [scale]: NAIP 2022 (left) beside the 2017 lidar chm (right), local metres, a 10 m grid"""
import os
from pathlib import Path as _P
VEG_READ = os.environ.get("VEG_READ", "/Volumes/Drive/codex/mf_work/veg/read")   # the vegetation pass's read of the 71 EPT nodes (veg_read.py); never downloads
AIROSO = os.environ.get("AIROSO", str(_P(__file__).resolve().parents[6]))
import numpy as np, json, math, sys
from PIL import Image, ImageDraw
e0,n0,e1,n1=map(float,sys.argv[1:5]); out=sys.argv[5]; sc=float(sys.argv[6]) if len(sys.argv)>6 else 4
O=dict(lon=-83.66362827905016,lat=42.56999810653583)
def mpd(lat0):
    phi=math.radians(lat0)
    return (111412.84*math.cos(phi)-93.5*math.cos(3*phi)+0.118*math.cos(5*phi), 111132.954-559.822*math.cos(2*phi)+1.175*math.cos(4*phi))
mlon,mlat=mpd(O['lat'])
LON0,LAT0,LON1,LAT1=-83.67,42.56050328638498,-83.657,42.57949671361502
NA=Image.open(AIROSO+'/tracks/milford-road-course/source/naip_2022_mrc.jpg')
Wp,Hp=NA.size
def topx(e,n):
    lon=O['lon']+e/mlon; lat=O['lat']+n/mlat
    return ((lon-LON0)/(LON1-LON0)*Wp, (LAT1-lat)/(LAT1-LAT0)*Hp)
w=int((e1-e0)*sc); h=int((n1-n0)*sc)
# NAIP resample
ee=np.linspace(e0,e1,w); nn=np.linspace(n1,n0,h)
E,N=np.meshgrid(ee,nn); px,py=topx(E,N)
A=np.asarray(NA); pxi=np.clip(px.astype(int),0,Wp-1); pyi=np.clip(py.astype(int),0,Hp-1)
left=A[pyi,pxi].copy(); left[(px<0)|(px>=Wp)|(py<0)|(py>=Hp)]=0
d=np.load(VEG_READ+'/veg.npz'); E0,N0=int(d['E0']),int(d['N0'])
chm=d['chm']; multi=d['multi']; ig=d['inten_g']; na=d['n_all']
ii=np.clip((E-E0).astype(int),0,chm.shape[1]-1); jj=np.clip((N-N0).astype(int),0,chm.shape[0]-1)
hc=chm[jj,ii]; mu=multi[jj,ii]; it=ig[jj,ii]
g=np.clip(np.nan_to_num((it-15000)/30000*150+30,nan=0),0,200)
right=np.stack([g,g,g],-1).astype(np.uint8)
v=hc>0.5
col=np.zeros_like(right)
# height colour: 0.5-2 blue, 2-4 cyan, 4-8 yellow, 8-15 orange, 15+ red ; crowns (multi>=.35) green tint
bands=[(0.5,2,(60,60,255)),(2,4,(0,230,230)),(4,8,(255,255,0)),(8,15,(255,140,0)),(15,99,(255,0,0))]
for lo,hi,cc in bands:
    m=v&(hc>=lo)&(hc<hi); right[m]=cc
right[v&(mu>=0.35)]=(0,150,0)
right[na[jj,ii]==0]=(60,0,60)
im=Image.fromarray(np.concatenate([left,right],1)); dr=ImageDraw.Draw(im)
W=AIROSO+'/tracks/milford-road-course-lm'
P=np.array(json.load(open(W+'/data/centerline.local.json'))['points_xyz_m'])
for off in (0,w):
    pts=[(off+(p[0]-e0)*sc,(n1-p[2])*sc) for p in P]
    dr.line(pts,fill=(0,160,255),width=1)
    for gx in np.arange(math.ceil(e0/10)*10,e1,10):
        x=off+(gx-e0)*sc; dr.line([(x,0),(x,4)],fill=(255,255,255))
        if gx%50==0: dr.text((x+1,5),str(int(gx)),fill=(255,255,255))
    for gy in np.arange(math.ceil(n0/10)*10,n1,10):
        y=(n1-gy)*sc; dr.line([(off,y),(off+4,y)],fill=(255,255,255))
        if gy%50==0: dr.text((off+5,y+1),str(int(gy)),fill=(255,255,255))
im.save(out,quality=88); print(im.size)
