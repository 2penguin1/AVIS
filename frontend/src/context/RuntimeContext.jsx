import { createContext, useContext, useEffect, useState } from 'react'
import { getRuntime } from '../api/client.js'

const RuntimeContext = createContext({
  plate_ocr_enabled: true,
  vlm_enabled: true,
  auto_confirm_threshold: 0.85,
  review_threshold: 0.55,
})

export function RuntimeProvider({ children }) {
  const [runtime, setRuntime] = useState(null)
  useEffect(() => {
    getRuntime().then(setRuntime).catch(() => setRuntime({}))
  }, [])
  return <RuntimeContext.Provider value={runtime || {}}>{children}</RuntimeContext.Provider>
}

export const useRuntime = () => useContext(RuntimeContext)

export function RuntimeBanner() {
  const rt = useRuntime()
  const msgs = []
  if (rt && rt.plate_ocr_enabled === false)
    msgs.push('Plate reading is OFF (set PLATE_PROVIDER=fastalpr in .env to enable).')
  if (rt && rt.vlm_enabled === false)
    msgs.push('AI verification (VLM) is OFF — ambiguous cases route to human review.')
  if (!msgs.length) return null
  return (
    <div className="banner warnb">
      {msgs.map((m, i) => (
        <div key={i}>⚠️ {m}</div>
      ))}
    </div>
  )
}
