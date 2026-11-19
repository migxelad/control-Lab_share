import { useEffect, useMemo, useRef, useState } from 'react'
import Latex from './Latex.jsx'
import Plot, { COLORS } from './Plot.jsx'
import { f, Box, Table } from './ui.jsx'
import { analyzeStability } from '../api.js'

const rangeTex = (name, sg) => {
  const lo = sg.lo_latex, hi = sg.hi_latex
  if (sg.lo == null && sg.hi == null) return `${name}\\in\\mathbb{R}`
  if (sg.lo == null) return `${name}<${hi}`
  if (sg.hi == null) return `${name}>${lo}`
  return `${lo}<${name}<${hi}`
}
const subName = (n) => n.replace(/_(\w+)/, '_{$1}')

function Verdict({ name, an, onApply }) {
  const stable = an.stable
  return (
    <Box title={`Resultado para ${name}`}>
      {stable.length === 0 ? (
        <p className="text-rose-500">No existe ningún valor de <b>{name}</b> que haga el sistema estable (con los demás parámetros en su valor actual).</p>
      ) : (
        <div className="space-y-1">
          <p className="text-sm text-slate-500 dark:text-slate-400">Rango de {name} con el sistema <b className="text-emerald-500">asintóticamente estable</b>:</p>
          {stable.map((sg, i) => (
            <div key={i} className="flex flex-wrap items-center gap-3">
              <Latex block tex={rangeTex(subName(name), sg)} />
              <button className="btn" onClick={() => onApply(name, sg.lo != null && sg.hi != null ? (sg.lo + sg.hi) / 2 : sg.lo != null ? sg.lo + Math.max(1, Math.abs(sg.lo)) : sg.hi - Math.max(1, Math.abs(sg.hi)))}>
                Analizar con {name} = punto medio
              </button>
            </div>
          ))}
        </div>
      )}
      {an.marginal.length > 0 && (
        <div className="mt-3 space-y-2">
          <p className="text-sm font-semibold">Estabilidad marginal</p>
          {an.marginal.map((m, i) => (
            <div key={i} className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-sm">
              <Latex tex={`${subName(name)}=${m.latex}`} />
              {m.kind === 'oscilation' ? (
                <span>
                  polos en <Latex tex={`\\pm j${m.w_latex || f(m.w, 5)}`} /> → oscilaciones mantenidas con ω = <b>{f(m.w, 5)}</b> rad/s (T = {f(m.period, 5)} s, f = {f(m.w / (2 * Math.PI), 4)} Hz)
                </span>
              ) : <span>polo en el origen (s = 0): sin oscilaciones; el sistema deja de ser estable sin oscilar.</span>}
              <button className="btn ml-auto" onClick={() => onApply(name, m.value)}>Analizar con {name} = {f(m.value, 5)}</button>
            </div>
          ))}
        </div>
      )}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-slate-500 dark:text-slate-400">Tramos analizados</summary>
        <Table head={['Tramo', 'Estado']} rows={an.segments.map((sg) => [<Latex tex={rangeTex(subName(name), sg)} />,
          sg.status === 'stable' ? 'Estable' : sg.status === 'unstable' ? 'Inestable' : sg.status])} />
      </details>
    </Box>
  )
}

function RouthBox({ d }) {
  const r = d.routh
  return (
    <Box title="Criterio de Routh–Hurwitz con parámetro simbólico">
      <p className="text-sm text-slate-500 dark:text-slate-400">Polinomio característico (denominador de T(s)):</p>
      <Latex block tex={`P(s)=${d.char_poly}`} />
      {r ? (<>
        <div className="overflow-x-auto"><table className="tbl w-auto min-w-[280px]"><tbody>
          {r.rows.map((row, i) => (
            <tr key={i}><th className="!normal-case"><Latex tex={r.labels[i]} /></th>{row.map((c, j) => <td key={j} className={j === 0 ? 'font-semibold' : ''}><Latex tex={c} /></td>)}</tr>))}
        </tbody></table></div>
        {r.conditions.length > 0 && <>
          <p className="mt-2 text-sm">Condiciones (todos los elementos de la 1ª columna positivos):</p>
          <div className="flex flex-wrap gap-x-6">{r.conditions.map((c, i) => <Latex key={i} tex={c} />)}</div>
        </>}
        {r.note && <p className="text-sm text-amber-500">{r.note}</p>}
      </>) : <p className="text-sm text-amber-500">No se pudo construir el array simbólico: {d.routh_error}</p>}
      {d.hurwitz && <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Determinante de Hurwitz Δ<sub>n−1</sub> (frontera de oscilación): <Latex tex={`${d.hurwitz}=0`} /></p>}
    </Box>
  )
}

function OneParam({ d, theme, onApply }) {
  const name = d.params[0]
  const an = d.analysis, sw = d.sweep
  const shapes = an.stable.map((sg) => ({ type: 'rect', xref: 'x', yref: 'paper', x0: sg.lo ?? sw.k[0], x1: sg.hi ?? sw.k.at(-1), y0: 0, y1: 1, fillcolor: 'rgba(74,222,128,.12)', line: { width: 0 }, layer: 'below' }))
  an.marginal.forEach((m) => shapes.push({ type: 'line', xref: 'x', yref: 'paper', x0: m.value, x1: m.value, y0: 0, y1: 1, line: { color: COLORS.yellow, dash: 'dot', width: 1.5 } }))
  const traj = sw.traj.map((b, i) => ({ x: b.re, y: b.im, mode: 'markers', type: 'scatter', showlegend: false, hovertemplate: `${name}=%{marker.color:.4g}<br>s=%{x:.3f}+j%{y:.3f}<extra></extra>`,
    marker: { size: 4, color: sw.traj_k, colorscale: 'Turbo', showscale: i === 0, colorbar: i === 0 ? { title: name, thickness: 10 } : undefined } }))
  const osc = an.marginal.filter((m) => m.kind === 'oscilation')
  if (osc.length) traj.push({ x: osc.flatMap(() => [0, 0]), y: osc.flatMap((m) => [m.w, -m.w]), mode: 'markers', name: 'cruce jω', marker: { symbol: 'star', size: 13, color: COLORS.yellow, line: { color: '#000', width: 1 } } })
  return (
    <div className="space-y-4">
      <Verdict name={name} an={an} onApply={onApply} />
      {!d.affects[name] && <p className="text-amber-500">El parámetro {name} no aparece en el polinomio característico: no influye en la estabilidad.</p>}
      <div className="grid gap-4 xl:grid-cols-2">
        <Box title={`Parte real máxima de los polos vs ${name}`}>
          <Plot theme={theme} height={360} data={[{ x: sw.k, y: sw.max_re, mode: 'lines', line: { color: COLORS.blue, width: 2.4 }, name: 'máx Re(p)' }]}
            layout={{ xaxis: { title: name }, yaxis: { title: 'máx Re(p)', zeroline: true }, shapes, showlegend: false }} />
          <p className="text-xs text-slate-500 dark:text-slate-400">Zona verde: estable (todos los polos con Re &lt; 0). La línea amarilla marca la estabilidad marginal.</p>
        </Box>
        <Box title={`Trayectoria de los polos al variar ${name}`}>
          <Plot theme={theme} height={360} data={traj} layout={{ xaxis: { title: 'Re(s)' }, yaxis: { title: 'Im(s)', scaleanchor: 'x' },
            shapes: [{ type: 'line', xref: 'x', yref: 'paper', x0: 0, x1: 0, y0: 0, y1: 1, line: { color: '#f87171', width: 1.2 } }] }} />
        </Box>
      </div>
      <RouthBox d={d} />
    </div>
  )
}

function TwoParams({ d, theme, onApply }) {
  const [a, b] = d.params, rg = d.region
  const cur = d.current
  const data = [
    { type: 'heatmap', x: rg.x, y: rg.y, z: rg.z, colorscale: [[0, '#16a34a'], [0.5, '#fafafa'], [1, '#dc2626']], zmid: 0, showscale: true, colorbar: { title: 'máx Re', thickness: 10 }, hovertemplate: `${a}=%{x:.3g}<br>${b}=%{y:.3g}<br>máx Re=%{z:.3g}<extra></extra>`, opacity: 0.85 },
    { type: 'contour', x: rg.x, y: rg.y, z: rg.z, showscale: false, contours: { start: 0, end: 0, size: 1, coloring: 'none' }, line: { color: '#0f172a', width: 2.5 }, hoverinfo: 'skip', name: 'frontera' },
    { type: 'scatter', x: [cur[a]], y: [cur[b]], mode: 'markers', name: 'valor actual', marker: { symbol: 'x', size: 12, color: '#0f172a', line: { width: 2 } } },
  ]
  return (
    <div className="space-y-4">
      <Box title={`Región de estabilidad en el plano (${a}, ${b})`}>
        <Plot theme={theme} height={470} data={data} layout={{ xaxis: { title: a }, yaxis: { title: b }, showlegend: false }} onClick={(p) => p && onApply([a, b], [p.x, p.y])} />
        <p className="text-sm text-slate-500 dark:text-slate-400">Verde: estable; rojo: inestable; el contorno negro es la frontera (estabilidad marginal). <b>Haz clic</b> en cualquier punto para analizar el sistema con esos valores.
          {' '}Fracción estable del recuadro: {f(100 * rg.stable_fraction, 3)} %.</p>
      </Box>
      <div className="grid gap-4 md:grid-cols-2">
        {d.params.map((nm) => {
          const sl = d.slices[nm]
          return (
            <Box key={nm} title={`Rango de ${nm} con ${sl.fixed} = ${f(sl.fixed_value)}`}>
              {sl.analysis.stable.length ? sl.analysis.stable.map((sg, i) => <Latex key={i} block tex={rangeTex(subName(nm), sg)} />) : <p className="text-rose-500">Ningún valor estabiliza el sistema.</p>}
              {sl.analysis.marginal.filter((m) => m.kind === 'oscilation').map((m, i) => (
                <p key={i} className="text-sm">Marginal: <Latex tex={`${subName(nm)}=${m.latex}`} /> (ω = {f(m.w, 5)} rad/s)
                  <button className="btn ml-2 !py-0.5" onClick={() => onApply(nm, m.value)}>aplicar</button></p>))}
            </Box>
          )
        })}
      </div>
      <RouthBox d={d} />
    </div>
  )
}

export default function ParamStability({ r, theme, request, onApply }) {
  const names = r.parameters.map((p) => p.name)
  const [sel, setSel] = useState([])
  const [ranges, setRanges] = useState({})
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const seq = useRef(0)

  useEffect(() => { setSel((s) => { const k = s.filter((n) => names.includes(n)); return k.length ? k : names.slice(0, 1) }) }, [names.join(',')])  // eslint-disable-line

  const toggle = (n) => setSel((s) => s.includes(n) ? s.filter((x) => x !== n) : [...s, n].slice(-2))
  const study = useMemo(() => ({
    params: sel,
    ranges: Object.fromEntries(sel.filter((n) => ranges[n]?.lo !== undefined && ranges[n]?.hi !== undefined && ranges[n].lo !== '' && ranges[n].hi !== '')
      .map((n) => [n, [parseFloat(ranges[n].lo), parseFloat(ranges[n].hi)]])),
  }), [sel, ranges])

  useEffect(() => {
    if (!sel.length) { setData(null); return }
    const id = ++seq.current
    setBusy(true)
    const h = setTimeout(async () => {
      try { const x = await analyzeStability({ ...request, study }); if (id === seq.current) { setData(x); setErr(null) } }
      catch (e) { if (id === seq.current) setErr(e.message) }
      finally { if (id === seq.current) setBusy(false) }
    }, 400)
    return () => clearTimeout(h)
  }, [request, study, sel.length])

  const apply = (nm, v) => {
    if (Array.isArray(nm)) nm.forEach((n, i) => onApply(n, +v[i].toPrecision(6)))
    else onApply(nm, +Number(v).toPrecision(8))
  }

  if (!names.length) return <Box><p>Este sistema no tiene parámetros simbólicos. Escribe símbolos (K, a, R…) en las funciones de transferencia o bloques, o usa los valores del esquema físico, para estudiar la estabilidad en función de ellos.</p></Box>
  return (
    <div className="space-y-4">
      <Box title="Parámetros a estudiar (1 ó 2)">
        <div className="flex flex-wrap items-end gap-3">
          {names.map((n) => (
            <label key={n} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${sel.includes(n) ? 'border-sky-500 bg-sky-500/10' : 'border-slate-300 dark:border-slate-700'}`}>
              <input type="checkbox" checked={sel.includes(n)} onChange={() => toggle(n)} />{n}
            </label>
          ))}
          {sel.map((n) => (
            <div key={n} className="flex items-end gap-1 text-sm">
              <span className="pb-2 text-xs text-slate-500">Rango {n}:</span>
              <input className="input !w-20" placeholder="auto" value={ranges[n]?.lo ?? ''} onChange={(e) => setRanges({ ...ranges, [n]: { ...ranges[n], lo: e.target.value, hi: ranges[n]?.hi ?? '' } })} />
              <input className="input !w-20" placeholder="auto" value={ranges[n]?.hi ?? ''} onChange={(e) => setRanges({ ...ranges, [n]: { ...ranges[n], hi: e.target.value, lo: ranges[n]?.lo ?? '' } })} />
            </div>
          ))}
          {busy && <span className="pb-2 text-xs text-slate-500">calculando…</span>}
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Se estudia el polinomio característico de T(s) variando los parámetros elegidos; el resto se mantiene en el valor del panel lateral. Con un parámetro el rango se obtiene de forma exacta (Routh/Hurwitz); con dos se calcula la región.</p>
      </Box>
      {err && <p className="rounded-xl border border-rose-500/50 bg-rose-500/10 p-3 text-sm text-rose-500">{err}</p>}
      {data && (data.params.length === 1 ? <OneParam d={data} theme={theme} onApply={apply} /> : <TwoParams d={data} theme={theme} onApply={apply} />)}
    </div>
  )
}
