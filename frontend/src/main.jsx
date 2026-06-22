import React from 'react'
import ReactDOM from 'react-dom/client'
// HashRouter so deep links + refreshes work when served by FastAPI StaticFiles (no catch-all needed).
import { HashRouter } from 'react-router-dom'
import App from './App.jsx'
import { RuntimeProvider } from './context/RuntimeContext.jsx'
import { ThemeProvider } from './context/ThemeContext.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <ThemeProvider>
        <RuntimeProvider>
          <App />
        </RuntimeProvider>
      </ThemeProvider>
    </HashRouter>
  </React.StrictMode>,
)
