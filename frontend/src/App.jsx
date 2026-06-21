import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import AnalyzePage from './pages/AnalyzePage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import SearchPage from './pages/SearchPage.jsx'

const TABS = [
  { to: '/analyze', label: 'Analyze a photo' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/review', label: 'Review queue' },
  { to: '/search', label: 'Search records' },
]

export default function App() {
  return (
    <>
      <header>
        <h1>AVIS — Traffic Violation Intelligence</h1>
        <p>
          Upload a traffic photo → the system detects road users, flags violations, reads
          plates, and <b>explains every decision</b> with confidence, law, and evidence.
        </p>
      </header>
      <nav>
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            {t.label}
          </NavLink>
        ))}
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/analyze" replace />} />
          <Route path="/analyze" element={<AnalyzePage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="*" element={<Navigate to="/analyze" replace />} />
        </Routes>
      </main>
    </>
  )
}
