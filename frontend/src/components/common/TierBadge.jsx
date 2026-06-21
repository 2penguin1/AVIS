import { TIER_INFO } from '../../lib/constants.js'

export default function TierBadge({ tier }) {
  return (
    <span className="badge tier" title={TIER_INFO[tier] || ''}>
      Tier {tier}
    </span>
  )
}
