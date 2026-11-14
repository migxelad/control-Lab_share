import { useCallback, useMemo, useRef } from 'react'
import { ReactFlow, ReactFlowProvider, Background, Controls, Handle, Position, ConnectionMode, applyNodeChanges, applyEdgeChanges, useReactFlow } from '@xyflow/react'
import { PHYS_EXAMPLES } from '../examples.js'

const ZZ = 'M0 20 H14 L18 8 L26 32 L34 8 L42 32 L50 8 L58 32 L62 20 H80'
const ICONS = {
  resistor: <path d={ZZ} />,
  inductor: <path d="M0 20 H12 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 H80" />,
  capacitor: <><path d="M0 20 H34 M46 20 H80" /><path d="M34 6 V34 M46 6 V34" /></>,
  vsource: <><circle cx="40" cy="20" r="15" /><path d="M0 20 H25 M55 20 H80 M30 20 H36 M33 17 V23 M45 20 H51" /></>,
  isource: <><circle cx="40" cy="20" r="15" /><path d="M0 20 H25 M55 20 H80 M31 20 H48 M44 15 L49 20 L44 25" /></>,
  spring: <path d={ZZ} />,
  tspring: <path d="M0 20 H12 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 a7 9 0 0 1 14 0 H80" />,
  damper: <><path d="M0 20 H26 M26 8 V32 M26 8 H56 M26 32 H56 M44 20 H80 M44 10 V30" /></>,
  rdamper: <><path d="M0 20 H26 M26 8 V32 M26 8 H56 M26 32 H56 M44 20 H80 M44 10 V30" /></>,
  mass: <><rect x="14" y="6" width="52" height="28" rx="3" /></>,
  inertia: <><circle cx="40" cy="20" r="16" /><circle cx="40" cy="20" r="3" /></>,
  force: <path d="M0 20 H66 M56 12 L68 20 L56 28" />,
  torque: <path d="M18 28 A16 16 0 1 1 62 28 M62 18 V30 H50" />,
  ground: <path d="M40 4 V16 M22 16 H58 M28 24 H52 M34 32 H46" />,
}
const DEFS = {
  trans: [['mass', 'Masa M', 'M', 1, 'kg'], ['spring', 'Muelle K', 'K', 1, 'N/m'], ['damper', 'Amortiguador B', 'B', 1, 'N·s/m'], ['force', 'Fuerza F(t)', 'F', null, ''], ['ground', 'Pared / suelo', 'Pared', null, '']],
  rot: [['inertia', 'Inercia J', 'J', 1, 'kg·m²'], ['tspring', 'Muelle torsional K', 'K', 1, 'N·m/rad'], ['rdamper', 'Fricción rot. B', 'B', 1, 'N·m·s/rad'], ['torque', 'Par τ(t)', 'T', null, ''], ['ground', 'Fijo', 'Fijo', null, '']],
  elec: [['resistor', 'Resistencia R', 'R', 1, 'Ω'], ['inductor', 'Inductancia L', 'L', 1, 'H'], ['capacitor', 'Capacidad C', 'C', 1, 'F'], ['vsource', 'Fuente V', 'V', null, ''], ['isource', 'Fuente I', 'I', null, ''], ['ground', 'Tierra GND', 'GND', null, '']],
}
export const UNITS = Object.fromEntries(Object.values(DEFS).flat().map(([t, , , , u]) => [t, u]))
const ONE_TERMINAL = new Set(['mass', 'inertia', 'ground', 'force', 'torque'])

function PartNode({ data, selected }) {
  const t = data.ptype
  const one = ONE_TERMINAL.has(t)
  const isSrc = ['force', 'torque', 'vsource', 'isource'].includes(t)
  return (
    <div className={`rounded-lg border-2 px-2 py-1 text-center ${selected ? 'border-sky-400' : 'border-slate-300 dark:border-slate-600'} bg-white dark:bg-slate-800`} style={{ width: 96 }}>
      <svg viewBox="0 0 80 40" className={`h-8 w-full ${isSrc ? 'text-amber-500' : 'text-slate-700 dark:text-slate-200'}`} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">{ICONS[t]}</svg>
      <div className="text-[11px] font-semibold leading-tight">{data.name}</div>
      {data.value != null && <div className="font-mono text-[10px] text-slate-500 dark:text-slate-400">{data.value} {UNITS[t]}</div>}
      {one ? (<>
        <Handle id="a" type="source" position={t === 'ground' ? Position.Top : t === 'force' || t === 'torque' ? Position.Right : Position.Top} />
        {(t === 'mass' || t === 'inertia') && <>
          <Handle id="a2" type="source" position={Position.Left} /><Handle id="a3" type="source" position={Position.Right} /><Handle id="a4" type="source" position={Position.Bottom} />
        </>}
        {(t === 'force' || t === 'torque') && <Handle id="a2" type="source" position={Position.Left} style={{ opacity: .5 }} />}
      </>) : (<>
        <Handle id="a" type="source" position={Position.Left} /><Handle id="b" type="source" position={Position.Right} />
      </>)}
    </div>
  )
}
const nodeTypes = { part: PartNode }

let counter = 200
function Inner({ phys, setPhys, theme }) {
  const wrap = useRef(null)
  const { screenToFlowPosition } = useReactFlow()
  const { domain, parts, wires } = phys
  const onNodesChange = useCallback((ch) => setPhys((p) => ({ ...p, parts: applyNodeChanges(ch, p.parts) })), [setPhys])
  const onEdgesChange = useCallback((ch) => setPhys((p) => ({ ...p, wires: applyEdgeChanges(ch, p.wires) })), [setPhys])
  const onConnect = useCallback((c) => setPhys((p) => ({ ...p, wires: [...p.wires, { ...c, id: `w${++counter}` }] })), [setPhys])

  const add = (def, pos) => {
    const [t, , nm, val] = def
    const id = `${t}_${++counter}`
    const position = pos || (() => {
      const r = wrap.current.getBoundingClientRect()
      return screenToFlowPosition({ x: r.left + r.width / 2 + (Math.random() - .5) * 140, y: r.top + r.height / 2 + (Math.random() - .5) * 80 })
    })()
    const same = p => p.parts.filter((x) => x.data.ptype === t).length
    setPhys((p) => ({
      ...p, parts: [...p.parts.map((n) => ({ ...n, selected: false })), {
        id, type: 'part', position, selected: true,
        data: { ptype: t, name: same(p) ? `${nm}${same(p) + 1}` : nm, value: val },
      }],
    }))
  }
  const onDrop = (e) => {
    e.preventDefault()
    const t = e.dataTransfer.getData('application/x-part')
    const def = DEFS[domain].find((d) => d[0] === t)
    if (def) add(def, screenToFlowPosition({ x: e.clientX, y: e.clientY }))
  }
  const sel = parts.find((n) => n.selected)
  const upd = (patch) => setPhys((p) => ({ ...p, parts: p.parts.map((n) => n.id === sel.id ? { ...n, data: { ...n.data, ...patch } } : n) }))

  const sources = parts.filter((n) => ['force', 'torque', 'vsource', 'isource'].includes(n.data.ptype))
  const outs = parts.filter((n) => n.data.ptype !== 'ground')
  const L = { trans: ['Posición x', 'Velocidad v', 'Fuerza a través'], rot: ['Ángulo θ', 'Velocidad ω', 'Par a través'], elec: ['Tensión', '—', 'Corriente'] }[domain]
  const kinds = [['across', L[0]], ...(domain === 'elec' ? [] : [['velocity', L[1]]]), ['through', L[2]]]
  const loadExample = (k) => {
    const ex = PHYS_EXAMPLES[domain][k]
    if (ex) setPhys({ domain, parts: structuredClone(ex.parts), wires: structuredClone(ex.wires), input: ex.input, output: ex.output })
  }
  const changeDomain = (d) => {
    const k = Object.keys(PHYS_EXAMPLES[d])[0]
    const ex = PHYS_EXAMPLES[d][k]
    setPhys({ domain: d, parts: structuredClone(ex.parts), wires: structuredClone(ex.wires), input: ex.input, output: ex.output })
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <select className="input !w-auto font-semibold" value={domain} onChange={(e) => changeDomain(e.target.value)}>
          <option value="trans">Mecánico de traslación</option><option value="rot">Mecánico de rotación</option><option value="elec">Eléctrico</option>
        </select>
        {DEFS[domain].map((d) => (
          <button key={d[0]} className="btn cursor-grab" draggable onClick={() => add(d)}
            onDragStart={(e) => { e.dataTransfer.setData('application/x-part', d[0]); e.dataTransfer.effectAllowed = 'move' }}>+ {d[1]}</button>
        ))}
        <select className="input !w-auto" value="" onChange={(e) => loadExample(e.target.value)}>
          <option value="">Cargar ejemplo…</option>{Object.keys(PHYS_EXAMPLES[domain]).map((k) => <option key={k}>{k}</option>)}
        </select>
      </div>
      <div ref={wrap} className="card min-h-[340px] flex-1 overflow-hidden" onDrop={onDrop} onDragOver={(e) => e.preventDefault()}>
        <ReactFlow nodes={parts} edges={wires} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
          connectionMode={ConnectionMode.Loose} colorMode={theme} fitView fitViewOptions={{ padding: 0.2 }} deleteKeyCode={['Backspace', 'Delete']}
          defaultEdgeOptions={{ type: 'smoothstep', style: { strokeWidth: 2 } }}>
          <Background gap={20} /><Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="card grid gap-3 p-3 text-sm md:grid-cols-2">
        <div className="flex flex-wrap items-end gap-3">
          <div><span className="label">Entrada</span>
            <select className="input" value={phys.input || ''} onChange={(e) => setPhys((p) => ({ ...p, input: e.target.value }))}>
              {sources.map((n) => <option key={n.id} value={n.id}>{n.data.name}</option>)}
            </select></div>
          <div><span className="label">Salida: elemento</span>
            <select className="input" value={phys.output?.comp || ''} onChange={(e) => setPhys((p) => ({ ...p, output: { ...p.output, comp: e.target.value } }))}>
              {outs.map((n) => <option key={n.id} value={n.id}>{n.data.name}</option>)}
            </select></div>
          <div><span className="label">Magnitud</span>
            <select className="input" value={phys.output?.kind || 'across'} onChange={(e) => setPhys((p) => ({ ...p, output: { ...p.output, kind: e.target.value } }))}>
              {kinds.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select></div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          {sel ? (<>
            <div className="w-24"><span className="label">Símbolo</span><input className="input" value={sel.data.name} onChange={(e) => upd({ name: e.target.value })} /></div>
            {sel.data.value != null && <div className="w-32"><span className="label">Valor ({UNITS[sel.data.ptype]})</span>
              <input className="input" type="number" step="any" value={sel.data.value} onChange={(e) => upd({ value: parseFloat(e.target.value) || 0 })} /></div>}
          </>) : <span className="text-slate-500 dark:text-slate-400">Selecciona un elemento para editar su símbolo/valor. Une terminales arrastrando entre puntos; las masas/inercias tienen 4 puntos y todas las conexiones al mismo punto forman un nodo.</span>}
        </div>
      </div>
    </div>
  )
}
export default function PhysicalEditor(p) { return <ReactFlowProvider><Inner {...p} /></ReactFlowProvider> }

export function physToRequest(phys) {
  const strip = (h) => (h || 'a')[0]
  return {
    domain: phys.domain,
    components: phys.parts.map((n) => ({ id: n.id, type: n.data.ptype, name: n.data.name, value: n.data.value ?? 1 })),
    wires: phys.wires.map((w) => [`${w.source}.${strip(w.sourceHandle)}`, `${w.target}.${strip(w.targetHandle)}`]),
    input: phys.input, output: phys.output,
  }
}
