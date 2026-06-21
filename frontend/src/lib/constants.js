// Central interpretability copy — the difference between "raw" and "readable".

export const TYPE = {
  HELMET_NON_COMPLIANCE: { label: 'No Helmet', icon: '🪖' },
  TRIPLE_RIDING: { label: 'Triple Riding', icon: '👥' },
  SEATBELT_NON_COMPLIANCE: { label: 'No Seatbelt', icon: '🔒' },
  STOP_LINE_VIOLATION: { label: 'Stop-line Crossing', icon: '🛑' },
  RED_LIGHT_VIOLATION: { label: 'Red-light Violation', icon: '🚦' },
  ILLEGAL_PARKING: { label: 'Illegal Parking', icon: '🅿️' },
  WRONG_SIDE_DRIVING: { label: 'Wrong-side Driving', icon: '↔️' },
}

export const ROUTE = {
  auto_confirmed: {
    label: 'Confirmed', variant: 'ok', note: 'auto',
    action: 'Auto-confirmed e-challan',
  },
  vlm_confirmed: {
    label: 'Confirmed', variant: 'ok', note: 'AI-verified',
    action: 'Confirmed after AI verification',
  },
  human_review: {
    label: 'Needs review', variant: 'warn', note: '',
    action: 'Routed to a human reviewer',
  },
  abstain: {
    label: 'No determination', variant: 'mute', note: '',
    action: 'Abstained — evidence insufficient',
  },
}

// What each evidence-sufficiency tier means, in plain English.
export const TIER_INFO = {
  A: 'Appearance — provable from the photo alone (e.g. helmet, triple riding). May auto-confirm.',
  B: 'Hard appearance — e.g. seatbelt; unreliable from a traffic cam, so always verified before issuing.',
  C: 'Spatial — needs per-camera calibration (stop-line, red-light, parking). Never auto-confirmed.',
  D: 'Temporal — needs video to prove (wrong-side driving). A single frame abstains by design.',
}

export const SUFFICIENCY_INFO = {
  sufficient: 'The evidence is strong enough to stand on its own.',
  candidate: 'A credible candidate that still needs confirmation.',
  insufficient: 'Not enough evidence in this photo to decide — the system abstained.',
}

export const typeInfo = (t) => TYPE[t] || { label: t, icon: '⚠️' }
export const routeInfo = (r) => ROUTE[r] || { label: r, variant: 'mute', note: '', action: r }

// Chart palette
export const PALETTE = ['#2563eb', '#16a34a', '#d97706', '#64748b', '#9333ea', '#dc2626', '#0891b2']
