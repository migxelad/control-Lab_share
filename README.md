# Control Lab — Análisis y cátedra de sistemas de control

Aplicación web interactiva: introduces un sistema (función de transferencia, diagrama de bloques,
esquema físico o servomotor DC) y obtiene el análisis dinámico completo con álgebra simbólica exacta.

## Arranque rápido

```bash
./start.sh            # o: python3 run.py      → http://localhost:8000
python3 run.py --dev  # modo desarrollo (Vite :5173 + API con recarga)
```
Requisitos: Python ≥ 3.11 y Node ≥ 18. La primera ejecución crea `.venv`, instala dependencias y compila el frontend.

## Entradas
| Modo | Qué puedes hacer |
|---|---|
| **Función de transferencia** | Numerador/denominador en `s` con parámetros simbólicos (`K`, `a`…), lazo abierto, unitario o con `H(s)`. |
| **Diagrama de bloques** | Lienzo React Flow: entrada, bloques G(s), sumadores (clic en la flecha = signo ±), ramificaciones, salida. Reducción por **regla de Mason** verificada con un sistema lineal simbólico. |
| **Sistema físico** | Traslación (M, K, B, F), rotación (J, B, K, τ) y eléctrico (R, L, C, V, I) por análisis nodal simbólico; eliges entrada, elemento y magnitud de salida (posición, velocidad, tensión, corriente…). |
| **Servomotor DC** | Ra, La, Kt, Kb, J, B → ω/V, θ/V o I/V. |

Los deslizadores del panel lateral recalculan todo en vivo.

## Resultados
T(s) simbólica y factorizada · polos/ceros · Routh–Hurwitz (casos ε y fila de ceros) · ζ, ωn, ωd, τ ·
escalón/impulso/rampa/parábola con %OS, tp, ts(2 %, 5 %), tr(10–90 %, 0–100 %), td ·
tipo, Kp, Kv, Ka, e_ss · mapa de polos y ceros · Bode con GM/PM · Nyquist (Z = N + P) · LGR con asíntotas,
puntos de ruptura y cruces con jω.

**Exportar**: PDF, Markdown (zip con figuras) o LaTeX (zip con figuras) desde la barra superior.

## Estructura
```
backend/app/   symbolic.py (parser seguro) · builders.py (Mason/nodal/motor) · routh.py · analysis.py · report.py · main.py (FastAPI)
backend/tests/ pytest (casos de referencia analíticos)
frontend/src/  React + Tailwind + React Flow + Plotly + KaTeX
run.py / start.sh
```
API: `POST /api/analyze`, `POST /api/report?format=pdf|md|tex` (docs interactivas en `/docs`).

## Convenciones y límites
- Sólo sistemas LTI racionales en `s` (no retardos puros). Funciones impropias: no se simula la respuesta temporal.
- Sin realimentación (“lazo abierto”), las constantes de error se refieren al cierre unitario de G(s).
- Con diagramas de bloques, Bode/Nyquist/LGR usan el lazo equivalente unitario L = T/(1−T).
- Tests: `cd backend && ../.venv/bin/python -m pytest`.

