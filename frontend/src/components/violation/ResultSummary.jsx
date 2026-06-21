import React from 'react'

export default function ResultSummary({ violations }) {
  const v = violations || []
  const confirmed = v.filter((x) => ['auto_confirmed', 'vlm_confirmed'].includes(x.route)).length
  const review = v.filter((x) => x.route === 'human_review').length
  const abstain = v.filter((x) => x.route === 'abstain').length

  const boxStyle = {
    padding: '16px',
    borderRadius: '10px',
    border: '1px solid var(--line)',
    background: 'var(--card2)',
    flex: '1 1 120px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  }

  return (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
      <div style={{ ...boxStyle, borderTop: '3px solid var(--blue)' }}>
        <span style={{ fontSize: '24px', fontWeight: 'bold' }}>{v.length}</span>
        <span className="muted">Total Violations</span>
      </div>
      <div style={{ ...boxStyle, borderTop: '3px solid var(--ok)' }}>
        <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--ok)' }}>{confirmed}</span>
        <span className="muted">Confirmed</span>
      </div>
      <div style={{ ...boxStyle, borderTop: '3px solid var(--warn)' }}>
        <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--warn)' }}>{review}</span>
        <span className="muted">Need Review</span>
      </div>
      <div style={{ ...boxStyle, borderTop: '3px solid var(--mut)' }}>
        <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--mut)' }}>{abstain}</span>
        <span className="muted">Abstained</span>
      </div>
    </div>
  )
}
