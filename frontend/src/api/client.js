// All requests go through Vite's proxy: /api → http://localhost:8000/api

const STATUS_MESSAGES = {
  409: 'That alias is already taken. Please choose a different one.',
  429: 'Too many requests — wait a moment and try again.',
  404: 'Short URL not found.',
  422: 'Invalid input. Please check your URL and try again.',
  500: 'Server error. Please try again later.',
}

function humanMessage(status, fallback) {
  return STATUS_MESSAGES[status] ?? fallback ?? `Unexpected error (${status}).`
}

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new Error('Could not reach the server. Check your connection and try again.')
  }

  if (res.status === 204) return null

  let body = null
  const ct = res.headers.get('content-type') ?? ''
  if (ct.includes('application/json')) {
    body = await res.json()
  }

  if (!res.ok) {
    const detail =
      body?.detail ??
      (typeof body === 'string' ? body : null)
    throw new Error(humanMessage(res.status, detail))
  }

  return body
}

export const api = {
  shorten({ url, expires_in_days, custom_code }) {
    const payload = { url }
    if (expires_in_days) payload.expires_in_days = expires_in_days
    if (custom_code) payload.custom_code = custom_code
    return request('/api/shorten', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  deleteUrl(shortCode) {
    return request(`/api/url/${shortCode}`, { method: 'DELETE' })
  },

  getAnalytics(shortCode) {
    return request(`/api/analytics/${shortCode}`)
  },
}
