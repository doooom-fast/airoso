"""Swap texture payloads inside a built kn5, by name, without touching geometry or materials.

For the public package of a track whose build binds textures we may not redistribute (the V3
Lake Murray kn5 carries LA Canyons' cracked asphalt and Hamburg's concrete — personal-use only,
see tracks/<slug>/LICENSES.md), this rewrites just the texture table: same names, so every
material binding survives, CC0 bytes underneath. The kn5 texture table is self-describing
(count, then per texture: type u32, name-length u32, name, size u32, bytes), so the file is
re-emitted as header + new table + the untouched materials/nodes tail. The gates do not need
re-running: nothing a gate measures changes.

    python tools/repack_kn5_textures.py <in.kn5> <out.kn5> name=path [name=path ...]

Every `name` must already exist in the kn5 (this swaps, it never adds).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

MAGIC = b"sc6969"


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    swaps = {}
    for arg in sys.argv[3:]:
        name, path = arg.split("=", 1)
        swaps[name] = Path(path).read_bytes()
    data = src.read_bytes()
    assert data[:6] == MAGIC, "not a kn5"
    version = struct.unpack_from("<I", data, 6)[0]
    pos = 10
    if version > 5:
        pos += 4
    count = struct.unpack_from("<I", data, pos)[0]
    table_start = pos + 4
    pos = table_start
    out = bytearray(data[:table_start])
    seen = set()
    for _ in range(count):
        ttype, nlen = struct.unpack_from("<II", data, pos)
        name = data[pos + 8:pos + 8 + nlen].decode("utf-8")
        size = struct.unpack_from("<I", data, pos + 8 + nlen)[0]
        payload_at = pos + 12 + nlen
        payload = data[payload_at:payload_at + size]
        pos = payload_at + size
        if name in swaps:
            payload = swaps[name]
            seen.add(name)
            print(f"  {name}: {size/1e6:.2f} MB -> {len(payload)/1e6:.2f} MB")
        out += struct.pack("<II", ttype, nlen) + name.encode("utf-8") + struct.pack("<I", len(payload)) + payload
    missing = set(swaps) - seen
    if missing:
        raise SystemExit(f"not in kn5: {sorted(missing)}")
    out += data[pos:]
    dst.write_bytes(out)
    print(f"wrote {dst} ({len(out)/1e6:.1f} MB; {len(seen)} texture(s) swapped, tail {len(data) - pos} bytes untouched)")


if __name__ == "__main__":
    main()
