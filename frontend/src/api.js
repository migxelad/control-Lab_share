async function post(url, body) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) {
    let msg = `Error ${r.status}`
    try { const j = await r.json(); msg = j.detail || msg } catch { /* ignore */ }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return r
}
export async function analyze(req) { return (await post('/api/analyze', req)).json() }
export async function downloadReport(req, format) {
  const r = await post(`/api/report?format=${format}`, req)
  const blob = await r.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = format === 'pdf' ? 'informe.pdf' : `informe_${format}.zip`
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 4000)
}
export async function analyzeStability(req) { return (await post('/api/param-stability', req)).json() }
