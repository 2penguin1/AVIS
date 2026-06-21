import { fmtDate } from '../../lib/format.js'

export default function AuditTrail({ audit }) {
  if (!audit || !audit.length)
    return <div className="muted">No human actions yet.</div>
  return (
    <ul className="audit">
      {audit.map((a, i) => (
        <li key={i}>
          <b>{a.decision || a.action}</b> by {a.reviewer || 'anonymous'} ·{' '}
          <span className="muted">{fmtDate(a.ts)}</span>
          {a.note ? <div className="muted">“{a.note}”</div> : null}
        </li>
      ))}
    </ul>
  )
}
