"""The A side of the 0.1.7 A/B: the same commit with the road_wear key out of the config and the road_wear gate out of
ship.json (and the version left at 0.1.7, so only the key differs)."""
import json, sys
root = sys.argv[1]
p = f'{root}/tracks/milford-road-course-lm/track.config.json'
d = json.load(open(p)); d.pop('road_wear')
open(p, 'w').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
p = f'{root}/tracks/milford-road-course-lm/ship.json'
s = json.load(open(p)); s['steps']['gate'].remove('road_wear')
open(p, 'w').write(json.dumps(s, indent=2, ensure_ascii=False) + '\n')
print('A side: no road_wear key, no road_wear gate')
