import { useRuntime } from '../../context/RuntimeContext.jsx'
import ScoreBar from './ScoreBar.jsx'

// Explains HOW the fused confidence was reached, source by source.
export default function ScoreBreakdown({ scores }) {
  const rt = useRuntime()
  if (!scores) return null
  const fused = Number(scores.fused) || 0
  const autoT = rt.auto_confirm_threshold ?? 0.85
  const reviewT = rt.review_threshold ?? 0.55
  const fusedColor = fused >= autoT ? '#16a34a' : fused >= reviewT ? '#d97706' : '#64748b'
  const note =
    fused >= autoT
      ? `≥ ${autoT} auto-confirm threshold ✓`
      : fused >= reviewT
        ? `between ${reviewT} and ${autoT} — needs a second opinion`
        : `below ${reviewT} review threshold`

  return (
    <div>
      <ScoreBar label="Detection" value={scores.detection} />
      <ScoreBar label="Rule" value={scores.rule} />
      <ScoreBar label="Attribute" value={scores.attribute} />
      <ScoreBar label="VLM" value={scores.vlm} off={scores.vlm == null} />
      <ScoreBar label="Fused" value={fused} color={fusedColor} fused />
      <div className="muted" style={{ marginTop: 4 }}>
        {note}
      </div>
    </div>
  )
}
