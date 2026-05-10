import { useEffect, useState, type MouseEvent } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import client from "../../api/client"
import { useAuth } from "../../hooks/useAuth"
import type { ApiResponse, Exam, LogEntry, QuestionWithAnswer, RiskScore, StudentUser } from "../../types"

type Tab = "exams" | "overview" | "questions" | "logs" | "risk" | "students"

interface ExamStatePayload {
  state: string
}

interface ActivationCodePayload {
  code: string
}

type ExamsResponse = ApiResponse<{ exams?: Exam[]; count?: number } | Exam[]>
type CreateExamResponse = ApiResponse<{ exam_id: string; title: string; state: string }>
type ApproveExamResponse = ApiResponse<{ exam_id: string; state: string }>
type ExamStateResponse = ApiResponse<ExamStatePayload>
type ExamDetailsResponse = ApiResponse<Exam>
type QuestionsResponse = ApiResponse<{ questions?: QuestionWithAnswer[]; count?: number } | QuestionWithAnswer[]>
type CreateQuestionResponse = ApiResponse<{ question_id: string }>
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

function normalizeArray<T>(payload: unknown, keys: string[]): T[] {
  if (Array.isArray(payload)) {
    return payload as T[]
  }

  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>
    for (const key of keys) {
      const value = record[key]
      if (Array.isArray(value)) {
        return value as T[]
      }
    }
  }

  return []
}

function getStateBadgeClass(state: string) {
  switch (state) {
    case "NOT_STARTED":
    case "DEVICE_VERIFIED":
      return "badge-zinc"
    case "TEACHER_APPROVED":
    case "ACTIVATION_VALID":
    case "ANALYZING":
      return "badge-orange"
    case "IN_PROGRESS":
      return "badge-green"
    case "SUBMITTED":
    case "COMPLETED":
      return "badge-white"
    default:
      return "badge-zinc"
  }
}

function formatLocalDateTime(value: string) {
  if (!value) return "-"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState<Tab>("exams")
  const [examId, setExamId] = useState("")
  const [examIdInput, setExamIdInput] = useState("")
  const [exams, setExams] = useState<Exam[]>([])
  const [newExamTitle, setNewExamTitle] = useState("")
  const [newExamDesc, setNewExamDesc] = useState("")
  const [newExamDuration, setNewExamDuration] = useState(60)
  const [newExamMaxStudents, setNewExamMaxStudents] = useState(30)
  const [newExamStartTime, setNewExamStartTime] = useState("")
  const [newExamEndTime, setNewExamEndTime] = useState("")
  const [questionText, setQuestionText] = useState("")
  const [questionOptions, setQuestionOptions] = useState(["", "", "", ""])
  const [correctAnswer, setCorrectAnswer] = useState("")
  const [questions, setQuestions] = useState<QuestionWithAnswer[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [riskData, setRiskData] = useState<RiskScore[]>([])
  const [students, setStudents] = useState<StudentUser[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [activationCode, setActivationCode] = useState("")
  const [examState, setExamState] = useState("")
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null)

  const highRiskCount = riskData.filter((item) => item.risk_level === "HIGH").length
  const canApproveExam = examState === "NOT_STARTED" || examState === "DEVICE_VERIFIED"

  const loadExams = async () => {
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.get<ExamsResponse>("/api/questions/exams/list")
      const examPayload = response.data.data
      setExams(normalizeArray<Exam>(examPayload, ["exams"]))
    } catch (examsError) {
      setError(getErrorMessage(examsError))
    } finally {
      setLoading(false)
    }
  }

  const loadExamOverview = async (targetExamId: string) => {
    if (!targetExamId) return

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const [stateResponse, detailsResponse, logsResponse] = await Promise.all([
        client.get<ExamStateResponse>(`/api/auth/exam/state/${targetExamId}`),
        client.get<ExamDetailsResponse>(`/api/questions/exams/${targetExamId}`),
        client.get<LogsResponse>("/api/logs/list", { params: { exam_id: targetExamId } }),
      ])

      setExamState(stateResponse.data.data.state)
      setSelectedExam(detailsResponse.data.data)
      setLogs(normalizeArray<LogEntry>(logsResponse.data.data, ["logs"]))
    } catch (overviewError) {
      setError(getErrorMessage(overviewError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadExams()
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [])

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

    setExamId(nextExamId)
    setTab("overview")
    await loadExamOverview(nextExamId)
  }

  const handleSelectExam = async (exam: Exam) => {
    setExamId(exam.exam_id)
    setTab("overview")
    await loadExamOverview(exam.exam_id)
  }

  const handleCreateExam = async () => {
    const title = newExamTitle.trim()
    const description = newExamDesc.trim()

    if (!title) {
      setError("Title is required")
      return
    }

    if (!newExamStartTime || !newExamEndTime) {
      setError("Start time and end time are required")
      return
    }

    if (newExamDuration < 10 || newExamDuration > 180) {
      setError("Duration must be between 10 and 180 minutes")
      return
    }

    if (newExamMaxStudents < 1 || newExamMaxStudents > 200) {
      setError("Max students must be between 1 and 200")
      return
    }

    const startTimeDate = new Date(newExamStartTime)
    const endTimeDate = new Date(newExamEndTime)
    if (Number.isNaN(startTimeDate.getTime()) || Number.isNaN(endTimeDate.getTime())) {
      setError("Start time and end time must be valid dates")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const startTimeIso = startTimeDate.toISOString()
      const endTimeIso = endTimeDate.toISOString()
      const response = await client.post<CreateExamResponse>("/api/questions/exams/create", {
        title,
        description,
        duration_minutes: newExamDuration,
        max_students: newExamMaxStudents,
        start_time: startTimeIso,
        end_time: endTimeIso,
      })

      const createdExam: Exam = {
        exam_id: response.data.data.exam_id,
        title,
        description,
        duration_minutes: newExamDuration,
        state: response.data.data.state,
        created_at: new Date().toISOString(),
        max_students: newExamMaxStudents,
        students_count: 0,
        start_time: startTimeIso,
        end_time: endTimeIso,
      }

      setExams((current) => [createdExam, ...current])
      setNewExamTitle("")
      setNewExamDesc("")
      setNewExamDuration(60)
      setNewExamMaxStudents(30)
      setNewExamStartTime("")
      setNewExamEndTime("")
      setSuccess("Exam created")
      setTab("exams")
    } catch (createError) {
      setError(getErrorMessage(createError))
    } finally {
      setLoading(false)
    }
  }

  const handleApproveExam = async (targetExamId: string) => {
    if (!targetExamId) return

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.post<ApproveExamResponse>("/api/questions/exams/approve", {
        exam_id: targetExamId,
      })

      const nextState = response.data.data.state
      setExams((current) => current.map((exam) => (exam.exam_id === targetExamId ? { ...exam, state: nextState } : exam)))
      if (examId === targetExamId) {
        setExamState(nextState)
      }
      setSuccess("Exam approved")
    } catch (approveError) {
      setError(getErrorMessage(approveError))
    } finally {
      setLoading(false)
    }
  }

  const fetchQuestions = async (targetExamId: string) => {
    const response = await client.get<QuestionsResponse>(`/api/questions/list/${targetExamId}`)
    return normalizeArray<QuestionWithAnswer>(response.data.data, ["questions"])
  }

  const handleLoadQuestions = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const nextQuestions = await fetchQuestions(examId)
      setQuestions(nextQuestions)
    } catch (questionError) {
      setError(getErrorMessage(questionError))
    } finally {
      setLoading(false)
    }
  }

  const handleAddQuestion = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    const normalizedText = questionText.trim()
    const normalizedOptions = questionOptions.map((option) => option.trim())
    const normalizedCorrectAnswer = correctAnswer.trim()

    if (!normalizedText) {
      setError("Question text is required")
      return
    }

    if (normalizedOptions.some((option) => !option)) {
      setError("All four options are required")
      return
    }

    if (!normalizedCorrectAnswer || !normalizedOptions.includes(normalizedCorrectAnswer)) {
      setError("Select a valid correct answer")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.post<CreateQuestionResponse>("/api/questions/create", {
        exam_id: examId,
        text: normalizedText,
        options: normalizedOptions,
        correct_answer: normalizedCorrectAnswer,
        marks: 1,
      })

      const nextQuestions = await fetchQuestions(examId)
      setQuestions(nextQuestions)
      setQuestionText("")
      setQuestionOptions(["", "", "", ""])
      setCorrectAnswer("")
      setSuccess("Question added")
    } catch (addQuestionError) {
      setError(getErrorMessage(addQuestionError))
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateActivationCode = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.post<ApiResponse<ActivationCodePayload>>("/api/activation/generate", {
        exam_id: examId,
      })
      setActivationCode(response.data.data.code)
      setSuccess("Activation code generated")
    } catch (activationError) {
      setError(getErrorMessage(activationError))
    } finally {
      setLoading(false)
    }
  }

  const handleRunRiskScoring = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.post(`/api/risk/compute/${examId}`)
      setSuccess("Risk scoring completed")
    } catch (riskError) {
      setError(getErrorMessage(riskError))
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshLogs = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.get<LogsResponse>("/api/logs/list", { params: { exam_id: examId } })
      setLogs(normalizeArray<LogEntry>(response.data.data, ["logs"]))
    } catch (logsError) {
      setError(getErrorMessage(logsError))
    } finally {
      setLoading(false)
    }
  }

  const handleLoadRiskScores = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.get<RiskResponse>(`/api/risk/dashboard/${examId}`)
      setRiskData(normalizeArray<RiskScore>(response.data.data, ["scores"]))
    } catch (riskLoadError) {
      setError(getErrorMessage(riskLoadError))
    } finally {
      setLoading(false)
    }
  }

  const handleLoadStudents = async () => {
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.get<StudentsResponse>("/api/rbac/users", { params: { role: "student" } })
      setStudents(normalizeArray<StudentUser>(response.data.data, ["users"]))
    } catch (studentError) {
      setError(getErrorMessage(studentError))
    } finally {
      setLoading(false)
    }
  }

  const handleToggleStudent = async (event: MouseEvent<HTMLTableRowElement>, userId: string) => {
    event.preventDefault()
    setError("")
    setSuccess("")

    try {
      await client.patch(`/api/rbac/users/${userId}/toggle`)
      await handleLoadStudents()
    } catch (toggleError) {
      setError(getErrorMessage(toggleError))
    }
  }

  return (
    <div>
      <header className="navbar">
        <div className="navbar-brand">SecureExam</div>
        <div className="navbar-right">
          <span className="badge badge-zinc">{user?.username || "Unknown"}</span>
          <span className="badge badge-zinc">Exam: {examId || "None"}</span>
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

          {error ? <div className="alert alert-error">{error}</div> : null}
          {success ? <div className="alert alert-success">{success}</div> : null}
        </section>

        <section className="card" style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          <button type="button" className={`btn ${tab === "exams" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("exams")}>Exams</button>
          <button type="button" className={`btn ${tab === "overview" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("overview")}>Overview</button>
          <button type="button" className={`btn ${tab === "questions" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("questions")}>Questions</button>
          <button type="button" className={`btn ${tab === "logs" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("logs")}>Logs</button>
          <button type="button" className={`btn ${tab === "risk" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("risk")}>Risk Scores</button>
          <button type="button" className={`btn ${tab === "students" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("students")}>Students</button>
        </section>

        {tab === "exams" ? (
          <section style={{ display: "grid", gap: 18 }}>
            <div className="card" style={{ display: "grid", gap: 16 }}>
              <h2>Create New Exam</h2>

              <div className="field">
                <label className="label">Title</label>
                <input className="input" value={newExamTitle} onChange={(event) => setNewExamTitle(event.target.value)} />
              </div>

              <div className="field">
                <label className="label">Description</label>
                <input className="input" value={newExamDesc} onChange={(event) => setNewExamDesc(event.target.value)} />
              </div>

              <div className="field">
                <label className="label">Duration (minutes)</label>
                <input className="input" type="number" value={newExamDuration} onChange={(event) => setNewExamDuration(Number.parseInt(event.target.value || "0", 10) || 0)} />
              </div>

              <div className="field">
                <label className="label">Max Students</label>
                <input
                  className="input"
                  type="number"
                  min={1}
                  max={200}
                  value={newExamMaxStudents}
                  onChange={(event) => setNewExamMaxStudents(Number.parseInt(event.target.value || "0", 10) || 0)}
                  placeholder="30"
                />
              </div>

              <div className="field">
                <label className="label">Exam Start Time</label>
                <input className="input" type="datetime-local" value={newExamStartTime} onChange={(event) => setNewExamStartTime(event.target.value)} />
              </div>

              <div className="field">
                <label className="label">Exam End Time</label>
                <input className="input" type="datetime-local" value={newExamEndTime} onChange={(event) => setNewExamEndTime(event.target.value)} />
              </div>

              <button type="button" className="btn btn-primary" onClick={() => void handleCreateExam()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Create Exam"}
              </button>
            </div>

            <div className="card" style={{ display: "grid", gap: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <h2 style={{ marginBottom: 0 }}>Exams</h2>
                <button type="button" className="btn btn-ghost" onClick={() => void loadExams()} disabled={loading}>
                  {loading ? <span className="spinner" aria-label="Loading" /> : "Refresh"}
                </button>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Duration</th>
                      <th>Start Time</th>
                      <th>End Time</th>
                      <th>Enrolled/Max</th>
                      <th>State</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exams.map((exam) => (
                      <tr key={exam.exam_id}>
                        <td>{exam.title}</td>
                        <td>{exam.duration_minutes} min</td>
                        <td>{formatLocalDateTime(exam.start_time)}</td>
                        <td>{formatLocalDateTime(exam.end_time)}</td>
                        <td>{exam.students_count}/{exam.max_students}</td>
                        <td><span className={`badge ${getStateBadgeClass(exam.state)}`}>{exam.state}</span></td>
                        <td>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <button type="button" className="btn btn-ghost" onClick={() => void handleSelectExam(exam)}>
                              Select
                            </button>
                            {exam.state === "NOT_STARTED" || exam.state === "DEVICE_VERIFIED" ? (
                              <button type="button" className="btn btn-primary" onClick={() => void handleApproveExam(exam.exam_id)} disabled={loading}>
                                {loading ? <span className="spinner" aria-label="Loading" /> : "Approve"}
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        ) : null}

        {tab === "overview" ? (
          <section className="card" style={{ display: "grid", gap: 18 }}>
            {!examId ? <div className="alert alert-warning">Select an exam from the Exams tab first</div> : null}

            {examId ? (
              <>
                {selectedExam ? (
                  <div className="card" style={{ display: "grid", gap: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <div className="label">Exam Info</div>
                        <h2 style={{ marginTop: 12 }}>{selectedExam.title}</h2>
                        <p className="muted">{selectedExam.description || "No description provided"}</p>
                      </div>
                      <span className={`badge ${getStateBadgeClass(selectedExam.state)}`}>{selectedExam.state}</span>
                    </div>

                    <div className="stats-grid">
                      <div className="stat-card">
                        <div className="stat-value">{selectedExam.duration_minutes}m</div>
                        <div className="stat-label">Duration</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-value">{selectedExam.students_count}/{selectedExam.max_students}</div>
                        <div className="stat-label">Enrolled</div>
                      </div>
                    </div>

                    <p className="muted">Starts: {formatLocalDateTime(selectedExam.start_time)}</p>
                    <p className="muted">Ends: {formatLocalDateTime(selectedExam.end_time)}</p>
                  </div>
                ) : null}

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
                  {canApproveExam ? (
                    <button type="button" className="btn btn-primary" onClick={() => void handleApproveExam(examId)} disabled={loading}>
                      {loading ? <span className="spinner" aria-label="Loading" /> : "Approve Exam"}
                    </button>
                  ) : null}
                  <button type="button" className="btn btn-primary" onClick={() => void handleGenerateActivationCode()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Generate Activation Code"}
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => void handleRunRiskScoring()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Run Risk Scoring"}
                  </button>
                </div>

                {activationCode ? <div className="alert alert-success">Activation Code: {activationCode}</div> : null}
              </>
            ) : null}
          </section>
        ) : null}

        {tab === "questions" ? (
          !examId ? (
            <section className="card">
              <div className="alert alert-warning">Select an exam first</div>
            </section>
          ) : (
            <section style={{ display: "grid", gap: 18 }}>
              <div className="card" style={{ display: "grid", gap: 16 }}>
                <h2>Add Question</h2>

                <div className="field">
                  <label className="label">Question Text</label>
                  <input className="input" value={questionText} onChange={(event) => setQuestionText(event.target.value)} />
                </div>

                {[0, 1, 2, 3].map((index) => (
                  <div className="field" key={index}>
                    <label className="label">Option {index + 1}</label>
                    <input
                      className="input"
                      value={questionOptions[index]}
                      onChange={(event) => {
                        const updated = [...questionOptions]
                        updated[index] = event.target.value
                        setQuestionOptions(updated)
                      }}
                    />
                  </div>
                ))}

                <div className="field">
                  <label className="label">Correct Answer</label>
                  <select className="select" value={correctAnswer} onChange={(event) => setCorrectAnswer(event.target.value)}>
                    <option value="">Select correct answer</option>
                    {questionOptions.filter((option) => option.trim()).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>

                <button type="button" className="btn btn-primary" onClick={() => void handleAddQuestion()} disabled={loading}>
                  {loading ? <span className="spinner" aria-label="Loading" /> : "Add Question"}
                </button>
              </div>

              <div className="card" style={{ display: "grid", gap: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                  <h2 style={{ marginBottom: 0 }}>Questions</h2>
                  <button type="button" className="btn btn-ghost" onClick={() => void handleLoadQuestions()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Load Questions"}
                  </button>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Question</th>
                        <th>Options</th>
                        <th>Correct Answer</th>
                        <th>Marks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questions.map((question) => (
                        <tr key={question.question_id}>
                          <td>{question.order_index}</td>
                          <td>{question.text}</td>
                          <td>{question.options.join(", ")}</td>
                          <td>{question.correct_answer}</td>
                          <td>{question.marks}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )
        ) : null}

        {tab === "logs" ? (
          <section className="card" style={{ display: "grid", gap: 16 }}>
            <button type="button" className="btn btn-primary" onClick={() => void handleRefreshLogs()} disabled={loading || !examId}>
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
                      <td><span className={`badge ${getStateBadgeClass(entry.level)}`}>{entry.level}</span></td>
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
            <button type="button" className="btn btn-primary" onClick={() => void handleLoadRiskScores()} disabled={loading || !examId}>
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
                      <td><span className={`badge ${getStateBadgeClass(row.risk_level)}`}>{row.risk_level}</span></td>
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