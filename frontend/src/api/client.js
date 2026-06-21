// Single source for all HTTP. Root-relative paths work in dev (Vite proxy) and prod (same origin).

async function getJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const getRuntime = () => getJSON('/runtime')
export const getAnalytics = () => getJSON('/analytics')
export const getImage = (id) => getJSON(`/images/${id}`)
export const getViolation = (id) => getJSON(`/violations/${id}`)
export const getReviewQueue = () => getJSON('/review-queue')

export const uploadImage = async (file, cameraId) => {
  const fd = new FormData()
  fd.append('file', file)
  const qs = cameraId ? `?camera_id=${encodeURIComponent(cameraId)}` : ''
  const r = await fetch(`/images${qs}`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export const listViolations = (params = {}) => {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) qs.set(k, v)
  return getJSON(`/violations?${qs.toString()}`)
}

export const reviewViolation = (id, decision, reviewer, note) =>
  postJSON(`/violations/${id}/review`, { decision, reviewer, note })

// Poll an image until processing finishes (or 90 ticks).
export const pollImage = async (id, onTick) => {
  for (let i = 0; i < 90; i++) {
    const d = await getImage(id)
    onTick?.(d)
    if (['completed', 'failed', 'undeterminable'].includes(d.status)) return d
    await new Promise((r) => setTimeout(r, 1200))
  }
  return getImage(id)
}
