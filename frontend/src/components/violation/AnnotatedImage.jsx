// Server-rendered annotated evidence (boxes coloured by disposition). Cache-busted.
export default function AnnotatedImage({ url, alt = 'annotated evidence' }) {
  if (!url) return null
  const src = `${url}${url.includes('?') ? '&' : '?'}t=${encodeURIComponent(url)}`
  return <img className="annot" src={src} alt={alt} />
}
