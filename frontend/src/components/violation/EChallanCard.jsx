import { fmtDate } from '../../lib/format.js'
import { typeInfo } from '../../lib/constants.js'
import EvidenceHash from './EvidenceHash.jsx'

const HEADERS = {
  auto_confirmed: 'AUTOMATED e-CHALLAN (DRAFT)',
  vlm_confirmed: 'AUTOMATED e-CHALLAN (DRAFT)',
  human_review: 'e-CHALLAN — PENDING REVIEW',
  abstain: 'e-CHALLAN — NOT ISSUED (ABSTAINED)',
}

export default function EChallanCard({ v }) {
  const t = typeInfo(v.type)
  const dispo = (v.review_status && v.review_status !== '' ? v.review_status : v.route) || v.route
  return (
    <div className="challan">
      <div className="hd">{HEADERS[v.route] || 'e-CHALLAN'}</div>
      <div className="grid">
        <span className="k">Violation</span>
        <span className="v">
          {t.label} <span className="muted">({v.type})</span>
        </span>
        <span className="k">Plate</span>
        <span className="v">
          {v.plate && v.plate.text ? (
            <span className="plate">{v.plate.text}</span>
          ) : (
            <span className="muted">not captured</span>
          )}
        </span>
        <span className="k">Law</span>
        <span className="v">
          {v.legal ? `${v.legal.act} · §${v.legal.section}` : '—'}
        </span>
        <span className="k">Fine</span>
        <span className="v">{v.legal ? v.legal.fine : '—'}</span>
        <span className="k">Disposition</span>
        <span className="v">{dispo}</span>
        <span className="k">Date</span>
        <span className="v">{fmtDate(v.created_at)} UTC</span>
        <span className="k">Evidence</span>
        <span className="v">
          <EvidenceHash hash={v.evidence_hash} />
        </span>
        <span className="k">Image ID</span>
        <span className="v hash">{v.image_id}</span>
      </div>
    </div>
  )
}
