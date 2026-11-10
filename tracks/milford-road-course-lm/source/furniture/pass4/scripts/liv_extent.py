"""Where the Livingston 2018 points are, near Milford's lap (run with -I on the G10)."""
import sys, glob, numpy as np, laspy
from pyproj import Transformer
t = Transformer.from_crs(3857, 4326, always_xy=True)
for f in sorted(glob.glob(sys.argv[1] + "/*.laz")):
    l = laspy.read(f); lon, lat = t.transform(np.asarray(l.x), np.asarray(l.y))
    band = (lat > 42.560) & (lat < 42.580)
    near = band & (lon > -83.70)
    print(f.split("/")[-1], len(lon), "lon range", round(lon.min(), 4), round(lon.max(), 4),
          "| in the lap's latitude band: easternmost", round(lon[band].max(), 5) if band.any() else None,
          "| points east of -83.70 in the band:", int(near.sum()), "east of -83.6673 (the front straight):", int((band & (lon > -83.6673)).sum()))
