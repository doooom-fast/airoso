"""Pavement mask of the PPIR infield off NAIP 2023 0.3 m: grey (low saturation) pixels; kerbs (red / white) count as pavement."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent) + "/")
from geo import IMG

im = np.asarray(Image.open(IMG).convert("RGB")).astype(float)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx = im.max(-1); mn = im.min(-1)
sat = (mx - mn) / np.maximum(mx, 1)
grey = (sat < 0.10) & (mx > 60) & (mx < 215)
red = (r > 150) & (r - g > 50) & (r - b > 50)
white = (mn > 200)
m = grey | red | white
m = ndimage.binary_opening(m, iterations=1)
m = ndimage.binary_closing(m, iterations=2)
np.save(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "pave_mask.npy", m)
out = (im * 0.35).astype(np.uint8); out[m] = [255, 255, 255]
Image.fromarray(out).save(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "pave_mask.jpg", quality=85)
Image.fromarray(out[240:1000, 280:1300]).save(str(__import__("pathlib").Path(__file__).resolve().parent) + "/" + "pave_mask_infield.jpg", quality=85)
print(m.mean())
