"""Ledger 0092: NAIP 2022 crops of run-off blobs, the outline in red, the centreline in cyan (the record's kept / left-out
evidence: ../left_out_blobs.jpg, ../kept_blobs_sample.jpg).

    python blob_crops.py <key,key,...> <out.jpg>"""
import json, sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from PIL import Image, ImageDraw
from scripts.geometry.projection import _meters_per_degree
T=str(Path(__file__).resolve().parents[3]) + "/"
cfg=json.load(open(T+"track.config.json")); rec=json.load(open(T+"source/runoff/runoff_pads.json"))
cl=json.load(open(T+"data/centerline.local.json")); o=cl["origin"]
m_lon,m_lat=_meters_per_degree(o["lat"])
W,Sb,E,N=cfg["road_wear"]["aerial"]["bbox_lonlat"]
im=Image.open(T+"source/road_wear/naip_2022_mrc.jpg").convert("RGB"); w,h=im.size
def px(x,z):
    lon=o["lon"]+x/m_lon; lat=o["lat"]+z/m_lat
    return ((lon-W)/(E-W)*w, (N-lat)/(N-Sb)*h)
keys=sys.argv[1].split(",")
tiles=[]
for b in rec["blobs"]:
    if b["key"] not in keys: continue
    poly=[px(*p) for p in b["inner_xz"]+b["outer_xz"][::-1]]
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2; r=max(max(xs)-min(xs),max(ys)-min(ys))/2+60
    box=(int(cx-r),int(cy-r),int(cx+r),int(cy+r))
    c=im.crop(box).copy(); d=ImageDraw.Draw(c)
    d.line([(p[0]-box[0],p[1]-box[1]) for p in poly+[poly[0]]], fill=(255,0,0), width=2)
    # centreline
    P=cl["points_xyz_m"]; pl=[px(p[0],p[2]) for p in P]
    d.line([(p[0]-box[0],p[1]-box[1]) for p in pl], fill=(0,255,255), width=1)
    d.text((4,4), b["key"], fill=(255,255,0))
    c=c.resize((360,int(360*c.size[1]/c.size[0])))
    tiles.append(c)
Wt=sum(t.size[0] for t in tiles); Ht=max(t.size[1] for t in tiles)
out=Image.new("RGB",(Wt,Ht)); x=0
for t in tiles: out.paste(t,(x,0)); x+=t.size[0]
out.save(sys.argv[2])
