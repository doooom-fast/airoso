"""Route the three Lake Murray tracks from OSM junction nodes."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.network import Network

net = Network()


def route_loop(legs):
    nodes = []
    for s, g, allow in legs:
        seg = net.route(s, g, allow=allow)
        if nodes:
            seg = seg[1:]
        nodes.extend(seg)
    return nodes


# Key junctions
j = {
    "alv_col":  net.junction("Alvarado Road", "College Avenue"),
    "col_nav":  net.junction("College Avenue", "Navajo Road"),
    "nav_jac":  net.junction("Navajo Road", "Jackson Drive"),
    "jac_lm":   net.junction("Jackson Drive", "Lake Murray Boulevard"),
    "lm_70":    net.junction("Lake Murray Boulevard", "70th Street"),
    "70_alv":   net.junction("70th Street", "Alvarado Road"),
    "col_dcb":  net.junction("College Avenue", "Del Cerro Boulevard"),
    "dca_air":  net.junction("Del Cerro Avenue", "Airoso Avenue"),
    "air_adel": net.junction("Airoso Avenue", "Adelante Avenue"),
    "adel_col": net.junction("Adelante Avenue", "Colorado Avenue"),
    "col_penn": net.junction("Colorado Avenue", "Pennsylvania Lane"),
    "penn_del": net.junction("Pennsylvania Lane", "Delaware Avenue"),
    "ct_wi":    net.junction("Connecticut Avenue", "Wisconsin Avenue"),
    "wi_lm":    net.junction("Wisconsin Avenue", "Lake Murray Boulevard"),
}


# FULL LOOP: Alvarado / College / Navajo / Jackson / Lake Murray
full = route_loop([
    (j["alv_col"], j["col_nav"], {"College Avenue"}),
    (j["col_nav"], j["nav_jac"], {"Navajo Road"}),
    (j["nav_jac"], j["jac_lm"],  {"Jackson Drive"}),
    (j["jac_lm"],  j["lm_70"],   {"Lake Murray Boulevard"}),
    (j["lm_70"],   j["70_alv"],   {"70th Street", "Lake Murray Boulevard"}),
    (j["70_alv"],  j["alv_col"],  {"Alvarado Road"}),
])


# MEDIUM: Airoso -> Del Cerro Ave -> Del Cerro Blvd -> College -> Navajo ->
#   Jackson -> Lake Murray -> Wisconsin/Connecticut -> back to Airoso
med = route_loop([
    (j["dca_air"], j["col_dcb"], {"Del Cerro Avenue", "Madra Avenue", "Del Cerro Boulevard"}),
    (j["col_dcb"], j["col_nav"], {"College Avenue"}),
    (j["col_nav"], j["nav_jac"], {"Navajo Road"}),
    (j["nav_jac"], j["jac_lm"],  {"Jackson Drive"}),
    (j["jac_lm"],  j["wi_lm"],   {"Lake Murray Boulevard"}),
    (j["wi_lm"],   j["ct_wi"],   {"Wisconsin Avenue"}),
    (j["ct_wi"],   j["penn_del"], {"Connecticut Avenue", "Delaware Avenue"}),
    (j["penn_del"], j["col_penn"], {"Pennsylvania Lane"}),
    (j["col_penn"], j["adel_col"], {"Colorado Avenue"}),
    (j["adel_col"], j["air_adel"], {"Adelante Avenue"}),
    (j["air_adel"], j["dca_air"],  {"Airoso Avenue"}),
])


# SHORT: Airoso -> neighborhood descent -> Connecticut -> Wisconsin ->
#   Lake Murray -> Alvarado -> College -> Del Cerro -> back to Airoso
short = route_loop([
    (j["dca_air"], j["air_adel"], {"Airoso Avenue"}),
    (j["air_adel"], j["adel_col"], {"Adelante Avenue"}),
    (j["adel_col"], j["col_penn"], {"Colorado Avenue"}),
    (j["col_penn"], j["penn_del"], {"Pennsylvania Lane"}),
    (j["penn_del"], j["ct_wi"],    {"Delaware Avenue", "Connecticut Avenue"}),
    (j["ct_wi"],    j["wi_lm"],    {"Wisconsin Avenue"}),
    (j["wi_lm"],    j["lm_70"],    {"Lake Murray Boulevard"}),
    (j["lm_70"],    j["70_alv"],   {"70th Street", "Lake Murray Boulevard"}),
    (j["70_alv"],   j["alv_col"],  {"Alvarado Road"}),
    (j["alv_col"],  j["col_dcb"],  {"College Avenue"}),
    (j["col_dcb"],  j["dca_air"],  {"Del Cerro Boulevard", "Del Cerro Avenue", "Madra Avenue"}),
])


# Output route data for mesh generation
tracks = {
    "full":   {"nodes": full,  "coords": net.coords(full),  "km": round(net.length(full)/1000, 2)},
    "medium": {"nodes": med,   "coords": net.coords(med),   "km": round(net.length(med)/1000, 2)},
    "short":  {"nodes": short, "coords": net.coords(short), "km": round(net.length(short)/1000, 2)},
}

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "routes.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(tracks, f)

for name, t in tracks.items():
    print(f"{name:8s}: {t['km']:6.2f} km, {len(t['nodes']):5d} nodes")
