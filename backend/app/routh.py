"""Criterio de Routh-Hurwitz exacto (SymPy) con casos especiales (ε y polinomio auxiliar)."""
from __future__ import annotations
import sympy as sp

eps = sp.Symbol(r"\varepsilon", positive=True)


def _sign(x) -> int:
    x = sp.simplify(x)
    if x.has(eps):
        x = sp.limit(x, eps, 0, "+")
    if x == 0:
        return 0
    return 1 if x > 0 else -1


def routh(coeffs: list) -> dict:
    """coeffs: coeficientes (Rational) en orden descendente de s."""
    c = [sp.nsimplify(x) for x in coeffs]
    while c and c[0] == 0:
        c.pop(0)
    notes = []
    if len(c) <= 1:
        return {"order": 0, "rows": [], "labels": [], "first_col": [], "sign_changes": 0,
                "notes": ["Polinomio constante: sin polos."], "stable": True, "marginal": False,
                "rhp": 0, "necessary_ok": True}
    if c[0] < 0:
        c = [-x for x in c]
        notes.append("Se multiplicó el polinomio por −1 para que el coeficiente líder sea positivo.")
    n = len(c) - 1
    necessary = all(x > 0 for x in c) or all(x >= 0 for x in c)
    if not all(x > 0 for x in c):
        notes.append("Condición necesaria incumplida: faltan coeficientes o hay coeficientes no positivos ⇒ no es estrictamente estable.")
    width = (n + 2) // 2
    r0 = c[0::2] + [sp.Integer(0)] * (width - len(c[0::2]))
    r1 = c[1::2] + [sp.Integer(0)] * (width - len(c[1::2]))
    rows = [r0, r1]
    special = False
    for i in range(2, n + 1):
        p1, p2 = rows[i - 1], rows[i - 2]
        if all(sp.simplify(x) == 0 for x in p1):
            # fila de ceros -> polinomio auxiliar de la fila anterior (p2)
            order = n - (i - 2)
            aux = [(order - 2 * j, p2[j]) for j in range(width) if p2[j] != 0]
            deriv = {pw: coef * pw for pw, coef in aux}
            p1 = [deriv.get(order - 1 - 2 * j, sp.Integer(0)) for j in range(width)]
            rows[i - 1] = p1
            special = True
            S = sp.Symbol("s")
            Aux = sum(coef * S ** pw for pw, coef in aux)
            notes.append(f"Fila de ceros en s^{n - (i - 1)}: polinomio auxiliar A(s) = {sp.latex(Aux)} "
                         "(raíces simétricas respecto al origen).")
        elif sp.simplify(p1[0]) == 0:
            p1 = [eps] + p1[1:]
            rows[i - 1] = p1
            special = True
            notes.append(f"Cero en la primera columna de la fila s^{n - (i - 1)}: se sustituye por ε → 0⁺.")
        new = []
        for j in range(width):
            a = p2[j + 1] if j + 1 < width else sp.Integer(0)
            b = p1[j + 1] if j + 1 < width else sp.Integer(0)
            new.append(sp.simplify((p1[0] * a - p2[0] * b) / p1[0]) if p1[0] != 0 else sp.Integer(0))
        rows.append(new)
    # último caso: la última fila puede tener primer elemento 0 (aux)
    first = [r[0] for r in rows]
    signs = [_sign(x) for x in first]
    changes = sum(1 for a, b in zip(signs, signs[1:]) if a * b < 0)
    zeros = sum(1 for x in signs if x == 0)
    labels = [f"s^{n - i}" for i in range(len(rows))]
    stable = changes == 0 and zeros == 0 and not special and necessary and all(x > 0 for x in c)
    marginal = (changes == 0) and (special or zeros > 0) and necessary
    if changes == 0 and special:
        notes.append("Sin cambios de signo, pero hay raíces sobre el eje jω ⇒ marginalmente estable (si son simples).")
    sp_rows = [[sp.latex(sp.simplify(x)) for x in r] for r in rows]
    return {
        "order": n, "rows": sp_rows, "labels": labels,
        "first_col": [sp.latex(sp.simplify(x)) for x in first],
        "signs": signs, "sign_changes": changes, "rhp": changes, "notes": notes,
        "stable": bool(stable), "marginal": bool(marginal and not stable),
        "necessary_ok": bool(all(x > 0 for x in c)),
    }
