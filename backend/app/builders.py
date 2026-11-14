"""Construcción de la función de transferencia simbólica a partir de las 4 entradas:
   tf (G,H), diagrama de bloques (Mason), sistema físico (análisis nodal) y motor DC."""
from __future__ import annotations
import itertools
import re
from dataclasses import dataclass, field
import networkx as nx
import sympy as sp
from .symbolic import s, AnalysisError, parse, param_symbol


@dataclass
class Built:
    T: sp.Expr                      # función de transferencia global Y/R (simbólica en s y parámetros)
    L_loop: sp.Expr                 # ganancia de lazo para Bode/Nyquist/LGR
    L_err: sp.Expr                  # lazo equivalente unitario (constantes de error)
    steps: list = field(default_factory=list)   # [{title, latex:[...], text}]
    feedback: str = "none"          # none | unity | custom | diagram
    G_open: sp.Expr | None = None
    notes: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def L(e) -> str:
    return sp.latex(e)


def _step(title, latex=None, text=None):
    return {"title": title, "latex": latex or [], "text": text or ""}


# --------------------------------------------------------------------------- tf
def apply_feedback(G: sp.Expr, fb: dict, steps: list) -> Built:
    kind = (fb or {}).get("type", "unity")
    G = sp.cancel(G)
    if kind == "none":
        steps.append(_step("Sistema en lazo abierto", [r"T(s)=G(s)=" + L(G)],
                           "Se analiza la planta G(s) tal cual. Las constantes de error se refieren a su cierre con realimentación unitaria."))
        return Built(T=G, L_loop=G, L_err=G, steps=steps, feedback="none", G_open=G)
    if kind == "unity":
        T = sp.cancel(sp.together(G / (1 + G)))
        steps.append(_step("Realimentación unitaria",
                           [r"T(s)=\frac{G(s)}{1+G(s)}", r"T(s)=\frac{G}{1+G}=" + L(T)]))
        return Built(T=T, L_loop=G, L_err=G, steps=steps, feedback="unity", G_open=G)
    H = parse((fb or {}).get("H", "1"))
    T = sp.cancel(sp.together(G / (1 + G * H)))
    Lloop = sp.cancel(G * H)
    Leq = sp.cancel(sp.together(T / (1 - T)))
    steps.append(_step("Realimentación con H(s)",
                       [r"H(s)=" + L(H), r"T(s)=\frac{G(s)}{1+G(s)H(s)}=" + L(T),
                        r"L(s)=G(s)H(s)=" + L(Lloop)],
                       "Lazo equivalente unitario para constantes de error: L_eq = T/(1-T)."))
    return Built(T=T, L_loop=Lloop, L_err=Leq, steps=steps, feedback="custom", G_open=G)


def build_tf(spec: dict, fb: dict) -> Built:
    G = parse(spec.get("G", ""))
    steps = [_step("Función de transferencia introducida", [r"G(s)=" + L(G)])]
    return apply_feedback(G, fb, steps)


# ----------------------------------------------------------------------- blocks
def _combos_nontouching(loops, node_sets):
    """Suma alternada de productos de lazos no tocantes: Σ(-1)^k Π L (k>=1)."""
    total = sp.Integer(0)
    idx = list(range(len(loops)))
    for k in range(1, len(idx) + 1):
        for comb in itertools.combinations(idx, k):
            ok = all(not (node_sets[a] & node_sets[b]) for a, b in itertools.combinations(comb, 2))
            if ok:
                term = sp.Integer(1)
                for i in comb:
                    term *= loops[i]
                total += (-1) ** k * term
    return total


def build_blocks(spec: dict) -> Built:
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    if not nodes:
        raise AnalysisError("El diagrama está vacío.")
    byid = {n["id"]: n for n in nodes}
    ins = [n for n in nodes if n["type"] == "input"]
    outs = [n for n in nodes if n["type"] == "output"]
    if len(ins) != 1 or len(outs) != 1:
        raise AnalysisError("El diagrama necesita exactamente una Entrada R(s) y una Salida Y(s).")
    rin, yout = ins[0]["id"], outs[0]["id"]

    # símbolos / nombres de señales
    gname, sig = {}, {}
    nb = ns = nbr = 0
    for n in nodes:
        t = n["type"]
        if t == "block":
            nb += 1
            nm = (n.get("name") or f"G_{nb}").strip().replace(" ", "")
            gname[n["id"]] = nm
            sig[n["id"]] = f"C_{nb}"
        elif t == "sum":
            ns += 1
            sig[n["id"]] = f"E_{ns}"
        elif t == "branch":
            nbr += 1
            sig[n["id"]] = f"B_{nbr}"
        elif t == "input":
            sig[n["id"]] = "R"
        elif t == "output":
            sig[n["id"]] = "Y"
    bsym = {i: sp.Symbol(nm) for i, nm in gname.items()}
    actual = {}
    for n in nodes:
        if n["type"] == "block":
            actual[bsym[n["id"]]] = parse(n.get("tf") or "1")
    gain = {n["id"]: (bsym[n["id"]] if n["type"] == "block" else sp.Integer(1)) for n in nodes}

    # pesos de arista (signo * ganancia del nodo destino)
    W = {}
    for e in edges:
        u, v = e["source"], e["target"]
        if u not in byid or v not in byid:
            continue
        if byid[v]["type"] == "input":
            raise AnalysisError("La entrada R(s) no puede recibir señales.")
        if byid[u]["type"] == "output":
            raise AnalysisError("La salida Y(s) no puede alimentar otros bloques.")
        sgn = -1 if (e.get("sign") == "-" and byid[v]["type"] == "sum") else 1
        W[(u, v)] = W.get((u, v), 0) + sgn * gain[v]
    for n in nodes:
        if n["type"] in ("block", "branch", "output") and not any(v == n["id"] for (_, v) in W):
            raise AnalysisError(f"El nodo «{gname.get(n['id'], sig[n['id']])}» no tiene entrada conectada.")
    Gr = nx.DiGraph()
    Gr.add_nodes_from(byid)
    for (u, v) in W:
        Gr.add_edge(u, v)
    if not nx.has_path(Gr, rin, yout):
        raise AnalysisError("No existe camino de R(s) a Y(s).")

    # ---- ecuaciones de señal
    eqs = []
    for n in nodes:
        if n["type"] == "input":
            continue
        terms = []
        for e in edges:
            if e["target"] == n["id"] and (e["source"], n["id"]) in W:
                sg = "-" if (e.get("sign") == "-" and n["type"] == "sum") else "+"
                terms.append((sg, sig[e["source"]]))
        rhs = " ".join((f"{sg} " if i or sg == "-" else "") + nm for i, (sg, nm) in enumerate(terms))
        if n["type"] == "block":
            rhs = f"{gname[n['id']]}\\,\\left({rhs}\\right)"
        eqs.append(f"{sig[n['id']]} = {rhs}")

    # ---- Mason
    paths = list(nx.all_simple_paths(Gr, rin, yout))
    loops_n = list(nx.simple_cycles(Gr))
    if len(loops_n) > 14:
        raise AnalysisError("Demasiados lazos para la regla de Mason (>14).")

    def pg(path):
        g = sp.Integer(1)
        for a, b in zip(path, path[1:]):
            g *= W[(a, b)]
        return g

    def lg(cyc):
        g = sp.Integer(1)
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            g *= W[(a, b)]
        return g

    Ls = [lg(c) for c in loops_n]
    Lset = [set(c) for c in loops_n]
    Pk = [pg(p) for p in paths]
    Delta = 1 + _combos_nontouching(Ls, Lset)
    Dk = []
    for p in paths:
        keep = [i for i in range(len(Ls)) if not (Lset[i] & set(p))]
        Dk.append(1 + _combos_nontouching([Ls[i] for i in keep], [Lset[i] for i in keep]))
    T_names = sp.together(sum(P * D for P, D in zip(Pk, Dk)) / Delta)

    # verificación independiente por sistema lineal x = A x + b R
    order = [n["id"] for n in nodes]
    xs = {i: sp.Symbol(f"x_{k}") for k, i in enumerate(order)}
    lin = []
    for i in order:
        if i == rin:
            lin.append(sp.Eq(xs[i], sp.Symbol("R_in")))
        else:
            lin.append(sp.Eq(xs[i], sum((W[(u, v)] * xs[u] for (u, v) in W if v == i), sp.Integer(0))))
    try:
        sol = sp.solve(lin, list(xs.values()), dict=True)[0]
        T_lin = sp.cancel(sol[xs[yout]] / sp.Symbol("R_in"))
    except Exception:  # noqa: BLE001
        T_lin = None
    T_n = sp.cancel(T_names)
    if T_lin is not None and sp.simplify(T_n - T_lin) != 0:
        T_n = T_lin  # confiamos en el sistema lineal si discrepan

    # ---- pasos
    def pretty(path):
        return r"\to ".join(sig[x] for x in path)

    steps = [_step("1. Ecuaciones de señal del diagrama", eqs,
                   "Cada nodo es una señal; los bloques multiplican, los sumadores combinan con su signo.")]
    mason = []
    for k, (p, P, D) in enumerate(zip(paths, Pk, Dk), 1):
        mason.append(rf"P_{{{k}}}\;({pretty(p)})={L(sp.factor(P))},\qquad \Delta_{{{k}}}={L(sp.factor(D))}")
    for k, (c, lv) in enumerate(zip(loops_n, Ls), 1):
        mason.append(rf"L_{{{k}}}\;({pretty(c + [c[0]])})={L(sp.factor(lv))}")
    mason.append(r"\Delta = 1-\sum L_i+\sum L_iL_j-\dots = " + L(sp.factor(sp.expand(Delta))))
    mason.append(r"T(s)=\frac{\sum_k P_k\Delta_k}{\Delta}=" + L(sp.factor(T_n)))
    steps.append(_step("2. Regla de Mason (grafo de flujo de señal)", mason,
                       f"{len(paths)} camino(s) directo(s) y {len(loops_n)} lazo(s)."))
    T = sp.cancel(sp.together(T_n.subs(actual)))
    sub_lines = [rf"{gname[i]}(s)={L(actual[bsym[i]])}" for i in gname]
    steps.append(_step("3. Sustitución de los bloques y simplificación",
                       sub_lines + [r"T(s)=\frac{Y(s)}{R(s)}=" + L(T)]))

    hasloop = len(loops_n) > 0
    if hasloop:
        Leq = sp.cancel(sp.together(T / (1 - T)))
        steps.append(_step("4. Lazo equivalente unitario",
                           [r"L_{eq}(s)=\frac{T}{1-T}=" + L(Leq)],
                           "Se usa para Bode, Nyquist, LGR y constantes de error (E/R = 1-T)."))
        b = Built(T=T, L_loop=Leq, L_err=Leq, steps=steps, feedback="diagram", G_open=None)
    else:
        b = Built(T=T, L_loop=T, L_err=T, steps=steps, feedback="none", G_open=T)
        b.notes.append("El diagrama no contiene lazos: se trata como sistema en lazo abierto.")
    b.summary = {"paths": len(paths), "loops": len(loops_n), "T_blocks": L(sp.factor(T_n))}
    return b


# --------------------------------------------------------------------- physical
_ELEC = {"resistor", "inductor", "capacitor", "vsource", "isource"}
_TYPES = {
    # tipo: (kind, dominio)
    "mass": ("mass", "trans"), "spring": ("spring", "trans"), "damper": ("damper", "trans"),
    "force": ("source", "trans"),
    "inertia": ("mass", "rot"), "tspring": ("spring", "rot"), "rdamper": ("damper", "rot"),
    "torque": ("source", "rot"),
    "resistor": ("res", "elec"), "inductor": ("ind", "elec"), "capacitor": ("cap", "elec"),
    "vsource": ("vsrc", "elec"), "isource": ("source", "elec"),
    "ground": ("ground", "any"),
}


def build_physical(spec: dict, params: dict) -> Built:
    comps = spec.get("components", [])
    wires = spec.get("wires", [])
    if not comps:
        raise AnalysisError("No hay componentes en el esquema.")
    byid = {c["id"]: c for c in comps}
    for c in comps:
        if c["type"] not in _TYPES:
            raise AnalysisError(f"Tipo de componente desconocido: {c['type']}")
    domains = {_TYPES[c["type"]][1] for c in comps} - {"any"}
    if len(domains) > 1:
        raise AnalysisError("No mezcles dominios (traslación/rotación/eléctrico) en el mismo esquema.")
    domain = (domains or {"trans"}).pop()

    # nombres únicos de parámetros
    names, used = {}, set()
    for c in comps:
        base = re.sub(r"\W", "_", (c.get("name") or c["type"]).strip()) or c["type"]
        nm, k = base, 2
        while nm in used:
            nm, k = f"{base}_{k}", k + 1
        used.add(nm)
        names[c["id"]] = nm
        if _TYPES[c["type"]][0] not in ("ground", "source", "vsrc") and nm not in params:
            params[nm] = c.get("value", 1.0)

    # redes por union-find sobre terminales id.a / id.b
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for c in comps:
        find(f"{c['id']}.a")
        if _TYPES[c["type"]][0] not in ("mass", "ground") and not (
                _TYPES[c["type"]][0] == "source" and domain != "elec"):
            find(f"{c['id']}.b")
    for w in wires:
        a, b = w
        if a.split(".")[0] in byid and b.split(".")[0] in byid:
            union(a, b)

    def net(cid, port):
        return find(f"{cid}.{port}")

    gnets = {net(c["id"], "a") for c in comps if c["type"] == "ground"}
    if domain == "elec" and not gnets:
        raise AnalysisError("El circuito eléctrico necesita un nodo de tierra (GND).")
    all_nets = sorted({find(k) for k in list(parent)}, key=str)
    nets = [n for n in all_nets if n not in gnets]
    idx = {n: i for i, n in enumerate(nets)}

    def vidx(n):
        return idx.get(n)  # None = tierra

    inp_id = spec.get("input")
    sources = [c for c in comps if _TYPES[c["type"]][0] in ("source", "vsrc")]
    if not sources:
        raise AnalysisError("Falta una fuente de entrada (fuerza, par o fuente eléctrica).")
    if inp_id not in byid or _TYPES[byid[inp_id]["type"]][0] not in ("source", "vsrc"):
        inp_id = sources[0]["id"]

    nN = len(nets)
    vsrcs = [c for c in comps if _TYPES[c["type"]][0] == "vsrc"]
    size = nN + len(vsrcs)
    Y = sp.zeros(size, size)
    rhs = sp.zeros(size, 1)
    U = sp.Symbol("U")
    sym = {cid: param_symbol(nm) for cid, nm in names.items()}

    def stamp(i, j, y):  # elemento de admitancia entre nodos i,j (None = tierra)
        if i is not None:
            Y[i, i] += y
        if j is not None:
            Y[j, j] += y
        if i is not None and j is not None:
            Y[i, j] -= y
            Y[j, i] -= y

    admit_of = {}
    for c in comps:
        kind = _TYPES[c["type"]][0]
        v = sym[c["id"]]
        na = vidx(net(c["id"], "a"))
        nb = vidx(net(c["id"], "b")) if kind not in ("mass", "ground") and not (kind == "source" and domain != "elec") else None
        if kind == "mass":
            y = v * s ** 2
            stamp(na, None, y)
        elif kind == "spring":
            y = v
            stamp(na, nb, y)
        elif kind == "damper":
            y = v * s
            stamp(na, nb, y)
        elif kind == "res":
            y = 1 / v
            stamp(na, nb, y)
        elif kind == "ind":
            y = 1 / (v * s)
            stamp(na, nb, y)
        elif kind == "cap":
            y = v * s
            stamp(na, nb, y)
        else:
            y = None
        admit_of[c["id"]] = y
        if kind == "source" and c["id"] == inp_id:
            # corriente/fuerza inyectada en el nodo a (y extraída del b en eléctrico)
            if na is not None:
                rhs[na] += U
            if domain == "elec" and nb is not None:
                rhs[nb] -= U
    for k, c in enumerate(vsrcs):
        row = nN + k
        na = vidx(net(c["id"], "a"))
        nb = vidx(net(c["id"], "b"))
        if na is not None:
            Y[na, row] += 1
            Y[row, na] += 1
        if nb is not None:
            Y[nb, row] -= 1
            Y[row, nb] -= 1
        if c["id"] == inp_id:
            rhs[row] = U
    if size == 0:
        raise AnalysisError("El esquema no tiene nodos libres.")
    if Y.det() == 0:
        raise AnalysisError("Sistema singular: revisa conexiones (nodos flotantes o fuentes en bucle).")
    sol = Y.LUsolve(rhs)

    out = spec.get("output") or {}
    oc = out.get("comp")
    if oc not in byid:
        cand = [c for c in comps if _TYPES[c["type"]][0] in ("mass", "cap", "res", "spring")]
        oc = (cand or comps)[0]["id"]
    okind = out.get("kind", "across")
    ckind = _TYPES[byid[oc]["type"]][0]
    va = vidx(net(oc, "a"))
    vb = vidx(net(oc, "b")) if ckind not in ("mass", "ground") else None
    across = (sol[va] if va is not None else 0) - (sol[vb] if vb is not None else 0)
    if okind == "velocity":
        out_expr, olabel = s * across, "velocity"
    elif okind == "through":
        y = admit_of.get(oc)
        if y is None:
            raise AnalysisError("La magnitud «a través» sólo existe para elementos pasivos.")
        out_expr, olabel = y * across, "through"
    else:
        out_expr, olabel = across, "across"
    T = sp.cancel(sp.together(out_expr / U))

    # --- pasos / texto
    lab = {"trans": ("x", "F", "Ecuación de equilibrio de fuerzas en cada masa"),
           "rot": (r"\theta", r"\tau", "Equilibrio de pares en cada inercia"),
           "elec": ("v", "i", "Análisis nodal modificado (KCL en cada nodo)")}[domain]
    unk = [sp.Symbol(f"{lab[0]}_{{{i + 1}}}") for i in range(nN)] + \
          [sp.Symbol(f"i_{{V{k + 1}}}") for k in range(len(vsrcs))]
    src_name = names[inp_id]
    steps = [_step("1. Modelo y ecuaciones nodales", [
        r"\mathbf{Y}(s)\,\mathbf{X}(s)=\mathbf{U}(s)\," + r"\quad\text{(" + lab[2] + ")}",
        sp.latex(Y) + sp.latex(sp.Matrix(unk)) + "=" + sp.latex(rhs),
    ], f"Entrada: {src_name}. Variables: {', '.join(str(u) for u in unk)}. Tierra/referencia excluida.")]
    steps.append(_step("2. Resolución simbólica (LU / Cramer)",
                       [sp.latex(sp.Matrix(unk)) + "=" + sp.latex(sp.simplify(sol))]))
    meas = {"across": "Salida", "velocity": "Velocidad (s·X)", "through": "Magnitud a través"}[olabel]
    steps.append(_step("3. Función de transferencia",
                       [r"G(s)=\frac{\text{" + meas + r"}(s)}{U(s)}=" + L(T)],
                       f"Salida: {names[oc]} ({olabel})."))
    b = Built(T=T, L_loop=T, L_err=T, steps=steps, feedback="none", G_open=T)
    b.summary = {"domain": domain, "nodes": nN}
    return b


# ------------------------------------------------------------------------ motor
def build_motor(spec: dict) -> Built:
    Ra, La, Kt, Kb, J, B = (param_symbol(n) for n in ("Ra", "La", "Kt", "Kb", "J", "B"))
    out = spec.get("output", "speed")
    den = (La * s + Ra) * (J * s + B) + Kt * Kb
    W = sp.cancel(Kt / den)
    G = {"speed": W, "position": W / s, "current": (J * s + B) / den}[out]
    G = sp.cancel(G)
    lbl = {"speed": r"\Omega(s)/V(s)", "position": r"\Theta(s)/V(s)", "current": r"I(s)/V(s)"}[out]
    steps = [
        _step("1. Ecuaciones del servomotor DC", [
            r"V(s)=(R_a+L_a s)I(s)+K_b\,\Omega(s)\quad\text{(malla de armadura)}",
            r"K_t I(s)=(Js+B)\,\Omega(s)\quad\text{(dinámica mecánica)}",
            r"\Theta(s)=\Omega(s)/s"]),
        _step("2. Eliminación de I(s)", [
            r"\frac{\Omega(s)}{V(s)}=\frac{K_t}{(L_a s+R_a)(Js+B)+K_tK_b}",
            r"\frac{I(s)}{V(s)}=\frac{Js+B}{(L_a s+R_a)(Js+B)+K_tK_b}"]),
        _step("3. Función de transferencia seleccionada", [lbl + "=" + L(G)]),
    ]
    b = Built(T=G, L_loop=G, L_err=G, steps=steps, feedback="none", G_open=G)
    return b


def build(req: dict, params: dict) -> Built:
    mode = req.get("mode", "tf")
    fb = req.get("feedback") or {"type": "unity"}
    if mode == "tf":
        return build_tf(req.get("tf") or {}, fb)
    if mode == "blocks":
        return build_blocks(req.get("blocks") or {})
    if mode == "motor":
        b = build_motor(req.get("motor") or {})
        return apply_feedback(b.G_open, fb, b.steps)
    if mode == "physical":
        b = build_physical(req.get("physical") or {}, params)
        return apply_feedback(b.G_open, fb, b.steps)
    raise AnalysisError(f"Modo desconocido: {mode}")
