import { useRuntime } from '../../context/RuntimeContext.jsx'

// Shows the plate, or a precise reason it's absent (OCR off vs nothing detected).
export default function PlateChip({ plate }) {
  const rt = useRuntime()
  if (plate && plate.text) {
    return (
      <span>
        <span className="plate">{plate.text}</span>{' '}
        {plate.regex_ok ? (
          <span style={{ color: '#5ee08b' }}>✓ valid format</span>
        ) : (
          <span className="muted">(format unverified)</span>
        )}
      </span>
    )
  }
  if (rt && rt.plate_ocr_enabled === false)
    return <span className="muted">plate reading disabled</span>
  return <span className="muted">no plate detected</span>
}
