import { useState } from 'react'
import { api } from '../api/client'

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

export function ShortenForm({ onSuccess, onError }) {
  const [url, setUrl] = useState('')
  const [customCode, setCustomCode] = useState('')
  const [expiresInDays, setExpiresInDays] = useState('')
  const [loading, setLoading] = useState(false)
  const [fieldError, setFieldError] = useState('')

  function validateUrl(value) {
    try {
      const parsed = new URL(value)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        return 'URL must start with http:// or https://'
      }
      return ''
    } catch {
      return 'Please enter a valid URL (e.g. https://example.com)'
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    onError(null)

    const urlErr = validateUrl(url)
    if (urlErr) {
      setFieldError(urlErr)
      return
    }
    setFieldError('')

    const days = expiresInDays ? parseInt(expiresInDays, 10) : undefined
    if (expiresInDays && (isNaN(days) || days < 1 || days > 3650)) {
      setFieldError('Expiry must be between 1 and 3650 days.')
      return
    }

    setLoading(true)
    try {
      const result = await api.shorten({
        url,
        custom_code: customCode || undefined,
        expires_in_days: days,
      })
      onSuccess(result)
      setUrl('')
      setCustomCode('')
      setExpiresInDays('')
    } catch (err) {
      onError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const inputBase =
    'w-full rounded-lg border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 transition-colors focus:border-teal-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/40 disabled:cursor-not-allowed disabled:opacity-50'

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {/* URL input */}
      <div>
        <label
          htmlFor="url"
          className="mb-1.5 block text-sm font-medium text-gray-700"
        >
          Destination URL
        </label>
        <input
          id="url"
          type="url"
          required
          className={inputBase}
          placeholder="https://your-very-long-url.com/goes/here"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            if (fieldError) setFieldError('')
          }}
          disabled={loading}
          aria-describedby={fieldError ? 'url-error' : undefined}
          aria-invalid={fieldError ? 'true' : undefined}
        />
      </div>

      {/* Optional fields row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="custom-code"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Custom alias{' '}
            <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-gray-400">
              snip/
            </span>
            <input
              id="custom-code"
              type="text"
              className={`${inputBase} pl-11`}
              placeholder="my-link"
              value={customCode}
              onChange={(e) => setCustomCode(e.target.value)}
              disabled={loading}
              maxLength={64}
              pattern="[a-zA-Z0-9_-]+"
              title="Letters, numbers, hyphens and underscores only"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="expires"
            className="mb-1.5 block text-sm font-medium text-gray-700"
          >
            Expires in{' '}
            <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <div className="relative">
            <input
              id="expires"
              type="number"
              className={`${inputBase} pr-12`}
              placeholder="30"
              value={expiresInDays}
              onChange={(e) => {
                setExpiresInDays(e.target.value)
                if (fieldError) setFieldError('')
              }}
              disabled={loading}
              min={1}
              max={3650}
            />
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-gray-400">
              days
            </span>
          </div>
        </div>
      </div>

      {/* Inline field error */}
      {fieldError && (
        <p id="url-error" role="alert" className="text-sm text-red-600">
          {fieldError}
        </p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !url.trim()}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 active:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading && <Spinner />}
        {loading ? 'Shortening…' : 'Shorten URL'}
      </button>
    </form>
  )
}
