import { useRef } from 'react'
import { f } from './Results.jsx'

const UNIT = { Ra: 'Ω', La: 'H', Kt: 'N·m/A', Kb: 'V·s/rad', J: 'kg·m²', B: 'N·m·s/rad' }

export default function ParamPanel({ params, values, onChange, ranges, setRanges, options, setOptions }) {
  const seen = useRef({})
  const rng = (p) => {
    const r = ranges[p.name]
    if (r) return r
    const v = p.value
    const max = v > 0 ? v * 5 : v < 0 ? 10 : 10
    return { min: v < 0 ? -max : 0, max: v < 0 ? 0 : max }
  }
  return (
    <aside className="card flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <h2 className="mb-1 text-sm font-semibold">Parámetros</h2>
        {params.length === 0 && <p className="text-xs text-slate-500 dark:text-slate-400">No hay parámetros simbólicos. Escribe símbolos (K, a, R…) en las funciones o edita los valores en el esquema físico.</p>}
        <div className="space-y-3">
          {params.map((p) => {
            const r = rng(p)
            const v = values[p.name] ?? p.value
            const max = Math.max(r.max, v)
            return (
              <div key={p.name}>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm font-semibold">{p.name}<span className="ml-1 text-xs font-normal text-slate-500">{UNIT[p.name] || ''}</span></label>
                  <input type="number" step="any" className="input !w-28 !py-0.5 text-right" value={v}
                    onChange={(e) => { const x = parseFloat(e.target.value); if (!isNaN(x)) onChange(p.name, x) }} />
                </div>
                <input type="range" min={r.min} max={max} step={(max - r.min) / 500 || 0.01} value={v} onChange={(e) => onChange(p.name, parseFloat(e.target.value))} />
                <div className="flex justify-between text-[10px] text-slate-500"><span>{f(r.min)}</span>
                  <button className="hover:text-sky-500" title="Ampliar rango ×2" onClick={() => setRanges({ ...ranges, [p.name]: { min: r.min, max: max * 2 } })}>rango ×2</button><span>{f(max)}</span></div>
              </div>
            )
          })}
        </div>
      </div>
      <div>
        <h2 className="mb-1 text-sm font-semibold">Opciones de simulación</h2>
        <span className="label">Tiempo final (s) — vacío = automático</span>
        <input className="input" type="number" min="0" step="any" value={options.t_end ?? ''} placeholder="auto"
          onChange={(e) => setOptions({ ...options, t_end: e.target.value === '' ? undefined : parseFloat(e.target.value) })} />
      </div>
    </aside>
  )
}
