"""Run the chain's own export_kn5_addon.py (the vendored AC add-on export) on the far-clip scene, with one change:
FARCLIP_* / FARLAD_* materials get ksPerPixel + their checker as txDiffuse and ksAmbient 1 / ksDiffuse 0 / ksSpecular 0
(flat, lit only by ambient). Nothing else in the script changes; it is exec'd from its own path so repo/vendor resolve."""
F = "D:/k10-scratch/eng_rehearsal/scripts/ac/export_kn5_addon.py"
src = open(F, encoding="utf-8").read()
HOOK = '''    _u = name.upper()
    if _u.startswith("FARLAD_") or _u.startswith("FARCLIP_"):
        if _u.startswith("FARLAD_"):
            _col = {"R": "red", "G": "green", "B": "blue"}[_u[-1]] + "_hi"
        else:
            _col = {"FARCLIP_025": "red", "FARCLIP_060": "green", "FARCLIP_105": "blue"}[_u[:11]] + ("_hi" if _u.endswith("_HI") else "")
        return "ksPerPixel", [("txDiffuse", "farclip_" + _col + ".png", "D:/k10-scratch/farclip_test/tex/farclip_" + _col + ".png")]
'''
anchor = "    key = next((k for k in pbr.TEXTURES"
assert src.count(anchor) == 1
src = src.replace(anchor, HOOK + anchor, 1)
anchor2 = "import pbr  # noqa: E402\n"
assert src.count(anchor2) == 1
src = src.replace(anchor2, anchor2 + 'pbr.KS_PROPS["FARCLIP_"] = {"ksAmbient": 1.0, "ksDiffuse": 0.0, "ksSpecular": 0.0}\n'
                                     'pbr.KS_PROPS["FARLAD_"] = {"ksAmbient": 1.0, "ksDiffuse": 0.0, "ksSpecular": 0.0}\n', 1)
exec(compile(src, F, "exec"), {"__file__": F, "__name__": "__main__"})
