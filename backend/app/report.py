"""Generación de informes: Markdown / LaTeX (zip con figuras) y PDF."""
from __future__ import annotations
import io
import math
import zipfile
import datetime as dt
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODE = {"tf": "Función de transferencia", "blocks": "Diagrama de bloques",
        "physical": "Sistema físico", "motor": "Servomotor DC"}


def _a(x):
    return np.array([np.nan if v is None else v for v in x], float)


def _fig(w=6.2, h=3.4):
    f, ax = plt.subplots(figsize=(w, h), dpi=130)
    ax.grid(alpha=.3)
    return f, ax


def _png(f):
    b = io.BytesIO()
    f.tight_layout()
    f.savefig(b, format="png")
    plt.close(f)
    return b.getvalue()


def figures(r: dict) -> dict[str, bytes]:
    out = {}
    tm = r.get("time", {})
    if "step" in tm:
        f, ax = _fig()
        ax.plot(_a(tm["step"]["t"]), _a(tm["step"]["y"]), lw=1.8)
        ax.axhline(1, color="gray", ls="--", lw=.8)
        m = tm.get("metrics", {})
        if m.get("tp") is not None:
            ax.plot([m["tp"]], [m["peak_value"]], "ro")
        ax.set(title="Respuesta al escalón unitario", xlabel="t [s]", ylabel="y(t)")
        out["step"] = _png(f)
        f, ax = _fig()
        ax.plot(_a(tm["impulse"]["t"]), _a(tm["impulse"]["y"]), lw=1.8)
        ax.set(title="Respuesta al impulso", xlabel="t [s]", ylabel="y(t)")
        out["impulse"] = _png(f)
        f, ax = _fig()
        ax.plot(_a(tm["ramp"]["t"]), _a(tm["ramp"]["y"]), lw=1.8, label="y(t)")
        ax.plot(_a(tm["ramp"]["t"]), _a(tm["ramp"]["r"]), "--", lw=1, label="r(t)=t")
        ax.legend(); ax.set(title="Respuesta a la rampa", xlabel="t [s]")
        out["ramp"] = _png(f)
    f, ax = _fig(4.6, 4.2)
    ax.plot([p["re"] for p in r["poles"]], [p["im"] for p in r["poles"]], "x", ms=9, mew=2, label="polos")
    if r["zeros"]:
        ax.plot([p["re"] for p in r["zeros"]], [p["im"] for p in r["zeros"]], "o", mfc="none", ms=8, label="ceros")
    ax.axhline(0, color="k", lw=.6); ax.axvline(0, color="k", lw=.6)
    ax.set(title="Mapa de polos y ceros", xlabel="Re", ylabel="Im"); ax.legend()
    out["pz"] = _png(f)
    fr = r.get("freq", {})
    if fr.get("bode"):
        b = fr["bode"]
        f, (a1, a2) = plt.subplots(2, 1, figsize=(6.2, 5), dpi=130, sharex=True)
        a1.semilogx(_a(b["w"]), _a(b["mag_db"])); a1.axhline(0, color="gray", lw=.7)
        a2.semilogx(_a(b["w"]), _a(b["phase"])); a2.axhline(-180, color="gray", lw=.7)
        a1.set(ylabel="|L| [dB]", title="Diagrama de Bode"); a2.set(ylabel="fase [°]", xlabel="ω [rad/s]")
        a1.grid(alpha=.3, which="both"); a2.grid(alpha=.3, which="both")
        out["bode"] = _png(f)
        n = fr["nyquist"]
        f, ax = _fig(4.8, 4.4)
        re_, im_ = _a(n["re"]), _a(n["im"])
        ax.plot(re_, im_, lw=1.5); ax.plot(re_, -im_, "--", lw=1)
        ax.plot([-1], [0], "r+", ms=10, mew=2)
        R = n["view"]; ax.set(xlim=(-R, R), ylim=(-R, R), title="Diagrama de Nyquist", xlabel="Re", ylabel="Im")
        ax.set_aspect("equal")
        out["nyquist"] = _png(f)
    rl = r.get("rlocus", {})
    if rl.get("branches"):
        f, ax = _fig(5.4, 4.4)
        for b in rl["branches"]:
            ax.plot(_a(b["re"]), _a(b["im"]), lw=1.3)
        ax.plot([p["re"] for p in rl["poles"]], [p["im"] for p in rl["poles"]], "kx", ms=8, mew=2)
        ax.plot([p["re"] for p in rl["zeros"]], [p["im"] for p in rl["zeros"]], "ko", mfc="none", ms=8)
        ax.plot([p["re"] for p in rl["current"]], [p["im"] for p in rl["current"]], "rs", ms=6)
        v = rl["view"]; ax.set(xlim=(v["xmin"], v["xmax"]), ylim=(-v["ymax"], v["ymax"]),
                               title="Lugar geométrico de las raíces", xlabel="Re", ylabel="Im")
        ax.axhline(0, color="k", lw=.5); ax.axvline(0, color="k", lw=.5)
        out["rlocus"] = _png(f)
    return out


def g(x, d=5):
    if x is None:
        return "—"
    if isinstance(x, float) and math.isinf(x):
        return "∞"
    return f"{x:.{d}g}" if isinstance(x, (int, float)) else str(x)


def _sections(r):
    """Estructura neutra: lista de (título, [bloques]); bloque = ('p',txt)|('m',latex)|('t',cabecera,filas)|('img',key,caption)."""
    S = []
    tfd, st = r["tf"], r["stability"]
    S.append(("1. Sistema y función de transferencia", [
        ("p", f"Origen del modelo: {MODE.get(r['mode'], r['mode'])}. Parámetros: " +
         (", ".join(f"{p['name']} = {g(p['value'])}" for p in r["parameters"]) or "ninguno") + "."),
        ("m", "T(s)=" + tfd["T_latex"]),
        ("m", "T(s)=" + tfd["T_zpk"]),
        ("p", f"Orden = {tfd['order']}; ganancia estática = {g(tfd['dc_gain'])}.")]))
    steps = []
    for stp in r["symbolic"]["steps"]:
        steps.append(("p", "**" + stp["title"] + "**" + (f" — {stp['text']}" if stp["text"] else "")))
        steps += [("m", l) for l in stp["latex"]]
    S.append(("2. Reducción paso a paso", steps))
    S.append(("3. Polos, ceros y estabilidad", [
        ("t", ["", "Valor"], [["Polos", "; ".join(p["text"] for p in r["poles"]) or "—"],
                              ["Ceros", "; ".join(p["text"] for p in r["zeros"]) or "—"],
                              ["Veredicto", st["verdict"]], ["Polos en el semiplano derecho", str(st["rhp"])]]),
        ("t", ["Fila"] + [f"c{j}" for j in range(len(st["routh"]["rows"][0]))] if st["routh"]["rows"] else ["Fila"],
         [[lb] + [f"${c}$" for c in row] for lb, row in zip(st["routh"]["labels"], st["routh"]["rows"])]),
        ("p", "Routh-Hurwitz: " + (" ".join(st["routh"]["notes"]) or "caso regular.") +
         f" Cambios de signo en la primera columna: {st['routh']['sign_changes']}."),
        ("img", "pz", "Mapa de polos y ceros")]))
    dy = r["dynamics"]
    rows = [[q["kind"], q["pole"] and f"{g(q['pole']['re'])} ± j{g(abs(q['pole']['im']))}" if q["kind"] == "complex" else g(q["pole"]["re"]),
             g(q.get("zeta")), g(q.get("wn")), g(q.get("wd")), g(q.get("tau"))] for q in dy["pairs"]]
    S.append(("4. Parámetros dinámicos", [("t", ["Tipo", "Polo", "ζ", "ωn", "ωd", "τ"], rows)]))
    tm = r["time"]
    blk = []
    if "step" in tm:
        m = tm["metrics"]
        if "overshoot_pct" in m:
            blk.append(("t", ["Métrica", "Valor"], [
                ["Valor final", g(m["final"])], ["Sobreimpulso %OS", g(m["overshoot_pct"])], ["Tiempo pico tp", g(m["tp"])],
                ["ts (2%)", g(m["ts2"])], ["ts (5%)", g(m["ts5"])], ["tr (10–90%)", g(m["tr_10_90"])],
                ["tr (0–100%)", g(m["tr_0_100"])], ["td (50%)", g(m["td"])]]))
        else:
            blk.append(("p", m.get("note", "")))
        blk += [("img", "step", "Escalón"), ("img", "impulse", "Impulso"), ("img", "ramp", "Rampa")]
    else:
        blk.append(("p", tm.get("error", "No disponible.")))
    S.append(("5. Respuesta temporal", blk))
    e = r["errors"]
    S.append(("6. Error en régimen estacionario", [
        ("t", ["Magnitud", "Valor"], [["Tipo de sistema", str(e["type"])], ["Kp", g(e["Kp"])], ["Kv", g(e["Kv"])],
                                       ["Ka", g(e["Ka"])], ["e_ss escalón", g(e["ess_step"])],
                                       ["e_ss rampa", g(e["ess_ramp"])], ["e_ss parábola", g(e["ess_parabola"])]]),
        ("p", e.get("note", "") or e.get("note_basis", ""))]))
    mg = r["freq"]["margins"]
    nq = r["freq"]["nyquist"]
    S.append(("7. Análisis frecuencial", [
        ("t", ["Magnitud", "Valor"], [["Margen de fase PM [°]", g(mg["pm"])], ["ω cruce de ganancia", g(mg["wgc"])],
                                       ["Margen de ganancia GM [dB]", g(mg["gm_db"])], ["ω cruce de fase", g(mg["wpc"])]]),
        ("p", f"Nyquist: P = {nq['P']}, Z = {nq['Z']}, N = Z − P = {nq['N']} giros horarios alrededor de −1."),
        ("img", "bode", "Diagrama de Bode"), ("img", "nyquist", "Diagrama de Nyquist")]))
    rl = r["rlocus"]
    b = [("img", "rlocus", "Lugar de las raíces")]
    if rl.get("crossings"):
        b.insert(0, ("p", "Cruces con el eje imaginario: " + "; ".join(f"K = {g(c['k'])} (ω = {g(c['w'])})" for c in rl["crossings"])))
    if rl.get("breakaway"):
        b.insert(0, ("p", "Puntos de ruptura: " + "; ".join(f"s = {g(c['s'])} (K = {g(c['k'])})" for c in rl["breakaway"])))
    if rl.get("asymptotes"):
        b.insert(0, ("p", f"Asíntotas: centroide σ = {g(rl['asymptotes']['centroid'])}, ángulos {rl['asymptotes']['angles']}°"))
    S.append(("8. Lugar de las raíces", b))
    return S


def markdown(r, figs, prefix="figs/") -> str:
    L = ["# Informe de análisis de sistema de control", f"_Generado: {dt.datetime.now():%Y-%m-%d %H:%M}_", ""]
    for title, blocks in _sections(r):
        L += [f"## {title}", ""]
        for b in blocks:
            if b[0] == "p":
                L += [b[1], ""]
            elif b[0] == "m":
                L += [f"$$ {b[1]} $$", ""]
            elif b[0] == "t":
                L += ["| " + " | ".join(b[1]) + " |", "|" + "---|" * len(b[1])]
                L += ["| " + " | ".join(row) + " |" for row in b[2]] + [""]
            elif b[0] == "img" and b[1] in figs:
                L += [f"![{b[2]}]({prefix}{b[1]}.png)", ""]
    return "\n".join(L)


def _tex_esc(t):
    return (t.replace("\\", " ").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
            .replace("ζ", r"$\zeta$").replace("ω", r"$\omega$").replace("τ", r"$\tau$").replace("°", r"$^\circ$")
            .replace("∞", r"$\infty$").replace("−", "-").replace("±", r"$\pm$").replace("—", "--").replace("ε", r"$\varepsilon$")
            .replace("⇒", r"$\Rightarrow$").replace("⁺", r"$^+$").replace("→", r"$\to$").replace("≥", r"$\geq$"))


def latex(r, figs) -> str:
    import re
    L = [r"\documentclass[11pt,a4paper]{article}", r"\usepackage[utf8]{inputenc}", r"\usepackage[T1]{fontenc}",
         r"\usepackage[spanish]{babel}", r"\usepackage{amsmath,amssymb,graphicx,booktabs,geometry}",
         r"\geometry{margin=2.2cm}", r"\title{Informe de an\'alisis de sistema de control}",
         r"\date{" + dt.datetime.now().strftime("%d/%m/%Y") + "}", r"\begin{document}", r"\maketitle"]
    for title, blocks in _sections(r):
        L.append(r"\section{" + _tex_esc(title.split(". ", 1)[1]) + "}")
        for b in blocks:
            if b[0] == "p":
                txt = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", b[1])
                L.append(_tex_esc(txt).replace(r"\textbf{", r"\textbf{") + "\n")
            elif b[0] == "m":
                L.append(r"\[ " + b[1] + r" \]")
            elif b[0] == "t":
                n = len(b[1])
                L.append(r"\begin{center}\begin{tabular}{" + "l" * n + r"}\toprule")
                L.append(" & ".join(_tex_esc(h) for h in b[1]) + r" \\ \midrule")
                for row in b[2]:
                    L.append(" & ".join(c if c.startswith("$") and c.endswith("$") else _tex_esc(c) for c in row) + r" \\")
                L.append(r"\bottomrule\end{tabular}\end{center}")
            elif b[0] == "img" and b[1] in figs:
                L.append(r"\begin{figure}[h]\centering\includegraphics[width=.8\linewidth]{figs/" + b[1] + r".png}\caption{" + _tex_esc(b[2]) + r"}\end{figure}")
    L.append(r"\end{document}")
    return "\n".join(L)


def zip_report(r, kind: str) -> bytes:
    figs = figures(r)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("informe.md" if kind == "md" else "informe.tex",
                   markdown(r, figs) if kind == "md" else latex(r, figs))
        for k, v in figs.items():
            z.writestr(f"figs/{k}.png", v)
    return buf.getvalue()


def _math_png(tex: str):
    try:
        f = plt.figure(figsize=(0.01, 0.01), dpi=200)
        f.text(0, 0, f"${tex}$", fontsize=11)
        b = io.BytesIO()
        f.savefig(b, format="png", bbox_inches="tight", pad_inches=0.04, transparent=False)
        plt.close(f)
        return b.getvalue()
    except Exception:  # noqa: BLE001
        plt.close("all")
        return None


def pdf(r) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
    import re
    figs = figures(r)
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Informe de análisis de sistema de control")
    E = [Paragraph("Informe de análisis de sistema de control", st["Title"]),
         Paragraph(f"Generado: {dt.datetime.now():%Y-%m-%d %H:%M}", st["Normal"]), Spacer(1, 10)]

    def clean_txt(t):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return t.replace("$", "").replace("\\varepsilon", "ε").replace("\\", "")

    for title, blocks in _sections(r):
        E.append(Paragraph(title, st["Heading2"]))
        for b in blocks:
            if b[0] == "p" and b[1]:
                E.append(Paragraph(clean_txt(b[1]), st["BodyText"]))
            elif b[0] == "m":
                png = _math_png(b[1])
                if png:
                    from PIL import Image as PI
                    im = PI.open(io.BytesIO(png))
                    wpt = min(im.width * 72 / 200 * 1.0, 16.5 * cm)
                    E.append(Image(io.BytesIO(png), width=wpt, height=wpt * im.height / im.width))
                else:
                    E.append(Paragraph("<font face='Courier' size=8>" + clean_txt(b[1]) + "</font>", st["BodyText"]))
                E.append(Spacer(1, 4))
            elif b[0] == "t":
                data = [[Paragraph(clean_txt(str(c)), st["BodyText"]) for c in b[1]]] + \
                       [[Paragraph(clean_txt(str(c)), st["BodyText"]) for c in row] for row in b[2]]
                t = Table(data, repeatRows=1)
                t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb"))]))
                E += [t, Spacer(1, 6)]
            elif b[0] == "img" and b[1] in figs:
                from PIL import Image as PI
                im = PI.open(io.BytesIO(figs[b[1]]))
                wpt = min(im.width * 72 / 130, 14 * cm)
                E.append(KeepTogether([Image(io.BytesIO(figs[b[1]]), width=wpt, height=wpt * im.height / im.width)]))
    doc.build(E)
    return buf.getvalue()
