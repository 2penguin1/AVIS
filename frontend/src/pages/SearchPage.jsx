import { useState } from 'react'
import { listViolations } from '../api/client.js'
import { fmtDate, pct } from '../lib/format.js'
import { TYPE, routeInfo, typeInfo } from '../lib/constants.js'
import Badge from '../components/common/Badge.jsx'
import ViolationDetail from '../components/violation/ViolationDetail.jsx'

const ROUTES = [
  ['', 'Any status'],
  ['auto_confirmed', 'Confirmed (auto)'],
  ['vlm_confirmed', 'Confirmed (AI)'],
  ['human_review', 'Needs review'],
  ['abstain', 'No determination'],
]

export default function SearchPage() {
  const [type, setType] = useState('')
  const [route, setRoute] = useState('')
  const [plate, setPlate] = useState('')
  const [rows, setRows] = useState(null)
  const [open, setOpen] = useState(null)

  const run = async () => {
    setRows(await listViolations({ type, route, plate: plate.trim() }))
  }

  return (
    <>
      <div className="card">
        <div className="row">
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">Any type</option>
            {Object.keys(TYPE).map((k) => (
              <option key={k} value={k}>
                {TYPE[k].label}
              </option>
            ))}
          </select>
          <select value={route} onChange={(e) => setRoute(e.target.value)}>
            {ROUTES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <input value={plate} onChange={(e) => setPlate(e.target.value)} placeholder="plate contains…" />
          <button className="go" onClick={run}>
            Search
          </button>
        </div>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Status</th>
              <th>Conf</th>
              <th>Plate</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {rows && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No matches.
                </td>
              </tr>
            )}
            {rows === null && (
              <tr>
                <td colSpan={5} className="muted">
                  Run a search to see records.
                </td>
              </tr>
            )}
            {rows &&
              rows.map((v) => {
                const r = routeInfo(v.route)
                return (
                  <tr key={v.id} onClick={() => setOpen(v)}>
                    <td>
                      {typeInfo(v.type).icon} {typeInfo(v.type).label}
                    </td>
                    <td>
                      <Badge variant={r.variant}>{r.label}</Badge>
                    </td>
                    <td>{pct(v.scores?.fused)}%</td>
                    <td>{v.plate?.text || '—'}</td>
                    <td className="muted">{fmtDate(v.created_at)}</td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>

      {open && <ViolationDetail violation={open} onClose={() => setOpen(null)} />}
    </>
  )
}
