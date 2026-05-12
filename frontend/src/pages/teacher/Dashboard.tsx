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
  const [questionType, setQuestionType] = useState<"mcq" | "text">("mcq")
  const [questionMarks, setQuestionMarks] = useState(1)
  const [wordLimit, setWordLimit] = useState(0)
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
  
  // Edit/Delete state
  const [editingExamId, setEditingExamId] = useState("")
  const [editExamTitle, setEditExamTitle] = useState("")
  const [editExamDesc, setEditExamDesc] = useState("")
  const [editExamDuration, setEditExamDuration] = useState(60)
  const [editExamMaxStudents, setEditExamMaxStudents] = useState(30)
  const [editExamStartTime, setEditExamStartTime] = useState("")
  const [editExamEndTime, setEditExamEndTime] = useState("")
  const [deleteExamId, setDeleteExamId] = useState("")
  const [deletingExamId, setDeletingExamId] = useState("")
  
  const [editingQuestionId, setEditingQuestionId] = useState("")
  const [editQuestionText, setEditQuestionText] = useState("")
  const [editQuestionType, setEditQuestionType] = useState<"mcq" | "text">("mcq")
  const [editQuestionMarks, setEditQuestionMarks] = useState(1)
  const [editWordLimit, setEditWordLimit] = useState(0)
  const [editQuestionOptions, setEditQuestionOptions] = useState(["", "", "", ""])
  const [editCorrectAnswer, setEditCorrectAnswer] = useState("")
  const [deleteQuestionId, setDeleteQuestionId] = useState("")
  const [deletingQuestionId, setDeletingQuestionId] = useState("")
  
  // Student approval state
  const [examStudents, setExamStudents] = useState<Array<{ student_id: string; joined_at: string; approved: boolean; approved_at: string | null; approved_by: string | null }>>([])
  const [approvingStudentId, setApprovingStudentId] = useState("")

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
    setExamIdInput(exam.exam_id)
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
        total_questions: 0,
        total_marks: 0,
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

    if (questionMarks < 1 || questionMarks > 10) {
      setError("Marks must be between 1 and 10")
      return
    }

    if (wordLimit < 0) {
      setError("Word limit must be 0 or greater")
      return
    }

    if (questionType === "mcq") {
      if (normalizedOptions.some((option) => !option)) {
        setError("All four options are required")
        return
      }

      if (!normalizedCorrectAnswer || !normalizedOptions.includes(normalizedCorrectAnswer)) {
        setError("Select a valid correct answer")
        return
      }
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.post<CreateQuestionResponse>("/api/questions/create", {
        exam_id: examId,
        text: normalizedText,
        question_type: questionType,
        marks: questionMarks,
        options: questionType === "mcq" ? normalizedOptions : [],
        correct_answer: questionType === "mcq" ? normalizedCorrectAnswer : "",
        word_limit: wordLimit,
      })

      const nextQuestions = await fetchQuestions(examId)
      setQuestions(nextQuestions)
      setQuestionText("")
      setQuestionType("mcq")
      setQuestionMarks(1)
      setWordLimit(0)
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
      try {
        const statusResponse = await client.get<ApiResponse<{ code?: string; is_expired?: boolean }>>(`/api/activation/status/${examId}`)
        const code = statusResponse.data.data.code

        if (code) {
          setActivationCode(code)
          setSuccess("Activation code loaded")
          return
        }
      } catch {
        // fall through to generation
      }

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

  const handleOpenEditExam = (exam: Exam) => {
    setEditingExamId(exam.exam_id)
    setEditExamTitle(exam.title)
    setEditExamDesc(exam.description)
    setEditExamDuration(exam.duration_minutes)
    setEditExamMaxStudents(exam.max_students)
    setEditExamStartTime(exam.start_time)
    setEditExamEndTime(exam.end_time)
  }

  const handleUpdateExam = async () => {
    if (!editingExamId) return

    const title = editExamTitle.trim()
    if (!title) {
      setError("Title is required")
      return
    }

    if (!editExamStartTime || !editExamEndTime) {
      setError("Start time and end time are required")
      return
    }

    if (editExamDuration < 10 || editExamDuration > 180) {
      setError("Duration must be between 10 and 180 minutes")
      return
    }

    if (editExamMaxStudents < 1 || editExamMaxStudents > 200) {
      setError("Max students must be between 1 and 200")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const startTimeDate = new Date(editExamStartTime)
      const endTimeDate = new Date(editExamEndTime)
      const startTimeIso = startTimeDate.toISOString()
      const endTimeIso = endTimeDate.toISOString()

      await client.put(`/api/questions/exams/${editingExamId}`, {
        title,
        description: editExamDesc.trim(),
        duration_minutes: editExamDuration,
        max_students: editExamMaxStudents,
        start_time: startTimeIso,
        end_time: endTimeIso,
      })

      setExams((current) =>
        current.map((exam) =>
          exam.exam_id === editingExamId
            ? {
                ...exam,
                title,
                description: editExamDesc.trim(),
                duration_minutes: editExamDuration,
                max_students: editExamMaxStudents,
                start_time: startTimeIso,
                end_time: endTimeIso,
              }
            : exam
        )
      )

      if (selectedExam?.exam_id === editingExamId) {
        setSelectedExam({
          ...selectedExam,
          title,
          description: editExamDesc.trim(),
          duration_minutes: editExamDuration,
          max_students: editExamMaxStudents,
          start_time: startTimeIso,
          end_time: endTimeIso,
        })
      }

      setEditingExamId("")
      setSuccess("Exam updated")
    } catch (updateError) {
      setError(getErrorMessage(updateError))
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteExam = async () => {
    if (!deleteExamId) return

    setDeletingExamId(deleteExamId)
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.delete(`/api/questions/exams/${deleteExamId}`)
      setExams((current) => current.filter((exam) => exam.exam_id !== deleteExamId))
      setDeleteExamId("")
      setSuccess("Exam deleted")
      if (examId === deleteExamId) {
        setExamId("")
        setTab("exams")
      }
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    } finally {
      setLoading(false)
      setDeletingExamId("")
    }
  }

  const handleOpenEditQuestion = (question: QuestionWithAnswer) => {
    setEditingQuestionId(question.question_id)
    setEditQuestionText(question.text)
    setEditQuestionType(question.question_type as "mcq" | "text")
    setEditQuestionMarks(question.marks)
    setEditWordLimit(question.word_limit)
    setEditQuestionOptions(question.options || ["", "", "", ""])
    setEditCorrectAnswer(question.correct_answer || "")
  }

  const handleUpdateQuestion = async () => {
    if (!editingQuestionId) return

    const normalizedText = editQuestionText.trim()
    if (!normalizedText) {
      setError("Question text is required")
      return
    }

    if (editQuestionMarks < 1 || editQuestionMarks > 10) {
      setError("Marks must be between 1 and 10")
      return
    }

    if (editWordLimit < 0) {
      setError("Word limit must be 0 or greater")
      return
    }

    if (editQuestionType === "mcq") {
      const normalizedOptions = editQuestionOptions.map((option) => option.trim())
      if (normalizedOptions.some((option) => !option)) {
        setError("All four options are required for MCQ")
        return
      }

      if (!editCorrectAnswer || !normalizedOptions.includes(editCorrectAnswer)) {
        setError("Select a valid correct answer")
        return
      }
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const payload: Record<string, unknown> = {
        text: normalizedText,
        question_type: editQuestionType,
        marks: editQuestionMarks,
        word_limit: editWordLimit,
      }

      if (editQuestionType === "mcq") {
        payload.options = editQuestionOptions.map((opt) => opt.trim())
        payload.correct_answer = editCorrectAnswer
      }

      await client.put(`/api/questions/${editingQuestionId}`, payload)

      const updatedQuestions = questions.map((q) =>
        q.question_id === editingQuestionId
          ? {
              ...q,
              text: normalizedText,
              question_type: editQuestionType,
              marks: editQuestionMarks,
              word_limit: editWordLimit,
              options: editQuestionType === "mcq" ? editQuestionOptions.map((opt) => opt.trim()) : [],
              correct_answer: editQuestionType === "mcq" ? editCorrectAnswer : "",
            }
          : q
      )
      setQuestions(updatedQuestions)

      setEditingQuestionId("")
      setSuccess("Question updated")
    } catch (updateError) {
      setError(getErrorMessage(updateError))
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteQuestion = async () => {
    if (!deleteQuestionId) return

    setDeletingQuestionId(deleteQuestionId)
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.delete(`/api/questions/${deleteQuestionId}`)
      setQuestions((current) => current.filter((q) => q.question_id !== deleteQuestionId))
      setDeleteQuestionId("")
      setSuccess("Question deleted")
    } catch (deleteError) {
      setError(getErrorMessage(deleteError))
    } finally {
      setLoading(false)
      setDeletingQuestionId("")
    }
  }

  const handleLoadExamStudents = async () => {
    if (!examId) {
      setError("Select an exam first")
      return
    }

    setLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await client.get<ApiResponse<{ students: Array<{ student_id: string; joined_at: string; approved: boolean; approved_at: string | null; approved_by: string | null }>; count: number }>>(
        `/api/questions/exams/${examId}/students`
      )
      setExamStudents(response.data.data.students || [])
    } catch (studentsError) {
      setError(getErrorMessage(studentsError))
    } finally {
      setLoading(false)
    }
  }

  const handleApproveStudent = async (studentId: string) => {
    if (!examId || !studentId) return

    setApprovingStudentId(studentId)
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await client.post("/api/questions/exams/students/approve", {
        exam_id: examId,
        student_id: studentId,
      })

      setExamStudents((current) =>
        current.map((student) =>
          student.student_id === studentId ? { ...student, approved: true, approved_at: new Date().toISOString() } : student
        )
      )
      setSuccess(`Student approved`)
    } catch (approveError) {
      setError(getErrorMessage(approveError))
    } finally {
      setLoading(false)
      setApprovingStudentId("")
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
                            {exam.state === "NOT_STARTED" ? (
                              <>
                                <button type="button" className="btn btn-ghost" onClick={() => handleOpenEditExam(exam)} disabled={loading}>
                                  Edit
                                </button>
                                <button type="button" className="btn btn-ghost" onClick={() => setDeleteExamId(exam.exam_id)} disabled={loading} style={{ color: "#dc2626" }}>
                                  Delete
                                </button>
                              </>
                            ) : null}
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
                      <div className="stat-card">
                        <div className="stat-value">{selectedExam.total_questions ?? 0}</div>
                        <div className="stat-label">Total Questions</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-value">{selectedExam.total_marks ?? 0}</div>
                        <div className="stat-label">Total Marks</div>
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
                  {selectedExam?.state === "NOT_STARTED" ? (
                    <>
                      <button type="button" className="btn btn-ghost" onClick={() => handleOpenEditExam(selectedExam)} disabled={loading}>
                        Edit Exam
                      </button>
                      <button type="button" className="btn btn-ghost" onClick={() => setDeleteExamId(examId)} disabled={loading} style={{ color: "#dc2626" }}>
                        Delete Exam
                      </button>
                    </>
                  ) : null}
                  <button type="button" className="btn btn-primary" onClick={() => void handleGenerateActivationCode()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "View Activation Code"}
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => void handleRunRiskScoring()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Run Risk Scoring"}
                  </button>
                </div>

                {activationCode ? <div className="alert alert-success">Activation Code: {activationCode}</div> : null}

                <hr style={{ margin: "24px 0", border: "none", borderTop: "1px solid #e5e7eb" }} />

                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                  <h3 style={{ marginBottom: 0 }}>Students Joined</h3>
                  <button type="button" className="btn btn-ghost" onClick={() => void handleLoadExamStudents()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Refresh Students"}
                  </button>
                </div>

                {examStudents.length === 0 ? (
                  <p className="muted">No students have joined this exam yet</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Student ID</th>
                          <th>Joined At</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {examStudents.map((student) => (
                          <tr key={student.student_id}>
                            <td>{student.student_id}</td>
                            <td>{formatLocalDateTime(student.joined_at)}</td>
                            <td>
                              <span className={`badge ${student.approved ? "badge-green" : "badge-zinc"}`}>
                                {student.approved ? "Approved" : "Pending"}
                              </span>
                            </td>
                            <td>
                              {!student.approved ? (
                                <button
                                  type="button"
                                  className="btn btn-primary"
                                  onClick={() => void handleApproveStudent(student.student_id)}
                                  disabled={loading}
                                >
                                  {approvingStudentId === student.student_id && loading ? <span className="spinner" aria-label="Loading" /> : "Approve"}
                                </button>
                              ) : (
                                <span className="muted">Approved</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
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

                <div className="field">
                  <label className="label">Question Type</label>
                  <select className="select" value={questionType} onChange={(event) => setQuestionType(event.target.value as "mcq" | "text")}>
                    <option value="mcq">Multiple Choice (MCQ)</option>
                    <option value="text">Text Answer</option>
                  </select>
                </div>

                <div className="field">
                  <label className="label">Marks</label>
                  <input className="input" type="number" min={1} max={10} value={questionMarks} onChange={(event) => setQuestionMarks(Number(event.target.value))} />
                </div>

                {questionType === "mcq" ? (
                  <>
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
                  </>
                ) : null}

                {questionType === "text" ? (
                  <div className="field">
                    <label className="label">Word Limit (0 = no limit)</label>
                    <input className="input" type="number" min={0} value={wordLimit} onChange={(event) => setWordLimit(Number(event.target.value))} />
                  </div>
                ) : null}

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
                        <th>Type</th>
                        <th>Question</th>
                        <th>Marks</th>
                        <th>Word Limit</th>
                        <th>Options count</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questions.map((question) => (
                        <tr key={question.question_id}>
                          <td>{question.order_index}</td>
                          <td>{question.question_type}</td>
                          <td>{question.text}</td>
                          <td>{question.marks}</td>
                          <td>{question.word_limit}</td>
                          <td>{question.options.length}</td>
                          <td>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <button type="button" className="btn btn-ghost" onClick={() => handleOpenEditQuestion(question)} disabled={loading}>
                                Edit
                              </button>
                              <button type="button" className="btn btn-ghost" onClick={() => setDeleteQuestionId(question.question_id)} disabled={loading} style={{ color: "#dc2626" }}>
                                Delete
                              </button>
                            </div>
                          </td>
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

      {/* Edit Exam Modal */}
      {editingExamId ? (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ width: "90%", maxWidth: 600, maxHeight: "90vh", overflowY: "auto", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <h2 style={{ marginBottom: 0 }}>Edit Exam</h2>
              <button type="button" className="btn btn-ghost" onClick={() => setEditingExamId("")}>
                ✕
              </button>
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Title</label>
              <input className="input" value={editExamTitle} onChange={(event) => setEditExamTitle(event.target.value)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Description</label>
              <input className="input" value={editExamDesc} onChange={(event) => setEditExamDesc(event.target.value)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Duration (minutes)</label>
              <input className="input" type="number" value={editExamDuration} onChange={(event) => setEditExamDuration(Number.parseInt(event.target.value || "0", 10) || 0)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Max Students</label>
              <input className="input" type="number" min={1} max={200} value={editExamMaxStudents} onChange={(event) => setEditExamMaxStudents(Number.parseInt(event.target.value || "0", 10) || 0)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Exam Start Time</label>
              <input className="input" type="datetime-local" value={editExamStartTime} onChange={(event) => setEditExamStartTime(event.target.value)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Exam End Time</label>
              <input className="input" type="datetime-local" value={editExamEndTime} onChange={(event) => setEditExamEndTime(event.target.value)} />
            </div>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn btn-ghost" onClick={() => setEditingExamId("")} disabled={loading}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void handleUpdateExam()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Delete Exam Confirmation */}
      {deleteExamId ? (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ width: "90%", maxWidth: 400, padding: 24 }}>
            <h3 style={{ marginTop: 0 }}>Delete Exam?</h3>
            <p className="muted">Are you sure you want to delete this exam? This action cannot be undone.</p>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn btn-ghost" onClick={() => setDeleteExamId("")} disabled={loading}>
                Cancel
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => void handleDeleteExam()} disabled={loading} style={{ color: "#dc2626" }}>
                {deletingExamId === deleteExamId && loading ? <span className="spinner" aria-label="Loading" /> : "Delete"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Edit Question Modal */}
      {editingQuestionId ? (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ width: "90%", maxWidth: 600, maxHeight: "90vh", overflowY: "auto", padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <h2 style={{ marginBottom: 0 }}>Edit Question</h2>
              <button type="button" className="btn btn-ghost" onClick={() => setEditingQuestionId("")}>
                ✕
              </button>
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Question Text</label>
              <input className="input" value={editQuestionText} onChange={(event) => setEditQuestionText(event.target.value)} />
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Question Type</label>
              <select className="select" value={editQuestionType} onChange={(event) => setEditQuestionType(event.target.value as "mcq" | "text")}>
                <option value="mcq">Multiple Choice (MCQ)</option>
                <option value="text">Text Answer</option>
              </select>
            </div>

            <div className="field" style={{ marginBottom: 16 }}>
              <label className="label">Marks</label>
              <input className="input" type="number" min={1} max={10} value={editQuestionMarks} onChange={(event) => setEditQuestionMarks(Number(event.target.value))} />
            </div>

            {editQuestionType === "mcq" ? (
              <>
                {[0, 1, 2, 3].map((index) => (
                  <div className="field" key={index} style={{ marginBottom: 16 }}>
                    <label className="label">Option {index + 1}</label>
                    <input
                      className="input"
                      value={editQuestionOptions[index]}
                      onChange={(event) => {
                        const updated = [...editQuestionOptions]
                        updated[index] = event.target.value
                        setEditQuestionOptions(updated)
                      }}
                    />
                  </div>
                ))}

                <div className="field" style={{ marginBottom: 16 }}>
                  <label className="label">Correct Answer</label>
                  <select className="select" value={editCorrectAnswer} onChange={(event) => setEditCorrectAnswer(event.target.value)}>
                    <option value="">Select correct answer</option>
                    {editQuestionOptions.filter((option) => option.trim()).map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            ) : null}

            {editQuestionType === "text" ? (
              <div className="field" style={{ marginBottom: 16 }}>
                <label className="label">Word Limit (0 = no limit)</label>
                <input className="input" type="number" min={0} value={editWordLimit} onChange={(event) => setEditWordLimit(Number(event.target.value))} />
              </div>
            ) : null}

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn btn-ghost" onClick={() => setEditingQuestionId("")} disabled={loading}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void handleUpdateQuestion()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Delete Question Confirmation */}
      {deleteQuestionId ? (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ width: "90%", maxWidth: 400, padding: 24 }}>
            <h3 style={{ marginTop: 0 }}>Delete Question?</h3>
            <p className="muted">Are you sure you want to delete this question? This action cannot be undone.</p>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn btn-ghost" onClick={() => setDeleteQuestionId("")} disabled={loading}>
                Cancel
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => void handleDeleteQuestion()} disabled={loading} style={{ color: "#dc2626" }}>
                {deletingQuestionId === deleteQuestionId && loading ? <span className="spinner" aria-label="Loading" /> : "Delete"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}