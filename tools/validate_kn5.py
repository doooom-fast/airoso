"""Validate a kn5 file by reading it back."""
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\airoso_short\airoso_short.kn5"

def ri(f): return struct.unpack("<i", f.read(4))[0]
def ru(f): return struct.unpack("<I", f.read(4))[0]
def rf(f): return struct.unpack("<f", f.read(4))[0]
def rb(f): return struct.unpack("B", f.read(1))[0]
def rbool(f): return struct.unpack("?", f.read(1))[0]
def rs(f):
    n = ru(f)
    return f.read(n).decode("utf-8", errors="replace")
def rh(f): return struct.unpack("<H", f.read(2))[0]

with open(path, "rb") as f:
    magic = f.read(6)
    ver = ru(f)
    print(f"Magic: {magic}  Version: {ver}")

    # Textures
    tc = ru(f)
    print(f"\nTextures: {tc}")
    for i in range(tc):
        ttype = ru(f)
        name = rs(f)
        dlen = ru(f)
        f.seek(dlen, 1)
        print(f"  [{i}] type={ttype} name='{name}' size={dlen}")

    # Materials
    mc = ru(f)
    print(f"\nMaterials: {mc}")
    for i in range(mc):
        mname = rs(f)
        shader = rs(f)
        blend = rb(f)
        alpha = rbool(f)
        depth = ri(f)
        print(f"  [{i}] name='{mname}' shader='{shader}' blend={blend} alpha={alpha} depth={depth}")

        pc = ru(f)
        print(f"      properties: {pc}")
        for j in range(pc):
            pn = rs(f)
            va = rf(f)
            vb = struct.unpack("<2f", f.read(8))
            vc = struct.unpack("<3f", f.read(12))
            vd = struct.unpack("<4f", f.read(16))
            print(f"        {pn}: a={va}")

        tmc = ru(f)
        print(f"      texmaps: {tmc}")
        for j in range(tmc):
            samp = rs(f)
            slot = ru(f)
            tn = rs(f)
            print(f"        {samp} slot={slot} -> '{tn}'")

    # Node tree
    print(f"\nNode tree (offset {f.tell()}):")
    nc = ru(f)
    print(f"  node_class: {nc}")
    if nc == 1:
        name = rs(f)
        children = ru(f)
        active = rbool(f)
        matrix = struct.unpack("<16f", f.read(64))
        print(f"  Transform: name='{name}' children={children} active={active}")
        print(f"  Matrix diag: {matrix[0]:.1f}, {matrix[5]:.1f}, {matrix[10]:.1f}, {matrix[15]:.1f}")

        for ci in range(children):
            cnc = ru(f)
            print(f"\n  Child {ci}: class={cnc}")
            if cnc == 2:
                cname = rs(f)
                cc = ru(f)
                cactive = rbool(f)
                cshadow = rbool(f)
                cvis = rbool(f)
                ctrans = rbool(f)
                print(f"    Mesh: name='{cname}' children={cc} active={cactive}")
                print(f"    shadows={cshadow} visible={cvis} transparent={ctrans}")

                vc = ru(f)
                print(f"    Vertices: {vc}")
                for vi in range(min(vc, 3)):
                    pos = struct.unpack("<3f", f.read(12))
                    nrm = struct.unpack("<3f", f.read(12))
                    uv = struct.unpack("<2f", f.read(8))
                    tan = struct.unpack("<3f", f.read(12))
                    print(f"      v[{vi}]: pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) uv=({uv[0]:.2f}, {uv[1]:.2f})")
                if vc > 3:
                    f.seek((vc - 3) * 44, 1)

                ic = ru(f)
                print(f"    Indices: {ic}")
                if ic > 0:
                    first6 = [rh(f) for _ in range(min(ic, 6))]
                    print(f"      first: {first6}")
                    if ic > 6:
                        for _ in range(ic - 6):
                            rh(f)

                matid = ru(f)
                layer = ru(f)
                lodin = rf(f)
                lodout = rf(f)
                bsc = struct.unpack("<3f", f.read(12))
                bsr = rf(f)
                renderable = rbool(f)
                print(f"    matId={matid} layer={layer} lodIn={lodin} lodOut={lodout}")
                print(f"    bsphere=({bsc[0]:.1f}, {bsc[1]:.1f}, {bsc[2]:.1f}) r={bsr:.1f}")
                print(f"    renderable={renderable}")

    remaining = f.read()
    print(f"\nRemaining bytes after parse: {len(remaining)}")
    if remaining:
        print(f"  First bytes: {remaining[:20].hex()}")

    print(f"\nTotal file size: {f.seek(0, 2)} bytes")
