import { Bar } from 'react-chartjs-2'
import { PALETTE, typeInfo } from '../../lib/constants.js'
import { axisOptions } from './chartSetup.js'

export default function ByTypeChart({ byType }) {
  const labels = Object.keys(byType || {}).map((k) => typeInfo(k).label)
  const data = Object.values(byType || {})
  return (
    <Bar
      options={{ ...axisOptions('Violations by type'), plugins: { ...axisOptions('Violations by type').plugins, legend: { display: false } } }}
      data={{ labels, datasets: [{ data, backgroundColor: PALETTE }] }}
    />
  )
}
