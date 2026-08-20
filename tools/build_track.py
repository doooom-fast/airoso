"""Build AC track kn5 + data files from routed OSM nodes.

Generates a flat drivable road surface for each of the three tracks.
Writes directly to AC's content/tracks/ folder.
"""

import json
import math
import os
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

AC_TRACKS = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks"

EARTH_R = 6371008.8
ROAD_HALF_W = 6.0  # 12 m total road width
JUNCTION_HALF_W = 9.0  # 18 m at junctions

# Reference point (center of area) for lon/lat → meters conversion
REF_LON = -117.042
REF_LAT = 32.782


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

def lonlat_to_xz(lon, lat):
    """Convert lon/lat to AC world coords (meters). X=east, Z=south, Y=up."""
    x = (lon - REF_LON) * math.cos(math.radians(REF_LAT)) * EARTH_R * math.radians(1)
    z = -(lat - REF_LAT) * EARTH_R * math.radians(1)
    return (x, z)


# ---------------------------------------------------------------------------
# Road mesh generation
# ---------------------------------------------------------------------------

def make_road_mesh(coords, junction_nodes=None, origin=(0.0, 0.0)):
    """Generate a road surface mesh from a list of [lon, lat] coords.

    Returns (vertices, indices) where each vertex is
    (px, py, pz, nx, ny, nz, u, v, tx, ty, tz).
    origin is (ox, oz) subtracted from all XZ coords to center the mesh.
    """
    if junction_nodes is None:
        junction_nodes = set()

    ox, oz = origin
    pts = [(x - ox, z - oz) for x, z in (lonlat_to_xz(c[0], c[1]) for c in coords)]
    n = len(pts)
    if n < 2:
        return [], []

    # Compute tangent direction at each point
    tangents = []
    for i in range(n):
        if i == 0:
            dx = pts[1][0] - pts[0][0]
            dz = pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx = pts[-1][0] - pts[-2][0]
            dz = pts[-1][1] - pts[-2][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dz = pts[i + 1][1] - pts[i - 1][1]
        length = math.hypot(dx, dz)
        if length < 1e-6:
            dx, dz = 1.0, 0.0
        else:
            dx /= length
            dz /= length
        tangents.append((dx, dz))

    # Compute cumulative distance for UV mapping
    cum_dist = [0.0]
    for i in range(1, n):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        cum_dist.append(cum_dist[-1] + d)

    vertices = []
    indices = []

    for i in range(n):
        tx, tz = tangents[i]
        # Perpendicular (left-hand normal in XZ plane)
        nx, nz = -tz, tx
        hw = ROAD_HALF_W
        u = cum_dist[i] / 10.0  # tile every 10 m

        # Left edge
        lx = pts[i][0] + nx * hw
        lz = pts[i][1] + nz * hw
        # Right edge
        rx = pts[i][0] - nx * hw
        rz = pts[i][1] - nz * hw

        # Vertex: pos(3) + normal(3) + uv(2) + tangent(3)
        # Normal points up (0, 1, 0), tangent along road
        vertices.append((lx, 0.0, lz, 0.0, 1.0, 0.0, u, 0.0, tx, 0.0, tz))
        vertices.append((rx, 0.0, rz, 0.0, 1.0, 0.0, u, 1.0, tx, 0.0, tz))

    # Triangle strip: each segment is a quad = 2 triangles
    for i in range(n - 1):
        v0 = i * 2      # left current
        v1 = i * 2 + 1  # right current
        v2 = i * 2 + 2  # left next
        v3 = i * 2 + 3  # right next
        # Triangle 1
        indices.extend([v0, v2, v1])
        # Triangle 2
        indices.extend([v1, v2, v3])

    return vertices, indices


# ---------------------------------------------------------------------------
# Minimal PNG generator (8x8 gray)
# ---------------------------------------------------------------------------

def make_gray_png(r, g, b):
    """Create a minimal 8x8 RGB PNG."""
    width, height = 8, 8

    def chunk(ctype, data):
        c = ctype + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b""
    for _ in range(height):
        raw += b"\x00"  # filter byte
        for _ in range(width):
            raw += bytes([r, g, b])

    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# KN5 writer
# ---------------------------------------------------------------------------

class KN5:
    def __init__(self, f):
        self.f = f

    def write_bytes(self, b):
        self.f.write(b)

    def uint(self, v):
        self.f.write(struct.pack("<I", v))

    def sint(self, v):
        self.f.write(struct.pack("<i", v))

    def ushort(self, v):
        self.f.write(struct.pack("<H", v))

    def byte(self, v):
        self.f.write(struct.pack("B", v))

    def boolean(self, v):
        self.f.write(struct.pack("?", v))

    def flt(self, v):
        self.f.write(struct.pack("<f", v))

    def vec2(self, v):
        self.f.write(struct.pack("<2f", *v))

    def vec3(self, v):
        self.f.write(struct.pack("<3f", *v))

    def vec4(self, v):
        self.f.write(struct.pack("<4f", *v))

    def string(self, s):
        b = s.encode("utf-8")
        self.uint(len(b))
        self.f.write(b)

    def identity_matrix(self):
        for r in range(4):
            for c in range(4):
                self.flt(1.0 if r == c else 0.0)

    def translation_matrix(self, x, y, z):
        m = [1,0,0,0, 0,1,0,0, 0,0,1,0, x,y,z,1]
        for v in m:
            self.flt(v)

    def write_ac_node(self, name, x, y, z, matrix=None):
        self.uint(1)  # class = Transform
        self.string(name)
        self.uint(0)  # no children
        self.boolean(True)
        if matrix:
            for v in matrix:
                self.flt(v)
        else:
            self.translation_matrix(x, y, z)

    def write_kn5(self, texture_data, texture_name, material_name, shader_name,
                  mesh_name, vertices, indices, start_pos=None, start_matrix=None):
        """Write a complete minimal kn5 file."""
        # Header
        self.write_bytes(b"sc6969")
        self.uint(5)  # version

        # Textures
        self.uint(1)  # texture count
        self.uint(1)  # type (1 = embedded)
        self.string(texture_name)
        self.uint(len(texture_data))
        self.write_bytes(texture_data)

        # Materials
        self.uint(1)  # material count
        self.string(material_name)
        self.string(shader_name)
        self.byte(0)      # blendMode = Opaque
        self.boolean(False)  # alphaTested
        self.sint(0)      # depthMode = DepthNormal

        # Shader properties
        self.uint(4)  # property count
        for pname, va in [("ksDiffuse", 0.6), ("ksAmbient", 0.5),
                          ("ksSpecular", 0.1), ("ksSpecularEXP", 20.0)]:
            self.string(pname)
            self.flt(va)
            self.vec2((0.0, 0.0))
            self.vec3((0.0, 0.0, 0.0))
            self.vec4((0.0, 0.0, 0.0, 0.0))

        # Texture mappings
        self.uint(1)
        self.string("txDiffuse")
        self.uint(0)  # slot
        self.string(texture_name)

        # Node tree
        sx, sy, sz = start_pos or (0.0, 0.0, 0.0)
        ac_nodes = ["AC_START_0", "AC_PIT_0", "AC_HOTLAP_START_0"]

        # Root transform node
        self.uint(1)  # node class = Node
        self.string("BlenderFile")
        self.uint(1 + len(ac_nodes))  # mesh + AC position nodes
        self.boolean(True)  # active
        self.identity_matrix()

        # Mesh node
        self.uint(2)  # node class = Mesh
        self.string(mesh_name)
        self.uint(0)  # no children
        self.boolean(True)   # active
        self.boolean(False)  # castShadows
        self.boolean(True)   # visible
        self.boolean(False)  # transparent

        self.uint(len(vertices))
        for v in vertices:
            self.vec3(v[0:3])   # position
            self.vec3(v[3:6])   # normal
            self.vec2(v[6:8])   # uv
            self.vec3(v[8:11])  # tangent

        self.uint(len(indices))
        for idx in indices:
            self.ushort(idx)

        self.uint(0)  # materialId = 0

        self.uint(0)     # layer
        self.flt(0.0)    # lodIn
        self.flt(0.0)    # lodOut

        # Bounding sphere
        if vertices:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            cz = (min(zs) + max(zs)) / 2
            radius = max(math.sqrt((v[0]-cx)**2 + (v[1]-cy)**2 + (v[2]-cz)**2) for v in vertices)
            self.vec3((cx, cy, cz))
            self.flt(radius)
        else:
            self.vec3((0, 0, 0))
            self.flt(0)

        self.boolean(True)  # renderable

        # AC position nodes (start grid, pit, hotlap start)
        for name in ac_nodes:
            self.write_ac_node(name, sx, sy, sz, matrix=start_matrix)


# ---------------------------------------------------------------------------
# Track folder creation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# AI spline generation
# ---------------------------------------------------------------------------

def write_ai_spline(path, coords, origin=(0.0, 0.0)):
    """Generate a fast_lane.ai binary spline file from lon/lat coords."""
    ox, oz = origin
    pts = [(x - ox, z - oz) for x, z in (lonlat_to_xz(c[0], c[1]) for c in coords)]
    n = len(pts)
    if n < 2:
        return

    cum_dist = [0.0]
    for i in range(1, n):
        d = math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        cum_dist.append(cum_dist[-1] + d)

    directions = []
    for i in range(n):
        if i == 0:
            dx = pts[1][0] - pts[0][0]
            dz = pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx = pts[-1][0] - pts[-2][0]
            dz = pts[-1][1] - pts[-2][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dz = pts[i + 1][1] - pts[i - 1][1]
        length = math.hypot(dx, dz)
        if length < 1e-6:
            dx, dz = 1.0, 0.0
        else:
            dx /= length
            dz /= length
        directions.append((dx, 0.0, dz))

    with open(path, "wb") as f:
        pack = struct.pack
        # Header
        f.write(pack("<i", 7))       # version
        f.write(pack("<i", n))       # numPoints
        f.write(pack("<i", n * 43))  # metadata

        # Section 1: positions + distances + indices
        f.write(pack("<i", n))
        for i in range(n):
            f.write(pack("<3f", pts[i][0], 0.0, pts[i][1]))
            f.write(pack("<f", cum_dist[i]))
            f.write(pack("<i", i))

        # Section 2: extra per-point data (18 floats each)
        f.write(pack("<i", n))
        for i in range(n):
            dx, dy, dz = directions[i]
            f.write(pack("<18f",
                ROAD_HALF_W,   # width left
                ROAD_HALF_W,   # width right
                0.0, 0.0,      # padding
                0.0,           # camber
                ROAD_HALF_W + 1.0,  # side distance left
                ROAD_HALF_W + 1.0,  # side distance right
                0.0, 0.0, 0.0,     # padding
                1.0,           # valid track flag
                0.0,           # padding
                cum_dist[i],   # cumulative distance (again)
                dx, dy, dz,    # direction (unit vector)
                0.0,           # padding
                dy,            # direction Y (repeated)
            ))

        # Footer
        f.write(pack("<i", 0))

    # Side CSVs
    side_l_path = os.path.join(os.path.dirname(path), "side_l.csv")
    side_r_path = os.path.join(os.path.dirname(path), "side_r.csv")
    with open(side_l_path, "w") as fl, open(side_r_path, "w") as fr:
        for i in range(n):
            dx, _, dz = directions[i]
            nx, nz = -dz, dx
            hw = ROAD_HALF_W + 1.0
            lx = pts[i][0] + nx * hw
            lz = pts[i][1] + nz * hw
            rx = pts[i][0] - nx * hw
            rz = pts[i][1] - nz * hw
            fl.write(f"{lx:.3f},0.000,{lz:.3f}\n")
            fr.write(f"{rx:.3f},0.000,{rz:.3f}\n")


def write_surfaces_ini(path):
    with open(path, "w") as f:
        f.write("""[SURFACE_0]
KEY=ROAD
WAV=
WAV_PITCH=0
FF_EFFECT=0
SIN_HEIGHT=0
SIN_LENGTH=0
BLACK_FLAG_TIME=0
FRICTION=0.98
DAMPING=0
IS_VALID_TRACK=1
DIRT_ADDITIVE=0
IS_PITLANE=0
VIBRATION_GAIN=0
VIBRATION_LENGTH=0

[SURFACE_1]
KEY=GRASS
WAV=grass.wav
WAV_PITCH=1.0
FF_EFFECT=0
SIN_HEIGHT=0
SIN_LENGTH=0
BLACK_FLAG_TIME=0
FRICTION=0.6
DAMPING=0.1
IS_VALID_TRACK=0
DIRT_ADDITIVE=1
IS_PITLANE=0
VIBRATION_GAIN=0
VIBRATION_LENGTH=0

[SURFACE_2]
KEY=WALL
WAV=
WAV_PITCH=0
FF_EFFECT=0
SIN_HEIGHT=0
SIN_LENGTH=0
BLACK_FLAG_TIME=0
FRICTION=0.3
DAMPING=0
IS_VALID_TRACK=0
DIRT_ADDITIVE=0
IS_PITLANE=0
VIBRATION_GAIN=0
VIBRATION_LENGTH=0
""")


def write_map_ini(path, vertices):
    xs = [v[0] for v in vertices]
    zs = [v[2] for v in vertices]
    x_range = max(xs) - min(xs)
    z_range = max(zs) - min(zs)
    size = 900
    margin = 40
    scale = max(x_range, z_range) / (size - 2 * margin)
    x_off = -min(xs) / scale + margin
    z_off = -min(zs) / scale + margin

    with open(path, "w") as f:
        f.write(f"""[PARAMETERS]
WIDTH={size}
HEIGHT={size}
SCALE_FACTOR={scale:.6f}
X_OFFSET={x_off:.3f}
Z_OFFSET={z_off:.3f}
MARGIN={margin}
DRAWING_SIZE=10
""")


def write_ui_track_json(path, name, desc, length_m, author="airoso"):
    data = {
        "name": name,
        "description": desc,
        "tags": ["street", "loop", "real-roads"],
        "geotags": ["32.782", "-117.042"],
        "country": "United States",
        "city": "San Diego",
        "length": str(int(length_m)),
        "width": "12",
        "pitboxes": "1",
        "run": "clockwise",
        "author": author,
        "version": "1.0.0",
        "year": 2026
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def build_one_track(track_name, display_name, description, coords, length_km):
    print(f"\n{'='*60}")
    print(f"Building: {display_name}")
    print(f"  {length_km:.2f} km, {len(coords)} nodes")

    # Center all coordinates around the first route point
    origin = lonlat_to_xz(coords[0][0], coords[0][1])

    # Compute initial heading from first two points for car orientation
    if len(coords) >= 2:
        p1 = lonlat_to_xz(coords[1][0], coords[1][1])
        hdx = p1[0] - origin[0]
        hdz = p1[1] - origin[1]
        hdist = math.hypot(hdx, hdz)
        if hdist > 1e-6:
            hdx /= hdist
            hdz /= hdist
        else:
            hdx, hdz = 0.0, -1.0
    else:
        hdx, hdz = 0.0, -1.0

    # Start position at origin (mesh is centered here)
    start_pos = (0.0, 0.0, 0.0)
    # Heading matrix: rotation around Y so car faces along road
    # Column-major 4x4: right=(hdz,0,-hdx), up=(0,1,0), fwd=(hdx,0,hdz)
    start_heading = [
        hdz,  0.0, -hdx, 0.0,
        0.0,  1.0,  0.0, 0.0,
        hdx,  0.0,  hdz, 0.0,
        0.0,  0.0,  0.0, 1.0,
    ]

    # Generate mesh (centered around origin)
    vertices, indices = make_road_mesh(coords, origin=origin)
    print(f"  {len(vertices)} vertices, {len(indices)} indices ({len(indices)//3} triangles)")

    # Create track folder
    track_dir = os.path.join(AC_TRACKS, track_name)
    data_dir = os.path.join(track_dir, "data")
    ui_dir = os.path.join(track_dir, "ui")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(ui_dir, exist_ok=True)

    # Generate texture
    road_tex = make_gray_png(90, 90, 95)

    # Write kn5
    kn5_path = os.path.join(track_dir, f"{track_name}.kn5")
    with open(kn5_path, "wb") as f:
        kn5 = KN5(f)
        kn5.write_kn5(
            texture_data=road_tex,
            texture_name="road.png",
            material_name="ROAD",
            shader_name="ksPerPixel",
            mesh_name="ROAD_0",
            vertices=vertices,
            indices=indices,
            start_pos=start_pos,
            start_matrix=start_heading,
        )
    print(f"  kn5: {os.path.getsize(kn5_path)} bytes -> {kn5_path}")

    # Write models.ini
    with open(os.path.join(track_dir, "models.ini"), "w") as f:
        f.write(f"[MODEL_0]\nFILE={track_name}.kn5\nPOSITION=0,0,0\nROTATION=0,0,0\n")

    # Write AI spline
    ai_dir = os.path.join(track_dir, "ai")
    os.makedirs(ai_dir, exist_ok=True)
    write_ai_spline(os.path.join(ai_dir, "fast_lane.ai"), coords, origin=origin)
    print(f"  AI spline: {len(coords)} points")

    # Write data files
    write_surfaces_ini(os.path.join(data_dir, "surfaces.ini"))
    write_map_ini(os.path.join(data_dir, "map.ini"), vertices)

    # Write ui_track.json
    write_ui_track_json(
        os.path.join(ui_dir, "ui_track.json"),
        display_name,
        description,
        length_km * 1000,
    )

    print(f"  Track installed: {track_dir}")
    return track_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # First, run route_tracks.py to generate routes.json
    print("Routing tracks...")
    sys.path.insert(0, HERE)
    import route_tracks  # this writes data/routes.json

    routes_path = os.path.join(DATA, "routes.json")
    with open(routes_path) as f:
        routes = json.load(f)

    tracks = [
        (
            "airoso_full",
            "Airoso — Full Loop",
            "13.5 km Lake Murray loop: College / Navajo / Jackson / Lake Murray / 70th / Alvarado.",
            routes["full"],
        ),
        (
            "airoso_medium",
            "Airoso — Medium",
            "Del Cerro / College / Navajo / Jackson / Lake Murray, closing through the neighborhood back to Airoso.",
            routes["medium"],
        ),
        (
            "airoso_short",
            "Airoso — Short",
            "Airoso neighborhood loop: Airoso / Connecticut / Wisconsin / Lake Murray / Alvarado / College / Del Cerro.",
            routes["short"],
        ),
    ]

    for track_name, display_name, desc, route_data in tracks:
        build_one_track(track_name, display_name, desc, route_data["coords"], route_data["km"])

    print("\n" + "="*60)
    print("Done. Three tracks installed to AC.")
    print("Open Content Manager and look for 'Airoso' tracks.")


if __name__ == "__main__":
    main()
