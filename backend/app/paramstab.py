"""Estabilidad en función de 1 ó 2 parámetros (Routh simbólico, Hurwitz, barrido numérico)."""
from __future__ import annotations
import math
import numpy as np
import sympy as sp
from scipy.optimize import linear_sum_assignment

from .symbolic import s, AnalysisError, param_symbol, rational, clean, free_params
from .builders import build

TOL = 1e-6


# ------------------------------------------------------------- utilidades numéricas
def _max_re(C: np.ndarray) -> np.ndarray:
    """C: (N, n+1) coeficientes (descendente). Devuelve max Re(raíces) por fila (nan si degenerado)."""
    C = np.asarray(C, float)
    N, m = C.shape
    n = m - 1
    out = np.full(N, np.nan)
    if n < 1:
        return np.full(N, -np.inf)
    ok = np.abs(C[:, 0]) > 1e-12 * np.maximum(1, np.abs(C).max(axis=1))
    if n == 1:
        out[ok] = -C[ok, 1] / C[ok, 0]
        return out
    A = np.zeros((ok.sum(), n, n))
    Cn = C[ok] / C[ok, :1]
    A[:, 0, :] = -Cn[:, 1:]
    A[:, np.arange(1, n), np.arange(0, n - 1)] = 1.0
    out[ok] = np.linalg.eigvals(A).real.max(axis=1)
    return out


def _coeff_fn(coeffs, syms):
    f = sp.lambdify(syms, coeffs, modules="numpy")

    def call(*vals):
        shape = np.broadcast(*[np.asarray(v) for v in vals]).shape
        res = f(*vals)
        cols = [np.broadcast_to(np.asarray(c, float), shape).reshape(-1) for c in res]
        return np.stack(cols, axis=1)
    return call


def _status(maxre, scale=1.0):
    if not np.isfinite(maxre):
        return "degenerate"
    t = TOL * max(1.0, scale)
    return "stable" if maxre < -t else ("marginal" if abs(maxre) <= t else "unstable")


# --------------------------------------------------------------- Routh / Hurwitz
def routh_symbolic(coeffs, label_syms):
    c = [sp.together(x) for x in coeffs]
    n = len(c) - 1
    width = (n + 2) // 2
    r0 = c[0::2] + [sp.Integer(0)] * (width - len(c[0::2]))
    r1 = c[1::2] + [sp.Integer(0)] * (width - len(c[1::2]))
    rows = [r0, r1]
    for i in range(2, n + 1):
        p1, p2 = rows[i - 1], rows[i - 2]
        new = []
        for j in range(width):
            a = p2[j + 1] if j + 1 < width else sp.Integer(0)
            b = p1[j + 1] if j + 1 < width else sp.Integer(0)
            if p1[0] == 0:
                new.append(sp.Integer(0))
            else:
                new.append(sp.factor(sp.cancel(sp.together((p1[0] * a - p2[0] * b) / p1[0]))))
        rows.append(new)
    return rows


def hurwitz_minor(coeffs, k):
    """Menor principal de orden k de la matriz de Hurwitz (a0 = coeficiente líder)."""
    n = len(coeffs) - 1
    a = lambda idx: coeffs[idx] if 0 <= idx <= n else sp.Integer(0)  # noqa: E731
    M = sp.Matrix(k, k, lambda i, j: a(2 * (j + 1) - (i + 1)))
    return sp.factor(M.det()) if k > 0 else sp.Integer(1)


# --------------------------------------------------------------------- 1 parámetro
def _real_roots(expr, sym):
    if expr.is_number or not expr.has(sym):
        return []
    p = sp.Poly(sp.expand(expr), sym)
    if p.degree() < 1:
        return []
    try:
        return [r for r in sp.real_roots(p)]
    except Exception:  # noqa: BLE001
        c = [float(x) for x in p.all_coeffs()]
        return [sp.Float(r.real) for r in np.roots(c) if abs(r.imag) < 1e-9]


def _exact(v):
    v = sp.nsimplify(v, rational=False) if not isinstance(v, sp.Basic) else v
    return sp.latex(v), float(sp.N(v))


def _sqrt_latex(w2):
    r = sp.nsimplify(w2, rational=True, tolerance=1e-9)
    return sp.latex(sp.sqrt(r)) if r.q <= 1000 else None


def analyze_1d(coeffs, sym, rng=None):
    """Análisis exacto de estabilidad respecto de un parámetro (polinomio característico en s)."""
    n = len(coeffs) - 1
    f = _coeff_fn(coeffs, [sym])
    cands = []
    for ex in [coeffs[0], coeffs[-1], hurwitz_minor(coeffs, n - 1) if n >= 2 else sp.Integer(1)]:
        cands += _real_roots(ex, sym)
    # únicos y ordenados
    vals = sorted({round(float(sp.N(r, 30)), 12): r for r in cands}.items())
    bps = [v for v, _ in vals]
    exact = {v: r for v, r in vals}

    def eval_at(x):
        C = f(np.array([x]))
        sc = float(np.abs(np.roots(C[0])).max()) if n >= 1 and abs(C[0][0]) > 1e-12 else 1.0
        return _status(float(_max_re(C)[0]), sc), C[0]

    edges = [-math.inf] + bps + [math.inf]
    segs = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        if lo == -math.inf and hi == math.inf:
            x = 1.0
        elif lo == -math.inf:
            x = hi - max(1.0, abs(hi))
        elif hi == math.inf:
            x = lo + max(1.0, abs(lo))
        else:
            x = 0.5 * (lo + hi)
        segs.append({"lo": lo, "hi": hi, "status": eval_at(x)[0]})
    # fusionar contiguos con el mismo estado (cuando el punto frontera no cambia nada)
    marginal = []
    for v in bps:
        st, C = eval_at(v)
        if st == "marginal":
            roots = np.roots(C) if len(C) > 1 else np.array([])
            sc = max(1.0, float(np.abs(roots).max())) if len(roots) else 1.0
            onax = [r for r in roots if abs(r.real) <= TOL * sc]
            w = max((abs(r.imag) for r in onax), default=0.0)
            ex = exact[v]
            lat, num = _exact(ex)
            item = {"value": float(sp.N(ex)), "latex": lat,
                    "kind": "oscilation" if w > 1e-6 * sc else "origin",
                    "w": w, "period": (2 * math.pi / w) if w > 1e-9 else None,
                    "w_latex": None, "poles": [{"re": float(r.real), "im": float(r.imag)} for r in roots]}
            if w > 1e-9:
                item["w_latex"] = _sqrt_latex(sp.Float(w ** 2, 15))
            marginal.append(item)
    merged = []
    for sg in segs:
        if merged and merged[-1]["status"] == sg["status"] and not any(
                abs(m["value"] - merged[-1]["hi"]) < 1e-9 and m["kind"] == "oscilation" for m in marginal):
            # frontera sin efecto (p.ej. sólo toca el eje en un punto aislado de tipo origen) -> mantener separadas si hay marginal
            if not any(abs(m["value"] - merged[-1]["hi"]) < 1e-9 for m in marginal):
                merged[-1]["hi"] = sg["hi"]
                continue
        merged.append(dict(sg))
    for sg in merged:
        for k in ("lo", "hi"):
            if math.isinf(sg[k]):
                sg[k + "_latex"] = r"-\infty" if sg[k] < 0 else r"\infty"
            else:
                sg[k + "_latex"] = _exact(exact.get(min(exact, key=lambda z: abs(z - sg[k])), sp.Float(sg[k])))[0]
    stable = [sg for sg in merged if sg["status"] == "stable"]
    return {"segments": merged, "stable": stable, "marginal": marginal, "breakpoints": bps}


def sweep_1d(coeffs, sym, lo, hi, N=600):
    f = _coeff_fn(coeffs, [sym])
    ks = np.linspace(lo, hi, N)
    C = f(ks)
    mr = _max_re(C)
    n = len(coeffs) - 1
    # trayectoria de polos (seguimiento por asignación)
    traj = [[] for _ in range(n)]
    kk = []
    prev = None
    for i, k in enumerate(ks):
        if not np.isfinite(mr[i]) or n < 1:
            continue
        r = np.roots(C[i])
        if len(r) != n:
            continue
        if prev is not None:
            cost = np.abs(prev[:, None] - r[None, :])
            ri, ci = linear_sum_assignment(cost)
            r = r[ci[np.argsort(ri)]]
        prev = r
        kk.append(k)
        for b in range(n):
            traj[b].append(r[b])
    return {"k": ks, "max_re": mr,
            "traj": [{"re": np.array([z.real for z in b]), "im": np.array([z.imag for z in b])} for b in traj],
            "traj_k": np.array(kk)}


# --------------------------------------------------------------------- 2 parámetros
def region_2d(coeffs, sa, sb, ra, rb, N=110):
    f = _coeff_fn(coeffs, [sa, sb])
    xs = np.linspace(ra[0], ra[1], N)
    ys = np.linspace(rb[0], rb[1], N)
    X, Y = np.meshgrid(xs, ys)
    C = f(X.reshape(-1), Y.reshape(-1))
    z = _max_re(C).reshape(N, N)
    cap = float(np.nanpercentile(np.abs(z), 90)) if np.isfinite(z).any() else 1.0
    cap = max(cap, 1e-6)
    zc = np.clip(z, -cap, cap)
    return {"x": xs, "y": ys, "z": zc, "stable_fraction": float(np.mean(z < -TOL))}


# -------------------------------------------------------------------------- API
def param_stability(req: dict) -> dict:
    study = req.get("study") or {}
    names = list(study.get("params") or [])
    if not names or len(names) > 2:
        raise AnalysisError("Elige 1 ó 2 parámetros para el estudio de estabilidad.")
    params = dict(req.get("params") or {})
    built = build(req, params)
    allsyms = free_params(built.T) | free_params(built.L_loop) | free_params(built.L_err)
    for nm in names:
        if nm not in allsyms:
            raise AnalysisError(f"El parámetro «{nm}» no aparece en el sistema.")
    for nm in allsyms:
        params.setdefault(nm, 1.0)
    study_syms = [param_symbol(n) for n in names]
    fixed = {param_symbol(n): rational(params[n]) for n in allsyms if n not in names}
    T = sp.cancel(sp.together(built.T.subs(fixed)))
    num, den = sp.fraction(T)
    try:
        P = sp.Poly(sp.expand(den), s)
    except sp.PolynomialError as ex:
        raise AnalysisError("El denominador no es polinómico en s.") from ex
    coeffs = [sp.factor(c) for c in P.all_coeffs()]
    n = len(coeffs) - 1
    if n < 1:
        raise AnalysisError("El sistema no tiene dinámica (orden 0).")
    if n > 10:
        raise AnalysisError("Orden demasiado alto para el estudio simbólico (máx. 10).")
    used = [nm for nm, sy in zip(names, study_syms) if any(c.has(sy) for c in coeffs)]
    out = {"ok": True, "params": names, "order": n,
           "char_poly": sp.latex(sp.factor(P.as_expr()) if False else P.as_expr()),
           "coeffs": [sp.latex(c) for c in coeffs],
           "affects": {nm: (nm in used) for nm in names},
           "current": {nm: float(params[nm]) for nm in names}}
    # Routh simbólico
    try:
        rows = routh_symbolic(coeffs, study_syms)
        labels = [f"s^{n - i}" for i in range(len(rows))]
        first = [r[0] for r in rows]
        out["routh"] = {"labels": labels, "rows": [[sp.latex(x) for x in r] for r in rows],
                        "conditions": [sp.latex(x) + r"\;>\;0" for x in first if x.free_symbols],
                        "lead_numeric_positive": bool(coeffs[0].is_number and coeffs[0] > 0)}
        if coeffs[0].is_number and coeffs[0] < 0:
            out["routh"]["note"] = "El coeficiente líder es negativo: todos los signos de la primera columna deben ser negativos (equivalente)."
    except Exception as ex:  # noqa: BLE001
        out["routh"] = None
        out["routh_error"] = str(ex)
    ranges = study.get("ranges") or {}
    cur = [float(params[nm]) for nm in names]
    if len(names) == 1:
        sym = study_syms[0]
        res = analyze_1d(coeffs, sym)
        out["analysis"] = res
        bps = res["breakpoints"]
        lo, hi = ranges.get(names[0]) or (None, None)
        if lo is None or hi is None or lo >= hi:
            pos = [b for b in bps if b > 0]
            hi = max([2.0 * max(pos) if pos else 0.0, 2 * abs(cur[0]), 10.0])
            lo = min(0.0, 2.0 * min(bps)) if bps and min(bps) < 0 else 0.0
        out["sweep"] = sweep_1d(coeffs, sym, float(lo), float(hi))
        out["range"] = [float(lo), float(hi)]
        out["hurwitz"] = sp.latex(hurwitz_minor(coeffs, n - 1)) if n >= 2 else None
    else:
        a, b = study_syms
        ra = ranges.get(names[0]); rb = ranges.get(names[1])
        def dflt(v): return [0.0, max(10.0, 3 * abs(v))]
        ra = ra if ra and ra[0] < ra[1] else dflt(cur[0])
        rb = rb if rb and rb[0] < rb[1] else dflt(cur[1])
        out["region"] = region_2d(coeffs, a, b, ra, rb)
        out["ranges"] = {names[0]: ra, names[1]: rb}
        out["hurwitz"] = sp.latex(hurwitz_minor(coeffs, n - 1)) if n >= 2 else None
        out["last_coeff"] = sp.latex(coeffs[-1])
        # cortes: un parámetro libre con el otro fijo en su valor actual
        sl = {}
        for i, nm in enumerate(names):
            other = names[1 - i]
            cs = [sp.factor(c.subs(study_syms[1 - i], rational(params[other]))) for c in coeffs]
            r1 = analyze_1d(cs, study_syms[i])
            sl[nm] = {"fixed": other, "fixed_value": float(params[other]), "analysis": r1}
        out["slices"] = sl
    return clean(_jsonable(out))


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (sp.Basic,)):
        return float(sp.N(o))
    return o
