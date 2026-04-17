import { useState } from 'react'
import { ShortenForm } from './components/ShortenForm'
import { ShortenResult } from './components/ShortenResult'
import { ErrorBanner } from './components/ErrorBanner'
import './index.css'

function LinkIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-6 w-6 text-white"
      aria-hidden="true"
    >
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
    </svg>
  )
}

export default function App() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  function handleSuccess(data) {
    setResult(data)
    setError(null)
  }

  function handleError(msg) {
    setError(msg)
  }

  function handleReset() {
    setResult(null)
    setError(null)
  }

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        background: 'linear-gradient(135deg, #f0fdfa 0%, #f0fdf4 50%, #ecfdf5 100%)',
      }}
    >
      {/* Main content */}
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-xl">
          {/* App header */}
          <div className="mb-8 text-center">
            <div className="mb-4 flex justify-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-600 shadow-lg shadow-teal-200">
                <LinkIcon />
              </div>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Snip
            </h1>
            <p className="mt-2 text-sm text-gray-500">
              Paste a long URL and get a clean, shareable short link in seconds.
            </p>
          </div>

          {/* Card */}
          <div className="rounded-2xl border border-white/80 bg-white/90 p-6 shadow-xl shadow-teal-100/40 backdrop-blur-sm sm:p-8">
            {/* Error banner */}
            {error && (
              <div className="mb-5">
                <ErrorBanner
                  message={error}
                  onDismiss={() => setError(null)}
                />
              </div>
            )}

            {result ? (
              <ShortenResult
                result={result}
                onReset={handleReset}
                onError={handleError}
              />
            ) : (
              <ShortenForm onSuccess={handleSuccess} onError={handleError} />
            )}
          </div>

          {/* Tips beneath card */}
          {!result && (
            <ul className="mt-5 flex flex-wrap justify-center gap-x-6 gap-y-1">
              {[
                'Custom aliases supported',
                'Set an expiry date',
                'Click analytics included',
              ].map((tip) => (
                <li
                  key={tip}
                  className="flex items-center gap-1.5 text-xs text-gray-400"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="h-3.5 w-3.5 text-teal-400"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M12.416 3.376a.75.75 0 01.208 1.04l-5 7.5a.75.75 0 01-1.154.114l-3-3a.75.75 0 011.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 011.04-.207z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {tip}
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-5 text-center text-xs text-gray-400">
        <p>
          Built with{' '}
          <span className="text-teal-500">FastAPI + React</span>
          {' · '}
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hover:text-teal-500 hover:underline focus:outline-none focus-visible:underline"
          >
            Source
          </a>
        </p>
      </footer>
    </div>
  )
}
