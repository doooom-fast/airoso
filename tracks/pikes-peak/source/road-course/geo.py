"""NAIP 2023 0.3 m crop of PPIR <-> the track's local ENU frame (x = E, z = N, metres about the port's origin)."""
import json, math
import numpy as np

import os
# the NAIP crop (not committed: 8.5 MB; tools/naip_crop.py on claude/circuit-kerbs-lm, item co_m_3810427_ne_13_030_20230920_20240104,
# --track tracks/pikes-peak --margin-m 40); its .json sidecar (the corners) is committed beside this file as naip_2023_030.json
IMG = os.environ.get("PPIR_NAIP", "/Volumes/Drive/codex/kerb_work/img/pikes-peak_2023_030.png")
META = json.load(open(str(__import__("pathlib").Path(__file__).resolve().parent / "naip_2023_030.json")))
W_, N_, E_, S_ = META["corners"]
WPX, HPX = META["w"], META["h"]
REPO = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/"
LOC = json.load(open(REPO + "tracks/pikes-peak/data/centerline.local.json"))
LON0, LAT0 = LOC["origin"]["lon"], LOC["origin"]["lat"]


def mpd(lat0):
    phi = math.radians(lat0)
    m_lat = 111132.954 - 559.822 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi) + 0.118 * math.cos(5 * phi)
    return m_lon, m_lat

M_LON, M_LAT = mpd(LAT0)


def en_to_px(e, n):
    e = np.asarray(e, float); n = np.asarray(n, float)
    lon = LON0 + e / M_LON; lat = LAT0 + n / M_LAT
    px = (lon - W_) / (E_ - W_) * WPX - 0.5
    py = (N_ - lat) / (N_ - S_) * HPX - 0.5
    return px, py


def px_to_en(px, py):
    px = np.asarray(px, float); py = np.asarray(py, float)
    lon = W_ + (px + 0.5) / WPX * (E_ - W_)
    lat = N_ - (py + 0.5) / HPX * (N_ - S_)
    return (lon - LON0) * M_LON, (lat - LAT0) * M_LAT


def en_to_lonlat(e, n):
    return LON0 + np.asarray(e) / M_LON, LAT0 + np.asarray(n) / M_LAT
