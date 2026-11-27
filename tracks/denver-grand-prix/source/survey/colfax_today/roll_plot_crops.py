"""Crops of Denver's 100% design roll plot for East Colfax, Broadway to Logan (COLFAX-TODAY.md's evidence).

    python3 roll_plot_crops.py <work-dir>      # downloads the PDF (6.4 MB) into <work-dir>, writes stills/*.jpg beside this file

Needs pymupdf and Pillow. The PDF is the City and County of Denver's (DOTI / Parsons, "100% DESIGN, AUGUST 2024", sheet
"DENVER ROLL 1 OF 4"); it is not committed, only these crops are, credited in COLFAX-TODAY.md. Page units are points:
1.44 pt per foot along the alignment (stations 100+00 at x 754, 105+00 at x 1474).
"""
import io, os, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 5))
sys.path.insert(0, ROOT)
from scripts.tls import https_context  # noqa: E402

URL = "https://www.denvergov.org/files/assets/public/v/3/doti/images/projects/colfax-brt/roll-plot-100percent-denver-1.pdf"
CROPS = {  # name: (x0, y0, x1, y1, zoom)
    "overview_broadway_logan": (560, 560, 2900, 1380, 0.75),
    "blk_1_broadway_lincoln": (740, 895, 1300, 1075, 2.6),
    "blk_2_lincoln_sherman": (1230, 895, 1790, 1075, 2.6),
    "blk_3_sherman_grant": (1740, 895, 2330, 1075, 2.6),
    "blk_4_grant_logan": (2270, 895, 2860, 1075, 2.6),
}

if __name__ == "__main__":
    import pymupdf
    from PIL import Image
    work = sys.argv[1]
    os.makedirs(work, exist_ok=True)
    pdf = os.path.join(work, "roll-plot-100percent-denver-1.pdf")
    if not os.path.exists(pdf):
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 research-client"})
        with urllib.request.urlopen(req, timeout=300, context=https_context()) as r:
            open(pdf, "wb").write(r.read())
    page = pymupdf.open(pdf)[0]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stills")
    os.makedirs(out, exist_ok=True)
    for name, (x0, y0, x1, y1, z) in CROPS.items():
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=pymupdf.Rect(x0, y0, x1, y1))
        Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB").save(os.path.join(out, name + ".jpg"), quality=82)
        print(name, pix.width, pix.height)
