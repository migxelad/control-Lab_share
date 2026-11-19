import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import BlockEditor, { graphToRequest } from './components/BlockEditor.jsx'
import PhysicalEditor, { physToRequest } from './components/PhysicalEditor.jsx'
import { TfEditor, MotorEditor, FeedbackPicker } from './components/Inputs.jsx'
import ParamPanel from './components/ParamPanel.jsx'
import Results from './components/Results.jsx'
import { analyze, downloadReport } from './api.js'
import { BLOCK_EXAMPLES, PHYS_EXAMPLES, MOTOR_DEFAULTS, TF_EXAMPLES } from './examples.js'

const MODES = [['tf', 'Función de transferencia'], ['blocks', 'Diagrama de bloques'], ['physical', 'Sistema físico'], ['motor', 'Servomotor DC']]
const clone = (x) => structuredClone(x)
const sanitize = (n) => (String(n || 'x').trim().replace(/[^\p{L}\p{N}_]/gu, '_') || 'x')

/** Nombres únicos de parámetros para cada pieza física (misma regla que el backend). */
function physNames(parts) {
  const used = new Set(), out = {}
  for (const p of parts) {
    const base = sanitize(p.data.name || p.data.ptype)
    let nm = base, k = 2
    while (used.has(nm)) nm = `${base}_${k++}`
    used.add(nm); out[p.id] = nm
  }
  return out
}

function useLocal(key, init) {
  const [v, setV] = useState(() => { try { return JSON.parse(localStorage.getItem(key)) ?? init } catch { return init } })
  useEffect(() => { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* ignore */ } }, [key, v])
  return [v, setV]
}

export default function App() {
  const [theme, setTheme] = useLocal('cl-theme', 'dark')
  useEffect(() => { document.documentElement.classList.toggle('dark', theme === 'dark') }, [theme])

  const [mode, setMode] = useState('tf')
  const [tf, setTf] = useState({ Gn: '25', Gd: 's*(s+5)' })
  const [fb, setFb] = useState({ type: 'unity', H: '1' })
  const [graph, setGraphRaw] = useState(() => ({ nodes: clone(BLOCK_EXAMPLES['Realimentación unitaria'].nodes), edges: clone(BLOCK_EXAMPLES['Realimentación unitaria'].edges) }))
  const [phys, setPhys] = useState(() => { const ex = PHYS_EXAMPLES.trans['Masa-resorte-amortiguador']; return { domain: 'trans', parts: clone(ex.parts), wires: clone(ex.wires), input: ex.input, output: ex.output } })
  const [motor, setMotor] = useState({ output: 'speed' })
  const [params, setParams] = useState({ K: 4 })           // sobrescrituras de parámetros (tf / blocks / motor)
  const [ranges, setRanges] = useState({})
  const [options, setOptions] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [exporting, setExporting] = useState('')

  const setGraph = useCallback((u) => {
    if (typeof u === 'function') return setGraphRaw(u)
    if (u.params) setParams(u.params)
    setGraphRaw({ nodes: u.nodes, edges: u.edges })
  }, [])
  const loadTf = (k) => {
    const ex = TF_EXAMPLES[k]; if (!ex) return
    setTf({ Gn: ex.Gn, Gd: ex.Gd }); setFb({ type: ex.fb, H: ex.Hd === '1' ? '1' : `(${ex.Hn})/(${ex.Hd})` }); setParams(ex.params || {})
  }
  const switchMode = (m) => {
    setMode(m)
    if (m === 'motor') setParams((p) => ({ ...MOTOR_DEFAULTS, ...(Object.keys(MOTOR_DEFAULTS).every((k) => k in p) ? p : {}) }))
    setFb((f) => (m === 'physical' || m === 'motor') && f.type === 'unity' ? { ...f, type: 'none' } : f)
  }

  const request = useMemo(() => {
    const base = { mode, feedback: fb, options }
    if (mode === 'tf') return { ...base, tf: { G: `(${tf.Gn})/(${tf.Gd})` }, params }
    if (mode === 'blocks') return { ...base, blocks: graphToRequest(graph), params }
    if (mode === 'motor') return { ...base, motor, params }
    const names = physNames(phys.parts)
    const p = physToRequest({ ...phys, parts: phys.parts.map((n) => ({ ...n, data: { ...n.data, name: names[n.id] } })) })
    return { ...base, physical: p, params: {} }
  }, [mode, tf, fb, graph, phys, motor, params, options])

  // análisis con debounce y descarte de respuestas obsoletas
  const seq = useRef(0)
  useEffect(() => {
    const id = ++seq.current
    setBusy(true)
    const h = setTimeout(async () => {
      try {
        const r = await analyze(request)
        if (id !== seq.current) return
        setResult(r); setError(null)
      } catch (e) {
        if (id !== seq.current) return
        setError(e.message)
      } finally { if (id === seq.current) setBusy(false) }
    }, 350)
    return () => clearTimeout(h)
  }, [request])

  // panel de parámetros: en modo físico edita directamente los valores del esquema
  const physMap = useMemo(() => physNames(phys.parts), [phys.parts])
  const onParam = (name, v) => {
    if (mode === 'physical') {
      const id = Object.keys(physMap).find((i) => physMap[i] === name)
      if (id) setPhys((p) => ({ ...p, parts: p.parts.map((n) => n.id === id ? { ...n, data: { ...n.data, value: v } } : n) }))
    } else setParams((p) => ({ ...p, [name]: v }))
  }
  const values = useMemo(() => {
    if (mode !== 'physical') return params
    return Object.fromEntries(phys.parts.filter((n) => n.data.value != null).map((n) => [physMap[n.id], n.data.value]))
  }, [mode, params, phys.parts, physMap])

  const doExport = async (fmt) => {
    setExporting(fmt)
    try { await downloadReport(request, fmt) } catch (e) { setError(e.message) } finally { setExporting('') }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-sky-600 font-bold text-white">∫</div>
          <div><div className="text-base font-semibold leading-tight">Control Lab</div><div className="text-[11px] leading-tight text-slate-500 dark:text-slate-400">Análisis y cátedra de sistemas de control</div></div>
        </div>
        <nav className="ml-2 flex gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
          {MODES.map(([k, l]) => <button key={k} onClick={() => switchMode(k)} className={`rounded-lg px-3 py-1.5 text-sm font-medium ${mode === k ? 'bg-white shadow dark:bg-slate-950' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}>{l}</button>)}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {busy && <span className="text-xs text-slate-500">calculando…</span>}
          {['pdf', 'md', 'tex'].map((k) => (
            <button key={k} className="btn" disabled={!result || !!exporting} onClick={() => doExport(k)}>
              {exporting === k ? '…' : '⬇'} {k === 'pdf' ? 'PDF' : k === 'md' ? 'Markdown' : 'LaTeX'}
            </button>
          ))}
          <button className="btn" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Tema">{theme === 'dark' ? '☀ Claro' : '☾ Oscuro'}</button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto p-4 lg:grid-cols-[1fr_280px] lg:overflow-hidden">
        <main className="min-h-0 space-y-4 lg:overflow-y-auto lg:pr-1">
          <section className={mode === 'blocks' || mode === 'physical' ? 'h-[560px]' : ''}>
            {mode === 'tf' && <TfEditor tf={tf} setTf={setTf} loadExample={loadTf} />}
            {mode === 'blocks' && <BlockEditor graph={graph} setGraph={setGraph} theme={theme} />}
            {mode === 'physical' && <PhysicalEditor phys={phys} setPhys={setPhys} theme={theme} />}
            {mode === 'motor' && <MotorEditor motor={motor} setMotor={setMotor} />}
          </section>
          {mode !== 'blocks' && <FeedbackPicker fb={fb} setFb={setFb} />}
          {error && <div className="rounded-xl border border-rose-500/50 bg-rose-500/10 p-3 text-sm text-rose-600 dark:text-rose-300"><b>No se pudo analizar:</b> {error}</div>}
          {result ? <div className={error ? 'opacity-50' : ''}><Results result={result} theme={theme} request={request} onApply={onParam} /></div>
            : !error && <p className="text-slate-500">Calculando…</p>}
        </main>
        <div className="min-h-0 lg:overflow-hidden">
          <ParamPanel params={result?.parameters || []} values={values} onChange={onParam} ranges={ranges} setRanges={setRanges} options={options} setOptions={setOptions} />
        </div>
      </div>
    </div>
  )
}
