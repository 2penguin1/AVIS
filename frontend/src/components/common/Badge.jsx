export default function Badge({ variant = 'mute', children, title }) {
  return (
    <span className={`badge ${variant}`} title={title}>
      {children}
    </span>
  )
}
