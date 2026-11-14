import { useMemo, useState } from 'react'
import Latex from './Latex.jsx'
import Plot, { COLORS } from './Plot.jsx'

export const f = (x, d = 4) => {
  if (x == null) return '—'
  if (typeof x === 'string') return x
  if (!isFinite(x)) return '∞'
  if (x === 0) return '0'
  const a = Math.abs(x)
  return a >= 1e5 || a < 1e-3 ? x.toExponential(d - 1) : String(+x.toPrecision(d))
}
const inf = (x) => (x == null ? '∞' : f(x))

function Tile({ label, value, sub, tone }) {
  const c = tone === 'good' ? 'text-emerald-500' : tone === 'bad' ? 'text-rose-500' : tone === 'warn' ? 'text-amber-500' : ''
  return (
    <div className="card p-3">
      <div className="label !mb-0.5">{label}</div>
      <div className={`text-xl font-semibold ${c}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 dark:text-slate-400">{sub}</div>}
    </div>
  )
}
const Box = ({ title, children, className = '' }) => (
  <section className={`card p-4 ${className}`}>{title && <h3 className="mb-2 text-sm font-semibold">{title}</h3>}{children}</section>
)
function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto"><table className="tbl">
      <thead><tr>{head.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

/* ------------------------------------------------------------------ Resumen */
function Summary({ r }) {
  const m = r.time?.metrics || {}
  const st = r.stability, dom = r.dynamics.dominant, mg = r.freq.margins, e = r.errors
  const tone = st.stable ? 'good' : st.marginal ? 'warn' : 'bad'
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label="Estabilidad" value={st.verdict} tone={tone} sub={`${st.rhp} polo(s) en el SPD`} />
        <Tile label="Orden / tipo" value={`${r.tf.order} / ${e.type}`} sub={`Ganancia estática ${f(r.tf.dc_gain)}`} />
        <Tile label="Sobreimpulso" value={m.overshoot_pct != null ? `${f(m.overshoot_pct)} %` : '—'} sub={m.tp != null ? `tp = ${f(m.tp)} s` : ''} />
        <Tile label="ts (2%)" value={m.ts2 != null ? `${f(m.ts2)} s` : '—'} sub={m.ts5 != null ? `ts (5%) = ${f(m.ts5)} s` : ''} />
        <Tile label="Margen de fase" value={mg.pm != null ? `${f(mg.pm, 3)}°` : '∞'} sub={mg.wgc ? `ωgc = ${f(mg.wgc)} rad/s` : ''} />
        <Tile label="Margen de ganancia" value={mg.gm_db != null ? `${f(mg.gm_db, 3)} dB` : '∞'} sub={mg.wpc ? `ωpc = ${f(mg.wpc)} rad/s` : ''} />
        <Tile label="ζ / ωn dominantes" value={dom ? `${f(dom.zeta)} / ${f(dom.wn)}` : '—'} sub={dom?.tau ? `τ = ${f(dom.tau)} s` : ''} />
        <Tile label="e_ss escalón / rampa" value={`${f(e.ess_step)} / ${f(e.ess_ramp)}`} tone={e.valid ? undefined : 'bad'} sub={e.valid ? '' : 'lazo inestable'} />
      </div>
      <Box title="Función de transferencia T(s) = Y(s)/R(s)">
        <Latex block tex={'T(s)=' + r.tf.T_latex} />
        <Latex block tex={'T(s)=' + r.tf.T_zpk} />
        <p className="text-xs text-slate-500 dark:text-slate-400">Forma factorizada racional (SymPy): <Latex tex={r.tf.T_factored} /></p>
      </Box>
      {r.feedback !== 'diagram' && r.symbolic.notes.length > 0 && <p className="text-sm text-amber-500">{r.symbolic.notes.join(' ')}</p>}
    </div>
  )
}

/* ---------------------------------------------------------------- Reducción */
function Reduction({ r }) {
  const s = r.symbolic
  return (
    <div className="space-y-3">
      {s.steps.map((st, i) => (
        <Box key={i} title={st.title}>
          {st.text && <p className="mb-1 text-sm text-slate-500 dark:text-slate-400">{st.text}</p>}
          {st.latex.map((l, j) => <Latex key={j} block tex={l} />)}
        </Box>
      ))}
      <Box title="Resultado simbólico (en función de los parámetros)">
        <Latex block tex={'T(s)=' + s.T_sym} />
        <Latex block tex={'T(s)=' + s.T_sym_factored} />
        {s.notes.map((n, i) => <p key={i} className="text-sm text-amber-500">{n}</p>)}
      </Box>
    </div>
  )
}

/* ----------------------------------------------------------------- Temporal */
function stepFigure(t) {
  const m = t.metrics || {}
  const tr = [{ x: t.step.t, y: t.step.y, name: 'y(t)', mode: 'lines', line: { color: COLORS.blue, width: 2.4 } }]
  const shapes = [], ann = []
  if (m.final != null && isFinite(m.final)) {
    shapes.push({ type: 'line', x0: 0, x1: t.step.t.at(-1), y0: m.final, y1: m.final, line: { dash: 'dash', color: '#94a3b8', width: 1 } })
    shapes.push({ type: 'rect', x0: 0, x1: t.step.t.at(-1), y0: m.final * 0.98, y1: m.final * 1.02, fillcolor: 'rgba(148,163,184,.13)', line: { width: 0 } })
  }
  if (m.tp != null) tr.push({ x: [m.tp], y: [m.peak_value], mode: 'markers+text', text: [`Mp ${f(m.overshoot_pct, 3)}%`], textposition: 'top right', marker: { color: COLORS.red, size: 9 }, name: 'pico', hovertemplate: `tp=${f(m.tp)} s` })
  const mark = (x, lbl, c) => { if (x != null) { shapes.push({ type: 'line', x0: x, x1: x, y0: 0, y1: m.final ?? 1, line: { dash: 'dot', color: c, width: 1.2 } }); ann.push({ x, y: 0, text: lbl, showarrow: false, yanchor: 'bottom', textangle: -90, font: { color: c, size: 10 } }) } }
  mark(m.ts2, 'ts2%', COLORS.orange); mark(m.tr_10_90 != null ? m.t90 : null, 't90', COLORS.green); mark(m.td, 'td', COLORS.violet)
  return { data: tr, layout: { title: 'Respuesta al escalón unitario', xaxis: { title: 't [s]' }, yaxis: { title: 'y(t)' }, shapes, annotations: ann, showlegend: false } }
}

function Temporal({ r, theme }) {
  const t = r.time
  const sf = useMemo(() => (t.error ? null : stepFigure(t)), [t])
  if (t.error) return <Box><p className="text-amber-500">{t.error}</p></Box>
  const m = t.metrics || {}
  const line = (o, name, c) => ({ x: o.t, y: o.y, name, mode: 'lines', line: { color: c, width: 2.2 } })
  return (
    <div className="space-y-4">
      {t.diverges && <p className="text-rose-500">La respuesta diverge (sistema inestable): se muestra hasta el horizonte indicado.</p>}
      <div className="grid gap-4 xl:grid-cols-2">
        <Box><Plot theme={theme} data={sf.data} layout={sf.layout} /></Box>
        <Box><Plot theme={theme} data={[line(t.impulse, 'h(t)', COLORS.orange)]} layout={{ title: 'Respuesta al impulso', xaxis: { title: 't [s]' }, yaxis: { title: 'y(t)' }, showlegend: false }} /></Box>
        <Box><Plot theme={theme} data={[line(t.ramp, 'y(t)', COLORS.blue), { x: t.ramp.t, y: t.ramp.r, name: 'r(t)=t', mode: 'lines', line: { dash: 'dash', color: '#94a3b8' } }]} layout={{ title: 'Respuesta a la rampa', xaxis: { title: 't [s]' } }} /></Box>
        <Box><Plot theme={theme} data={[line(t.parabola, 'y(t)', COLORS.green), { x: t.parabola.t, y: t.parabola.r, name: 'r(t)=t²/2', mode: 'lines', line: { dash: 'dash', color: '#94a3b8' } }]} layout={{ title: 'Respuesta a la parábola', xaxis: { title: 't [s]' } }} /></Box>
      </div>
      <Box title="Métricas de la respuesta al escalón">
        {m.overshoot_pct != null ? (
          <Table head={['Métrica', 'Valor', 'Definición']} rows={[
            ['Valor final', f(m.final), 'y(∞) = T(0)'],
            ['Sobreimpulso %OS (Mp)', `${f(m.overshoot_pct)} %`, '(ymax − y∞)/y∞ · 100'],
            ['Tiempo pico tp', m.tp != null ? `${f(m.tp)} s` : 'sin sobreimpulso', 'instante del primer máximo'],
            ['Asentamiento ts (2%)', m.ts2 != null ? `${f(m.ts2)} s` : 'fuera del horizonte', '|y − y∞| ≤ 2 %'],
            ['Asentamiento ts (5%)', m.ts5 != null ? `${f(m.ts5)} s` : 'fuera del horizonte', '|y − y∞| ≤ 5 %'],
            ['Subida tr (10–90 %)', m.tr_10_90 != null ? `${f(m.tr_10_90)} s` : '—', 't(0.9y∞) − t(0.1y∞)'],
            ['Subida tr (0–100 %)', m.tr_0_100 != null ? `${f(m.tr_0_100)} s` : '— (no alcanza y∞)', 'primer cruce de y∞'],
            ['Retardo td', m.td != null ? `${f(m.td)} s` : '—', 'tiempo en alcanzar 50 % de y∞'],
          ]} />
        ) : <p className="text-sm text-amber-500">{m.note}</p>}
      </Box>
    </div>
  )
}

/* -------------------------------------------------- Estabilidad y dinámica */
function Stability({ r, theme }) {
  const st = r.stability, ro = st.routh
  const P = r.poles, Z = r.zeros
  const ext = Math.max(1, ...P.concat(Z).flatMap((p) => [Math.abs(p.re), Math.abs(p.im)])) * 1.4
  const data = [
    { x: P.map((p) => p.re), y: P.map((p) => p.im), mode: 'markers', name: 'polos', marker: { symbol: 'x', size: 12, color: COLORS.red, line: { width: 2.5 } } },
    { x: Z.map((p) => p.re), y: Z.map((p) => p.im), mode: 'markers', name: 'ceros', marker: { symbol: 'circle-open', size: 11, color: COLORS.blue, line: { width: 2.5 } } },
  ]
  const dom = r.dynamics.dominant
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Box title="Mapa de polos y ceros (plano s)">
        <Plot theme={theme} height={380} data={data} layout={{ xaxis: { title: 'Re(s)', range: [-ext, ext * 0.5], zeroline: true }, yaxis: { title: 'Im(s)', range: [-ext, ext], scaleanchor: 'x', zeroline: true },
          shapes: [{ type: 'rect', x0: 0, x1: ext, y0: -ext, y1: ext, fillcolor: 'rgba(248,113,113,.08)', line: { width: 0 }, layer: 'below' }] }} />
      </Box>
      <div className="space-y-4">
        <Box title="Polos y ceros exactos">
          <Table head={['', 'Valores']} rows={[
            ['Polos pᵢ', P.length ? P.map((p) => p.text).join('   ·   ') : '—'],
            ['Ceros zᵢ', Z.length ? Z.map((p) => p.text).join('   ·   ') : '—'],
          ]} />
          <Latex block tex={'T(s)=' + r.tf.T_zpk} />
        </Box>
        <Box title="Parámetros dinámicos">
          <Table head={['Tipo', 'Polo', 'ζ', 'ωn', 'ωd', 'τ']} rows={r.dynamics.pairs.map((q) => [
            q.kind === 'complex' ? 'par complejo' : 'real',
            q.kind === 'complex' ? `${f(q.pole.re)} ± j${f(Math.abs(q.pole.im))}` : f(q.pole.re),
            f(q.zeta), f(q.wn), f(q.wd), f(q.tau)])} />
          {dom && <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Dominante (más cercano al eje jω): {dom.kind === 'complex'
            ? <>ζ = {f(dom.zeta)}, ωn = {f(dom.wn)} rad/s, ωd = {f(dom.wd)} rad/s, τ = 1/σ = {f(dom.tau)} s</> : <>polo real, τ = {f(dom.tau)} s</>}</p>}
        </Box>
      </div>
      <Box title="Criterio de Routh–Hurwitz" className="xl:col-span-2">
        <p className="mb-2 text-sm">Polinomio característico de T(s), orden {ro.order}. Veredicto: <b className={st.stable ? 'text-emerald-500' : st.marginal ? 'text-amber-500' : 'text-rose-500'}>{st.verdict}</b>
          {' '}— cambios de signo en la 1ª columna: <b>{ro.sign_changes}</b> (= polos en el semiplano derecho).</p>
        {ro.rows.length > 0 && (
          <div className="overflow-x-auto"><table className="tbl w-auto min-w-[320px]">
            <tbody>{ro.rows.map((row, i) => (
              <tr key={i}><th className="!normal-case">{<Latex tex={ro.labels[i]} />}</th>{row.map((c, j) => <td key={j} className={j === 0 ? 'font-semibold' : ''}><Latex tex={c} /></td>)}</tr>
            ))}</tbody></table></div>)}
        {ro.notes.map((n, i) => <p key={i} className="mt-1 text-sm text-slate-500 dark:text-slate-400">• {n}</p>)}
      </Box>
    </div>
  )
}

/* -------------------------------------------------------------------- Error */
function Errors({ r }) {
  const e = r.errors
  return (
    <div className="space-y-4">
      {!e.valid && <p className="text-rose-500">{e.note}</p>}
      {e.note_basis && <p className="text-sm text-amber-500">{e.note_basis}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <Box title="Tipo y constantes de error">
          <Table head={['Magnitud', 'Valor', 'Definición']} rows={[
            ['Tipo de sistema', e.type, 'nº de integradores en L(s)'],
            ['Kp', f(e.Kp), 'lim L(s), s→0'], ['Kv', f(e.Kv), 'lim s·L(s)'], ['Ka', f(e.Ka), 'lim s²·L(s)']]} />
          <Latex block tex={'L(s)=' + r.tf.L_latex} />
        </Box>
        <Box title="Error en estado estable">
          <Table head={['Entrada', 'e_ss', 'Fórmula']} rows={[
            ['Escalón unitario', f(e.ess_step), '1/(1+Kp)'], ['Rampa unitaria', f(e.ess_ramp), '1/Kv'], ['Parábola (t²/2)', f(e.ess_parabola), '1/Ka']]} />
        </Box>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------- Frecuencial */
function Frequency({ r, theme }) {
  const b = r.freq.bode, mg = r.freq.margins, n = r.freq.nyquist, cl = r.freq.closed_loop || {}
  const w0 = b.w[0], w1 = b.w.at(-1)
  const magTr = [{ x: b.w, y: b.mag_db, mode: 'lines', name: '|L| dB', line: { color: COLORS.blue, width: 2.2 }, xaxis: 'x', yaxis: 'y' }]
  const phTr = [{ x: b.w, y: b.phase, mode: 'lines', name: 'fase', line: { color: COLORS.orange, width: 2.2 }, xaxis: 'x2', yaxis: 'y2' }]
  if (mg.wgc) phTr.push({ x: [mg.wgc], y: [mg.pm - 180], mode: 'markers', marker: { color: COLORS.green, size: 9 }, name: `PM = ${f(mg.pm, 3)}°`, xaxis: 'x2', yaxis: 'y2' })
  if (mg.wgc) magTr.push({ x: [mg.wgc], y: [0], mode: 'markers', marker: { color: COLORS.green, size: 9 }, name: 'ωgc', xaxis: 'x', yaxis: 'y' })
  if (mg.wpc) magTr.push({ x: [mg.wpc], y: [-mg.gm_db], mode: 'markers', marker: { color: COLORS.red, size: 9 }, name: `GM = ${f(mg.gm_db, 3)} dB`, xaxis: 'x', yaxis: 'y' })
  const lay = {
    grid: undefined, showlegend: true, legend: { orientation: 'h', y: -0.12 },
    xaxis: { type: 'log', range: [Math.log10(w0), Math.log10(w1)], showticklabels: false, anchor: 'y' }, yaxis: { title: 'Magnitud [dB]', domain: [0.56, 1] },
    xaxis2: { type: 'log', range: [Math.log10(w0), Math.log10(w1)], title: 'ω [rad/s]', anchor: 'y2' }, yaxis2: { title: 'Fase [°]', domain: [0, 0.44] },
    shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 0, y1: 0, line: { dash: 'dash', color: '#94a3b8', width: 1 } },
      { type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y2', y0: -180, y1: -180, line: { dash: 'dash', color: '#94a3b8', width: 1 } }],
    margin: { l: 60, r: 18, t: 20, b: 40 },
  }
  const R = n.view
  const nyq = [
    { x: n.re, y: n.im, mode: 'lines', name: 'ω > 0', line: { color: COLORS.blue, width: 2.2 } },
    { x: n.re, y: n.im.map((v) => (v == null ? null : -v)), mode: 'lines', name: 'ω < 0', line: { color: COLORS.blue, width: 1.5, dash: 'dash' } },
    { x: [-1], y: [0], mode: 'markers', name: '−1', marker: { symbol: 'cross', size: 11, color: COLORS.red, line: { width: 2.5 } } },
  ]
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <Tile label="Margen de fase PM" value={mg.pm != null ? `${f(mg.pm, 3)}°` : '∞'} sub={mg.wgc ? `en ωgc = ${f(mg.wgc)} rad/s` : 'no cruza 0 dB'} tone={mg.pm == null ? undefined : mg.pm > 0 ? 'good' : 'bad'} />
        <Tile label="Margen de ganancia GM" value={mg.gm_db != null ? `${f(mg.gm_db, 3)} dB` : '∞'} sub={mg.wpc ? `en ωpc = ${f(mg.wpc)} rad/s` : 'no cruza −180°'} tone={mg.gm_db == null ? undefined : mg.gm_db > 0 ? 'good' : 'bad'} />
        <Tile label="Ancho de banda (−3 dB) de T" value={cl.bandwidth ? `${f(cl.bandwidth)} rad/s` : '—'} />
        <Tile label="Pico de resonancia Mr" value={cl.wr ? `${f(cl.Mr_db, 3)} dB` : '0 dB'} sub={cl.wr ? `en ωr = ${f(cl.wr)} rad/s` : ''} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Box title="Diagrama de Bode de L(s)"><Plot theme={theme} height={500} data={[...magTr, ...phTr]} layout={lay} /></Box>
        <Box title="Diagrama de Nyquist de L(s)">
          <Plot theme={theme} height={500} data={nyq} layout={{ xaxis: { title: 'Re', range: [-R, R] }, yaxis: { title: 'Im', range: [-R, R], scaleanchor: 'x' } }} />
          <p className="text-sm text-slate-500 dark:text-slate-400">Criterio de Nyquist: Z = N + P ⇒ con P = {n.P} polo(s) de L en el SPD y Z = {n.Z} polo(s) de lazo cerrado en el SPD, N = {n.N} (giros horarios en torno a −1).
            {n.poles_on_axis > 0 && ' L tiene polos sobre jω: el contorno se indenta; el trazo muestra ω > 0 y su espejo.'}</p>
        </Box>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------------- LGR */
function RootLocus({ r, theme }) {
  const rl = r.rlocus
  if (rl.error) return <Box><p className="text-amber-500">{rl.error}</p></Box>
  const v = rl.view
  const pal = [COLORS.blue, COLORS.orange, COLORS.green, COLORS.violet, COLORS.yellow, '#f472b6', '#2dd4bf', '#a3e635']
  const data = rl.branches.map((b, i) => ({ x: b.re, y: b.im, mode: 'lines', line: { color: pal[i % pal.length], width: 2 }, name: `rama ${i + 1}`, showlegend: false, hoverinfo: 'x+y' }))
  data.push({ x: rl.poles.map((p) => p.re), y: rl.poles.map((p) => p.im), mode: 'markers', name: 'polos de L', marker: { symbol: 'x', size: 11, color: '#e2e8f0', line: { width: 2.5, color: '#e2e8f0' } } })
  if (rl.zeros.length) data.push({ x: rl.zeros.map((p) => p.re), y: rl.zeros.map((p) => p.im), mode: 'markers', name: 'ceros de L', marker: { symbol: 'circle-open', size: 11, color: '#e2e8f0', line: { width: 2.5 } } })
  data.push({ x: rl.current.map((p) => p.re), y: rl.current.map((p) => p.im), mode: 'markers', name: 'polos actuales (K=1)', marker: { symbol: 'square', size: 9, color: COLORS.red } })
  if (rl.breakaway.length) data.push({ x: rl.breakaway.map((b) => b.s), y: rl.breakaway.map(() => 0), mode: 'markers', name: 'ruptura', marker: { symbol: 'diamond', size: 9, color: COLORS.green }, text: rl.breakaway.map((b) => `K=${f(b.k)}`), hovertemplate: 's=%{x}<br>%{text}' })
  if (rl.crossings.length) data.push({ x: rl.crossings.flatMap((c) => [0, 0]), y: rl.crossings.flatMap((c) => [c.w, -c.w]), mode: 'markers', name: 'cruce jω', marker: { symbol: 'star', size: 11, color: COLORS.yellow }, text: rl.crossings.flatMap((c) => [`K=${f(c.k)}`, `K=${f(c.k)}`]), hovertemplate: 'ω=%{y}<br>%{text}' })
  const shapes = []
  if (rl.asymptotes) {
    const L = Math.max(v.ymax, Math.abs(v.xmin)) * 2
    for (const a of rl.asymptotes.angles) { const rad = a * Math.PI / 180; shapes.push({ type: 'line', x0: rl.asymptotes.centroid, y0: 0, x1: rl.asymptotes.centroid + L * Math.cos(rad), y1: L * Math.sin(rad), line: { dash: 'dot', color: '#64748b', width: 1 } }) }
  }
  return (
    <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
      <Box title="Lugar geométrico de las raíces  1 + K·L(s) = 0">
        <Plot theme={theme} height={520} data={data} layout={{ xaxis: { title: 'Re(s)', range: [v.xmin, v.xmax] }, yaxis: { title: 'Im(s)', range: [-v.ymax, v.ymax] }, shapes }} />
      </Box>
      <Box title="Propiedades del LGR">
        <Table head={['Propiedad', 'Valor']} rows={[
          ['Ramas', rl.branches.length],
          ['Asíntotas', rl.asymptotes ? `${rl.asymptotes.angles.length} a ${rl.asymptotes.angles.map((a) => f(a, 4) + '°').join(', ')}` : 'ninguna'],
          ['Centroide σ', rl.asymptotes ? f(rl.asymptotes.centroid) : '—'],
          ['Puntos de ruptura', rl.breakaway.length ? rl.breakaway.map((b) => `s=${f(b.s)} (K=${f(b.k)})`).join('; ') : 'ninguno'],
          ['Cruces con jω', rl.crossings.length ? rl.crossings.map((c) => `ω=${f(c.w)} (K=${f(c.k)})`).join('; ') : 'ninguno'],
          ['Ganancia crítica Kc', rl.crossings.length ? f(Math.min(...rl.crossings.map((c) => c.k))) : '∞'],
        ]} />
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Los cuadrados rojos son los polos de lazo cerrado con la ganancia actual (K = 1 sobre L(s)).</p>
      </Box>
    </div>
  )
}

export const TABS = [
  ['summary', 'Resumen', Summary], ['reduction', 'Reducción', Reduction], ['time', 'Respuesta temporal', Temporal],
  ['stability', 'Polos, estabilidad', Stability], ['errors', 'Error estacionario', Errors], ['freq', 'Frecuencia', Frequency], ['rl', 'Lugar de las raíces', RootLocus],
]

export default function Results({ result, theme }) {
  const [tab, setTab] = useState('summary')
  const Cmp = TABS.find((t) => t[0] === tab)[2]
  return (
    <div className="space-y-3">
      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'tab-active' : ''}`} onClick={() => setTab(k)}>{l}</button>)}
      </div>
      <Cmp r={result} theme={theme} />
    </div>
  )
}
