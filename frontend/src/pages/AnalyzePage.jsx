import { useRef, useState } from 'react'
import { UploadCloud, Camera, BrainCircuit, Scale } from 'lucide-react'
import { pollImage, uploadImage } from '../api/client.js'
import { RuntimeBanner } from '../context/RuntimeContext.jsx'
import AnnotatedImage from '../components/violation/AnnotatedImage.jsx'
import ViolationCard from '../components/violation/ViolationCard.jsx'
import ViolationDetail from '../components/violation/ViolationDetail.jsx'
import ResultSummary from '../components/violation/ResultSummary.jsx'
import TraceLog from '../components/common/TraceLog.jsx'
import Spinner from '../components/common/Spinner.jsx'

export default function AnalyzePage() {
  const fileRef = useRef(null)
  const [camera, setCamera] = useState('cam_demo')
  const [fileName, setFileName] = useState('Choose a file')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [open, setOpen] = useState(null)

  const analyse = async () => {
    const f = fileRef.current?.files?.[0]
    if (!f) return alert('Choose an image first.')
    setBusy(true)
    setResult(null)
    setStatus('uploading…')
    try {
      const { image_id } = await uploadImage(f, camera.trim())
      const d = await pollImage(image_id, (x) =>
        setStatus(`status: ${x.status}${x.status === 'processing' ? ' (analysing…)' : ''}`),
      )
      setResult(d)
    } catch (e) {
      setStatus(`error: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  const v = result?.violations || []
  const isIdle = !status && !result

  return (
    <>
      {isIdle && (
        <div style={{ textAlign: 'center', marginBottom: 32, marginTop: 16 }}>
          <h2 style={{ fontSize: '28px', marginBottom: 12 }}>Ready for Analysis</h2>
          <p className="muted" style={{ fontSize: '16px', maxWidth: 600, margin: '0 auto' }}>
            Select a traffic photo to instantly detect road users, evaluate rule violations, and verify evidence.
          </p>
        </div>
      )}

      <div className="card" style={{ padding: isIdle ? 32 : 16, display: 'flex', flexDirection: 'column', alignItems: isIdle ? 'center' : 'stretch' }}>
        <div className="row" style={{ justifyContent: isIdle ? 'center' : 'flex-start', width: '100%', flexWrap: 'wrap' }}>
          <label className="custom-upload">
            <UploadCloud size={18} />
            {fileName}
            <input 
              type="file" 
              ref={fileRef} 
              accept="image/*" 
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) setFileName(f.name)
              }}
            />
          </label>
          <input value={camera} onChange={(e) => setCamera(e.target.value)} placeholder="camera id (e.g. cam_demo)" />
          <button className="go" onClick={analyse} disabled={busy}>
            {busy ? <Spinner /> : 'Analyse'}
          </button>
          <span className="muted">{status}</span>
        </div>
        <div style={{ marginTop: 12, textAlign: isIdle ? 'center' : 'left', width: '100%' }}>
          <RuntimeBanner />
        </div>
      </div>

      {isIdle && (
        <div className="feature-grid">
          <div className="feature-card">
            <Camera size={32} color="var(--blue)" />
            <h3 style={{ margin: 0 }}>Instant Capture</h3>
            <p className="muted" style={{ margin: 0, fontSize: 14 }}>Upload images from any camera angle. The system automatically calibrates and assesses quality.</p>
          </div>
          <div className="feature-card">
            <BrainCircuit size={32} color="var(--ok)" />
            <h3 style={{ margin: 0 }}>AI Processing</h3>
            <p className="muted" style={{ margin: 0, fontSize: 14 }}>Powered by YOLO11 object detection and deterministic spatial rule evaluation.</p>
          </div>
          <div className="feature-card">
            <Scale size={32} color="var(--warn)" />
            <h3 style={{ margin: 0 }}>VLM Verification</h3>
            <p className="muted" style={{ margin: 0, fontSize: 14 }}>Secondary verification via Gemini Vision to ensure undeniable evidence and prevent false positives.</p>
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <TraceLog status={status} result={result} />
      </div>

      {result && result.status === 'undeterminable' && (
        <div className="card">
          <div className="banner warnb" style={{ margin: 0 }}>
            Image quality too low to judge — the system <b>abstained</b>. This is intentional
            (abstaining beats a false accusation), not an error.
          </div>
        </div>
      )}
      {result && result.status === 'failed' && (
        <div className="card">
          <div className="banner warnb">Processing failed — check the server log.</div>
        </div>
      )}

      {result && result.status === 'completed' && (
        <div className="card">
          <ResultSummary violations={v} />
          {v.length === 0 && (
            <div className="banner good">
              No violations detected ✅
            </div>
          )}
          {v.map((x) => (
            <ViolationCard key={x.id} v={x} onOpen={setOpen} />
          ))}
          <AnnotatedImage url={result.annotated_url} />
        </div>
      )}

      <div className="card legend">
        <b>How to read results</b>
        <br />
        <span className="badge ok">Confirmed</span> the system is confident (auto or AI-verified) ·{' '}
        <span className="badge warn">Needs review</span> sent to a human ·{' '}
        <span className="badge mute">No determination</span> the photo couldn't prove it.
        <br />
        Tiers: <b>A</b> provable from a photo (helmet, triple riding) · <b>B</b> hard (seatbelt) ·{' '}
        <b>C</b> needs camera calibration (stop-line, red-light, parking) · <b>D</b> needs video (wrong-side).
      </div>

      {open && <ViolationDetail violation={open} onClose={() => setOpen(null)} />}
    </>
  )
}
