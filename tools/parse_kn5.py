"""Parse a KN5 file to understand format for writing."""
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\san_diego_lake_murray\san_diego_lake_murray.kn5"

def read_int(f):
    return struct.unpack("<i", f.read(4))[0]

def read_uint(f):
    return struct.unpack("<I", f.read(4))[0]

def read_float(f):
    return struct.unpack("<f", f.read(4))[0]

def read_str(f):
    n = read_int(f)
    return f.read(n).decode("ascii", errors="replace")

def read_byte(f):
    return struct.unpack("B", f.read(1))[0]

with open(path, "rb") as f:
    magic = f.read(6)
    ver = read_int(f)

    # Skip textures
    tex_count = read_int(f)
    for i in range(tex_count):
        ttype = read_int(f)
        name = read_str(f)
        dlen = read_int(f)
        f.seek(dlen, 1)

    mat_count = read_int(f)
    print(f"Materials: {mat_count}, offset={f.tell()}")

    # Dump first material's raw bytes
    pos = f.tell()
    raw = f.read(200)
    f.seek(pos)

    # Try to read first material name
    mname = read_str(f)
    shader = read_str(f)
    print(f"  mat[0] name={mname} shader={shader} offset_after_shader={f.tell()}")

    # Dump next 50 bytes as hex + attempt int32/float interpretations
    pos2 = f.tell()
    chunk = f.read(60)
    f.seek(pos2)
    print(f"  Next bytes: {chunk[:40].hex()}")

    for off in range(0, 40, 4):
        iv = struct.unpack_from("<i", chunk, off)[0]
        fv = struct.unpack_from("<f", chunk, off)[0]
        bv = chunk[off]
        print(f"    +{off}: byte={bv} int32={iv} float={fv:.6f}")

    # Try blendMode as int32 instead of byte
    print("\n--- Try blendMode as int32 ---")
    f.seek(pos2)
    blend = read_int(f)
    alpha = read_int(f)
    depth = read_int(f)
    sort = read_float(f)
    prop_count = read_int(f)
    print(f"  blend={blend} alpha={alpha} depth={depth} sort={sort} props={prop_count}")

    if 0 <= prop_count < 50:
        for i in range(prop_count):
            pname = read_str(f)
            va = read_float(f)
            vb = struct.unpack("<2f", f.read(8))
            vc = struct.unpack("<3f", f.read(12))
            vd = struct.unpack("<4f", f.read(16))
            print(f"    prop {i}: {pname} a={va} b={vb}")
        tex_map_count = read_int(f)
        print(f"  texMaps={tex_map_count}")
        for i in range(tex_map_count):
            sampler = read_str(f)
            slot = read_int(f)
            tex_name = read_str(f)
            print(f"    map {i}: {sampler} slot={slot} -> {tex_name}")
