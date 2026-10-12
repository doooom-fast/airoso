"""Derive a tileable dry-chaparral ground texture for the far ring (ledger 0046 fix round) from two owned textures:
assets/textures/grass_diffuse.jpg (ambientCG Grass001: the fine vegetation detail) and ground_dry_diffuse.jpg (LA
Canyons dirt: the bare-soil detail). Colour: San Diego coastal sage scrub / chamise in October — grey-olive shrubs
over darker shadow with tan soil between. usage (from the airoso root): python tracks/san-diego-lake-murray/textures/make_chaparral_far.py . tracks/san-diego-lake-murray/textures/chaparral_far_diffuse.jpg"""
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageStat

root, out = Path(sys.argv[1]), Path(sys.argv[2])
N = 1024
grass = Image.open(root / "assets/textures/grass_diffuse.jpg").convert("L").resize((N, N), Image.LANCZOS)
soil = Image.open(root / "assets/textures/ground_dry_diffuse.jpg").convert("L").resize((N, N), Image.LANCZOS)
grass = ImageOps.autocontrast(grass, cutoff=1)
soil = ImageOps.autocontrast(soil, cutoff=1)


def wrap_blur(img, small):
    """a tileable low-frequency field: shrink, tile 3x3, enlarge, keep the centre (wraps at the edges)"""
    s = img.resize((small, small), Image.BOX)
    t = Image.new("L", (3 * small, 3 * small))
    for a in range(3):
        for b in range(3):
            t.paste(s, (a * small, b * small))
    t = t.resize((3 * N, 3 * N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(N / small / 2))
    return t.crop((N, N, 2 * N, 2 * N))


# shrub clumps: the grass texture's own mid-frequency structure, wrapped
clump = ImageOps.autocontrast(wrap_blur(grass, 24), cutoff=2)
# bare patches between clumps: where the clump field is low (threshold with a soft edge)
patch = clump.point(lambda v: max(0, min(255, int((110 - v) * 4))))
SHRUB_LIT = (104, 108, 74)     # grey-olive sage / chamise
SHRUB_DARK = (52, 58, 40)      # shrub shadow
SOIL_LIT = (158, 140, 108)     # decomposed granite / dry grass
SOIL_DARK = (108, 94, 72)
veg = Image.composite(Image.new("RGB", (N, N), SHRUB_LIT), Image.new("RGB", (N, N), SHRUB_DARK), grass)
dirt = Image.composite(Image.new("RGB", (N, N), SOIL_LIT), Image.new("RGB", (N, N), SOIL_DARK), soil)
img = Image.composite(dirt, veg, patch)
img.save(out, quality=90, optimize=True)
st = ImageStat.Stat(img)
print(f"{out.name}: {N}x{N}, mean RGB {[round(m) for m in st.mean]}, bare share "
      f"{sum(1 for v in patch.tobytes() if v > 127) / (N * N):.2f}")
