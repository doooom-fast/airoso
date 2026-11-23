"""Plan-grade horizon study for the Denver Grand Prix and Sand Creek (tracks/denver-grand-prix/PLAN.md section 3).

What terrain forms the skyline, at what bearing, altitude and distance, from a car's eye on the circuit and at Sand
Creek. DEM: AWS Terrain Tiles (terrarium PNG, zoom 10, ~60 m cells): the only elevation host the cloud session of
2026-11-23 could reach. PLAN-GRADE: re-run on 3DEP before any backdrop mesh is cut.

    python3 horizon_study.py fetch     # tiles 209-214 x 384-392 into ./dem (54 files)
    python3 horizon_study.py           # prints the peak table and writes horizon.plan-grade.json's numbers
"""
import os, sys, urllib.request


def fetch():
    os.makedirs('dem', exist_ok=True)
    for x in range(209, 215):
        for y in range(384, 393):
            p = f'dem/10_{x}_{y}.png'
            if not os.path.exists(p):
                url = f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/10/{x}/{y}.png'
                open(p, 'wb').write(urllib.request.urlopen(url, timeout=60).read())


if len(sys.argv) > 1 and sys.argv[1] == 'fetch':
    fetch()
    sys.exit(0)

import math, json
import numpy as np
from PIL import Image
z=10; x0,x1,y0,y1=209,214,384,392
W=(x1-x0+1)*256; H=(y1-y0+1)*256
dem=np.zeros((H,W),np.float32)
for x in range(x0,x1+1):
    for y in range(y0,y1+1):
        a=np.asarray(Image.open(f'dem/{z}_{x}_{y}.png').convert('RGB'),np.float32)
        dem[(y-y0)*256:(y-y0+1)*256,(x-x0)*256:(x-x0+1)*256]=a[...,0]*256+a[...,1]+a[...,2]/256-32768
n=2**z
def px(lon,lat):
    return ((lon+180)/360*n-x0)*256, ((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n-y0)*256
def elev(lon,lat):
    fx,fy=px(lon,lat); ix=int(fx); iy=int(fy)
    if ix<0 or iy<0 or ix>=W-1 or iy>=H-1: return None
    tx=fx-ix; ty=fy-iy; d=dem
    return float(d[iy,ix]*(1-tx)*(1-ty)+d[iy,ix+1]*tx*(1-ty)+d[iy+1,ix]*(1-tx)*ty+d[iy+1,ix+1]*tx*ty)
R=6371000.0; K=0.13  # refraction
def dest(lon,lat,brg,d):
    b=math.radians(brg); la=math.radians(lat); lo=math.radians(lon); a=d/R
    la2=math.asin(math.sin(la)*math.cos(a)+math.cos(la)*math.sin(a)*math.cos(b))
    lo2=lo+math.atan2(math.sin(b)*math.sin(a)*math.cos(la),math.cos(a)-math.sin(la)*math.sin(la2))
    return math.degrees(lo2),math.degrees(la2)
def bearing_dist(lon,lat,lon2,lat2):
    la=math.radians(lat); la2=math.radians(lat2); dl=math.radians(lon2-lon)
    y=math.sin(dl)*math.cos(la2); x=math.cos(la)*math.sin(la2)-math.sin(la)*math.cos(la2)*math.cos(dl)
    a=math.sin((la2-la)/2)**2+math.cos(la)*math.cos(la2)*math.sin(dl/2)**2
    return (math.degrees(math.atan2(y,x))+360)%360, 2*R*math.asin(math.sqrt(a))
def ang(h0,h,d): return math.degrees(math.atan2(h-h0-d*d*(1-K)/(2*R),d))
def horizon(lon,lat,eye=1.2,b0=170,b1=360,step=0.5,dmax=140000):
    h0=elev(lon,lat)+eye; out=[]
    for i in range(int((b1-b0)/step)+1):
        b=b0+i*step; best=(-90,0,0); d=300.0
        while d<dmax:
            p=dest(lon,lat,b,d); e=elev(*p)
            if e is None: break
            a=ang(h0,e,d)
            if a>best[0]: best=(a,d,e)
            d+=max(120.0,d*0.004)
        out.append((b%360,)+best)
    return h0,out
def peak_vis(lon,lat,plon,plat,eye=1.2):
    h0=elev(lon,lat)+eye; b,dd=bearing_dist(lon,lat,plon,plat)
    # local max within ~600m of nominal
    best=-1e9
    for dx in np.linspace(-0.008,0.008,17):
        for dy in np.linspace(-0.006,0.006,17):
            e=elev(plon+dx,plat+dy)
            if e and e>best: best=e
    ap=ang(h0,best,dd); block=-90; d=300.0
    while d<dd-2500:
        e=elev(*dest(lon,lat,b,d)); a=ang(h0,e,d)
        if a>block: block=a
        d+=max(120.0,d*0.004)
    return b,dd,best,ap,block


SITES = {'Denver GP start (Colfax/Sherman)': (-104.9853, 39.7401), 'Denver GP Speer/Colfax': (-105.0005, 39.7400),
         'Sand Creek origin': (-104.92279, 39.78645)}
# nominal summits (lon, lat); peak_vis takes the DEM's local maximum within ~600 m
PEAKS = {'Longs Peak': (-105.6151, 40.2549), 'Mt Meeker': (-105.6050, 40.2486), 'Mt Blue Sky (Evans)': (-105.6438, 39.5883),
         'Mt Bierstadt': (-105.6688, 39.5826), 'Pikes Peak': (-105.0442, 38.8405), 'Grays Peak': (-105.8176, 39.6339),
         'Torreys Peak': (-105.8212, 39.6428), 'James Peak': (-105.6902, 39.8522), 'South Arapaho Peak': (-105.6499, 40.0236),
         'Mt Audubon': (-105.6158, 40.0994), 'Mestaaehehe Mtn': (-105.4935, 39.6786), 'Lookout Mtn': (-105.2386, 39.7322),
         'Green Mtn (Lakewood)': (-105.1790, 39.6990), 'Mt Morrison': (-105.2190, 39.6690), 'Bear Peak': (-105.2953, 39.9603),
         'South Boulder Peak': (-105.2994, 39.9537), 'Green Mtn (Boulder)': (-105.3016, 39.9821), 'Devils Head': (-105.1010, 39.2597),
         'Mt Rosalie': (-105.6316, 39.5269), 'Chief Mtn': (-105.5222, 39.6767), 'North Table Mtn': (-105.2060, 39.7830),
         'South Table Mtn': (-105.1900, 39.7570), 'Thorodin Mtn': (-105.4170, 39.8900), 'Bergen Peak': (-105.3990, 39.6730)}

if __name__ == '__main__':
    for s, (lo, la) in SITES.items():
        print('\n==', s, 'ground', round(elev(lo, la), 1))
        for b, p, d, e, ap, bl in sorted((peak_vis(lo, la, *pk)[0], n) + peak_vis(lo, la, *pk)[1:] for n, pk in PEAKS.items()):
            print(f'{b:6.1f} deg  {p:22s} {d / 1000:6.1f} km  dem {e:5.0f} m  alt {ap:5.2f}  blocked-below {bl:5.2f}  '
                  f'{"VISIBLE" if ap > bl else "hidden"}')
        h0, hz = horizon(lo, la)
        ds = sorted(d for b, a, d, e in hz if 200 <= b <= 330)
        print(f'  skyline cells, bearings 200-330: {ds[0] / 1000:.1f} / {ds[len(ds) // 2] / 1000:.1f} / {ds[-1] / 1000:.1f} km '
              f'(min / median / max); highest {max(a for b, a, d, e in hz):.2f} deg')
