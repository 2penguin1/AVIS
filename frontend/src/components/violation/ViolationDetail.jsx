import { useEffect, useState } from 'react'
import { getViolation } from '../../api/client.js'
import { SUFFICIENCY_INFO, TIER_INFO, routeInfo, typeInfo } from '../../lib/constants.js'
import Badge from '../common/Badge.jsx'
import Modal from '../common/Modal.jsx'
import PlateChip from '../common/PlateChip.jsx'
import ScoreBreakdown from '../common/ScoreBreakdown.jsx'
import TierBadge from '../common/TierBadge.jsx'
import AnnotatedImage from './AnnotatedImage.jsx'
import AuditTrail from './AuditTrail.jsx'
import EChallanCard from './EChallanCard.jsx'
import RouteExplainer from './RouteExplainer.jsx'

function Section({ title, children }) {
  return (
    <div className="block">
      <h3 className="sec">{title}</h3>
      {children}
    </div>
  )
}

// Full interpretability panel. Refetches the latest payload by id (fresh audit trail).
export default function ViolationDetail({ violation, onClose, showReview = false, reviewSlot }) {
  const [v, setV] = useState(violation)
  useEffect(() => {
    if (violation?.id) getViolation(violation.id).then(setV).catch(() => {})
  }, [violation?.id])

  const t = typeInfo(v.type)
  const r = routeInfo(v.route)
  const annotated = v.annotated_url || `/files/${v.image_id}_annotated.jpg`

  return (
    <Modal title={t.label} icon={t.icon} onClose={onClose}>
      <div className="row spread" style={{ marginBottom: 14 }}>
        <TierBadge tier={v.tier} />
        <Badge variant={r.variant}>{r.label}</Badge>
      </div>

      <Section title="What was detected">{v.reason || '—'}</Section>

      <Section title="Why it's a violation">
        {v.legal ? (
          <>
            {v.legal.act} · <b>§{v.legal.section}</b> — fine <b>{v.legal.fine}</b>
          </>
        ) : (
          'No legal mapping found.'
        )}
      </Section>

      <Section title="Confidence breakdown">
        <ScoreBreakdown scores={v.scores} />
      </Section>

      <Section title="Evidence tier">
        <div>
          <TierBadge tier={v.tier} /> {TIER_INFO[v.tier]}
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          Evidence is <b>{v.evidence_sufficiency}</b> —{' '}
          {SUFFICIENCY_INFO[v.evidence_sufficiency] || ''}
        </div>
      </Section>

      <Section title="Action taken">
        <RouteExplainer v={v} />
      </Section>

      <Section title="License plate">
        <PlateChip plate={v.plate} />
      </Section>

      <Section title="e-Challan">
        <EChallanCard v={v} />
      </Section>

      <Section title="Annotated evidence">
        <AnnotatedImage url={annotated} />
      </Section>

      <Section title="Audit trail">
        <AuditTrail audit={v.audit} />
      </Section>

      {showReview && reviewSlot ? <Section title="Review">{reviewSlot(v)}</Section> : null}
    </Modal>
  )
}
