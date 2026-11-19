import math
from app.paramstab import param_stability

def run(G, names, params=None, fb="unity", ranges=None):
    return param_stability({"mode": "tf", "tf": {"G": G}, "feedback": {"type": fb},
                            "params": params or {}, "study": {"params": names, "ranges": ranges or {}}})

def test_classic_k_range():
    r = run("K/(s*(s+1)*(s+2))", ["K"], {"K": 1})
    st = r["analysis"]["stable"]
    assert len(st) == 1 and abs(st[0]["lo"]) < 1e-9 and abs(st[0]["hi"] - 6) < 1e-9
    osc = [m for m in r["analysis"]["marginal"] if m["kind"] == "oscilation"]
    assert abs(osc[0]["value"] - 6) < 1e-9 and abs(osc[0]["w"] - math.sqrt(2)) < 1e-6
    assert abs(osc[0]["period"] - 2 * math.pi / math.sqrt(2)) < 1e-6
    assert any(m["kind"] == "origin" for m in r["analysis"]["marginal"])  # K = 0
    assert r["routh"]["rows"]

def test_unbounded_stable_range():
    # s^3 + 5 s^2 + (K-6) s + K  ->  estable para K > 7.5 ; w^2 = K-6 = 1.5
    r = run("K*(s+1)/(s*(s-1)*(s+6))", ["K"], {"K": 10})
    st = r["analysis"]["stable"]
    assert len(st) == 1 and abs(st[0]["lo"] - 7.5) < 1e-9 and st[0]["hi"] is None or st[0]["hi"] > 1e300 or st[0]["hi"] is None
    osc = [m for m in r["analysis"]["marginal"] if m["kind"] == "oscilation"][0]
    assert abs(osc["value"] - 7.5) < 1e-9 and abs(osc["w"] - math.sqrt(1.5)) < 1e-6

def test_two_params():
    r = run("1/(s^3+3*s^2+a*s+K)", ["a", "K"], {"a": 2, "K": 1}, fb="none", ranges={"a": [0, 10], "K": [0, 10]})
    reg = r["region"]
    import numpy as np
    z = np.array([[v if v is not None else np.nan for v in row] for row in reg["z"]])
    xs, ys = reg["x"], reg["y"]
    i = int(np.argmin(abs(np.array(ys) - 1))); j = int(np.argmin(abs(np.array(xs) - 5)))   # K=1, a=5 -> estable (3a>K)
    assert z[i, j] < 0
    i = int(np.argmin(abs(np.array(ys) - 9))); j = int(np.argmin(abs(np.array(xs) - 1)))   # K=9, a=1 -> inestable
    assert z[i, j] > 0
    assert set(r["slices"]) == {"a", "K"}
