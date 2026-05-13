import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import {
  ShieldCheck,
  LogOut,
  Send,
  Map as MapIcon,
} from "lucide-react"
import client from "../../api/client"
import { useAuth } from "../../hooks/useAuth"
import { getDeviceSignals, useDeviceFingerprint } from "../../hooks/useDeviceFingerprint"
import { useExamMonitoring } from "../../hooks/useExamMonitoring"
import type { ApiResponse, ExamStep, Question } from "../../types"

interface ExamStatePayload {
  state: string
}

interface PublicExamPayload {
  exam_id: string
  title: string
  description: string
  duration_minutes: number
  state: string
  start_time: string
  end_time: string
  max_students: number
  students_count: number
  total_questions: number
  total_marks: number
}

interface EnrollExamPayload {
  already_enrolled: boolean
  exam_id: string
}

interface TimerStartPayload {
  remaining_seconds: number
  resumed?: boolean
}

interface AllQuestionsPayload {
  questions: Question[]
  total_questions: number
  total_marks: number
}

interface AnswersListPayload {
  answers: Record<string, string>
}

type ExamStateResponse = ApiResponse<ExamStatePayload>
type PublicExamResponse = ApiResponse<PublicExamPayload>
type EnrollExamResponse = ApiResponse<EnrollExamPayload>
type TimerStartResponse = ApiResponse<TimerStartPayload>
type AllQuestionsResponse = ApiResponse<AllQuestionsPayload>
type AnswersListResponse = ApiResponse<AnswersListPayload>

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage
    }
  }

  return "Unknown error"
}

function formatLocalDateTime(value: string) {
  if (!value) return "-"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function getRemainingSeconds(value: string, referenceTime: number) {
  if (!value) return 0
  const time = new Date(value).getTime()
  if (Number.isNaN(time)) return 0
  return Math.max(0, Math.ceil((time - referenceTime) / 1000))
}

const STEP_ORDER: ExamStep[] = [
  "DEVICE_REGISTRATION",
  "EXAM_SELECTION",
  "EXAM_WAITING",
  "ACTIVATION",
  "RANDOMIZATION",
  "IN_PROGRESS",
  "SUBMITTED",
]

const STEP_LABELS: Record<ExamStep, string> = {
  DEVICE_REGISTRATION: "Device",
  EXAM_SELECTION: "Pick exam",
  EXAM_WAITING: "Lobby",
  ACTIVATION: "Activate",
  RANDOMIZATION: "Shuffle",
  IN_PROGRESS: "Sit",
  SUBMITTED: "Submitted",
}

function StepIndicator({ currentStep }: { currentStep: ExamStep }) {
  const currentIndex = STEP_ORDER.indexOf(currentStep)
  return (
    <div className="exam-progress">
      {STEP_ORDER.map((step, idx) => {
        const status = idx < currentIndex ? "done" : idx === currentIndex ? "current" : ""
        return (
          <span key={step} className={`exam-step ${status}`}>
            <span className={`exam-step-dot ${status}`}>
              {idx < currentIndex ? "✓" : idx + 1}
            </span>
            <span className="exam-step-label">{STEP_LABELS[step]}</span>
            {idx < STEP_ORDER.length - 1 ? (
              <span className={`exam-step-rule ${idx < currentIndex ? "done" : ""}`} />
            ) : null}
          </span>
        )
      })}
    </div>
  )
}

function StudentChrome({
  user,
  currentStep,
  onLogout,
  showStepIndicator = true,
  children,
}: {
  user: { username: string; role: string } | null
  currentStep: ExamStep
  onLogout: () => void
  showStepIndicator?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="exam-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="topbar-brand-mark"><ShieldCheck size={12} /></span>
          Secure Exam
        </div>
        <div className="topbar-context">
          <span className="exam-title">{user?.username || "—"}</span>
          <span className="badge badge-zinc">{user?.role || "student"}</span>
        </div>
        <div className="topbar-right">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onLogout}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </header>
      {showStepIndicator ? <StepIndicator currentStep={currentStep} /> : null}
      {children}
    </div>
  )
}

export default function ExamPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const deviceFingerprint = useDeviceFingerprint()

  const [step, setStep] = useState<ExamStep>("DEVICE_REGISTRATION")
  const [examId, setExamId] = useState("")
  const [examIdInput, setExamIdInput] = useState("")
  const [examTitle, setExamTitle] = useState("")
  const [examDuration, setExamDuration] = useState(0)
  const [examStartTime, setExamStartTimeStr] = useState("")
  const [examEndTime, setExamEndTime] = useState("")
  const [maxStudents, setMaxStudents] = useState(0)
  const [studentsCount, setStudentsCount] = useState(0)
  const [activationCode, setActivationCode] = useState("")
  const [questions, setQuestions] = useState<Question[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentIndex, setCurrentIndex] = useState(0)
  const [questionStartTimes, setQuestionStartTimes] = useState<Record<string, number>>({})
  const [showMap, setShowMap] = useState(false)
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false)
  const [savingAnswer, setSavingAnswer] = useState(false)
  const [totalMarks, setTotalMarks] = useState(0)
  const [examTimerStartTime, setExamTimerStartTime] = useState(0)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [currentTime, setCurrentTime] = useState(() => Date.now())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [examState, setExamState] = useState("")
  const [resumeMessage, setResumeMessage] = useState("")

  const autoSubmitRef = useRef(false)
  const currentTimeRef = useRef(currentTime)

  useEffect(() => {
    currentTimeRef.current = currentTime
  }, [currentTime])

  const currentQuestion = questions[currentIndex]
  const timerColor = remainingSeconds < 60 ? "red" : remainingSeconds <= 300 ? "orange" : "green"
  const answeredCount = Object.values(answers).filter((answer) => String(answer).trim().length > 0).length

  const formatTime = (seconds: number): string => {
    const safeSeconds = Math.max(0, Math.floor(seconds))
    const minutes = Math.floor(safeSeconds / 60).toString().padStart(2, "0")
    const secs = (safeSeconds % 60).toString().padStart(2, "0")
    return `${minutes}:${secs}`
  }

  const handleLogout = () => {
    logout()
    navigate("/login", { replace: true })
  }

  const clearExamSelectionDetails = () => {
    setExamTitle("")
    setExamDuration(0)
    setExamStartTimeStr("")
    setExamEndTime("")
    setMaxStudents(0)
    setStudentsCount(0)
    setTotalMarks(0)
  }

  const isExamJoinable =
    Boolean(examStartTime) &&
    Boolean(examEndTime) &&
    currentTime >= new Date(examStartTime).getTime() &&
    currentTime <= new Date(examEndTime).getTime()

  const handleSubmitExam = useCallback(async () => {
    if (autoSubmitRef.current) return
    autoSubmitRef.current = true
    setLoading(true)

    try {
      await client.post("/api/timer/submit", { exam_id: examId })
    } catch {
      // ignore submit collisions such as already-submitted
    }

    try {
      await client.post(`/api/behavioral/analyze?exam_id=${examId}`)
    } catch {
      // best effort
    }

    setStep("SUBMITTED")
    setLoading(false)
  }, [examId])

  const handleSelectAnswer = async (answer: string) => {
    if (!currentQuestion) return

    const qId = currentQuestion.question_id
    const previousAnswer = answers[qId]
    const startAt = questionStartTimes[qId] || currentTime
    const timeTaken = Math.max(0, (currentTime - startAt) / 1000)

    setAnswers((prev) => ({ ...prev, [qId]: answer }))
    setSavingAnswer(true)

    try {
      await client.post("/api/questions/answer/save", {
        exam_id: examId,
        question_id: qId,
        answer,
        time_taken_seconds: timeTaken,
      })

      client.post("/api/behavioral/event", {
        exam_id: examId,
        question_id: qId,
        answer_time_seconds: timeTaken,
        submission_time_seconds: Math.max(0, (currentTime - examTimerStartTime) / 1000),
        edit_count: previousAnswer ? 1 : 0,
        answer,
      }).catch(() => {})
    } catch {
      // silent by design
    } finally {
      setSavingAnswer(false)
    }
  }

  const handleTextAnswer = (value: string) => {
    if (!currentQuestion) return

    const qId = currentQuestion.question_id
    if (currentQuestion.word_limit > 0) {
      const words = value.trim().split(/\s+/).filter(Boolean)
      if (words.length > currentQuestion.word_limit) return
    }
    setAnswers((prev) => ({ ...prev, [qId]: value }))
  }

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      const nextQ = questions[currentIndex + 1]
      setCurrentIndex(currentIndex + 1)
      if (nextQ && !questionStartTimes[nextQ.question_id]) {
        setQuestionStartTimes((prev) => ({ ...prev, [nextQ.question_id]: currentTime }))
      }
    }
  }

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleSkip = () => {
    if (questions.length === 0) return

    for (let offset = 1; offset <= questions.length; offset += 1) {
      const idx = (currentIndex + offset) % questions.length
      const question = questions[idx]
      if (!String(answers[question.question_id] || "").trim()) {
        setCurrentIndex(idx)
        if (!questionStartTimes[question.question_id]) {
            setQuestionStartTimes((prev) => ({ ...prev, [question.question_id]: currentTime }))
        }
        return
      }
    }

    handleNext()
  }

  const handleEnroll = async () => {
    if (!examId) return

    setLoading(true)
    setError("")

    try {
      const response = await client.post<EnrollExamResponse>("/api/questions/exams/enroll", {
        exam_id: examId,
      })

      if (response.data.data.already_enrolled) {
        setResumeMessage("Resuming your exam session...")
      } else {
        setResumeMessage("")
      }

      setStep("EXAM_WAITING")
    } catch (enrollError) {
      setError(getErrorMessage(enrollError))
    } finally {
      setLoading(false)
    }
  }

  useExamMonitoring({ examId, active: step === "IN_PROGRESS" })

  useEffect(() => {
    let cancelled = false

    const registerDevice = async () => {
      setLoading(true)
      setError("")

      try {
        await client.post("/api/device/register", {
          ...getDeviceSignals(),
          device_fingerprint: deviceFingerprint,
        })

        if (!cancelled) {
          setStep("EXAM_SELECTION")
        }
      } catch {
        if (!cancelled) {
          setError("Device registration failed")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void registerDevice()

    return () => {
      cancelled = true
    }
  }, [deviceFingerprint])

  useEffect(() => {
    if (step !== "EXAM_WAITING" || !examId) return

    let cancelled = false

    const checkApproval = async () => {
      try {
        const response = await client.get<ExamStateResponse>(`/api/auth/exam/state/${examId}`)
        if (cancelled) return

        const nextState = response.data.data.state
        setExamState(nextState)
        if (nextState === "TEACHER_APPROVED") {
          setStep("ACTIVATION")
        } else if (nextState === "IN_PROGRESS") {
          setResumeMessage("Resuming your exam session...")
          setStep("RANDOMIZATION")
        }
      } catch (waitingError) {
        if (!cancelled) {
          setError(getErrorMessage(waitingError))
        }
      }
    }

    void checkApproval()
    const intervalId = window.setInterval(() => {
      void checkApproval()
    }, 5000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [examId, step])

  useEffect(() => {
    if (step !== "RANDOMIZATION" || !examId) return

    let cancelled = false

    const prepareExam = async () => {
      setLoading(true)
      setError("")

      try {
        await client.post("/api/randomization/generate", { exam_id: examId })

        const timerResponse = await client.post<TimerStartResponse>("/api/timer/start", { exam_id: examId })
        if (cancelled) return

        setRemainingSeconds(timerResponse.data.data.remaining_seconds ?? 0)
        setExamTimerStartTime(currentTimeRef.current)

        const questionsResponse = await client.get<AllQuestionsResponse>(`/api/questions/exam/${examId}/all`)
        if (cancelled) return

        const allQuestions = questionsResponse.data.data.questions || []
        setQuestions(allQuestions)
        setTotalMarks(questionsResponse.data.data.total_marks || 0)

        const answersResponse = await client.get<AnswersListResponse>("/api/questions/answer/list", {
          params: { exam_id: examId },
        })
        if (cancelled) return

        const loadedAnswers = answersResponse.data.data.answers || {}
        setAnswers(loadedAnswers)
        setCurrentIndex(0)

        if (allQuestions.length > 0) {
          setQuestionStartTimes({ [allQuestions[0].question_id]: currentTimeRef.current })
        } else {
          setQuestionStartTimes({})
        }

        if (timerResponse.data.data.resumed) {
          setResumeMessage("Resuming your exam...")
          window.setTimeout(() => {
            if (!cancelled) {
              setStep("IN_PROGRESS")
            }
          }, 900)
        } else {
          setResumeMessage("")
          setStep("IN_PROGRESS")
        }
      } catch (randomizationError) {
        if (!cancelled) {
          setError(getErrorMessage(randomizationError))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void prepareExam()

    return () => {
      cancelled = true
    }
  }, [examId, step])

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)

    return () => {
      window.clearInterval(timerId)
    }
  }, [])

  useEffect(() => {
    if (step !== "IN_PROGRESS") return

    const timerId = window.setInterval(() => {
      setRemainingSeconds((current) => Math.max(0, current - 1))
    }, 1000)

    return () => {
      window.clearInterval(timerId)
    }
  }, [step])

  useEffect(() => {
    if (step !== "IN_PROGRESS" || remainingSeconds > 0) return

    if (!autoSubmitRef.current) {
      autoSubmitRef.current = true
      void handleSubmitExam()
    }
  }, [remainingSeconds, step, handleSubmitExam])

  useEffect(() => {
    const qId = currentQuestion?.question_id
    if (!qId || currentQuestion?.question_type !== "text") return

    const answer = answers[qId]
    if (!answer) return

    const timer = window.setTimeout(async () => {
      const now = currentTimeRef.current
      const startAt = questionStartTimes[qId] || now
      const timeTaken = Math.max(0, (now - startAt) / 1000)

      try {
        await client.post("/api/questions/answer/save", {
          exam_id: examId,
          question_id: qId,
          answer,
          time_taken_seconds: timeTaken,
        })
      } catch {
        // silent by design
      }
    }, 1000)

    return () => {
      window.clearTimeout(timer)
    }
  }, [answers, currentQuestion, examId, questionStartTimes])

  const handleExamSelectionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError("")
    setResumeMessage("")
    clearExamSelectionDetails()

    try {
      const nextExamId = examIdInput.trim()
      const response = await client.get<PublicExamResponse>(`/api/questions/exams/public/${nextExamId}`)
      const exam = response.data.data

      setExamId(nextExamId)
      setExamTitle(exam.title)
      setExamDuration(exam.duration_minutes)
      setExamStartTimeStr(exam.start_time)
      setExamEndTime(exam.end_time)
      setMaxStudents(exam.max_students)
      setStudentsCount(exam.students_count)
      setTotalMarks(exam.total_marks || 0)

      if (new Date(exam.start_time).getTime() > currentTime) {
        setError(`Exam starts at ${formatLocalDateTime(exam.start_time)}. Please come back then.`)
      }
    } catch (selectionError) {
      setError(getErrorMessage(selectionError))
    } finally {
      setLoading(false)
    }
  }

  const handleActivationSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError("")

    try {
      await client.post("/api/activation/validate", {
        exam_id: examId,
        code: activationCode,
      })
      setStep("RANDOMIZATION")
    } catch (activationError) {
      setError(getErrorMessage(activationError))
    } finally {
      setLoading(false)
    }
  }

  if (step === "DEVICE_REGISTRATION") {
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 1 of 7</div>
            <h1 className="exam-stage-title">Verifying your device</h1>
          </div>
          <p className="exam-stage-body">
            Hold on while we register this browser. No action required.
          </p>
          {error ? <div className="alert alert-error">{error}</div> : null}
          <div className="exam-stage-cta">
            <span className="badge badge-accent"><span className="spinner" style={{ width: 10, height: 10 }} /> Registering</span>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "EXAM_SELECTION") {
    const canJoinExam = isExamJoinable
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 2 of 7</div>
            <h1 className="exam-stage-title">Select your exam</h1>
          </div>
          <p className="exam-stage-body">
            Enter the exam ID provided by your teacher.
          </p>

          {error ? <div className="alert alert-warning">{error}</div> : null}

          <form onSubmit={handleExamSelectionSubmit} className="card">
            <label className="field">
              <span className="label">Exam ID</span>
              <input
                type="text"
                className="input mono"
                value={examIdInput}
                onChange={(event) => setExamIdInput(event.target.value)}
                placeholder="Enter exam ID"
                required
              />
            </label>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" aria-label="Loading" /> : "Continue"}
            </button>
          </form>

          {examTitle ? (
            <div className="card" style={{ display: "grid", gap: 14 }}>
              <div>
                <div className="eyebrow">Exam found</div>
                <h2 style={{ marginTop: 4 }}>{examTitle}</h2>
              </div>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-eyebrow">Duration</div>
                  <div className="stat-value">{examDuration}<span className="stat-suffix">min</span></div>
                </div>
                <div className="stat-card">
                  <div className="stat-eyebrow">Enrolled</div>
                  <div className="stat-value">{studentsCount}<span className="stat-suffix">/{maxStudents}</span></div>
                </div>
                <div className="stat-card">
                  <div className="stat-eyebrow">Opens</div>
                  <div className="stat-value mono" style={{ fontSize: "0.875rem", lineHeight: 1.3 }}>
                    {formatLocalDateTime(examStartTime)}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-eyebrow">Closes</div>
                  <div className="stat-value mono" style={{ fontSize: "0.875rem", lineHeight: 1.3 }}>
                    {formatLocalDateTime(examEndTime)}
                  </div>
                </div>
              </div>
              {new Date(examStartTime).getTime() > currentTime ? (
                <div className="alert alert-warning">
                  This exam opens at {formatLocalDateTime(examStartTime)}.
                </div>
              ) : null}
              {canJoinExam ? (
                <button type="button" className="btn btn-primary" onClick={() => void handleEnroll()} disabled={loading}>
                  {loading ? <span className="spinner" aria-label="Loading" /> : "Enroll"}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </StudentChrome>
    )
  }

  if (step === "EXAM_WAITING") {
    const countdownSeconds = examState === "TEACHER_APPROVED" ? 0 : getRemainingSeconds(examStartTime, currentTime)
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 3 of 7</div>
            <h1 className="exam-stage-title">Waiting room</h1>
          </div>
          <p className="exam-stage-body">
            You&apos;re enrolled in <b>{examTitle || "this exam"}</b>. We&apos;ll continue automatically once it opens.
          </p>

          <div className="card" style={{ display: "grid", gap: 12 }}>
            <div>
              <span className="eyebrow">Status</span>
              <h3 style={{ marginTop: 4 }}>{examState || "Checking…"}</h3>
            </div>
            {countdownSeconds > 0 && examState !== "TEACHER_APPROVED" ? (
              <div>
                <span className="eyebrow">Opens in</span>
                <div className="timer-value green" style={{ marginTop: 4 }}>{formatTime(countdownSeconds)}</div>
              </div>
            ) : null}
          </div>

          {resumeMessage ? <div className="alert alert-success">{resumeMessage}</div> : null}
          {error ? <div className="alert alert-error">{error}</div> : null}
        </div>
      </StudentChrome>
    )
  }

  if (step === "ACTIVATION") {
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 4 of 7</div>
            <h1 className="exam-stage-title">Enter activation code</h1>
          </div>
          <p className="exam-stage-body">
            Enter the activation code provided by your teacher.
          </p>

          {error ? <div className="alert alert-error">{error}</div> : null}

          <form onSubmit={handleActivationSubmit} className="card">
            <label className="field">
              <span className="label">Activation code</span>
              <input
                type="text"
                className="input mono"
                value={activationCode}
                onChange={(event) => setActivationCode(event.target.value)}
                placeholder="Enter code"
                required
                autoFocus
                style={{ fontSize: "1.125rem", letterSpacing: "0.08em", textAlign: "center" }}
              />
            </label>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? <span className="spinner" aria-label="Loading" /> : "Continue"}
            </button>
          </form>
        </div>
      </StudentChrome>
    )
  }

  if (step === "RANDOMIZATION") {
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 5 of 7</div>
            <h1 className="exam-stage-title">Preparing exam</h1>
          </div>
          <p className="exam-stage-body">
            Almost ready.
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="spinner" />
            <span className="muted">Loading questions…</span>
          </div>
          {resumeMessage ? <div className="alert alert-success">{resumeMessage}</div> : null}
        </div>
      </StudentChrome>
    )
  }

  if (step === "SUBMITTED") {
    return (
      <StudentChrome user={user} currentStep={step} onLogout={handleLogout}>
        <div className="exam-stage">
          <div>
            <div className="exam-stage-eyebrow">Step 7 of 7</div>
            <h1 className="exam-stage-title">Submitted</h1>
          </div>
          <p className="exam-stage-body">
            Your responses have been recorded. You may close this window.
          </p>
          <div className="exam-stage-cta">
            <button type="button" className="btn btn-ghost" onClick={handleLogout}>
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (!currentQuestion) {
    return (
      <StudentChrome user={user} currentStep="IN_PROGRESS" onLogout={handleLogout} showStepIndicator={false}>
        <div className="exam-stage">
          {error ? <div className="alert alert-error">{error}</div> : null}
          <div style={{ display: "grid", placeItems: "center", padding: "64px 0" }}>
            <span className="spinner" />
          </div>
        </div>
      </StudentChrome>
    )
  }

  return (
    <div className="exam-shell">
      <header className="exam-timer-bar">
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span className="topbar-brand">
            <span className="topbar-brand-mark"><ShieldCheck size={12} /></span>
            Secure Exam
          </span>
          <span className="muted">{user?.username || "—"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ textAlign: "right" }}>
            <div className="timer-meta">Time remaining</div>
            <div className={`timer-value ${timerColor}`}>{formatTime(remainingSeconds)}</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowMap(true)}>
            <MapIcon size={14} /> Map
          </button>
        </div>
      </header>

      <div className="in-progress-shell">
        <nav className="question-rail">
          <div className="question-rail-title">Paper</div>
          {questions.map((q, i) => {
            const answered = String(answers[q.question_id] || "").trim().length > 0
            return (
              <button
                key={q.question_id}
                type="button"
                className={`question-pill ${i === currentIndex ? "active" : ""} ${answered ? "answered" : ""}`}
                onClick={() => {
                  setCurrentIndex(i)
                  if (!questionStartTimes[q.question_id]) {
                    setQuestionStartTimes((prev) => ({ ...prev, [q.question_id]: currentTime }))
                  }
                }}
              >
                <span>
                  <span className="num">{String(i + 1).padStart(2, "0")}</span>
                  Question {i + 1}
                </span>
                <span className="dot" />
              </button>
            )
          })}

          <div className="hairline" style={{ margin: "20px 0 12px" }} />
          <div style={{ padding: "0 4px", fontSize: "0.75rem", color: "var(--ink-3)", display: "grid", gap: 4 }}>
            <span><span className="num" style={{ color: "var(--ink)" }}>{answeredCount}</span> of {questions.length} answered</span>
            <span>{totalMarks} marks total</span>
            {savingAnswer ? <span className="serif-italic">Saving…</span> : null}
          </div>
        </nav>

        <main className="answer-pane">
          {error ? <div className="alert alert-error">{error}</div> : null}

          <div className="question-prompt-eyebrow">
            Question {currentIndex + 1} of {questions.length} · {currentQuestion.marks} mark{currentQuestion.marks > 1 ? "s" : ""}
          </div>
          <h2 className="question-prompt">{currentQuestion.text}</h2>

          {currentQuestion.question_type === "mcq" ? (
            <div>
              {currentQuestion.options.map((opt, i) => (
                <button
                  key={`${currentQuestion.question_id}-${i}`}
                  className={`option-btn ${answers[currentQuestion.question_id] === opt ? "selected" : ""}`}
                  onClick={() => void handleSelectAnswer(opt)}
                >
                  <span className="option-mark">{String.fromCharCode(65 + i)}</span>
                  <span>{opt}</span>
                </button>
              ))}
            </div>
          ) : null}

          {currentQuestion.question_type === "text" ? (
            <div className="field">
              <textarea
                className="textarea"
                rows={6}
                placeholder={
                  currentQuestion.word_limit > 0
                    ? `Up to ${currentQuestion.word_limit} words…`
                    : "Compose your answer…"
                }
                value={answers[currentQuestion.question_id] || ""}
                onChange={(event) => handleTextAnswer(event.target.value)}
              />
              {currentQuestion.word_limit > 0 ? (
                <span className="muted" style={{ textAlign: "right" }}>
                  <span className="num">
                    {(answers[currentQuestion.question_id] || "").trim().split(/\s+/).filter(Boolean).length}
                  </span>
                  &nbsp;/ {currentQuestion.word_limit} words
                </span>
              ) : null}
            </div>
          ) : null}

          <div className="answer-actions">
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-ghost" disabled={currentIndex === 0} onClick={handlePrevious}>
                &larr; Previous
              </button>
              <button className="btn btn-ghost" onClick={handleSkip}>
                Skip
              </button>
              <button className="btn btn-primary" disabled={currentIndex === questions.length - 1} onClick={handleNext}>
                Next &rarr;
              </button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              {savingAnswer ? <span className="answer-saved">saving…</span> : null}
              <button className="btn btn-danger" onClick={() => setShowSubmitConfirm(true)}>
                <Send size={14} /> Submit final answers
              </button>
            </div>
          </div>
        </main>
      </div>

      {showMap ? (
        <div
          style={{
            position: "fixed", inset: 0,
            background: "rgba(11, 12, 10, 0.55)",
            backdropFilter: "blur(4px)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
          }}
          onClick={() => setShowMap(false)}
        >
          <div className="card" style={{ width: "min(540px,92vw)", maxHeight: "80vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
              <div>
                <div className="eyebrow">Navigate</div>
                <h2 style={{ marginTop: 4 }}>Question map</h2>
              </div>
              <button className="btn-icon" onClick={() => setShowMap(false)} aria-label="Close map">✕</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(56px, 1fr))", gap: 6 }}>
              {questions.map((q, i) => {
                const answered = String(answers[q.question_id] || "").trim().length > 0
                return (
                  <button
                    key={q.question_id}
                    onClick={() => {
                      setCurrentIndex(i)
                      setShowMap(false)
                      if (!questionStartTimes[q.question_id]) {
                        setQuestionStartTimes((prev) => ({ ...prev, [q.question_id]: currentTime }))
                      }
                    }}
                    style={{
                      padding: "12px 0",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid",
                      borderColor: answered ? "var(--accent)" : "var(--rule)",
                      background: i === currentIndex ? "var(--ink)" : answered ? "var(--accent-tint)" : "var(--vellum)",
                      color: i === currentIndex ? "var(--paper)" : answered ? "var(--accent)" : "var(--ink-2)",
                      cursor: "pointer",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.8125rem",
                      fontWeight: 500,
                    }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </button>
                )
              })}
            </div>
            <div className="rule-ornate">legend</div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--ink-3)" }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--accent-tint)", border: "1px solid var(--accent)", display: "inline-block" }} />
                Answered ({answeredCount})
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--ink-3)" }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--vellum)", border: "1px solid var(--rule)", display: "inline-block" }} />
                Unanswered ({questions.length - answeredCount})
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "var(--ink-3)" }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--ink)", display: "inline-block" }} />
                Current
              </span>
            </div>
          </div>
        </div>
      ) : null}

      {showSubmitConfirm ? (
        <div
          style={{
            position: "fixed", inset: 0,
            background: "rgba(11, 12, 10, 0.55)",
            backdropFilter: "blur(4px)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
          }}
          onClick={() => setShowSubmitConfirm(false)}
        >
          <div className="card" style={{ width: "min(440px,92vw)" }} onClick={(e) => e.stopPropagation()}>
            <div className="eyebrow">Final answer</div>
            <h2 style={{ marginTop: 4 }}>Hand it in?</h2>
            <p style={{ marginTop: 12, marginBottom: 20 }}>
              You&apos;ve answered <b className="num">{answeredCount}</b> of <b className="num">{questions.length}</b>.
              {questions.length - answeredCount > 0
                ? ` ${questions.length - answeredCount} question${questions.length - answeredCount > 1 ? "s remain" : " remains"} blank.`
                : " Every question has an answer."}
              {" "}This is irreversible.
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-ghost btn-full" onClick={() => setShowSubmitConfirm(false)}>
                Not yet
              </button>
              <button
                className="btn btn-danger btn-full"
                onClick={() => {
                  setShowSubmitConfirm(false)
                  void handleSubmitExam()
                }}
              >
                <Send size={14} /> Submit
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
