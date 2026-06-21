import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import AnalyzePage from './pages/AnalyzePage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import SearchPage from './pages/SearchPage.jsx'
import { useTheme } from './context/ThemeContext.jsx'
import { ShieldAlert, Activity, LayoutList, Search, Sun, Moon } from 'lucide-react'

const TABS = [
  { to: '/analyze', label: 'Analyze a photo', icon: ShieldAlert },
  { to: '/analytics', label: 'Analytics', icon: Activity },
  { to: '/review', label: 'Review queue', icon: LayoutList },
  { to: '/search', label: 'Search records', icon: Search },
]

export default function App() {
  const { theme, toggleTheme } = useTheme()
  return (
    <>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          <div style={{ marginTop: '2px', color: 'var(--blue)' }}>
            <ShieldAlert size={36} strokeWidth={1.5} />
          </div>
          <div>
            <h1 style={{ fontSize: '28px', marginBottom: '6px', letterSpacing: '-0.5px' }}>AVIS Intelligence</h1>
            <p className="muted" style={{ fontSize: '15px', maxWidth: '500px', lineHeight: '1.5' }}>
              Automated road safety analysis powered by <b>Vision AI</b>. Detect violations, extract plates, and verify evidence in seconds.
            </p>
          </div>
        </div>
        <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>
      <nav>
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <t.icon size={16} style={{ marginBottom: '-3px', marginRight: '6px' }} />
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
      <footer>
        <p>Built by team panchayat</p>
      </footer>
    </>
  )
}
