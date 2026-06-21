export const pct = (x) => Math.round((Number(x) || 0) * 100)

export const fmtDate = (iso) => {
  if (!iso) return '—'
  return String(iso).replace('T', ' ').slice(0, 16)
}

export const shortHash = (h) => {
  if (!h) return '—'
  const s = String(h)
  return s.length > 20 ? `${s.slice(0, 14)}…${s.slice(-6)}` : s
}

export const clamp01 = (x) => Math.max(0, Math.min(1, Number(x) || 0))
