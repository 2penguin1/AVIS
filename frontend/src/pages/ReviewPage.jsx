import { useEffect, useState } from 'react'
import { getReviewQueue, reviewViolation } from '../api/client.js'
import { pct } from '../lib/format.js'
import { typeInfo } from '../lib/constants.js'
import EmptyState from '../components/common/EmptyState.jsx'
import PlateChip from '../components/common/PlateChip.jsx'
import Spinner from '../components/common/Spinner.jsx'
import TierBadge from '../components/common/TierBadge.jsx'
import ViolationDetail from '../components/violation/ViolationDetail.jsx'

export default function ReviewPage() {
  const [rows, setRows] = useState(null)
  const [reviewer, setReviewer] = useState('')
  const [note, setNote] = useState('')
  const [open, setOpen] = useState(null)

  const load = () => {
    setRows(null)
    getReviewQueue().then(setRows).catch(() => setRows([]))
  }
  useEffect(load, [])

  const decide = async (id, decision) => {
    await reviewViolation(id, decision, reviewer.trim() || 'anonymous', note.trim())
    setNote('')
    load()
  }

  return (
    <>
      <div className="card">
        <div className="row">
          <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="your name" />
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="note (optional, saved to the audit trail)"
            style={{ flex: 1, minWidth: 220 }}
          />
          <button className="go" onClick={load}>
            Refresh
          </button>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          Cases the system wasn't confident enough to confirm automatically.
        </div>
      </div>

      {rows === null && (
        <div className="card">
          <Spinner /> loading queue…
        </div>
      )}
      {rows && rows.length === 0 && <EmptyState>Queue is empty 🎉</EmptyState>}
      {rows && rows.length > 0 && (
        <div className="card">
          {rows.map((v) => {
            const t = typeInfo(v.type)
            return (
              <div className="vcard" key={v.id} onClick={() => setOpen(v)}>
                <div className="vicon">{t.icon}</div>
                <div>
                  <div className="vtitle">
                    {t.label} <span className="muted">· {pct(v.scores?.fused)}%</span>{' '}
                    <TierBadge tier={v.tier} />
                  </div>
                  <div className="vsub">{v.reason}</div>
                  <div className="vsub">
                    Plate: <PlateChip plate={v.plate} />
                  </div>
                </div>
                <div className="right" onClick={(e) => e.stopPropagation()}>
                  <button className="go approve" onClick={() => decide(v.id, 'approved')}>
                    Approve
                  </button>{' '}
                  <button className="go reject" onClick={() => decide(v.id, 'rejected')}>
                    Reject
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {open && (
        <ViolationDetail
          violation={open}
          onClose={() => setOpen(null)}
          showReview
          reviewSlot={(v) => (
            <div className="row">
              <button className="go approve" onClick={() => { decide(v.id, 'approved'); setOpen(null) }}>
                Approve
              </button>
              <button className="go reject" onClick={() => { decide(v.id, 'rejected'); setOpen(null) }}>
                Reject
              </button>
            </div>
          )}
        />
      )}
    </>
  )
}
