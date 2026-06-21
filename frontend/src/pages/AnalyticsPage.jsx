import { useEffect, useState } from 'react'
import { getAnalytics } from '../api/client.js'
import ByDayChart from '../components/charts/ByDayChart.jsx'
import ByRouteChart from '../components/charts/ByRouteChart.jsx'
import ByTypeChart from '../components/charts/ByTypeChart.jsx'
import Spinner from '../components/common/Spinner.jsx'

function Kpi({ n, l }) {
  return (
    <div className="kpi">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
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
      <div className="card kpis">
        <Kpi n={a.total} l="Total violations" />
        <Kpi n={confirmed} l="Confirmed (no human)" />
        <Kpi n={a.pending_review} l="Pending review" />
        <Kpi n={a.plates_read ?? 0} l="Plates read" />
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
