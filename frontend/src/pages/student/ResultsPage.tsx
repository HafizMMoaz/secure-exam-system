import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { BarChart3, ClipboardList, LogOut, PlayCircle } from "lucide-react"
import client from "../../api/client"
import { getErrorMessage } from "../../api/errors"
import { useAuth } from "../../hooks/useAuth"
import type { ApiResponse, StudentExamResult } from "../../types"

type StudentResultsResponse = ApiResponse<{ results: StudentExamResult[]; count: number }>

function formatLocalDateTime(value: string | null) {
  if (!value) return "-"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatPercent(score: number, total: number) {
  if (!total) return "0%"
  return `${Math.round((score / total) * 100)}%`
}

export default function ResultsPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [results, setResults] = useState<StudentExamResult[]>([])

  useEffect(() => {
    let cancelled = false

    const loadResults = async () => {
      setLoading(true)
      setError("")
      try {
        const response = await client.get<StudentResultsResponse>("/api/questions/exams/results/me")
        if (!cancelled) {
          setResults(response.data.data.results || [])
        }
      } catch (resultsError) {
        if (!cancelled) {
          setError(getErrorMessage(resultsError))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadResults()
    return () => {
      cancelled = true
    }
  }, [])

  const totals = useMemo(() => {
    const examsTaken = results.length
    const totalScore = results.reduce((sum, row) => sum + row.final_score, 0)
    const totalPossible = results.reduce((sum, row) => sum + row.exam_total, 0)
    const average = examsTaken ? totalScore / examsTaken : 0
    return {
      examsTaken,
      average: average.toFixed(2),
      overallPercent: formatPercent(totalScore, totalPossible),
    }
  }, [results])

  const handleLogout = () => {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <div className="exam-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-brand-mark"><BarChart3 size={12} /></span>
          My Results
        </div>
        <div className="topbar-context">
          <span className="exam-title">{user?.username || "—"}</span>
          <span className="badge badge-zinc">student</span>
        </div>
        <div className="topbar-right" style={{ display: "flex", gap: 8 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate("/exam")}> 
            <PlayCircle size={14} /> Go to Exam
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={handleLogout}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </header>

      <main style={{ padding: "16px 20px 24px", display: "grid", gap: 16 }}>
        {error ? <div className="alert alert-error">{error}</div> : null}

        <section className="stats-grid" style={{ marginBottom: 0 }}>
          <div className="stat-card">
            <div className="stat-eyebrow">Exams Completed</div>
            <div className="stat-value">{totals.examsTaken}</div>
          </div>
          <div className="stat-card">
            <div className="stat-eyebrow">Average Score</div>
            <div className="stat-value">{totals.average}</div>
          </div>
          <div className="stat-card">
            <div className="stat-eyebrow">Overall Percentage</div>
            <div className="stat-value">{totals.overallPercent}</div>
          </div>
        </section>

        <section className="card" style={{ display: "grid", gap: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <h2 style={{ marginBottom: 0 }}>Previous Tests</h2>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => window.location.reload()}
              disabled={loading}
            >
              {loading ? <span className="spinner" aria-label="Loading" /> : "Refresh"}
            </button>
          </div>

          {loading ? (
            <div style={{ display: "grid", placeItems: "center", minHeight: 160 }}>
              <span className="spinner" aria-label="Loading" />
            </div>
          ) : null}

          {!loading && results.length === 0 ? (
            <div className="card card-tight" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <ClipboardList size={16} />
              <span className="muted">No completed tests found yet.</span>
            </div>
          ) : null}

          {!loading && results.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Exam</th>
                    <th>End Time</th>
                    <th>Final Score</th>
                    <th>MCQ</th>
                    <th>Risk</th>
                    <th>Penalty</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((row) => (
                    <tr key={row.exam_id}>
                      <td>
                        <div style={{ display: "grid", gap: 4 }}>
                          <strong>{row.exam_title || "Untitled exam"}</strong>
                          <span className="muted">{row.exam_id}</span>
                        </div>
                      </td>
                      <td>{formatLocalDateTime(row.end_time)}</td>
                      <td>
                        <span className="num">{row.final_score}</span>
                        <span className="muted"> / {row.exam_total} ({formatPercent(row.final_score, row.exam_total)})</span>
                      </td>
                      <td>
                        <span className="num">{row.mcq_correct}</span>
                        <span className="muted"> correct</span>
                      </td>
                      <td>
                        <span className="num">{row.risk_score}</span>
                        <span className="muted"> / 10</span>
                      </td>
                      <td>
                        <span className="num">{row.negative_penalty + row.risk_penalty}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  )
}
