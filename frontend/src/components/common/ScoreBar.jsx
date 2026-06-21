import { clamp01, pct } from '../../lib/format.js'

// One labeled confidence bar. `off` greys it out (e.g. VLM not used).
export default function ScoreBar({ label, value, color = '#2563eb', fused = false, off = false }) {
  if (off) {
    return (
      <div className="sbrow off">
        <span className="lbl">{label}</span>
        <span className="muted">not used</span>
        <span className="val">—</span>
      </div>
    )
  }
  return (
    <div className={`sbrow ${fused ? 'fused' : ''}`}>
      <span className="lbl">{label}</span>
      <span className="bar">
        <i style={{ width: `${pct(clamp01(value))}%`, background: color }} />
      </span>
      <span className="val">{pct(clamp01(value))}%</span>
    </div>
  )
}
