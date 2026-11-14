import { useCallback, useMemo, useRef } from 'react'
import { ReactFlow, ReactFlowProvider, Background, Controls, Handle, Position, MarkerType, applyNodeChanges, applyEdgeChanges, useReactFlow } from '@xyflow/react'
import { BLOCK_EXAMPLES } from '../examples.js'

const base = 'flex items-center justify-center border-2 shadow-sm select-none'

function InputNode({ selected }) {
  return (
    <div className={`${base} rounded-full px-3 py-1.5 font-semibold ${selected ? 'border-sky-400' : 'border-emerald-500'} bg-emerald-500/15 text-emerald-600 dark:text-emerald-300`}>
      R(s)<Handle type="source" position={Position.Right} />
    </div>
  )
}
function OutputNode({ selected }) {
  return (
    <div className={`${base} rounded-full px-3 py-1.5 font-semibold ${selected ? 'border-sky-400' : 'border-rose-500'} bg-rose-500/15 text-rose-600 dark:text-rose-300`}>
      <Handle type="target" position={Position.Left} />Y(s)
    </div>
  )
}
function BlockNode({ data, selected }) {
  const flip = !!data.flip
  return (
    <div className={`${base} min-w-[110px] flex-col rounded-lg px-3 py-2 ${selected ? 'border-sky-400' : 'border-slate-400 dark:border-slate-500'} bg-white dark:bg-slate-800`}>
      <Handle type="target" position={flip ? Position.Right : Position.Left} />
      <div className="text-sm font-bold">{data.name || 'G'}(s)</div>
      <div className="max-w-[170px] truncate font-mono text-[11px] text-slate-500 dark:text-slate-400" title={data.tf}>{data.tf || '1'}</div>
      <Handle type="source" position={flip ? Position.Left : Position.Right} />
    </div>
  )
}
function SumNode({ selected }) {
  return (
    <div className={`${base} h-9 w-9 rounded-full text-lg ${selected ? 'border-sky-400' : 'border-slate-400 dark:border-slate-500'} bg-white dark:bg-slate-800`}>
      Σ
      <Handle id="l" type="target" position={Position.Left} />
      <Handle id="t" type="target" position={Position.Top} />
      <Handle id="b" type="target" position={Position.Bottom} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}
function BranchNode({ selected }) {
  // Entradas: izquierda y arriba. Salidas: derecha y abajo.
  return (
    <div className={`h-4 w-4 rounded-full ${selected ? 'bg-sky-400' : 'bg-slate-500 dark:bg-slate-300'}`}>
      <Handle type="target" position={Position.Left} />
      <Handle id="ti" type="target" position={Position.Top} />
      <Handle type="source" position={Position.Right} />
      <Handle id="b" type="source" position={Position.Bottom} />
    </div>
  )
}
const nodeTypes = { input: InputNode, output: OutputNode, block: BlockNode, sum: SumNode, branch: BranchNode }

const PALETTE = [
  ['input', 'Entrada R(s)'], ['block', 'Bloque G(s)'], ['sum', 'Sumador Σ'], ['branch', 'Punto de ramificación'], ['output', 'Salida Y(s)'],
]

let counter = 100
function Inner({ graph, setGraph, theme }) {
  const wrap = useRef(null)
  const { screenToFlowPosition } = useReactFlow()
  const { nodes, edges } = graph

  const onNodesChange = useCallback((ch) => setGraph((g) => ({ ...g, nodes: applyNodeChanges(ch, g.nodes) })), [setGraph])
  const onEdgesChange = useCallback((ch) => setGraph((g) => ({ ...g, edges: applyEdgeChanges(ch, g.edges) })), [setGraph])
  const onConnect = useCallback((c) => setGraph((g) => ({
    ...g, edges: [...g.edges, { ...c, id: `e${++counter}`, data: { sign: '+' } }],
  })), [setGraph])

  const addNode = (type, pos) => {
    const id = `${type}_${++counter}`
    const data = type === 'block' ? { name: `G_${counter % 100}`, tf: '1/(s+1)' } : {}
    const position = pos || (() => {
      const r = wrap.current.getBoundingClientRect()
      return screenToFlowPosition({ x: r.left + r.width / 2 + (Math.random() - .5) * 120, y: r.top + r.height / 2 + (Math.random() - .5) * 80 })
    })()
    setGraph((g) => ({ ...g, nodes: [...g.nodes.map((n) => ({ ...n, selected: false })), { id, type, position, data, selected: true }] }))
  }
  const onDrop = (e) => {
    e.preventDefault()
    const t = e.dataTransfer.getData('application/x-block')
    if (t) addNode(t, screenToFlowPosition({ x: e.clientX, y: e.clientY }))
  }

  const nodeById = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes])
  const shown = useMemo(() => edges.map((e) => {
    const toSum = nodeById[e.target]?.type === 'sum'
    const sign = e.data?.sign || '+'
    return {
      ...e, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed },
      label: toSum ? (sign === '-' ? '−' : '+') : undefined,
      labelStyle: { fontWeight: 700, fontSize: 15, fill: sign === '-' ? '#f87171' : '#4ade80' },
      labelBgStyle: { fill: theme === 'dark' ? '#0f172a' : '#fff' }, labelBgPadding: [3, 1],
      style: { strokeWidth: 1.8, stroke: sign === '-' && toSum ? '#f87171' : undefined },
    }
  }), [edges, nodeById, theme])

  const onEdgeClick = (_, e) => {
    if (nodeById[e.target]?.type !== 'sum') return
    setGraph((g) => ({ ...g, edges: g.edges.map((x) => x.id === e.id ? { ...x, data: { ...x.data, sign: x.data?.sign === '-' ? '+' : '-' } } : x) }))
  }

  const sel = nodes.find((n) => n.selected && (n.type === 'block'))
  const upd = (patch) => setGraph((g) => ({ ...g, nodes: g.nodes.map((n) => n.id === sel.id ? { ...n, data: { ...n.data, ...patch } } : n) }))

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        {PALETTE.map(([t, l]) => (
          <button key={t} className="btn cursor-grab" draggable onClick={() => addNode(t)}
            onDragStart={(e) => { e.dataTransfer.setData('application/x-block', t); e.dataTransfer.effectAllowed = 'move' }}>
            + {l}
          </button>
        ))}
        <select className="input !w-auto" value="" onChange={(e) => { const ex = BLOCK_EXAMPLES[e.target.value]; if (ex) setGraph({ nodes: structuredClone(ex.nodes), edges: structuredClone(ex.edges), params: ex.params }) }}>
          <option value="">Cargar ejemplo…</option>
          {Object.keys(BLOCK_EXAMPLES).map((k) => <option key={k}>{k}</option>)}
        </select>
        <button className="btn" onClick={() => setGraph({ nodes: [], edges: [] })}>Limpiar</button>
      </div>
      <div ref={wrap} className="card min-h-[340px] flex-1 overflow-hidden" onDrop={onDrop} onDragOver={(e) => e.preventDefault()}>
        <ReactFlow nodes={nodes} edges={shown} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={onConnect} onEdgeClick={onEdgeClick} colorMode={theme} fitView fitViewOptions={{ padding: 0.2 }} deleteKeyCode={['Backspace', 'Delete']}>
          <Background gap={20} /><Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="card flex flex-wrap items-end gap-3 p-3 text-sm">
        {sel ? (<>
          <div className="w-28"><span className="label">Nombre</span><input className="input" value={sel.data.name || ''} onChange={(e) => upd({ name: e.target.value })} /></div>
          <div className="min-w-[220px] flex-1"><span className="label">Función de transferencia (en s, con parámetros)</span>
            <input className="input font-mono" value={sel.data.tf || ''} onChange={(e) => upd({ tf: e.target.value })} placeholder="K/(s*(s+2))" /></div>
          <label className="flex items-center gap-2 pb-2"><input type="checkbox" checked={!!sel.data.flip} onChange={(e) => upd({ flip: e.target.checked })} />Invertir (rama de realimentación)</label>
        </>) : (
          <span className="text-slate-500 dark:text-slate-400">Selecciona un bloque para editar G(s). Arrastra de un punto de conexión a otro para unir; <b>clic en una flecha hacia un sumador</b> cambia su signo (+/−); Supr borra lo seleccionado.</span>
        )}
      </div>
    </div>
  )
}

export default function BlockEditor(props) {
  return <ReactFlowProvider><Inner {...props} /></ReactFlowProvider>
}

export function graphToRequest(graph) {
  return {
    nodes: graph.nodes.map((n) => ({ id: n.id, type: n.type, name: n.data?.name, tf: n.data?.tf })),
    edges: graph.edges.map((e) => ({ source: e.source, target: e.target, sign: e.data?.sign || '+' })),
  }
}
