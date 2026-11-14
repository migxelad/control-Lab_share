"""Parsing seguro de expresiones en s y utilidades de polinomios (SymPy)."""
from __future__ import annotations
import re
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication, convert_xor,
)

s = sp.Symbol("s")


class AnalysisError(Exception):
    """Error de usuario (entrada inválida, sistema mal definido...)."""


_FUNCS = {n: getattr(sp, n) for n in
          ("exp", "sqrt", "sin", "cos", "tan", "log", "ln", "Abs")}
_FUNCS["ln"] = sp.log
_CONSTS = {"pi": sp.pi}
_ALLOWED = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]*$")
_NUM = re.compile(r"(?<![\w.])(?:\d+\.\d*|\.\d+|\d+(?=[eE][+-]?\d))(?:[eE][+-]?\d+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TRANSF = standard_transformations + (implicit_multiplication, convert_xor)


def param_symbol(name: str) -> sp.Symbol:
    return sp.Symbol(name, real=True)


def parse(expr: str, extra_local: dict | None = None) -> sp.Expr:
    """Convierte texto -> expresión SymPy (racional exacta). Variables != s = parámetros."""
    if expr is None or not str(expr).strip():
        raise AnalysisError("Expresión vacía.")
    expr = str(expr).strip()
    if not _ALLOWED.match(expr) or "__" in expr or re.search(r"(?<!\d)\.(?!\d)", expr):
        raise AnalysisError(f"Caracteres no permitidos en la expresión «{expr}».")
    local = dict(_CONSTS)
    local.update(_FUNCS)
    for name in set(_IDENT.findall(expr)):
        if name in local:
            continue
        local[name] = s if name == "s" else param_symbol(name)
    if extra_local:
        local.update(extra_local)
    text = _NUM.sub(lambda m: f"Rational('{m.group(0)}')", expr)
    glob = {"__builtins__": {}, "Rational": sp.Rational, "Integer": sp.Integer,
            "Float": sp.Float, "Symbol": sp.Symbol}
    try:
        e = parse_expr(text, local_dict=local, global_dict=glob,
                       transformations=_TRANSF, evaluate=True)
    except Exception as ex:  # noqa: BLE001
        raise AnalysisError(f"No se pudo interpretar «{expr}»: {ex}") from ex
    return sp.sympify(e)


def rational(v) -> sp.Rational:
    try:
        return sp.Rational(str(float(v))) if not isinstance(v, (int, str)) else sp.Rational(v)
    except Exception as ex:  # noqa: BLE001
        raise AnalysisError(f"Valor numérico inválido: {v!r}") from ex


def free_params(expr: sp.Expr) -> set[str]:
    return {x.name for x in expr.free_symbols if x != s}


def num_den(expr: sp.Expr) -> tuple[sp.Poly, sp.Poly]:
    """Racional en s -> (Poly num, Poly den) con coeficientes exactos, simplificado."""
    expr = sp.cancel(sp.together(expr))
    n, d = sp.fraction(expr)
    try:
        pn = sp.Poly(n, s)
        pd = sp.Poly(d, s)
    except sp.PolynomialError as ex:
        raise AnalysisError("La función no es racional en s (¿exp, retardos?).") from ex
    if pd.is_zero:
        raise AnalysisError("Denominador nulo.")
    return pn, pd


def coeffs(p: sp.Poly) -> np.ndarray:
    return np.array([float(c) for c in p.all_coeffs()], dtype=float)


def fnum(x, digits=6):
    """Representación sympy 'bonita' de un número para LaTeX."""
    x = float(x)
    if abs(x - round(x)) < 1e-12 * max(1, abs(x)):
        return sp.Integer(int(round(x)))
    return sp.Float(float(f"{x:.{digits}g}"), digits)


def poly_expr(p_or_coeffs, digits=6) -> sp.Expr:
    c = coeffs(p_or_coeffs) if isinstance(p_or_coeffs, sp.Poly) else np.asarray(p_or_coeffs, float)
    n = len(c) - 1
    return sum((fnum(ci, digits) * s ** (n - i) for i, ci in enumerate(c)), sp.Integer(0))


def tf_latex(num, den, digits=6) -> str:
    n = sp.latex(poly_expr(num, digits)); d = sp.latex(poly_expr(den, digits))
    dc = coeffs(den) if isinstance(den, sp.Poly) else np.asarray(den, float)
    if len(dc) == 1 and abs(dc[0] - 1) < 1e-12:
        return n
    return rf"\frac{{{n}}}{{{d}}}"


def clean(x):
    """float/complex/ndarray -> JSON-seguro."""
    if isinstance(x, (complex, np.complexfloating)):
        return {"re": clean(x.real), "im": clean(x.imag)}
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return None if (np.isnan(x) or np.isinf(x)) else x
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return [clean(v) for v in x.tolist()]
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x
