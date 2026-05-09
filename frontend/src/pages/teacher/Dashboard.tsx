import { useEffect, useState, type MouseEvent } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import client from "../../api/client"
import { useAuth } from "../../hooks/useAuth"
import type { ApiResponse, LogEntry, RiskScore } from "../../types"

type Tab = "overview" | "logs" | "risk" | "students"

interface ExamStatePayload {
  state: string
}

interface ActivationCodePayload {
  code: string
}

interface StudentUser {
  user_id: string
  username: string
  role: string
  is_active: boolean
  joined_at?: string
}

type ExamStateResponse = ApiResponse<ExamStatePayload>
type LogsResponse = ApiResponse<{ logs?: LogEntry[] } | LogEntry[]>
type RiskResponse = ApiResponse<{ scores?: RiskScore[] } | RiskScore[]>
type StudentsResponse = ApiResponse<{ users?: StudentUser[] } | StudentUser[]>

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage
    }
  }

  return "Unable to complete the request"
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>("overview")
  const [examId, setExamId] = useState("")
  const [examIdInput, setExamIdInput] = useState("")
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [riskData, setRiskData] = useState<RiskScore[]>([])
  const [students, setStudents] = useState<StudentUser[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [activationCode, setActivationCode] = useState("")
  const [examState, setExamState] = useState("")

  const highRiskCount = riskData.filter((item) => item.risk_level === "HIGH").length

  useEffect(() => {
    if (!examId) return

    const loadOverview = async () => {
      setLoading(true)
      setError("")

      try {
        const [stateResponse, logsResponse] = await Promise.all([
          client.get<ExamStateResponse>(`/api/auth/exam/state/${examId}`),
          client.get<LogsResponse>("/api/logs/list", { params: { exam_id: examId } }),
        ])

        setExamState(stateResponse.data.data.state)
        const logPayload = logsResponse.data.data
        setLogs(Array.isArray(logPayload) ? logPayload : logPayload.logs ?? [])
      } catch (overviewError) {
        setError(getErrorMessage(overviewError))
      } finally {
        setLoading(false)
      }
    }

    void loadOverview()
  }, [examId])

  const handleLogout = () => {
    logout()
    navigate("/login", { replace: true })
  }

  const handleLoadExam = async () => {
    const nextExamId = examIdInput.trim()
    if (!nextExamId) {
      setError("Enter an exam ID first")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await client.get<ExamStateResponse>(`/api/auth/exam/state/${nextExamId}`)
      setExamId(nextExamId)
      setExamState(response.data.data.state)
      setActivationCode("")

      const logsResponse = await client.get<LogsResponse>("/api/logs/list", { params: { exam_id: nextExamId } })
      const logPayload = logsResponse.data.data
      setLogs(Array.isArray(logPayload) ? logPayload : logPayload.logs ?? [])
      setRiskData([])
      setStudents([])
    } catch (loadError) {
      setError(getErrorMessage(loadError))
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateActivationCode = async () => {
    if (!examId) {
      setError("Load an exam first")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await client.post<ApiResponse<ActivationCodePayload>>("/api/activation/generate", {
        exam_id: examId,
      })
      setActivationCode(response.data.data.code)
    } catch (activationError) {
      setError(getErrorMessage(activationError))
    } finally {
      setLoading(false)
    }
  }

  const handleRunRiskScoring = async () => {
    if (!examId) {
      setError("Load an exam first")
      return
    }

    setLoading(true)
    setError("")

    try {
      await client.post(`/api/risk/compute/${examId}`)
      setError("")
    } catch (riskError) {
      setError(getErrorMessage(riskError))
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshLogs = async () => {
    if (!examId) {
      setError("Load an exam first")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await client.get<LogsResponse>("/api/logs/list", { params: { exam_id: examId } })
      const logPayload = response.data.data
      setLogs(Array.isArray(logPayload) ? logPayload : logPayload.logs ?? [])
    } catch (logsError) {
      setError(getErrorMessage(logsError))
    } finally {
      setLoading(false)
    }
  }

  const handleLoadRiskScores = async () => {
    if (!examId) {
      setError("Load an exam first")
      return
    }

    setLoading(true)
    setError("")

    try {
      const response = await client.get<RiskResponse>(`/api/risk/dashboard/${examId}`)
      const riskPayload = response.data.data
      setRiskData(Array.isArray(riskPayload) ? riskPayload : riskPayload.scores ?? [])
    } catch (riskLoadError) {
      setError(getErrorMessage(riskLoadError))
    } finally {
      setLoading(false)
    }
  }

  const handleLoadStudents = async () => {
    setLoading(true)
    setError("")

    try {
      const response = await client.get<StudentsResponse>("/api/rbac/users", { params: { role: "student" } })
      const studentPayload = response.data.data
      setStudents(Array.isArray(studentPayload) ? studentPayload : studentPayload.users ?? [])
    } catch (studentError) {
      setError(getErrorMessage(studentError))
    } finally {
      setLoading(false)
    }
  }

  const handleToggleStudent = async (event: MouseEvent<HTMLTableRowElement>, userId: string) => {
    event.preventDefault()
    setLoading(true)
    setError("")

    try {
      await client.patch(`/api/rbac/users/${userId}/toggle`)
      await handleLoadStudents()
    } catch (toggleError) {
      setError(getErrorMessage(toggleError))
    } finally {
      setLoading(false)
    }
  }

  const renderBadge = (value: string) => {
    const normalized = value.toUpperCase()
    if (normalized === "ERROR" || normalized === "SECURITY" || normalized === "HIGH") return "badge-red"
    if (normalized === "WARNING" || normalized === "MEDIUM") return "badge-orange"
    if (normalized === "LOW") return "badge-green"
    if (normalized === "INFO") return "badge-zinc"
    return "badge-zinc"
  }

  return (
    <div>
      <header className="navbar">
        <div className="navbar-brand">SecureExam</div>
        <div className="navbar-right">
          <span className="badge badge-zinc">{user?.username || "Unknown"}</span>
          <button type="button" className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="page">
        <section className="card" style={{ display: "grid", gap: 16 }}>
          <div>
            <span className="label">Active Exam ID</span>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <input
                className="input"
                style={{ flex: "1 1 280px" }}
                value={examIdInput}
                onChange={(event) => setExamIdInput(event.target.value)}
                placeholder="Enter active exam ID"
              />
              <button type="button" className="btn btn-primary" onClick={() => void handleLoadExam()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Load Exam"}
              </button>
            </div>
          </div>

          {examId ? <span className="badge badge-zinc">Current Exam: {examId}</span> : null}
          {error ? <div className="alert alert-error">{error}</div> : null}
        </section>

        <section className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          <button type="button" className={`btn ${tab === "overview" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("overview")}>Overview</button>
          <button type="button" className={`btn ${tab === "logs" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("logs")}>Logs</button>
          <button type="button" className={`btn ${tab === "risk" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("risk")}>Risk Scores</button>
          <button type="button" className={`btn ${tab === "students" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("students")}>Students</button>
        </section>

        {tab === "overview" ? (
          <section className="card" style={{ display: "grid", gap: 18 }}>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{examState || "-"}</div>
                <div className="stat-label">Exam State</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{logs.length}</div>
                <div className="stat-label">Total Logs</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{highRiskCount}</div>
                <div className="stat-label">High Risk</div>
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              <button type="button" className="btn btn-primary" onClick={() => void handleGenerateActivationCode()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Generate Activation Code"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => void handleRunRiskScoring()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Run Risk Scoring"}
              </button>
            </div>

            {activationCode ? <div className="alert alert-success">Activation Code: {activationCode}</div> : null}
          </section>
        ) : null}

        {tab === "logs" ? (
          <section className="card" style={{ display: "grid", gap: 16 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleRefreshLogs()} disabled={loading}>
              {loading ? <span className="spinner" aria-label="Loading" /> : "Refresh Logs"}
            </button>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Level</th>
                    <th>Action</th>
                    <th>User</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((entry) => (
                    <tr key={entry.log_id}>
                      <td>{entry.module}</td>
                      <td><span className={`badge ${renderBadge(entry.level)}`}>{entry.level}</span></td>
                      <td>{entry.action}</td>
                      <td>{entry.user_id}</td>
                      <td>{entry.timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {tab === "risk" ? (
          <section className="card" style={{ display: "grid", gap: 16 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleLoadRiskScores()} disabled={loading}>
              {loading ? <span className="spinner" aria-label="Loading" /> : "Load Risk Scores"}
            </button>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Score</th>
                    <th>Risk Level</th>
                    <th>Tab Switches</th>
                    <th>Fast Answers</th>
                  </tr>
                </thead>
                <tbody>
                  {riskData.map((row) => (
                    <tr key={`${row.student_id}-${row.computed_at}`}>
                      <td>{row.username}</td>
                      <td>{row.score}</td>
                      <td><span className={`badge ${renderBadge(row.risk_level)}`}>{row.risk_level}</span></td>
                      <td>{row.metrics.tab_switches ?? 0}</td>
                      <td>{row.metrics.fast_answers ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {tab === "students" ? (
          <section className="card" style={{ display: "grid", gap: 16 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleLoadStudents()} disabled={loading}>
              {loading ? <span className="spinner" aria-label="Loading" /> : "Load Students"}
            </button>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.user_id} onClick={(event) => void handleToggleStudent(event, student.user_id)} style={{ cursor: "pointer" }}>
                      <td>{student.username}</td>
                      <td>{student.role}</td>
                      <td>
                        <span className={`badge ${student.is_active ? "badge-green" : "badge-zinc"}`}>
                          {student.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>{student.joined_at || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  )
}
