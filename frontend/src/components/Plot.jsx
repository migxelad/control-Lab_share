import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'

export const COLORS = { blue: '#38bdf8', orange: '#fb923c', green: '#4ade80', red: '#f87171', violet: '#a78bfa', yellow: '#facc15' }

function axisDefaults(dark, extra = {}) {
  return { gridcolor: dark ? '#1e293b' : '#e2e8f0', zerolinecolor: dark ? '#475569' : '#94a3b8', linecolor: dark ? '#334155' : '#cbd5e1', automargin: true, ...extra }
}

export default function Plot({ data, layout = {}, theme = 'dark', height = 340 }) {
  const ref = useRef(null)
  useEffect(() => {
    const dark = theme === 'dark'
    const l = {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: dark ? '#cbd5e1' : '#334155', size: 12 },
      margin: { l: 55, r: 18, t: 38, b: 46 }, height, legend: { orientation: 'h', y: -0.22 }, hovermode: 'closest',
      ...layout,
    }
    for (const k of Object.keys(layout)) if (/^[xy]axis\d*$/.test(k)) l[k] = axisDefaults(dark, layout[k])
    if (!l.xaxis) l.xaxis = axisDefaults(dark)
    if (!l.yaxis) l.yaxis = axisDefaults(dark)
    Plotly.react(ref.current, data, l, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] })
  }, [data, layout, theme, height])
  useEffect(() => { const el = ref.current; return () => Plotly.purge(el) }, [])
  return <div ref={ref} style={{ width: '100%', height }} />
}
