import { useReducer, useEffect } from 'react'
import { api } from '../api/client'

function SkeletonLine({ className = '' }) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 ${className}`}
      aria-hidden="true"
    />
  )
}

function StatBlock({ value, label }) {
  return (
    <div className="flex flex-col items-center rounded-xl bg-teal-50 px-6 py-4 text-center">
      <span className="text-4xl font-bold tracking-tight text-teal-600">
        {value.toLocaleString()}
      </span>
      <span className="mt-1 text-xs font-medium uppercase tracking-wider text-teal-400">
        {label}
      </span>
    </div>
  )
}

function DateRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-700">
        {new Date(value).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })}
      </span>
    </div>
  )
}

const initialState = { data: null, loading: true, error: null }

function reducer(state, action) {
  switch (action.type) {
    case 'LOADING':
      return { data: null, loading: true, error: null }
    case 'SUCCESS':
      return { data: action.payload, loading: false, error: null }
    case 'ERROR':
      return { data: null, loading: false, error: action.payload }
    default:
      return state
  }
}

export function AnalyticsPanel({ shortCode, onClose }) {
  const [{ data, loading, error }, dispatch] = useReducer(reducer, initialState)

  useEffect(() => {
    if (!shortCode) return
    let cancelled = false

    dispatch({ type: 'LOADING' })

    api
      .getAnalytics(shortCode)
      .then((result) => {
        if (!cancelled) dispatch({ type: 'SUCCESS', payload: result })
      })
      .catch((err) => {
        if (!cancelled) dispatch({ type: 'ERROR', payload: err.message })
      })

    return () => {
      cancelled = true
    }
  }, [shortCode])

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Bar chart icon */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-5 w-5 text-teal-500"
            aria-hidden="true"
          >
            <path d="M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 003 0v-13A1.5 1.5 0 0015.5 2zM9.5 6A1.5 1.5 0 008 7.5v9a1.5 1.5 0 003 0v-9A1.5 1.5 0 009.5 6zM3.5 10A1.5 1.5 0 002 11.5v5a1.5 1.5 0 003 0v-5A1.5 1.5 0 003.5 10z" />
          </svg>
          <h2 className="text-sm font-semibold text-gray-800">
            Analytics —{' '}
            <span className="font-mono text-teal-600">{shortCode}</span>
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close analytics"
          className="rounded p-1 text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading analytics…">
          <SkeletonLine className="mx-auto h-16 w-36" />
          <SkeletonLine className="h-4 w-full" />
          <SkeletonLine className="h-4 w-4/5" />
          <SkeletonLine className="h-4 w-3/5" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {/* Data */}
      {!loading && data && (
        <div className="space-y-3">
          <StatBlock value={data.click_count} label="total clicks" />
          <div className="divide-y divide-gray-100 rounded-lg bg-white px-4">
            <DateRow label="Created" value={data.created_at} />
            <DateRow label="Expires" value={data.expires_at} />
          </div>
        </div>
      )}
    </div>
  )
}
