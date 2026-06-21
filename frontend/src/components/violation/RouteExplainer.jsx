import { pct } from '../../lib/format.js'
import { routeInfo } from '../../lib/constants.js'
import { useRuntime } from '../../context/RuntimeContext.jsx'

// Plain-English "what action was taken and why" — mirrors core/pipeline._adjudicate.
export default function RouteExplainer({ v }) {
  const rt = useRuntime()
  const r = routeInfo(v.route)
  const fused = pct(v.scores?.fused)
  const autoT = pct(rt.auto_confirm_threshold ?? 0.85)
  const reviewT = pct(rt.review_threshold ?? 0.55)
  let why = ''
  switch (v.route) {
    case 'auto_confirmed':
      why = `Tier-A appearance violation with fused confidence ${fused}% ≥ ${autoT}% — no human or AI review needed.`
      break
    case 'vlm_confirmed':
      why = `Confirmed by the AI auditor (VLM) and fused confidence ${fused}% ≥ ${reviewT}%.`
      break
    case 'human_review':
      why = `Fused confidence ${fused}% is below the auto-confirm bar (or the tier forbids auto-confirm), so a human makes the final call.`
      break
    case 'abstain':
      why = `The photo doesn't carry enough evidence to decide — the system abstained rather than guess.`
      break
    default:
      why = ''
  }
  const icon =
    v.route === 'auto_confirmed' || v.route === 'vlm_confirmed' ? '✅' : v.route === 'human_review' ? '🧑‍⚖️' : '🚫'
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        {icon} {r.action}
      </div>
      <div className="muted">{why}</div>
    </div>
  )
}
