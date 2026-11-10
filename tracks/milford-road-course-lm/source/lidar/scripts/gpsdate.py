import sys, datetime, glob, json
import numpy as np, laspy
fs = sorted(glob.glob(sys.argv[1] + "/ept-data/8-*.laz"))[:40]
ts = []
for f in fs:
    l = laspy.read(f)
    t = np.asarray(l.gps_time); ts.append(t[::50])
t = np.concatenate(ts)
print("gps_time range", t.min(), t.max(), "global_encoding", l.header.global_encoding)
gps0 = datetime.datetime(1980, 1, 6)
for v in np.percentile(t, [0, 5, 50, 95, 100]):
    print(v, gps0 + datetime.timedelta(seconds=float(v) + 1e9))
print([s["name"] for s in json.load(open(sys.argv[1] + "/ept.json")).get("schema", [])])
