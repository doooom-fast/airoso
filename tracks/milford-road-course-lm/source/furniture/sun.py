"""sun.py: solar azimuth / elevation over 2022-08-16 at the MRC centroid (NOAA's simplified equations)."""
import math
LAT, LON = 42.570024, -83.6636
def sun(utc_h, doy=228, year_frac=None):
    g = 2 * math.pi / 365 * (doy - 1 + (utc_h - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    tst = utc_h * 60 + eqt + 4 * LON
    ha = math.radians(tst / 4 - 180)
    phi = math.radians(LAT)
    cz = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha)
    z = math.acos(cz)
    az = math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(phi) - math.tan(dec) * math.cos(phi))) + 180
    return az, 90 - math.degrees(z), math.degrees(dec)
for m in range(13 * 60, 19 * 60, 10):
    az, el, dec = sun(m / 60)
    print(f"UTC {m // 60:02d}:{m % 60:02d} EDT {m // 60 - 4:02d}:{m % 60:02d}  az {az:6.1f}  el {el:5.1f}")
