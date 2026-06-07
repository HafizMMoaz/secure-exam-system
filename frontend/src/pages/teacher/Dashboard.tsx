import { useEffect, useRef, useState, type MouseEvent } from "react"
import { useNavigate } from "react-router-dom"
import { io, type Socket } from "socket.io-client"
import {
  BookOpen,
  LayoutDashboard,
  FileQuestion,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  LogOut,
  Activity,
  Clipboard,
  Eye,
  Zap,
  Gauge,
  Copy,
  Check,
  Menu,
  X,
  Download,
} from "lucide-react"
import client from "../../api/client"
import { getErrorMessage } from "../../api/errors"
import { useAuth } from "../../hooks/useAuth"
import type { ApiResponse, ApprovalMode, Exam, LogEntry, QuestionWithAnswer, RiskScore, StudentUser } from "../../types"

type Tab = "exams" | "overview" | "questions" | "logs" | "risk" | "students"

interface ExamStatePayload {
  state: string
}

interface ActivationCodePayload {
  code: string
}

type ExamsResponse = ApiResponse<{ exams?: Exam[]; count?: number } | Exam[]>
type CreateExamResponse = ApiResponse<{ exam_id: string; title: string; state: string; approval_mode: ApprovalMode }>
type ApproveExamResponse = ApiResponse<{ exam_id: string; state: string }>
type ExamStateResponse = ApiResponse<ExamStatePayload>
type ExamDetailsResponse = ApiResponse<Exam>
type QuestionsResponse = ApiResponse<{ questions?: QuestionWithAnswer[]; count?: number } | QuestionWithAnswer[]>
type CreateQuestionResponse = ApiResponse<{ question_id: string }>
type LogsResponse = ApiResponse<{ logs?: LogEntry[] } | LogEntry[]>
type RiskResponse = ApiResponse<{ students?: RiskScore[]; scores?: RiskScore[] } | RiskScore[]>
type StudentsResponse = ApiResponse<{ users?: StudentUser[] } | StudentUser[]>


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

function CopyButton({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="btn-icon"
      title={copied ? "Copied" : (label || "Copy")}
      aria-label={label || "Copy"}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        } catch {/* clipboard blocked */}
      }}
      style={{ color: copied ? "var(--accent)" : undefined }}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  )
}

function humanizeAction(action: string): string {
  if (!action) return "—"
  const map: Record<string, string> = {
    user_login: "Signed in",
    user_logout: "Signed out",
    exam_started: "Started the exam",
    exam_submitted: "Submitted the exam",
    exam_approved: "Exam approved",
    exam_auto_submitted: "Auto-submitted (time up)",
    exam_state_transition: "Stage changed",
    tab_switch_detected: "Switched away from the exam",
    tab_focus_returned: "Returned to the exam",
    clipboard_paste_detected: "Pasted text",
    clipboard_copy_detected: "Copied text",
    clipboard_cut_detected: "Cut text",
    idle_period_detected: "Was idle",
    fast_answer_detected: "Answered very quickly",
    risk_score_computed: "Risk score calculated",
    otp_issued: "One-time code issued",
    otp_consumed: "Signed in with one-time code",
    otp_expired: "One-time code expired",
    otp_bad_code: "One-time code rejected",
    otp_max_attempts: "Too many code attempts",
    user_active_toggled: "Account access changed",
    input_validation_failed: "Suspicious input blocked",
    suspicious_behavior_detected: "Suspicious behaviour",
  }
  if (map[action]) return map[action]
  return action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

// Translate raw PRD state names into something a teacher reads as English.
// The backend state machine still uses the section 27.4 names - this only affects
// what the user sees on the UI.
function prettyExamState(state: string): string {
  switch (state) {
    case "NOT_STARTED": return "Draft"
    case "DEVICE_VERIFIED": return "Draft"
    case "TEACHER_APPROVED": return "Ready"
    case "ACTIVATION_VALID": return "Ready"
    case "IN_PROGRESS": return "Live"
    case "SUBMITTED": return "Finalising"
    case "ANALYZING": return "Finalising"
    case "COMPLETED": return "Closed"
    default: return state.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
  }
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
    case "HIGH":
      return "badge-red"
    case "MEDIUM":
      return "badge-orange"
    case "LOW":
      return "badge-green"
    default:
      return "badge-zinc"
  }
}

function formatLocalDateTime(value: string) {
  if (!value) return "-"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function approvalModeLabel(mode: ApprovalMode) {
  switch (mode) {
    case "manual":
      return "Manual approval only"
    case "code":
      return "Verification code only"
    default:
      return "Manual approval + verification code"
  }
}

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState<Tab>("exams")
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [examId, setExamId] = useState("")
  const [exams, setExams] = useState<Exam[]>([])
  const [newExamTitle, setNewExamTitle] = useState("")
  const [newExamDesc, setNewExamDesc] = useState("")
  const [newExamDuration, setNewExamDuration] = useState(60)
  const [newExamMaxStudents, setNewExamMaxStudents] = useState(30)
  const [newExamDate, setNewExamDate] = useState("")
  const [newExamStartTime, setNewExamStartTime] = useState("")
  const [newExamEndTime, setNewExamEndTime] = useState("")
  const [newExamApprovalMode, setNewExamApprovalMode] = useState<ApprovalMode>("both")
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
  const [liveEvents, setLiveEvents] = useState<Array<{ kind: string; user_id?: string; username?: string; timestamp?: string }>>([])
  const logsSocketRef = useRef<Socket | null>(null)
  const examRoomSocketRef = useRef<Socket | null>(null)
  // Mirror of the selected exam so the always-on log socket (which sets up
  // once on mount) can filter events without re-subscribing on every change.
  const examIdRef = useRef("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  // Auto-dismiss toasts so stale messages don't sit on screen forever
  // (e.g. "Activation code loaded" hanging around for the entire session).
  useEffect(() => {
    if (!success) return
    const t = window.setTimeout(() => setSuccess(""), 4000)
    return () => window.clearTimeout(t)
  }, [success])
  useEffect(() => {
    if (!error) return
    const t = window.setTimeout(() => setError(""), 6000)
    return () => window.clearTimeout(t)
  }, [error])
  const [activationCode, setActivationCode] = useState("")
  const [examState, setExamState] = useState("")
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null)
  
  // Edit/Delete state
  const [editingExamId, setEditingExamId] = useState("")
  const [editExamTitle, setEditExamTitle] = useState("")
  const [editExamDesc, setEditExamDesc] = useState("")
  const [editExamDuration, setEditExamDuration] = useState(60)
  const [editExamMaxStudents, setEditExamMaxStudents] = useState(30)
  const [editExamDate, setEditExamDate] = useState("")
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
  const [examStudents, setExamStudents] = useState<Array<{ student_id: string; username?: string; joined_at: string; approved: boolean; approved_at: string | null; approved_by: string | null; activated_at?: string | null }>>([])
  const [approvingStudentId, setApprovingStudentId] = useState("")

  // Sync the ref used by the always-on log socket to filter events to
  // the currently-selected exam.
  useEffect(() => {
    examIdRef.current = examId
  }, [examId])

  const highRiskCount = riskData.filter((item) => item.risk_level === "HIGH").length
  const canApproveExam = examState === "NOT_STARTED" || examState === "DEVICE_VERIFIED"
  // Questions and exam metadata become read-only once the exam is approved
  // - same gate the backend enforces on create/update/delete_question.
  const canEditQuestions = examState === "NOT_STARTED" || !examState
  const canShowActivationCode = ["TEACHER_APPROVED", "ACTIVATION_VALID", "IN_PROGRESS"].includes(examState)
  const requiresManualApproval = (selectedExam?.approval_mode || "both") !== "code"
  const requiresVerificationCode = (selectedExam?.approval_mode || "both") !== "manual"

  // Update once every 30s so the "exam is over" gate (end_time-based)
  // flips without requiring a refresh.
  const [nowTs, setNowTs] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNowTs(Date.now()), 30_000)
    return () => window.clearInterval(id)
  }, [])
  const endsAt = selectedExam?.end_time ? new Date(selectedExam.end_time).getTime() : 0
  const examOver = examState === "COMPLETED" || (endsAt > 0 && nowTs > endsAt)

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
      void loadExamStudents(targetExamId, { silent: true })
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

    if (!newExamDate || !newExamStartTime || !newExamEndTime) {
      setError("Please pick a date, a start time and an end time.")
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

    const startTimeDate = new Date(`${newExamDate}T${newExamStartTime}`)
    const endTimeDate = new Date(`${newExamDate}T${newExamEndTime}`)
    if (Number.isNaN(startTimeDate.getTime()) || Number.isNaN(endTimeDate.getTime())) {
      setError("That date and time don't look right.")
      return
    }
    if (endTimeDate <= startTimeDate) {
      setError("End time must be after start time.")
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
        approval_mode: newExamApprovalMode,
      })

      const createdExam: Exam = {
        exam_id: response.data.data.exam_id,
        title,
        description,
        duration_minutes: newExamDuration,
        approval_mode: response.data.data.approval_mode,
        state: response.data.data.state,
        created_at: new Date().toISOString(),
        max_students: newExamMaxStudents,
        students_count: 0,
        approved_count: 0,
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
      setNewExamDate("")
      setNewExamStartTime("")
      setNewExamEndTime("")
      setNewExamApprovalMode("both")
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

  const loadRiskDashboard = async (targetExamId: string, opts?: { silent?: boolean }) => {
    if (!targetExamId) return
    const silent = opts?.silent
    if (!silent) {
      setLoading(true)
      setError("")
      setSuccess("")
    }
    try {
      const response = await client.get<RiskResponse>(`/api/risk/dashboard/${targetExamId}`)
      setRiskData(normalizeArray<RiskScore>(response.data.data, ["students", "scores"]))
    } catch (riskLoadError) {
      if (!silent) setError(getErrorMessage(riskLoadError))
    } finally {
      if (!silent) setLoading(false)
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
    // Split the stored ISO into date + time fields for the form.
    const start = new Date(exam.start_time)
    const end = new Date(exam.end_time)
    if (!Number.isNaN(start.getTime())) {
      const pad = (n: number) => String(n).padStart(2, "0")
      setEditExamDate(`${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`)
      setEditExamStartTime(`${pad(start.getHours())}:${pad(start.getMinutes())}`)
    } else {
      setEditExamDate("")
      setEditExamStartTime("")
    }
    if (!Number.isNaN(end.getTime())) {
      const pad = (n: number) => String(n).padStart(2, "0")
      setEditExamEndTime(`${pad(end.getHours())}:${pad(end.getMinutes())}`)
    } else {
      setEditExamEndTime("")
    }
  }

  const handleUpdateExam = async () => {
    if (!editingExamId) return

    const title = editExamTitle.trim()
    if (!title) {
      setError("Title is required")
      return
    }

    if (!editExamDate || !editExamStartTime || !editExamEndTime) {
      setError("Please pick a date, a start time and an end time.")
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
      const startTimeDate = new Date(`${editExamDate}T${editExamStartTime}`)
      const endTimeDate = new Date(`${editExamDate}T${editExamEndTime}`)
      if (Number.isNaN(startTimeDate.getTime()) || Number.isNaN(endTimeDate.getTime())) {
        setError("That date and time don't look right.")
        setLoading(false)
        return
      }
      if (endTimeDate <= startTimeDate) {
        setError("End time must be after start time.")
        setLoading(false)
        return
      }
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

  const loadExamStudents = async (targetExamId: string, opts?: { silent?: boolean }) => {
    if (!targetExamId) return
    const silent = opts?.silent
    if (!silent) setLoading(true)
    try {
      const response = await client.get<ApiResponse<{ students: Array<{ student_id: string; username?: string; joined_at: string; approved: boolean; approved_at: string | null; approved_by: string | null; activated_at?: string | null }>; count: number }>>(
        `/api/questions/exams/${targetExamId}/students`
      )
      setExamStudents(response.data.data.students || [])
    } catch (studentsError) {
      if (!silent) setError(getErrorMessage(studentsError))
    } finally {
      if (!silent) setLoading(false)
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

  // Auto-load risk dashboard whenever the user opens the Risk tab with an
  // exam selected. WebSocket updates from `risk_computed` keep it fresh
  // after that - no manual refresh button.
  useEffect(() => {
    if (tab === "risk" && examId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadRiskDashboard(examId, { silent: true })
    }
  }, [tab, examId])

  // Always-on audit log stream. Connects when the dashboard mounts and
  // stays connected regardless of which tab is active - logs accumulate
  // in the background so the Activity tab is fresh the moment you open it.
  useEffect(() => {
    const base = client.defaults.baseURL || window.location.origin
    const socket = io(`${base}/monitoring`, {
      transports: ["websocket", "polling"],
      reconnection: true,
    })
    logsSocketRef.current = socket

    socket.on("connect", () => socket.emit("subscribe_logs"))
    socket.on("log_event", (incoming: LogEntry) => {
      // The logs WebSocket is global - it streams every audit entry in
      // the system. The audit-log view is scoped to the selected exam
      // (initial load filters by exam_id), so the live stream has to
      // match. Empty exam_id is a system-wide event (no exam context)
      // and we still surface it for the selected exam too.
      const current = examIdRef.current
      if (!current) return
      const incomingExam = incoming.exam_id || ""
      if (incomingExam && incomingExam !== current) return
      setLogs((prev) => [{ ...incoming, received_at: incoming.timestamp } as LogEntry, ...prev].slice(0, 500))
    })

    return () => {
      socket.disconnect()
      logsSocketRef.current = null
    }
  }, [])

  // Always-on exam-room subscription. Stays connected for the lifetime of
  // any loaded exam regardless of which tab is active, so the live events
  // feed, audit log, and Students Joined table all accumulate continuously.
  // Previously this was tab-scoped - events that fired while the teacher
  // was on a different tab were lost until a manual refresh.
  useEffect(() => {
    if (!examId) {
      if (examRoomSocketRef.current) {
        examRoomSocketRef.current.disconnect()
        examRoomSocketRef.current = null
      }
      return
    }

    const base = client.defaults.baseURL || window.location.origin
    const socket = io(`${base}/monitoring`, {
      transports: ["websocket", "polling"],
      reconnection: true,
    })
    examRoomSocketRef.current = socket

    socket.on("connect", () => socket.emit("subscribe", { exam_id: examId }))

    socket.on("students_changed", () => {
      void loadExamStudents(examId, { silent: true })
    })

    const onMonitoring = (kind: string) => (data: {
      user_id?: string; username?: string; timestamp?: string;
      event_type?: string; is_idle?: boolean; is_fast_answer?: boolean;
    }) => {
      // Only surface signals that are actually suspicious - a quiet feed is
      // a healthy feed. Every save_answer fires `behavioral_event`, every
      // 15s heartbeat fires `activity_event` - without filtering you get a
      // wall of noise and miss the real signals.
      if (kind === "behavioral_event" && !data.is_fast_answer) return
      if (kind === "activity_event" && !data.is_idle) return
      if (kind === "tab_event" && data.event_type !== "blur" && data.event_type !== "hidden") return
      // clipboard_event always lands - paste / copy / cut all matter

      setLiveEvents((prev) => [
        { kind, user_id: data.user_id, username: data.username, timestamp: data.timestamp || new Date().toISOString() },
        ...prev,
      ].slice(0, 50))
    }
    socket.on("tab_event", onMonitoring("tab_event"))
    socket.on("clipboard_event", onMonitoring("clipboard_event"))
    socket.on("activity_event", onMonitoring("activity_event"))
    socket.on("behavioral_event", onMonitoring("behavioral_event"))

    socket.on("risk_computed", () => {
      // State has just moved through SUBMITTED -> ANALYZING -> COMPLETED on
      // the server. Pull the new state silently so the Current Stage card
      // and the risk dashboard both stay in sync without nuking any error
      // banner the teacher might be reading.
      void loadRiskDashboard(examId, { silent: true })
      client
        .get<ExamStateResponse>(`/api/auth/exam/state/${examId}`)
        .then((res) => {
          const next = res.data.data.state
          setExamState(next)
          setExams((current) => current.map((exam) => (exam.exam_id === examId ? { ...exam, state: next } : exam)))
        })
        .catch(() => {})
    })

    return () => {
      socket.disconnect()
      examRoomSocketRef.current = null
    }
  }, [examId])

  const handleExportResultsCsv = async () => {
    if (!examId) return
    try {
      const response = await client.get<ApiResponse<{
        exam_title: string
        total_marks: number
        negative_marking_factor: number
        risk_max_penalty_fraction: number
        students: Array<{
          username: string
          mcq_correct: number
          mcq_wrong: number
          mcq_unanswered: number
          mcq_score: number
          mcq_total: number
          text_pending_review: number
          text_total: number
          negative_penalty: number
          risk_score: number
          risk_penalty: number
          final_score: number
          exam_total: number
        }>
      }>>(`/api/questions/exams/${examId}/results`)
      const { exam_title, students, negative_marking_factor, risk_max_penalty_fraction } = response.data.data
      const headers = [
        "username",
        "mcq_correct",
        "mcq_wrong",
        "mcq_unanswered",
        "mcq_score",
        "mcq_total",
        "text_pending_review",
        "text_total",
        "negative_penalty",
        "risk_score",
        "risk_penalty",
        "final_score",
        "exam_total",
      ]
      const escape = (v: unknown) => {
        const s = v === null || v === undefined ? "" : String(v)
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
      }
      const rows = students.map((r) => headers.map((h) => escape((r as unknown as Record<string, unknown>)[h])).join(","))
      const meta = [
        `# Exam: ${exam_title}`,
        `# Negative marking: -${(negative_marking_factor * 100).toFixed(0)}% of each wrong MCQ's marks`,
        `# Risk penalty: up to -${(risk_max_penalty_fraction * 100).toFixed(0)}% of marks earned at 10/10 risk (scaled linearly)`,
        `# final_score = max(0, mcq_score - negative_penalty - risk_penalty)`,
      ].join("\n")
      const csv = [meta, headers.join(","), ...rows].join("\n")
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      const slug = (exam_title || "exam").replace(/[^\w-]+/g, "_")
      a.href = url
      a.download = `${slug}_results.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (resultsError) {
      setError(getErrorMessage(resultsError))
    }
  }

  const handleExportRiskCsv = () => {
    if (!riskData.length) return
    const examTitle = (selectedExam?.title || "exam").replace(/[^\w-]+/g, "_")
    const headers = [
      "username", "score", "risk_level",
      "tab_switches", "clipboard_pastes", "idle_seconds",
      "fast_answers", "similarity_score", "computed_at",
    ]
    const escape = (v: unknown) => {
      const s = v === null || v === undefined ? "" : String(v)
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
    }
    const rows = [...riskData]
      .sort((a, b) => b.score - a.score)
      .map((r) => [
        r.username || "Deleted user",
        r.score.toFixed(2),
        r.risk_level,
        r.metrics.tab_switch_count ?? r.metrics.tab_switches ?? 0,
        r.metrics.clipboard_paste_count ?? 0,
        r.metrics.idle_time_seconds ?? 0,
        r.metrics.fast_answer_count ?? r.metrics.fast_answers ?? 0,
        (r.metrics.similarity_score ?? 0).toFixed?.(4) ?? r.metrics.similarity_score ?? 0,
        r.computed_at || "",
      ].map(escape).join(","))
    const csv = [headers.join(","), ...rows].join("\n")
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${examTitle}_risk_scores.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const navItems: Array<{ key: Tab; label: string; icon: typeof BookOpen }> = [
    { key: "exams", label: "Exams", icon: BookOpen },
    { key: "overview", label: "Overview", icon: LayoutDashboard },
    { key: "questions", label: "Questions", icon: FileQuestion },
    { key: "logs", label: "Activity", icon: ScrollText },
    { key: "risk", label: "Risk", icon: ShieldAlert },
  ]

  const pageMeta: Record<Tab, { title: string; sub: string }> = {
    exams: { title: "Exams", sub: "Create exams, approve students, and start the timer." },
    overview: { title: "Overview", sub: "A quick summary of the exam you have open." },
    questions: { title: "Questions", sub: "Add, edit, or remove the questions on this paper." },
    logs: { title: "Activity", sub: "Recent activity from students and the system, updated live." },
    risk: { title: "Risk", sub: "See which students may need a closer look." },
    students: { title: "Students", sub: "Who has joined this exam." },
  }
  const currentMeta = pageMeta[tab]

  return (
    <div className="exam-shell">
      <header className="topbar">
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            className="sidebar-toggle"
            aria-label={sidebarOpen ? "Close menu" : "Open menu"}
            onClick={() => setSidebarOpen((v) => !v)}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <div className="topbar-brand">
            <span className="topbar-brand-mark"><ShieldCheck size={12} /></span>
            Secure Exam
          </div>
        </div>

        <div className="topbar-context">
          {selectedExam ? (
            <>
              <span className="exam-title">{selectedExam.title}</span>
              {examState ? (
                <span className={`badge ${getStateBadgeClass(examState)}`}>
                  {prettyExamState(examState)}
                </span>
              ) : null}
            </>
          ) : (
            <span className="crumb">No exam selected</span>
          )}
        </div>

        <div className="topbar-right">
          <span className="topbar-user"><b>{user?.username || "—"}</b></span>
        </div>
      </header>

      <div className="app-shell">
        <nav className={`sidebar ${sidebarOpen ? "open" : ""}`}>
          <div className="sidebar-group">
            <div className="sidebar-group-title">Navigation</div>
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.key}
                  type="button"
                  className={`sidebar-link ${tab === item.key ? "active" : ""}`}
                  onClick={() => { setTab(item.key); setSidebarOpen(false) }}
                >
                  <Icon /> {item.label}
                </button>
              )
            })}
          </div>

          <div className="sidebar-group">
            <div className="sidebar-group-title">Current exam</div>
            <div style={{ padding: "0 10px" }}>
              {exams.length > 0 ? (
                <select
                  className="select"
                  value={examId}
                  onChange={(event) => {
                    const id = event.target.value
                    if (!id) return
                    const exam = exams.find((e) => e.exam_id === id)
                    if (exam) void handleSelectExam(exam)
                  }}
                  style={{ fontSize: "0.875rem" }}
                >
                  <option value="">Choose an exam…</option>
                  {exams.map((exam) => (
                    <option key={exam.exam_id} value={exam.exam_id}>{exam.title}</option>
                  ))}
                </select>
              ) : (
                <p className="muted" style={{ fontSize: "0.8125rem", padding: 0 }}>
                  No exams yet — use the <b>Exams</b> tab to create one.
                </p>
              )}
            </div>
          </div>

          <div className="sidebar-spacer" />

          <div className="sidebar-bottom">
            <button type="button" className="sidebar-link" onClick={handleLogout}>
              <LogOut /> Sign out
            </button>
          </div>

        </nav>
        {sidebarOpen ? (
          <div
            className="sidebar-backdrop open"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        ) : null}

        <main className="main">
          <div className="page-header">
            <div>
              <h1 className="page-title">{currentMeta.title}</h1>
              <p className="page-sub">{currentMeta.sub}</p>
            </div>
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}
          {success ? <div className="alert alert-success">{success}</div> : null}

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

              <div className="form-grid-2">
                <div className="field">
                  <label className="label">Max students</label>
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
                  <label className="label">Exam date</label>
                  <input className="input" type="date" value={newExamDate} onChange={(event) => setNewExamDate(event.target.value)} />
                </div>
              </div>

              <div className="form-grid-3">
                <div className="field">
                  <label className="label">Duration (min)</label>
                  <input className="input" type="number" value={newExamDuration} onChange={(event) => setNewExamDuration(Number.parseInt(event.target.value || "0", 10) || 0)} />
                </div>
                <div className="field">
                  <label className="label">Starts at</label>
                  <input className="input" type="time" value={newExamStartTime} onChange={(event) => setNewExamStartTime(event.target.value)} />
                </div>
                <div className="field">
                  <label className="label">Ends at</label>
                  <input className="input" type="time" value={newExamEndTime} onChange={(event) => setNewExamEndTime(event.target.value)} />
                </div>
              </div>

              <div className="field">
                <label className="label">Student entry approval</label>
                <select
                  className="input"
                  value={newExamApprovalMode}
                  onChange={(event) => setNewExamApprovalMode(event.target.value as ApprovalMode)}
                >
                  <option value="both">Manual approval + verification code</option>
                  <option value="manual">Manual approval only</option>
                  <option value="code">Verification code only</option>
                </select>
              </div>

              <button type="button" className="btn btn-primary" onClick={() => void handleCreateExam()} disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Create exam"}
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
                        <td>{exam.approved_count ?? 0}/{exam.max_students}</td>
                        <td><span className={`badge ${getStateBadgeClass(exam.state)}`}>{prettyExamState(exam.state)}</span></td>
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
                  <div className="card" style={{ display: "grid", gap: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
                      <div style={{ minWidth: 0 }}>
                        <h2 style={{ marginBottom: 4 }}>{selectedExam.title}</h2>
                        <p className="muted">{selectedExam.description || "No description"}</p>
                      </div>
                      <span className={`badge ${getStateBadgeClass(selectedExam.state)}`} style={{ flexShrink: 0 }}>{prettyExamState(selectedExam.state)}</span>
                    </div>

                    <div className="stats-grid" style={{ marginBottom: 0 }}>
                      <div className="stat-card">
                        <div className="stat-eyebrow">Duration</div>
                        <div className="stat-value">{selectedExam.duration_minutes}<span className="stat-suffix">min</span></div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-eyebrow">Approved</div>
                        <div className="stat-value">
                          {selectedExam.approved_count ?? 0}
                          <span className="stat-suffix">/{selectedExam.max_students}</span>
                        </div>
                        {selectedExam.students_count > (selectedExam.approved_count ?? 0) ? (
                          <div className="muted" style={{ fontSize: "0.75rem", marginTop: 4 }}>
                            {selectedExam.students_count - (selectedExam.approved_count ?? 0)} pending approval
                          </div>
                        ) : null}
                      </div>
                      <div className="stat-card">
                        <div className="stat-eyebrow">Questions</div>
                        <div className="stat-value">{selectedExam.total_questions ?? 0}</div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-eyebrow">Total marks</div>
                        <div className="stat-value">{selectedExam.total_marks ?? 0}</div>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: 24, flexWrap: "wrap", fontSize: "0.8125rem", color: "var(--ink-3)" }}>
                      <span><b style={{ color: "var(--ink-2)" }}>Starts</b> · {formatLocalDateTime(selectedExam.start_time)}</span>
                      <span><b style={{ color: "var(--ink-2)" }}>Ends</b> · {formatLocalDateTime(selectedExam.end_time)}</span>
                      <span><b style={{ color: "var(--ink-2)" }}>Entry mode</b> · {approvalModeLabel(selectedExam.approval_mode || "both")}</span>
                    </div>

                    <div className="hairline" />

                    <div style={{ display: "grid", gap: 12 }}>
                      <div>
                        <div className="eyebrow" style={{ marginBottom: 6 }}>Exam ID — share with students</div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.8125rem", padding: "8px 12px", background: "var(--surface-2)", border: "1px solid var(--rule)", borderRadius: "var(--radius-sm)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {examId}
                          </code>
                          <CopyButton value={examId} label="Copy exam ID" />
                        </div>
                      </div>
                      {requiresVerificationCode && activationCode ? (
                        <div>
                          <div className="eyebrow" style={{ marginBottom: 6 }}>Join code — share with students</div>
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <code style={{ fontFamily: "var(--font-mono)", fontSize: "1rem", fontWeight: 500, padding: "8px 12px", background: "var(--accent-tint)", border: "1px solid var(--accent)", color: "var(--accent)", borderRadius: "var(--radius-sm)", flex: 1, letterSpacing: "0.05em" }}>
                              {activationCode}
                            </code>
                            <CopyButton value={activationCode} label="Copy join code" />
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                <div className="stats-grid" style={{ marginBottom: 0 }}>
                  <div className="stat-card">
                    <div className="stat-eyebrow">Activity records</div>
                    <div className="stat-value">{logs.length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-eyebrow">High-risk students</div>
                    <div className="stat-value" style={{ color: highRiskCount > 0 ? "var(--risk-high)" : "var(--ink)" }}>{highRiskCount}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-eyebrow">Current stage</div>
                    <div className="stat-value" style={{ fontSize: "1rem", fontFamily: "var(--font-sans)", textTransform: "none", letterSpacing: 0 }}>
                      {examState ? prettyExamState(examState) : "—"}
                    </div>
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
                  {canShowActivationCode && requiresVerificationCode ? (
                    <button type="button" className="btn btn-primary" onClick={() => void handleGenerateActivationCode()} disabled={loading}>
                      {loading ? <span className="spinner" aria-label="Loading" /> : "View Activation Code"}
                    </button>
                  ) : null}
                  {!requiresVerificationCode ? (
                    <span className="badge badge-zinc" style={{ alignSelf: "center" }}>
                      Verification code disabled for this exam
                    </span>
                  ) : null}
                  {examState === "SUBMITTED" || examState === "ANALYZING" ? (
                    <span className="badge badge-zinc" style={{ alignSelf: "center" }}>
                      <span className="spinner" style={{ width: 10, height: 10, marginRight: 6 }} /> Scoring…
                    </span>
                  ) : null}
                  {examState === "COMPLETED" ? (
                    <button type="button" className="btn btn-ghost" onClick={() => setTab("risk")} disabled={loading}>
                      View Risk Scores
                    </button>
                  ) : null}
                  {examOver ? (
                    <button type="button" className="btn btn-primary" onClick={() => void handleExportResultsCsv()} disabled={loading}>
                      <Download size={14} /> Export Results
                    </button>
                  ) : null}
                </div>


                <hr style={{ margin: "24px 0", border: "none", borderTop: "1px solid #e5e7eb" }} />

                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                  <h3 style={{ marginBottom: 0 }}>Students Joined</h3>
                  <span className="muted" style={{ fontSize: "0.8125rem" }}>
                    {examStudents.length} {examStudents.length === 1 ? "student" : "students"} · {requiresManualApproval ? "manual approval" : "auto-approved"}
                  </span>
                </div>

                {examStudents.length === 0 ? (
                  <p className="muted">No students have joined this exam yet</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Student</th>
                          <th>Joined</th>
                          <th>Activated</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {examStudents.map((student) => (
                          <tr key={student.student_id}>
                            <td>{student.username || "—"}</td>
                            <td>{formatLocalDateTime(student.joined_at)}</td>
                            <td>{student.activated_at ? formatLocalDateTime(student.activated_at) : <span className="muted">—</span>}</td>
                            <td>
                              <span className={`badge ${student.approved ? "badge-green" : "badge-zinc"}`}>
                                {student.approved ? "Approved" : requiresManualApproval ? "Pending" : "Auto-approved"}
                              </span>
                            </td>
                            <td>
                              {!student.approved && requiresManualApproval ? (
                                <button
                                  type="button"
                                  className="btn btn-primary"
                                  onClick={() => void handleApproveStudent(student.student_id)}
                                  disabled={loading}
                                >
                                  {approvingStudentId === student.student_id && loading ? <span className="spinner" aria-label="Loading" /> : "Approve"}
                                </button>
                              ) : (
                                <span className="muted">{requiresManualApproval ? "Approved" : "Not required"}</span>
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
              {!canEditQuestions ? (
                <div className="alert alert-warning">
                  This exam is locked — questions can't be added, edited, or removed once it has been approved.
                </div>
              ) : null}
              {canEditQuestions ? (
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
              ) : null}

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
                            {canEditQuestions ? (
                              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                <button type="button" className="btn btn-ghost" onClick={() => handleOpenEditQuestion(question)} disabled={loading}>
                                  Edit
                                </button>
                                <button type="button" className="btn btn-ghost" onClick={() => setDeleteQuestionId(question.question_id)} disabled={loading} style={{ color: "#dc2626" }}>
                                  Delete
                                </button>
                              </div>
                            ) : (
                              <span className="muted" style={{ fontSize: "0.8125rem" }}>locked</span>
                            )}
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <h3 style={{ marginBottom: 0 }}>Audit log</h3>
              <span className="muted" style={{ fontSize: "0.8125rem" }}>{logs.length} entries · live</span>
            </div>

            {logs.length === 0 ? (
              <div className="empty">
                <ScrollText />
                <div className="empty-title">No activity yet</div>
                <div className="empty-body">
                  Once students start, you&apos;ll see their actions here automatically.
                </div>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>When</th>
                      <th>Who</th>
                      <th>What happened</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((entry, idx) => (
                      <tr key={`${entry.log_id}-${idx}`}>
                        <td className="mono" style={{ color: "var(--ink-3)", whiteSpace: "nowrap" }}>
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "—"}
                        </td>
                        <td>{entry.username || (entry.user_id ? "—" : "system")}</td>
                        <td>{humanizeAction(entry.action)}</td>
                        <td><span className={`badge ${getStateBadgeClass(entry.level)}`}>{entry.level}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : null}

        {tab === "risk" ? (
          <section className="card" style={{ display: "grid", gap: 20 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <h3 style={{ margin: 0 }}>Risk scores</h3>
                {liveEvents.length > 0 ? (
                  <span className="muted" style={{ fontSize: "0.8125rem" }}>{liveEvents.length} live events</span>
                ) : null}
              </div>
              {examState === "COMPLETED" && riskData.length > 0 ? (
                <button type="button" className="btn btn-ghost btn-sm" onClick={handleExportRiskCsv}>
                  <Download size={14} /> Export CSV
                </button>
              ) : null}
            </div>

            {riskData.length === 0 ? (
              <div className="empty">
                <Gauge />
                <div className="empty-title">No scores yet</div>
                <div className="empty-body">
                  {!examId
                    ? "Pick an exam from the sidebar to see its risk breakdown."
                    : examState === "COMPLETED"
                    ? "Scores will appear here once they finish publishing."
                    : examState === "SUBMITTED" || examState === "ANALYZING"
                    ? "Scoring is running in the background. Results will show up here as soon as they're ready."
                    : "Scores appear automatically once the exam ends."}
                </div>
              </div>
            ) : (
              <div>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-eyebrow">High risk</div>
                    <div className="stat-value">{riskData.filter((r) => r.risk_level === "HIGH").length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-eyebrow">Medium</div>
                    <div className="stat-value">{riskData.filter((r) => r.risk_level === "MEDIUM").length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-eyebrow">Low</div>
                    <div className="stat-value">{riskData.filter((r) => r.risk_level === "LOW").length}</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-eyebrow">Cohort avg.</div>
                    <div className="stat-value">
                      {(riskData.reduce((acc, r) => acc + r.score, 0) / riskData.length).toFixed(1)}
                      <span className="stat-suffix">/10</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "16px 0 10px" }}>
                  <h3>Students</h3>
                  <span className="muted">Sorted by score</span>
                </div>

                <div className="risk-list">
                  {[...riskData]
                    .sort((a, b) => b.score - a.score)
                    .map((row) => (
                      <div key={`${row.student_id}-${row.computed_at}`} className={`risk-row ${row.risk_level.toLowerCase()}`}>
                        <div className="risk-row-head">
                          <span className="risk-row-name">{row.username || "Deleted user"}</span>
                          <span className={`badge ${getStateBadgeClass(row.risk_level)}`}>{row.risk_level}</span>
                        </div>
                        <div className="risk-row-score">
                          <span className="num">{row.score.toFixed(1)}</span>
                          <span className="muted">/10</span>
                        </div>
                        <div className="risk-row-bar">
                          <div className="risk-row-bar-fill" style={{ width: `${Math.min(100, row.score * 10)}%` }} />
                        </div>
                        <div className="risk-row-metrics">
                          <span className="risk-metric">
                            <Eye />
                            <span className="num">{row.metrics.tab_switch_count ?? row.metrics.tab_switches ?? 0}</span>
                            <span className="label-inline">tab switches</span>
                          </span>
                          <span className="risk-metric">
                            <Clipboard />
                            <span className="num">{row.metrics.clipboard_paste_count ?? 0}</span>
                            <span className="label-inline">pastes</span>
                          </span>
                          <span className="risk-metric">
                            <Activity />
                            <span className="num">{row.metrics.idle_time_seconds ?? 0}</span>
                            <span className="label-inline">idle (s)</span>
                          </span>
                          <span className="risk-metric">
                            <Zap />
                            <span className="num">{row.metrics.fast_answer_count ?? row.metrics.fast_answers ?? 0}</span>
                            <span className="label-inline">fast answers</span>
                          </span>
                          <span className="risk-metric">
                            <Gauge />
                            <span className="num">{(row.metrics.similarity_score ?? 0).toFixed?.(2) ?? row.metrics.similarity_score ?? 0}</span>
                            <span className="label-inline">similarity</span>
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {liveEvents.length > 0 ? (
              <div>
                <div className="live-feed-head">
                  <h3>Live telemetry</h3>
                  <span className="muted">Last 50 · newest first</span>
                </div>
                <div className="live-feed">
                  {liveEvents.map((ev, idx) => {
                    const iconMap: Record<string, typeof Eye> = {
                      tab_event: Eye,
                      clipboard_event: Clipboard,
                      activity_event: Activity,
                      behavioral_event: Zap,
                    }
                    const labelMap: Record<string, string> = {
                      tab_event: "Tab switch",
                      clipboard_event: "Clipboard event",
                      activity_event: "Activity heartbeat",
                      behavioral_event: "Behavioral signal",
                    }
                    const Icon = iconMap[ev.kind] || Activity
                    const who = ev.username || (ev.user_id ? "anonymous" : "")
                    let timeText = ""
                    if (ev.timestamp) {
                      const d = new Date(ev.timestamp)
                      timeText = Number.isNaN(d.getTime())
                        ? ""
                        : d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
                    }
                    return (
                      <div key={`${ev.kind}-${idx}`} className={`live-event kind-${ev.kind}`}>
                        <span className="live-event-icon"><Icon /></span>
                        <div>
                          <div className="live-event-title">{labelMap[ev.kind] || ev.kind}</div>
                          {who ? <div className="live-event-meta">{who}</div> : null}
                        </div>
                        {timeText ? <span className="live-event-time">{timeText}</span> : null}
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}
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

            <div className="form-grid-2" style={{ marginBottom: 16 }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Max students</label>
                <input className="input" type="number" min={1} max={200} value={editExamMaxStudents} onChange={(event) => setEditExamMaxStudents(Number.parseInt(event.target.value || "0", 10) || 0)} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Exam date</label>
                <input className="input" type="date" value={editExamDate} onChange={(event) => setEditExamDate(event.target.value)} />
              </div>
            </div>

            <div className="form-grid-3" style={{ marginBottom: 16 }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Duration (min)</label>
                <input className="input" type="number" value={editExamDuration} onChange={(event) => setEditExamDuration(Number.parseInt(event.target.value || "0", 10) || 0)} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Starts at</label>
                <input className="input" type="time" value={editExamStartTime} onChange={(event) => setEditExamStartTime(event.target.value)} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="label">Ends at</label>
                <input className="input" type="time" value={editExamEndTime} onChange={(event) => setEditExamEndTime(event.target.value)} />
              </div>
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