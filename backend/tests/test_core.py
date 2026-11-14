import math
from app.analysis import analyze

def run(**kw):
    return analyze(kw)

def test_second_order_unity():
    r = run(mode="tf", tf={"G": "25/(s*(s+5))"}, feedback={"type": "unity"})
    # T = 25/(s^2+5s+25): wn=5, zeta=0.5
    d = r["dynamics"]["dominant"]
    assert abs(d["wn"] - 5) < 1e-6 and abs(d["zeta"] - 0.5) < 1e-6
    m = r["time"]["metrics"]
    assert abs(m["overshoot_pct"] - 16.303) < 0.1
    assert abs(m["tp"] - math.pi / (5 * math.sqrt(0.75))) < 0.01
    assert r["errors"]["type"] == 1 and abs(r["errors"]["Kv"] - 5) < 1e-9
    assert abs(r["errors"]["ess_ramp"] - 0.2) < 1e-9 and r["errors"]["ess_step"] == 0
    assert r["stability"]["stable"]

def test_blocks_mason_matches_tf():
    nodes = [{"id": "r", "type": "input"}, {"id": "e", "type": "sum"},
             {"id": "g", "type": "block", "tf": "10/(s*(s+2))", "name": "G"},
             {"id": "b", "type": "branch"}, {"id": "h", "type": "block", "tf": "1/(s+1)", "name": "H"},
             {"id": "y", "type": "output"}]
    edges = [{"source": "r", "target": "e", "sign": "+"}, {"source": "e", "target": "g"},
             {"source": "g", "target": "b"}, {"source": "b", "target": "y"},
             {"source": "b", "target": "h"}, {"source": "h", "target": "e", "sign": "-"}]
    r = run(mode="blocks", blocks={"nodes": nodes, "edges": edges})
    # T = G/(1+GH) = 10(s+1)/(s^3+3s^2+2s+10)
    assert r["tf"]["den"] == [1, 3, 2, 10] or all(abs(a - b) < 1e-9 for a, b in zip(r["tf"]["den"], [1, 3, 2, 10]))
    assert r["feedback"] == "diagram"

def test_routh_unstable():
    r = run(mode="tf", tf={"G": "1/(s^3+s^2+2*s+8)"}, feedback={"type": "none"})
    assert r["stability"]["rhp"] == 2 and not r["stability"]["stable"]

def test_physical_msd():
    comps = [{"id": "m", "type": "mass", "name": "M", "value": 2}, {"id": "k", "type": "spring", "name": "K", "value": 8},
             {"id": "b", "type": "damper", "name": "B", "value": 4}, {"id": "f", "type": "force", "name": "F"},
             {"id": "w", "type": "ground", "name": "W"}]
    wires = [["m.a", "k.a"], ["m.a", "b.a"], ["m.a", "f.a"], ["k.b", "w.a"], ["b.b", "w.a"]]
    r = run(mode="physical", physical={"components": comps, "wires": wires, "input": "f",
                                       "output": {"comp": "m", "kind": "across"}}, feedback={"type": "none"})
    # X/F = 1/(2s^2+4s+8)
    assert abs(r["tf"]["dc_gain"] - 1 / 8) < 1e-9 and r["tf"]["order"] == 2

def test_rlc():
    comps = [{"id": "v", "type": "vsource", "name": "V"}, {"id": "r", "type": "resistor", "name": "R", "value": 1},
             {"id": "l", "type": "inductor", "name": "L", "value": 1}, {"id": "c", "type": "capacitor", "name": "C", "value": 1},
             {"id": "g", "type": "ground"}]
    wires = [["v.a", "r.a"], ["r.b", "l.a"], ["l.b", "c.a"], ["c.b", "g.a"], ["v.b", "g.a"]]
    r = run(mode="physical", physical={"components": comps, "wires": wires, "input": "v",
                                       "output": {"comp": "c", "kind": "across"}}, feedback={"type": "none"})
    assert abs(r["tf"]["dc_gain"] - 1) < 1e-9 and r["tf"]["order"] == 2

def test_motor():
    r = run(mode="motor", motor={"output": "speed"}, params={"Ra": 1, "La": 0.5, "Kt": 0.01, "Kb": 0.01, "J": 0.01, "B": 0.1},
            feedback={"type": "none"})
    assert r["tf"]["order"] == 2 and r["stability"]["stable"]

def test_rlocus_and_margins():
    r = run(mode="tf", tf={"G": "K/(s*(s+1)*(s+2))", "H": "1"}, params={"K": 1}, feedback={"type": "unity"})
    cr = r["rlocus"]["crossings"][0]
    assert abs(cr["k"] - 6) < 0.05 and abs(cr["w"] - math.sqrt(2)) < 0.01
    r6 = run(mode="tf", tf={"G": "K/(s*(s+1)*(s+2))"}, params={"K": 1}, feedback={"type": "unity"})
    assert abs(r6["freq"]["margins"]["gm_db"] - 20 * math.log10(6)) < 0.2

def test_tf_latex_keeps_denominator():
    from app.symbolic import tf_latex
    import numpy as np
    assert "frac" in tf_latex(np.array([1.0]), np.array([1.0, 1.0]))

def test_nyquist_and_errors_json_safe():
    import json
    r = run(mode="tf", tf={"G": "1/(s^2)"}, feedback={"type": "unity"})
    json.dumps(r, allow_nan=False)
    assert r["errors"]["type"] == 2 and r["errors"]["Kp"] == "∞"
