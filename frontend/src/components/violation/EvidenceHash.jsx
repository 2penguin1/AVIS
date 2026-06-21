import { useState } from 'react'
import { shortHash } from '../../lib/format.js'

export default function EvidenceHash({ hash }) {
  const [copied, setCopied] = useState(false)
  if (!hash) return <span className="muted">—</span>
  const copy = () => {
    navigator.clipboard?.writeText(hash).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <span className="row" style={{ gap: 8 }}>
      <span className="hash" title={hash}>
        {shortHash(hash)}
      </span>
      <button className="ghost" onClick={copy} style={{ padding: '2px 8px' }}>
        {copied ? 'copied' : 'copy'}
      </button>
    </span>
  )
}
