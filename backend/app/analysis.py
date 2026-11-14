"""Análisis dinámico completo: polos/ceros, Routh, respuesta temporal, error, frecuencia, LGR."""
from __future__ import annotations
import math
import numpy as np
import sympy as sp
import control as ct
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import linear_sum_assignment

from .symbolic import (s, AnalysisError, num_den, coeffs, tf_latex, poly_expr,
                       param_symbol, rational, clean, free_params)
from .builders import build, Built
from .routh import routh

TOL = 1e-9


# ------------------------------------------------------------------ utilidades
def trim(c, tol=1e-12):
    c = np.array(c, float)
    if c.size == 0:
        return np.array([0.0])
    m = np.max(np.abs(c))
    if m == 0:
        return np.array([0.0])
    k = 0
    while k < len(c) - 1 and abs(c[k]) <= tol * m:
        k += 1
    return c[k:]


def roots_of(c) -> np.ndarray:
    c = trim(c)
    if len(c) <= 1:
        return np.array([], complex)
    r = np.roots(c).astype(complex)
    scale = np.maximum(1.0, np.abs(r))
    r.real[np.abs(r.real) < 1e-9 * scale] = 0.0
    r.imag[np.abs(r.imag) < 1e-9 * scale] = 0.0
    return r


def polyc(r, K=1.0):
    return K * np.poly(r) if len(r) else np.array([K])


def fmt(x, d=5):
    return f"{x:.{d}g}"


def cplx_text(z, d=5):
    if abs(z.imag) < 1e-12:
        return fmt(z.real, d)
    return f"{fmt(z.real, d)} {'+' if z.imag >= 0 else '−'} j{fmt(abs(z.imag), d)}"


def zpk_latex(num, den) -> str:
    num, den = trim(num), trim(den)
    K = num[0] / den[0]
    z, p = roots_of(num), roots_of(den)

    def factors(r):
        out, used = [], np.zeros(len(r), bool)
        for i, ri in enumerate(r):
            if used[i]:
                continue
            used[i] = True
            if abs(ri.imag) < 1e-12:
                a = ri.real
                out.append("s" if abs(a) < 1e-12 else f"(s {'+' if a < 0 else '-'} {fmt(abs(a))})")
            else:
                for j in range(i + 1, len(r)):
                    if not used[j] and abs(r[j] - np.conj(ri)) < 1e-6 * max(1, abs(ri)):
                        used[j] = True
                        break
                out.append(f"(s^2 {'+' if -2 * ri.real >= 0 else '-'} {fmt(abs(2 * ri.real))}s + {fmt(abs(ri) ** 2)})")
        return out

    nf, df = factors(z), factors(p)
    nn = r"\,".join(nf) if nf else "1"
    dd = r"\,".join(df) if df else "1"
    kk = "" if abs(K - 1) < 1e-12 else fmt(K) + r"\,"
    return rf"{kk}\frac{{{nn}}}{{{dd}}}" if df else kk + nn


def first_cross(t, y, level):
    i = np.where((y[1:] >= level) & (y[:-1] < level))[0]
    if y[0] >= level:
        return float(t[0])
    if i.size == 0:
        return None
    k = i[0]
    return float(t[k] + (level - y[k]) * (t[k + 1] - t[k]) / (y[k + 1] - y[k]))


def lowest(c):
    """Índice (potencia) del coeficiente no nulo de menor orden y su valor."""
    c = np.asarray(c, float)[::-1]
    m = np.max(np.abs(c)) if c.size else 0
    for k, v in enumerate(c):
        if abs(v) > 1e-12 * m:
            return k, float(v)
    return len(c), 0.0


def lim0(num, den, power):
    """lim_{s→0} s^power · num/den  (power puede ser negativo)."""
    a, na = lowest(num)
    b, nb = lowest(den)
    if na == 0:
        return 0.0
    e = a + power - b
    if e > 0:
        return 0.0
    if e == 0:
        return na / nb
    return math.inf


# ------------------------------------------------------------------- dinámica
def dynamics(poles):
    pairs, seen = [], np.zeros(len(poles), bool)
    for i, p in enumerate(poles):
        if seen[i]:
            continue
        seen[i] = True
        if abs(p.imag) < 1e-12:
            tau = 1 / abs(p.real) if abs(p.real) > 1e-12 else None
            pairs.append({"kind": "real", "pole": clean(p), "sigma": clean(-p.real),
                          "tau": clean(tau) if tau and p.real < 0 else None,
                          "wn": clean(abs(p.real)), "zeta": None, "wd": None})
        else:
            for j in range(i + 1, len(poles)):
                if not seen[j] and abs(poles[j] - np.conj(p)) < 1e-6 * max(1, abs(p)):
                    seen[j] = True
                    break
            wn = abs(p)
            z = -p.real / wn
            pairs.append({"kind": "complex", "pole": clean(complex(p.real, abs(p.imag))),
                          "sigma": clean(-p.real), "wn": clean(wn), "zeta": clean(z),
                          "wd": clean(abs(p.imag)), "tau": clean(1 / abs(p.real)) if abs(p.real) > 1e-12 else None})
    dom = None
    cand = [q for q in pairs if q["sigma"] is not None and q["sigma"] > 1e-12]
    if cand:
        dom = min(cand, key=lambda q: q["sigma"])
    return pairs, dom


# ------------------------------------------------------------ respuesta temporal
def horizon(poles, t_end=None):
    if t_end:
        return float(t_end)
    if len(poles) == 0:
        return 1.0
    unst = [p for p in poles if p.real > 1e-9]
    if unst:
        return min(6 / max(p.real for p in unst), 1e5)
    ts = []
    for p in poles:
        if p.real < -1e-9:
            ts.append(8 / -p.real)
        elif abs(p.imag) > 1e-9:
            ts.append(12 * math.pi / abs(p.imag))
    return min(max(ts), 1e5) if ts else 10.0


def pick(n, keep_head=300, total=1500):
    if n <= total:
        return np.arange(n)
    return np.unique(np.concatenate([np.arange(min(n, keep_head)), np.linspace(0, n - 1, total).astype(int)]))


def step_metrics(t, y, yf):
    out = {"final": yf}
    if not np.isfinite(yf) or abs(yf) < 1e-12:
        out["note"] = "Valor final nulo o infinito: métricas normalizadas no definidas."
        return out
    yn = y / yf
    imax = int(np.argmax(yn))
    ov = max(0.0, float(yn[imax] - 1)) * 100
    out["overshoot_pct"] = ov
    out["peak_value"] = float(y[imax]) if ov > 1e-6 else None
    out["tp"] = float(t[imax]) if ov > 1e-6 else None
    for tol, key in ((0.02, "ts2"), (0.05, "ts5")):
        idx = np.where(np.abs(yn - 1) > tol)[0]
        out[key] = None if (idx.size and idx[-1] >= len(t) - 1) else (float(t[idx[-1] + 1]) if idx.size else 0.0)
    t10, t90 = first_cross(t, yn, 0.1), first_cross(t, yn, 0.9)
    out["t10"], out["t90"] = t10, t90
    out["tr_10_90"] = (t90 - t10) if (t10 is not None and t90 is not None) else None
    out["tr_0_100"] = first_cross(t, yn, 1.0)
    out["td"] = first_cross(t, yn, 0.5)
    return out


def time_responses(num, den, poles, t_end=None):
    num, den = trim(num), trim(den)
    if len(num) > len(den):
        return {"error": "Función impropia (grado del numerador > denominador): no se simula la respuesta temporal."}
    T = horizon(poles, t_end)
    fast = float(np.max(np.abs(poles))) if len(poles) else 1.0
    N = int(np.clip(20 * T * fast, 4000, 60000))
    t = np.linspace(0, T, N)
    sys_ = ct.tf(num, den)
    try:
        y = np.asarray(ct.step_response(sys_, T=t).outputs).reshape(-1)
        h = np.asarray(ct.impulse_response(sys_, T=t).outputs).reshape(-1)
    except Exception as ex:  # noqa: BLE001
        return {"error": f"Fallo de simulación: {ex}"}
    ramp = cumulative_trapezoid(y, t, initial=0.0)
    parab = cumulative_trapezoid(ramp, t, initial=0.0)
    stable = len(poles) == 0 or bool(np.all(poles.real < -TOL))
    diverges = (not stable) and (not np.all(np.isfinite(y)) or np.max(np.abs(y)) > 1e12)
    lim = 1e12
    y, h, ramp, parab = (np.clip(np.nan_to_num(a, nan=0, posinf=lim, neginf=-lim), -lim, lim) for a in (y, h, ramp, parab))
    res = {"t_end": T, "stable": stable, "diverges": bool(diverges)}
    ix = pick(len(t))
    res["step"] = {"t": t[ix], "y": y[ix]}
    res["impulse"] = {"t": t[ix], "y": h[ix]}
    res["ramp"] = {"t": t[ix], "y": ramp[ix], "r": t[ix]}
    res["parabola"] = {"t": t[ix], "y": parab[ix], "r": 0.5 * t[ix] ** 2}
    if stable and den[-1] != 0:
        res["metrics"] = step_metrics(t, y, float(num[-1] / den[-1]) if len(num) else 0.0)
    else:
        res["metrics"] = {"note": "Sistema no asintóticamente estable: no existe valor final; métricas no definidas."}
    return res


# --------------------------------------------------------------------- errores
def steady_state_errors(nL, dL, closed_stable):
    nL, dL = trim(nL), trim(dL)
    k, _ = lowest(dL)
    a, _ = lowest(nL)
    typ = max(0, k - a)
    # tipo = nº de polos en el origen de L (tras cancelación): potencia de s en el denominador - numerador
    Kp = lim0(nL, dL, 0)
    Kv = lim0(nL, dL, 1)
    Ka = lim0(nL, dL, 2)

    def e(K):
        if K == math.inf:
            return 0.0
        return math.inf if K == 0 else 1.0 / K

    ess_step = 0.0 if Kp == math.inf else 1.0 / (1.0 + Kp)
    out = {"type": int(typ), "Kp": Kp, "Kv": Kv, "Ka": Ka,
           "ess_step": ess_step, "ess_ramp": e(Kv), "ess_parabola": e(Ka),
           "valid": bool(closed_stable)}
    if not closed_stable:
        out["note"] = "El lazo cerrado es inestable: los errores en régimen estacionario no están definidos (divergen)."
    return out


# ------------------------------------------------------------------ frecuencia
def freq_grid(nL, dL, n=1200):
    r = np.concatenate([roots_of(nL), roots_of(dL)])
    m = np.abs(r[np.abs(r) > 1e-9])
    if m.size == 0:
        lo, hi = 1e-2, 1e2
    else:
        lo, hi = m.min(), m.max()
        lo = 10 ** (math.floor(math.log10(lo)) - 1)
        hi = 10 ** (math.ceil(math.log10(hi)) + 1)
        if hi / lo < 1e3:
            c = math.sqrt(lo * hi)
            lo, hi = c / 31.7, c * 31.7
    return np.logspace(math.log10(lo), math.log10(hi), n)


def fr(num, den, w):
    z = 1j * w
    return np.polyval(num, z) / np.polyval(den, z)


def crossings(x, level):
    i = np.where((x[1:] - level) * (x[:-1] - level) < 0)[0]
    return i


def margins(w, mag_db, ph):
    lw = np.log10(w)
    gx, px = [], []
    for i in crossings(mag_db, 0.0):
        f = (0 - mag_db[i]) / (mag_db[i + 1] - mag_db[i])
        wc = 10 ** (lw[i] + f * (lw[i + 1] - lw[i]))
        phc = ph[i] + f * (ph[i + 1] - ph[i])
        gx.append({"w": float(wc), "phase": float(phc), "pm": float(180 + phc)})
    q = (ph + 180.0) / 360.0
    fl = np.floor(q)
    for i in np.where(fl[1:] != fl[:-1])[0]:
        a, b = ph[i], ph[i + 1]
        target = -180 + 360 * max(fl[i], fl[i + 1])
        f = (target - a) / (b - a) if b != a else 0
        wp = 10 ** (lw[i] + f * (lw[i + 1] - lw[i]))
        mg = mag_db[i] + f * (mag_db[i + 1] - mag_db[i])
        px.append({"w": float(wp), "gm_db": float(-mg), "mag_db": float(mg)})
    res = {"gain_crossings": gx, "phase_crossings": px}
    res["pm"] = min(gx, key=lambda d: abs(d["pm"]))["pm"] if gx else None
    res["wgc"] = min(gx, key=lambda d: abs(d["pm"]))["w"] if gx else None
    res["gm_db"] = min(px, key=lambda d: abs(d["gm_db"]))["gm_db"] if px else None
    res["wpc"] = min(px, key=lambda d: abs(d["gm_db"]))["w"] if px else None
    return res


def freq_analysis(nL, dL, nT, dT, closed_poles, open_poles):
    nL, dL = trim(nL), trim(dL)
    w = freq_grid(nL, dL)
    H = fr(nL, dL, w)
    mag_db = 20 * np.log10(np.maximum(np.abs(H), 1e-300))
    ph = np.degrees(np.unwrap(np.angle(H)))
    mg = margins(w, mag_db, ph)
    out = {"bode": {"w": w, "mag_db": mag_db, "phase": ph}, "margins": mg}
    # Nyquist
    wn = np.logspace(math.log10(w[0]) - 1, math.log10(w[-1]) + 1, 3000)
    Hn = fr(nL, dL, wn)
    mx = np.abs(Hn)
    core = np.isfinite(mx) & (mx <= 2.5)
    R = float(np.clip(1.6 * max(1.5, np.max(np.maximum(np.abs(Hn.real[core]), np.abs(Hn.imag[core]))) if core.any() else 1.5), 2.0, 6.0))
    P = int(np.sum(open_poles.real > TOL))
    Z = int(np.sum(closed_poles.real > TOL))
    out["nyquist"] = {"re": Hn.real, "im": Hn.imag, "w": wn, "view": R, "P": P, "Z": Z, "N": Z - P,
                      "poles_on_axis": int(np.sum(np.abs(open_poles.real) <= TOL))}
    # ancho de banda / pico de resonancia de T
    try:
        wt = np.logspace(math.log10(w[0]) - 1, math.log10(w[-1]) + 1, 3000)
        Ht = np.abs(fr(trim(nT), trim(dT), wt))
        dc = Ht[0]
        bw = None
        if np.isfinite(dc) and dc > 0:
            lvl = dc / math.sqrt(2)
            i = np.where((Ht[1:] < lvl) & (Ht[:-1] >= lvl))[0]
            if i.size:
                bw = float(wt[i[0]])
        ip = int(np.argmax(Ht))
        out["closed_loop"] = {"bandwidth": bw, "Mr_db": float(20 * np.log10(Ht[ip] / dc)) if dc > 0 and Ht[ip] > dc * 1.0001 else 0.0,
                              "wr": float(wt[ip]) if Ht[ip] > dc * 1.0001 else None}
    except Exception:  # noqa: BLE001
        out["closed_loop"] = {}
    return out


# --------------------------------------------------------------------- LGR
def root_locus(nL, dL):
    nL, dL = trim(nL), trim(dL)
    n, m = len(dL) - 1, len(nL) - 1
    if n < 1 or n > 14 or (len(nL) == 1 and nL[0] == 0):
        return {"error": "Lugar de las raíces no disponible para este sistema."}
    npad = np.concatenate([np.zeros(n - m), nL]) if m <= n else None
    if npad is None:
        return {"error": "L(s) impropia: no se calcula el LGR."}
    zeros, poles = roots_of(nL), roots_of(dL)
    kref = float(np.max(np.abs(dL)) / np.max(np.abs(nL)))
    ks = np.concatenate([[0.0], kref * np.geomspace(1e-4, 1e4, 1500)])
    ks = np.unique(np.concatenate([ks, [1.0]]))

    def rts(k):
        c = dL + k * npad
        r = roots_of(c)
        return r

    sets = [rts(k) for k in ks]
    good = [i for i, r in enumerate(sets) if len(r) == n]
    branches = [[] for _ in range(n)]
    kk = []
    prev = None
    for i in good:
        r = sets[i]
        if prev is None:
            order = np.arange(n)
        else:
            C = np.abs(prev[:, None] - r[None, :])
            ri, ci = linear_sum_assignment(C)
            order = ci[np.argsort(ri)]
        cur = r[order]
        for b in range(n):
            branches[b].append(cur[b])
        prev = cur
        kk.append(ks[i])
    br = [{"re": np.array([z.real for z in b]), "im": np.array([z.imag for z in b])} for b in branches]
    asym = None
    if n > m:
        cen = float((np.sum(poles) - np.sum(zeros)).real / (n - m))
        asym = {"centroid": cen, "angles": [180.0 * (2 * q + 1) / (n - m) for q in range(n - m)]}
    # puntos de ruptura
    brk = []
    if n >= 2:
        dd = np.polysub(np.polymul(nL, np.polyder(dL)), np.polymul(dL, np.polyder(nL)))
        for r in roots_of(dd):
            if abs(r.imag) < 1e-7:
                x = r.real
                den_v = np.polyval(nL, x)
                if abs(den_v) > 1e-12:
                    k = -np.polyval(dL, x) / den_v
                    if k > 1e-12:
                        brk.append({"s": float(x), "k": float(k)})
    # cruces con el eje jω (cambio de signo del máx. Re)
    cross = []
    mr = np.array([np.max(sets[i].real) for i in good])
    ksg = ks[good]
    for i in np.where(mr[1:] * mr[:-1] < 0)[0][:4]:
        a, b = ksg[i], ksg[i + 1]
        for _ in range(60):
            mid = 0.5 * (a + b)
            if np.max(rts(mid).real) * np.max(rts(a).real) > 0:
                a = mid
            else:
                b = mid
        r = rts(0.5 * (a + b))
        j = r[np.argmin(np.abs(r.real))]
        cross.append({"k": float(0.5 * (a + b)), "w": float(abs(j.imag))})
    allp = np.concatenate([poles, zeros] + [np.array([s0["s"] for s0 in brk])]) if (len(poles) or len(zeros)) else np.array([0j])
    ext = max(1.0, float(np.max(np.abs(allp)))) * 2.2
    view = {"xmin": float(min(-ext, np.min(allp.real) - 0.3 * ext)), "xmax": float(max(ext * 0.5, np.max(allp.real) + 0.3 * ext)),
            "ymax": float(ext)}
    return {"branches": br, "poles": poles, "zeros": zeros, "asymptotes": asym, "breakaway": brk,
            "crossings": cross, "current": rts(1.0), "view": view, "k": np.array(kk)}


# --------------------------------------------------------------- orquestación
def analyze(req: dict) -> dict:
    params = {k: v for k, v in (req.get("params") or {}).items()}
    built = build(req, params)
    allsyms = free_params(built.T) | free_params(built.L_loop) | free_params(built.L_err)
    for nm in sorted(allsyms):
        params.setdefault(nm, 1.0)
    subs = {param_symbol(nm): rational(params[nm]) for nm in allsyms}

    def numeric(e):
        return sp.cancel(sp.together(e.subs(subs)))

    T_num, L_loop, L_err = numeric(built.T), numeric(built.L_loop), numeric(built.L_err)
    nT_p, dT_p = num_den(T_num)
    nL_p, dL_p = num_den(L_loop)
    nE_p, dE_p = num_den(L_err)
    nT, dT, nL, dL, nE, dE = (coeffs(p) for p in (nT_p, dT_p, nL_p, dL_p, nE_p, dE_p))

    poles, zeros = roots_of(dT), roots_of(nT)
    open_poles = roots_of(dL)
    # polos del lazo cerrado equivalente (para error y Nyquist)
    cl_char = np.polyadd(dL, nL) if len(dL) >= len(nL) else np.polyadd(nL, dL)
    cl_poles = roots_of(cl_char)
    closed_for_err = bool(np.all(roots_of(np.polyadd(dE, nE)).real < -TOL)) if len(trim(np.polyadd(dE, nE))) > 1 else True

    pairs, dom = dynamics(poles)
    rh = routh([sp.nsimplify(c, rational=True) for c in dT_p.all_coeffs()])
    stable = bool(len(poles) == 0 or np.all(poles.real < -TOL))
    marginal = bool((not stable) and np.all(poles.real <= TOL))
    verdict = "Asintóticamente estable" if stable else ("Marginalmente estable" if marginal else "Inestable")
    rhp = int(np.sum(poles.real > TOL))

    time_ = time_responses(nT, dT, poles, (req.get("options") or {}).get("t_end"))
    err = steady_state_errors(nE, dE, closed_for_err)
    err = {k: ("∞" if isinstance(v, float) and math.isinf(v) else v) for k, v in err.items()}
    if built.feedback == "none":
        err["basis"] = "unity_closure"
        err["note_basis"] = "Sistema en lazo abierto: constantes de L(s)=G(s); errores referidos al cierre con realimentación unitaria."
    freq = freq_analysis(nL, dL, nT, dT, cl_poles, open_poles)
    rl = root_locus(nL, dL)

    exact_T = sp.factor(T_num)
    dc = None if (len(trim(dT)) and dT[-1] == 0) else float(nT[-1] / dT[-1])
    result = {
        "ok": True, "mode": req.get("mode"), "feedback": built.feedback,
        "parameters": [{"name": n, "value": float(params[n])} for n in sorted(allsyms)],
        "symbolic": {
            "steps": built.steps, "notes": built.notes,
            "T_sym": sp.latex(built.T), "T_sym_factored": sp.latex(sp.factor(built.T)),
            "L_sym": sp.latex(built.L_loop), "summary": built.summary,
        },
        "tf": {
            "T_latex": tf_latex(nT_p, dT_p), "T_factored": sp.latex(exact_T),
            "T_zpk": zpk_latex(nT, dT), "L_latex": tf_latex(nL_p, dL_p), "L_zpk": zpk_latex(nL, dL),
            "num": nT, "den": dT, "dc_gain": dc, "order": int(len(trim(dT)) - 1),
            "relative_degree": int(len(trim(dT)) - len(trim(nT))),
            "L_num": nL, "L_den": dL,
        },
        "poles": [{"re": clean(p.real), "im": clean(p.imag), "text": cplx_text(p)} for p in poles],
        "zeros": [{"re": clean(z.real), "im": clean(z.imag), "text": cplx_text(z)} for z in zeros],
        "poles_L": [{"re": clean(p.real), "im": clean(p.imag)} for p in open_poles],
        "zeros_L": [{"re": clean(z.real), "im": clean(z.imag)} for z in roots_of(nL)],
        "stability": {"verdict": verdict, "stable": stable, "marginal": marginal, "rhp": rhp, "routh": rh},
        "dynamics": {"pairs": pairs, "dominant": dom},
        "time": time_, "errors": err, "freq": freq, "rlocus": rl,
    }
    return clean(result)
