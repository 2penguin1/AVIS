import { useRef, useState } from 'react'
import { pollImage, uploadImage } from '../api/client.js'
import { RuntimeBanner } from '../context/RuntimeContext.jsx'
import AnnotatedImage from '../components/violation/AnnotatedImage.jsx'
import ViolationCard from '../components/violation/ViolationCard.jsx'
import ViolationDetail from '../components/violation/ViolationDetail.jsx'
import Spinner from '../components/common/Spinner.jsx'

export default function AnalyzePage() {
  const fileRef = useRef(null)
  const [camera, setCamera] = useState('cam_demo')
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
  const confirmed = v.filter((x) => ['auto_confirmed', 'vlm_confirmed'].includes(x.route)).length
  const review = v.filter((x) => x.route === 'human_review').length
  const abstain = v.filter((x) => x.route === 'abstain').length

  return (
    <>
      <div className="card">
        <div className="row">
          <input type="file" ref={fileRef} accept="image/*" />
          <input value={camera} onChange={(e) => setCamera(e.target.value)} placeholder="camera id (e.g. cam_demo)" />
          <button className="go" onClick={analyse} disabled={busy}>
            {busy ? <Spinner /> : 'Analyse'}
          </button>
          <span className="muted">{status}</span>
        </div>
        <div style={{ marginTop: 12 }}>
          <RuntimeBanner />
        </div>
      </div>

      {result && result.status === 'undeterminable' && (
        <div className="card">
          <div className="banner warnb">
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
          <div className={`banner ${v.length ? 'info' : 'good'}`}>
            {v.length ? (
              <>
                <b>{v.length}</b> violation(s):{' '}
                <b style={{ color: '#5ee08b' }}>{confirmed}</b> confirmed ·{' '}
                <b style={{ color: '#ffc560' }}>{review}</b> need review · {abstain} no-determination.
                Click a card for the full evidence breakdown.
              </>
            ) : (
              'No violations detected ✅'
            )}
          </div>
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
