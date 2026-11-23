import json,math,collections,heapq
d=json.load(open('tracks/denver-grand-prix/source/osm.json'))
N={int(k):v for k,v in d['nodes'].items()}
LON0,LAT0=-104.9849,39.7401
def xy(n):
    lo,la=N[n]; return ((lo-LON0)*111320*math.cos(math.radians(LAT0)),(la-LAT0)*110950)
G=collections.defaultdict(list)
ns=collections.defaultdict(set)
for w in d['ways']:
    t=w['tags']
    if t.get('highway')=='service': continue
    nm=t.get('name','?')
    for a,b in zip(w['nodes'],w['nodes'][1:]):
        L=math.dist(xy(a),xy(b)); ow=t.get('oneway')=='yes'
        G[a].append((b,L,w,True)); G[b].append((a,L,w,not ow))   # 4th: with traffic?
    for n in w['nodes']: ns[n].add(nm)
def near(x,y,names=None):
    if names and not any(set(names)<=ns[n] for n in G): print('  (no node on',names,')'); names=names[:1]
    c=[n for n in G if (names is None or (set(names)<=ns[n]))]
    return min(c,key=lambda n:math.dist(xy(n),(x,y)))
def route(a,b,allow):
    pq=[(0,a,None)]; seen={}
    while pq:
        c,n,p=heapq.heappop(pq)
        if n in seen: continue
        seen[n]=p
        if n==b: break
        for m,L,w,ok in G[n]:
            if m in seen: continue
            nm=w['tags'].get('name','?')
            if allow and nm not in allow: continue
            heapq.heappush(pq,(c+L,m,(n,w,ok,L)))
    if b not in seen: return None
    out=[]; n=b
    while seen[n]: p=seen[n]; out.append(p+(n,)); n=p[0]
    return out[::-1]
C,SP,ST,KA,SF,BL='West Colfax Avenue','North Speer Boulevard','Stout Street','North Kalamath Street','North Santa Fe Drive','Blake Street'
EC='East Colfax Avenue'
wp=[('S/F Colfax at Sherman',near(0,5,[EC]),None),
 ('Colfax WB to Speer NB',near(-1133,8,[C,SP]),{EC,C}),
 ('Speer NB to Stout',near(-1193,146,[SP,ST]),{SP}),
 ('Stout to 15th St',near(-801,535,[ST,'15th Street']),{ST}),
 ('15th St to Blake',near(-1322,1057,[BL,'15th Street']),{'15th Street'}),
 ('Blake to Speer SB',near(-1580,925,[SP,'Auraria Parkway']),{BL,'Auraria Parkway'}),
 ('Speer SB to Kalamath',near(-1280,201,[SP,KA]),{SP}),
 ('Kalamath S to W 14th Ave',near(-1305,-180,[KA,'West 14th Avenue']),{KA}),
 ('W 14th Ave to Santa Fe',near(-1239,-180,[SF,'West 14th Avenue']),{'West 14th Avenue'}),
 ('Santa Fe N to Colfax',near(-1290,-9,[SF,C]),{SF}),
 ('Kalamath NB branch to Speer SB',near(-1247,123,[SP,KA,ST]),{KA}),
 ('Speer SB to W 14th Ave',near(-1091,-181,[SP,'West 14th Avenue']),{SP}),
 ('14th Ave E to Logan',near(310,-182,['East 14th Avenue','Logan Street']),{'West 14th Avenue','East 14th Avenue','West 14th Avenue Parkway'}),
 ('Logan N to Colfax',near(310,0,[EC,'Logan Street']),{'Logan Street'}),
 ('Colfax W to S/F',None,{EC})]
wp[-1]=(wp[-1][0],wp[0][1],wp[-1][2])
tot=0; allids=[]
for (n0,a,_),(nm,b,allow) in zip(wp,wp[1:]):
    r=route(a,b,allow)
    if r is None: print(f'{nm:34s} NO ROUTE on {allow}  from {xy(a)} to {xy(b)}'); continue
    L=sum(s[3] for s in r); tot+=L; wr=sum(s[3] for s in r if not s[2])
    ids=[]; 
    for s in r:
        if not ids or ids[-1]!=s[1]['id']: ids.append(s[1]['id'])
    lanes=sorted({s[1]['tags'].get('lanes','?') for s in r}); sp={k for s in r for k in ('bridge','tunnel','covered') if s[1]['tags'].get(k)}
    print(f"{nm:34s} {L:6.0f} m  against one-way {wr:5.0f} m  lanes {','.join(lanes):9s} {sorted(sp)}  ({xy(a)[0]:.0f},{xy(a)[1]:.0f})->({xy(b)[0]:.0f},{xy(b)[1]:.0f}) ways {len(ids)}")
    allids.append((nm,ids))
print('TOTAL %.0f m'%tot)
json.dump({'_doc':'lap legs as OSM way ids, routed on tracks/denver-grand-prix/source/osm.json (frame: metres east/north of -104.9849, 39.7401)','legs':[{'leg':n,'ways':i} for n,i in allids]},open('tracks/denver-grand-prix/data/lap_ways.plan.json','w'),indent=1)
