import { useEffect, useState } from 'react'
import { getAnalytics } from '../api/client.js'
import ByDayChart from '../components/charts/ByDayChart.jsx'
import ByRouteChart from '../components/charts/ByRouteChart.jsx'
import ByTypeChart from '../components/charts/ByTypeChart.jsx'
import Spinner from '../components/common/Spinner.jsx'

function Kpi({ n, l, color = 'var(--blue)' }) {
  return (
    <div style={{
      padding: '16px', borderRadius: '10px', border: '1px solid var(--line)', background: 'var(--card2)',
      borderTop: `3px solid ${color}`, flex: '1 1 140px', display: 'flex', flexDirection: 'column', gap: '6px'
    }}>
      <span style={{ fontSize: '24px', fontWeight: 'bold', color: color }}>{n}</span>
      <span className="muted">{l}</span>
    </div>
  )
}

export default function AnalyticsPage() {
  const [a, setA] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    getAnalytics().then(setA).catch((e) => setErr(e.message))
  }, [])

  if (err) return <div className="card">Failed to load analytics: {err}</div>
  if (!a) return <div className="card"><Spinner /> loading analytics…</div>

  const confirmed = (a.by_route?.auto_confirmed || 0) + (a.by_route?.vlm_confirmed || 0)
  const reduction = a.total ? Math.round((100 * confirmed) / a.total) : 0
  const plateRate = a.plates_read ? Math.round((100 * (a.plates_valid || 0)) / a.plates_read) : 0

  return (
    <>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
        <Kpi n={a.total} l="Total violations" color="var(--blue)" />
        <Kpi n={confirmed} l="Confirmed (no human)" color="var(--ok)" />
        <Kpi n={a.pending_review} l="Pending review" color="var(--warn)" />
        <Kpi n={a.plates_read ?? 0} l="Plates read" color="var(--txt)" />
      </div>

      <div className="card">
        <div className="banner good">
          🤖 <b>Human-review reduction: {reduction}%</b> — that share of violations was resolved
          automatically (auto- or AI-confirmed), with no human needed.
        </div>
        <div className="muted">
          Plate OCR: {a.plate_ocr_enabled ? 'on' : 'off'} · {a.plates_read || 0} read,{' '}
          {a.plates_valid || 0} valid format ({plateRate}%).
        </div>
      </div>

      <div className="charts">
        <div className="card">
          <ByTypeChart byType={a.by_type} />
        </div>
        <div className="card">
          <ByRouteChart byRoute={a.by_route} />
        </div>
      </div>
      <div className="card">
        <ByDayChart byDay={a.by_day} />
      </div>
    </>
  )
}
