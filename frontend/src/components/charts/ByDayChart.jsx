import { Line } from 'react-chartjs-2'
import { axisOptions } from './chartSetup.js'

export default function ByDayChart({ byDay }) {
  const labels = Object.keys(byDay || {})
  const data = Object.values(byDay || {})
  return (
    <Line
      options={{ ...axisOptions('Violations per day'), plugins: { ...axisOptions('Violations per day').plugins, legend: { display: false } } }}
      data={{
        labels,
        datasets: [
          {
            data,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,.2)',
            tension: 0.3,
            fill: true,
          },
        ],
      }}
    />
  )
}
