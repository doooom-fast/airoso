"""px <-> lon/lat for an image stitched by pc_tiles.py. usage: geo.py IMG.georef.json px x y | ll lon lat"""
import json, math, sys
def load(p): return json.load(open(p))
def px2ll(g, px, py):
    n = 2 ** g["z"]; X = g["x0"] + px / 256; Y = g["y0"] + py / 256
    lon = X / n * 360 - 180; lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * Y / n))))
    return lon, lat
def ll2px(g, lon, lat):
    n = 2 ** g["z"]; r = math.radians(lat)
    X = (lon + 180) / 360 * n; Y = (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n
    return (X - g["x0"]) * 256, (Y - g["y0"]) * 256
def mpp(g, lat): return g["m_per_px_equator"] * math.cos(math.radians(lat))
if __name__ == "__main__":
    g = load(sys.argv[1]); a, b = float(sys.argv[3]), float(sys.argv[4])
    if sys.argv[2] == "px":
        lon, lat = px2ll(g, a, b); print(f"{lat:.6f}, {lon:.6f}  ({mpp(g, lat):.3f} m/px)")
    else:
        print("px %.1f %.1f" % ll2px(g, a, b))
