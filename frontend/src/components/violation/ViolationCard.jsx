import { pct } from '../../lib/format.js'
import { routeInfo, typeInfo } from '../../lib/constants.js'
import Badge from '../common/Badge.jsx'
import PlateChip from '../common/PlateChip.jsx'

// Compact, interpretable card. Click opens the full detail view.
export default function ViolationCard({ v, onOpen }) {
  const t = typeInfo(v.type)
  const r = routeInfo(v.route)
  const conf = pct(v.scores?.fused)
  const law = v.legal ? `${v.legal.act}, §${v.legal.section} · fine ${v.legal.fine}` : ''
  return (
    <div className="vcard" onClick={() => onOpen?.(v)}>
      <div className="vicon">{t.icon}</div>
      <div>
        <div className="vtitle">
          {t.label} <span className="muted">· Tier {v.tier}</span>
        </div>
        <div className="vsub">{v.reason}</div>
        <div className="vsub">
          Plate: <PlateChip plate={v.plate} />
          {law ? ` · ${law}` : ''}
        </div>
        <div className="bar thin">
          <i style={{ width: `${conf}%` }} />
        </div>
      </div>
      <div className="right">
        <Badge variant={r.variant}>{r.label}</Badge>
        <div className="muted" style={{ marginTop: 6 }}>
          {conf}%{r.note ? ` · ${r.note}` : ''}
        </div>
      </div>
    </div>
  )
}
