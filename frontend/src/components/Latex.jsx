import katex from 'katex'
import { useMemo } from 'react'

export default function Latex({ tex, block = false, className = '' }) {
  const html = useMemo(() => {
    try { return katex.renderToString(String(tex ?? ''), { throwOnError: false, displayMode: block, strict: 'ignore' }) }
    catch { return String(tex) }
  }, [tex, block])
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
}
