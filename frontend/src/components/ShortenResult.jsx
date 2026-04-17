import { useState } from 'react'
import { api } from '../api/client'
import { useClipboard } from '../hooks/useClipboard'
import { AnalyticsPanel } from './AnalyticsPanel'

function CopyIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
      <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
        clipRule="evenodd"
      />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
        clipRule="evenodd"
      />
    </svg>
  )
}

export function ShortenResult({ result, onReset, onError }) {
  const { copied, copy } = useClipboard()
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleted, setDeleted] = useState(false)

  const { short_code, short_url, original_url, expires_at } = result

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    try {
      await api.deleteUrl(short_code)
      setDeleted(true)
    } catch (err) {
      onError(err.message)
      setConfirmDelete(false)
    } finally {
      setDeleting(false)
    }
  }

  // Truncate long URLs for display
  function truncate(str, max = 60) {
    return str.length > max ? str.slice(0, max) + '…' : str
  }

  if (deleted) {
    return (
      <div className="space-y-4 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <TrashIcon />
        </div>
        <div>
          <p className="font-semibold text-gray-800">Link deleted</p>
          <p className="mt-1 text-sm text-gray-500">
            <span className="font-mono text-gray-700">{short_code}</span> has
            been permanently removed.
          </p>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="w-full rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2"
        >
          Shorten another URL
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Success header */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4 text-emerald-600"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">
          Your short link is ready
        </p>
      </div>

      {/* Short URL display + copy */}
      <div className="flex items-center gap-2 rounded-lg border border-teal-200 bg-teal-50 px-4 py-3">
        <a
          href={short_url}
          target="_blank"
          rel="noreferrer"
          className="min-w-0 flex-1 truncate font-semibold text-teal-700 hover:text-teal-900 hover:underline focus:outline-none focus-visible:underline"
        >
          {short_url}
        </a>
        <button
          type="button"
          onClick={() => copy(short_url)}
          aria-label={copied ? 'Copied!' : 'Copy short URL'}
          className={`flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-1 ${
            copied
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-teal-100 text-teal-700 hover:bg-teal-200'
          }`}
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Metadata */}
      <div className="space-y-1.5 rounded-lg bg-gray-50 px-4 py-3 text-sm">
        <div className="flex items-start gap-2">
          <span className="shrink-0 text-gray-400">Original</span>
          <span
            className="min-w-0 break-all text-gray-600"
            title={original_url}
          >
            {truncate(original_url)}
          </span>
        </div>
        {expires_at && (
          <div className="flex items-center gap-2">
            <span className="shrink-0 text-gray-400">Expires</span>
            <span className="text-gray-600">
              {new Date(expires_at).toLocaleString(undefined, {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}
            </span>
          </div>
        )}
      </div>

      {/* Analytics panel */}
      {showAnalytics && (
        <AnalyticsPanel
          shortCode={short_code}
          onClose={() => setShowAnalytics(false)}
        />
      )}

      {/* Action buttons */}
      <div className="flex flex-col gap-2">
        {!showAnalytics && (
          <button
            type="button"
            onClick={() => setShowAnalytics(true)}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50 hover:text-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-1"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 003 0v-13A1.5 1.5 0 0015.5 2zM9.5 6A1.5 1.5 0 008 7.5v9a1.5 1.5 0 003 0v-9A1.5 1.5 0 009.5 6zM3.5 10A1.5 1.5 0 002 11.5v5a1.5 1.5 0 003 0v-5A1.5 1.5 0 003.5 10z" />
            </svg>
            View Analytics
          </button>
        )}

        <div className="grid grid-cols-2 gap-2">
          {/* Delete with confirmation */}
          {confirmDelete ? (
            <>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center justify-center gap-1.5 rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-60"
              >
                {deleting ? 'Deleting…' : 'Confirm delete'}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={onReset}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 shadow-sm transition-colors hover:bg-gray-50 hover:text-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-1"
              >
                Shorten another
              </button>
              <button
                type="button"
                onClick={handleDelete}
                aria-label="Delete this short URL"
                className="flex items-center justify-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-600 shadow-sm transition-colors hover:bg-red-50 hover:text-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-1"
              >
                <TrashIcon />
                Delete
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
