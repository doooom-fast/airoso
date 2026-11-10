import re,sys
def fix(path, fn):
    t=open(path,encoding='utf-8').read()
    pat=re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> claude/milford-furniture-018\n', re.S)
    i=[0]
    def rep(m):
        i[0]+=1
        return fn(i[0], m.group(1), m.group(2))
    t2=pat.sub(rep,t)
    assert '<<<<<<<' not in t2 and '>>>>>>>' not in t2, path
    open(path,'w',encoding='utf-8').write(t2)
    print(path, i[0])
# config: version 0.1.9
fix('tracks/milford-road-course-lm/track.config.json', lambda k,a,b: '  "version": "0.1.9",\n')
# ship.json: both, 017's first then 018's (comma join)
def ship(k,a,b):
    return a.rstrip('\n')+',\n'+b
fix('tracks/milford-road-course-lm/ship.json', ship)
# test: reseat first (chain order), then road wear
fix('tests/tools/test_ship_track_chain.py', lambda k,a,b: b+a)
# ship_track.sh: reseat block (closed with fi) then road wear block (its fi follows the markers)
def sh(k,a,b):
    return b + '  fi\n' + a
fix('tools/ship_track.sh', sh)
