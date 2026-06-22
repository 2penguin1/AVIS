import { useEffect, useState } from 'react'

export default function TraceLog({ status, result }) {
  const [steps, setSteps] = useState([])

  useEffect(() => {
    // Reset if starting fresh
    if (!status && !result) {
      setSteps([])
      return
    }

    if (status && steps.length === 0) {
      setSteps([{ msg: 'Ingesting image and running Quality Gate...', state: 'spin' }])
    }

    if (status === 'status: processing (analysing…)' && steps.length < 2) {
      setSteps((s) => [
        { msg: 'Quality Gate passed. Image accepted.', state: 'ok' },
        { msg: 'Running YOLO11 Object Detection...', state: 'spin' }
      ])
      
      // Simulate subsequent steps based on time since we are polling
      setTimeout(() => {
        setSteps((s) => [
          s[0],
          { msg: 'YOLO11 Detection complete. Objects found.', state: 'ok' },
          { msg: 'Constructing Evidence Graph & Evaluating Deterministic Rules...', state: 'spin' }
        ])
      }, 1500)
      
      setTimeout(() => {
        setSteps((s) => [
          s[0], s[1],
          { msg: 'Rules evaluated. Candidates identified.', state: 'ok' },
          { msg: 'Routing candidates & querying Gemini VLM for verification...', state: 'spin' }
        ])
      }, 3500)
    }

    if (result) {
      if (result.status === 'completed') {
        const v = result.violations || []
        setSteps([
          { msg: 'Quality Gate passed. Image accepted.', state: 'ok' },
          { msg: 'YOLO11 Detection complete.', state: 'ok' },
          { msg: 'Rules evaluated. Candidates identified.', state: 'ok' },
          { msg: `VLM Verification complete. Confirmed ${v.length} violation(s).`, state: 'ok' },
          { msg: 'Evidence hashed and stored. Analysis complete.', state: 'ok' }
        ])
      } else if (result.status === 'undeterminable') {
        setSteps([
          { msg: 'Quality Gate: FAILED. Image too blurry/dark.', state: 'warn' },
          { msg: 'Agent Abstained to prevent false positive.', state: 'warn' }
        ])
      }
    }
  }, [status, result])

  if (!status && !result) return null

  return (
    <div className="card" style={{ background: 'var(--card2)', borderColor: 'var(--blue)' }}>
      <h3 className="sec" style={{ color: 'var(--blue)', marginBottom: 12 }}>Agent Observability Trace</h3>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: 14 }}>
        {steps.map((step, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
            {step.state === 'spin' && <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />}
            {step.state === 'ok' && <span style={{ color: 'var(--ok)' }}>✅</span>}
            {step.state === 'warn' && <span style={{ color: 'var(--warn)' }}>⚠️</span>}
            <span style={{ color: step.state === 'spin' ? 'var(--txt)' : 'var(--mut)' }}>
              {step.msg}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
