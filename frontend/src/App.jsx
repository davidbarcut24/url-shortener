import { useState } from "react";

const API = "http://localhost:8000";

function App() {
  const [url, setUrl] = useState("");
  const [expiresInDays, setExpiresInDays] = useState("");
  const [result, setResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function shorten(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setAnalytics(null);
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/shorten`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          expires_in_days: expiresInDays ? parseInt(expiresInDays) : null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Something went wrong");
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchAnalytics(code) {
    const res = await fetch(`${API}/api/analytics/${code}`);
    if (res.ok) setAnalytics(await res.json());
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>URL Shortener</h1>

        <form onSubmit={shorten} style={styles.form}>
          <input
            style={styles.input}
            type="text"
            placeholder="https://your-long-url.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
          <input
            style={{ ...styles.input, width: "160px", flex: "none" }}
            type="number"
            placeholder="Expires in days"
            value={expiresInDays}
            onChange={(e) => setExpiresInDays(e.target.value)}
            min={1}
          />
          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? "Shortening…" : "Shorten"}
          </button>
        </form>

        {error && <p style={styles.error}>{error}</p>}

        {result && (
          <div style={styles.result}>
            <p style={styles.label}>Your short link:</p>
            <a href={result.short_url} target="_blank" rel="noreferrer" style={styles.link}>
              {result.short_url}
            </a>
            <p style={styles.meta}>
              Original: <span style={styles.muted}>{result.original_url}</span>
            </p>
            {result.expires_at && (
              <p style={styles.meta}>
                Expires: <span style={styles.muted}>{new Date(result.expires_at).toLocaleString()}</span>
              </p>
            )}
            <button
              style={{ ...styles.button, marginTop: "12px", background: "#374151" }}
              onClick={() => fetchAnalytics(result.short_code)}
            >
              View Analytics
            </button>
          </div>
        )}

        {analytics && (
          <div style={styles.analytics}>
            <h2 style={styles.analyticsTitle}>Analytics — {analytics.short_code}</h2>
            <div style={styles.stat}>
              <span style={styles.statNum}>{analytics.click_count}</span>
              <span style={styles.statLabel}>total clicks</span>
            </div>
            <p style={styles.meta}>
              Created: <span style={styles.muted}>{new Date(analytics.created_at).toLocaleString()}</span>
            </p>
            {analytics.expires_at && (
              <p style={styles.meta}>
                Expires: <span style={styles.muted}>{new Date(analytics.expires_at).toLocaleString()}</span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif" },
  card: { background: "#1e293b", borderRadius: "16px", padding: "40px", width: "100%", maxWidth: "580px", boxShadow: "0 25px 50px rgba(0,0,0,0.5)" },
  title: { color: "#f1f5f9", fontSize: "28px", marginBottom: "24px", fontWeight: 700 },
  form: { display: "flex", gap: "8px", flexWrap: "wrap" },
  input: { flex: 1, minWidth: "200px", padding: "10px 14px", borderRadius: "8px", border: "1px solid #334155", background: "#0f172a", color: "#f1f5f9", fontSize: "14px", outline: "none" },
  button: { padding: "10px 20px", borderRadius: "8px", border: "none", background: "#6366f1", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: "14px" },
  error: { color: "#f87171", marginTop: "12px", fontSize: "14px" },
  result: { marginTop: "24px", borderTop: "1px solid #334155", paddingTop: "20px" },
  label: { color: "#94a3b8", fontSize: "12px", marginBottom: "4px" },
  link: { color: "#818cf8", fontSize: "18px", fontWeight: 600, wordBreak: "break-all" },
  meta: { color: "#64748b", fontSize: "13px", marginTop: "8px" },
  muted: { color: "#94a3b8" },
  analytics: { marginTop: "20px", borderTop: "1px solid #334155", paddingTop: "20px" },
  analyticsTitle: { color: "#f1f5f9", fontSize: "16px", fontWeight: 600, marginBottom: "12px" },
  stat: { display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "12px" },
  statNum: { color: "#818cf8", fontSize: "36px", fontWeight: 700 },
  statLabel: { color: "#94a3b8", fontSize: "14px" },
};

export default App;
