import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js'

ChartJS.register(
  BarElement,
  ArcElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
)

export const baseOptions = (title) => ({
  responsive: true,
  plugins: {
    title: { display: true, text: title, color: '#e6edf6' },
    legend: { labels: { color: '#aab6c8' } },
  },
})

export const axisOptions = (title) => ({
  ...baseOptions(title),
  scales: {
    x: { ticks: { color: '#93a4bd' }, grid: { color: '#1d273b' } },
    y: { ticks: { color: '#93a4bd' }, grid: { color: '#1d273b' }, beginAtZero: true },
  },
})
