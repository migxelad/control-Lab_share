export const f = (x, d = 4) => {
  if (x == null) return '—'
  if (typeof x === 'string') return x
  if (!isFinite(x)) return '∞'
  if (x === 0) return '0'
  const a = Math.abs(x)
  return a >= 1e5 || a < 1e-3 ? x.toExponential(d - 1) : String(+x.toPrecision(d))
}
export const inf = (x) => (x == null ? '∞' : f(x))

export function Tile({ label, value, sub, tone }) {
  const c = tone === 'good' ? 'text-emerald-500' : tone === 'bad' ? 'text-rose-500' : tone === 'warn' ? 'text-amber-500' : ''
  return (
    <div className="card p-3">
      <div className="label !mb-0.5">{label}</div>
      <div className={`text-xl font-semibold ${c}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 dark:text-slate-400">{sub}</div>}
    </div>
  )
}
export const Box = ({ title, children, className = '' }) => (
  <section className={`card p-4 ${className}`}>{title && <h3 className="mb-2 text-sm font-semibold">{title}</h3>}{children}</section>
)
export function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto"><table className="tbl">
      <thead><tr>{head.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table></div>
  )
}
