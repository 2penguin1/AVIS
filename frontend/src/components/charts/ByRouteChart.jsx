import { Doughnut } from 'react-chartjs-2'
import { PALETTE, routeInfo } from '../../lib/constants.js'
import { baseOptions } from './chartSetup.js'

export default function ByRouteChart({ byRoute }) {
  const labels = Object.keys(byRoute || {}).map((k) => `${routeInfo(k).label} (${routeInfo(k).note || k})`)
  const data = Object.values(byRoute || {})
  return (
    <Doughnut
      options={baseOptions('By outcome')}
      data={{ labels, datasets: [{ data, backgroundColor: PALETTE }] }}
    />
  )
}
