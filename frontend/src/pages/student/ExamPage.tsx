import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
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

function StudentChrome({
  user,
  onLogout,
  children,
}: {
  user: { username: string; role: string } | null
  onLogout: () => void
  children: React.ReactNode
}) {
  return (
    <div>
      <header className="navbar">
        <div className="navbar-brand">SecureExam</div>
        <div className="navbar-right">
          <span>{user?.username || "Unknown"}</span>
          <span className="badge badge-zinc">{user?.role || "student"}</span>
          <button type="button" className="btn btn-ghost" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>
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
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(540px, 100%)", textAlign: "center" }}>
            <div className="card" style={{ minHeight: 240 }}>
              <div>
                <div className="label">Device Registration</div>
                <h2 style={{ marginTop: 18 }}>Registering your device...</h2>
                <p>Please wait while we validate your browser fingerprint.</p>
              </div>
            </div>
            {error ? <div className="alert alert-error">{error}</div> : null}
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "EXAM_SELECTION") {
    const canJoinExam = isExamJoinable

    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(560px, 100%)" }}>
            <h1>Join your exam</h1>
            <p className="muted">Enter the exam identifier provided by your teacher to continue.</p>

            {error ? <div className="alert alert-warning">{error}</div> : null}

            <form onSubmit={handleExamSelectionSubmit} className="card">
              <label className="field">
                <span className="label">Exam ID</span>
                <input
                  type="text"
                  className="input"
                  value={examIdInput}
                  onChange={(event) => setExamIdInput(event.target.value)}
                  placeholder="Paste exam ID"
                  required
                />
              </label>

              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Continue"}
              </button>
            </form>

            {examTitle ? (
              <div className="card" style={{ display: "grid", gap: 16 }}>
                <h2>{examTitle}</h2>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-value">{examDuration}m</div>
                    <div className="stat-label">Duration</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{studentsCount}/{maxStudents}</div>
                    <div className="stat-label">Enrolled</div>
                  </div>
                </div>
                <p className="muted">Starts: {formatLocalDateTime(examStartTime)}</p>
                <p className="muted">Ends: {formatLocalDateTime(examEndTime)}</p>
                {new Date(examStartTime).getTime() > currentTime ? (
                  <div className="alert alert-warning">
                    Exam starts at {formatLocalDateTime(examStartTime)}. Please come back then.
                  </div>
                ) : null}
                {canJoinExam ? (
                  <button type="button" className="btn btn-primary btn-full" onClick={() => void handleEnroll()} disabled={loading}>
                    {loading ? <span className="spinner" aria-label="Loading" /> : "Join Exam"}
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "EXAM_WAITING") {
    const countdownSeconds = examState === "TEACHER_APPROVED" ? 0 : getRemainingSeconds(examStartTime, currentTime)

    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(620px, 100%)" }}>
            <div className="card">
              <span className="label">Waiting Room</span>
              <h2 style={{ marginTop: 16 }}>{examTitle || "Waiting for teacher approval..."}</h2>
              <p style={{ marginBottom: 14 }}>
                Exam ID: <strong>{examId}</strong>
              </p>
              <p>
                Current state: <strong>{examState || "Checking..."}</strong>
              </p>
              {countdownSeconds > 0 && examState !== "TEACHER_APPROVED" ? (
                <p className="muted">Exam opens in {formatTime(countdownSeconds)}</p>
              ) : null}
              {resumeMessage ? <div className="alert alert-success" style={{ marginTop: 16 }}>{resumeMessage}</div> : null}
              {error ? <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div> : null}
            </div>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "ACTIVATION") {
    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(560px, 100%)" }}>
            <h1>Enter your activation code</h1>
            <p className="muted">The code unlocks your exam session after teacher approval.</p>

            {error ? <div className="alert alert-error">{error}</div> : null}

            <form onSubmit={handleActivationSubmit} className="card">
              <label className="field">
                <span className="label">Activation Code</span>
                <input
                  type="text"
                  className="input"
                  value={activationCode}
                  onChange={(event) => setActivationCode(event.target.value)}
                  placeholder="Enter activation code"
                  required
                />
              </label>

              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <span className="spinner" aria-label="Loading" /> : "Activate"}
              </button>
            </form>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "RANDOMIZATION") {
    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(620px, 100%)", textAlign: "center" }}>
            <div className="card" style={{ minHeight: 260 }}>
              <div>
                <div className="label">Randomization</div>
                <h2 style={{ marginTop: 18 }}>Preparing your exam...</h2>
                <p>Shuffling questions and starting the secure timer.</p>
                {resumeMessage ? <div className="alert alert-success" style={{ marginTop: 16 }}>{resumeMessage}</div> : null}
              </div>
            </div>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "SUBMITTED") {
    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(680px, 100%)" }}>
            <div className="card">
              <span className="label">Submitted</span>
              <h1 style={{ marginTop: 16 }}>Exam Submitted</h1>
              <p style={{ marginBottom: 24 }}>Your responses have been recorded.</p>
              <button type="button" className="btn btn-ghost" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (!currentQuestion) {
    return (
      <div>
        <header className="navbar">
          <span className="navbar-brand">SecureExam</span>
          <div className="navbar-right">
            <span className="muted">{user?.username}</span>
            <span className={`timer-value ${timerColor}`}>{formatTime(remainingSeconds)}</span>
          </div>
        </header>
        <div className="page">
          {error ? <div className="alert alert-error">{error}</div> : null}
          <div className="card" style={{ minHeight: 220, display: "grid", placeItems: "center" }}>
            <span className="spinner" aria-label="Loading" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="navbar">
        <span className="navbar-brand">SecureExam</span>
        <div className="navbar-right">
          <span className="muted">{user?.username}</span>
          <span className={`timer-value ${timerColor}`}>{formatTime(remainingSeconds)}</span>
          <button className="btn btn-ghost" onClick={() => setShowMap(true)}>
            Question Map
          </button>
        </div>
      </div>

      <div className="page">
        {error ? <div className="alert alert-error">{error}</div> : null}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="muted">
            Question {currentIndex + 1} of {questions.length}
          </span>
          <span className="muted">
            {answeredCount} answered · {totalMarks} total marks
            {savingAnswer ? " · saving..." : ""}
          </span>
        </div>

        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
            <span className="badge badge-zinc">Q{currentIndex + 1}</span>
            <span className="badge badge-white">{currentQuestion.marks} mark{currentQuestion.marks > 1 ? "s" : ""}</span>
          </div>

          <h3 style={{ marginBottom: 20, fontSize: "1.05rem", color: "#f4f4f5" }}>
            {currentQuestion.text}
          </h3>

          {currentQuestion.question_type === "mcq" ? (
            <div>
              {currentQuestion.options.map((opt, i) => (
                <button
                  key={`${currentQuestion.question_id}-${i}`}
                  className={`option-btn ${answers[currentQuestion.question_id] === opt ? "selected" : ""}`}
                  onClick={() => void handleSelectAnswer(opt)}
                >
                  {String.fromCharCode(65 + i)}. {opt}
                </button>
              ))}
            </div>
          ) : null}

          {currentQuestion.question_type === "text" ? (
            <div className="field">
              <textarea
                className="input"
                rows={5}
                style={{ resize: "vertical" }}
                placeholder={
                  currentQuestion.word_limit > 0
                    ? `Answer in max ${currentQuestion.word_limit} words`
                    : "Type your answer here"
                }
                value={answers[currentQuestion.question_id] || ""}
                onChange={(event) => handleTextAnswer(event.target.value)}
              />
              {currentQuestion.word_limit > 0 ? (
                <span className="muted">
                  {(answers[currentQuestion.question_id] || "").trim().split(/\s+/).filter(Boolean).length}
                  / {currentQuestion.word_limit} words
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost" disabled={currentIndex === 0} onClick={handlePrevious}>
              ← Previous
            </button>
            <button className="btn btn-ghost" onClick={handleSkip}>
              Skip
            </button>
            <button className="btn btn-primary" disabled={currentIndex === questions.length - 1} onClick={handleNext}>
              Next →
            </button>
          </div>
          <button className="btn btn-danger" onClick={() => setShowSubmitConfirm(true)}>
            Submit Exam
          </button>
        </div>
      </div>

      {showMap ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
          }}
        >
          <div className="card" style={{ width: "min(500px,90vw)", maxHeight: "80vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>Question Map</h2>
              <button className="btn btn-ghost" onClick={() => setShowMap(false)}>✕</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
              {questions.map((q, i) => (
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
                    padding: "10px",
                    borderRadius: 8,
                    border: "1px solid",
                    borderColor: String(answers[q.question_id] || "").trim() ? "#4ade80" : "#27272a",
                    background: String(answers[q.question_id] || "").trim() ? "rgba(34,197,94,0.1)" : "#09090b",
                    color: i === currentIndex ? "#f4f4f5" : "#a1a1aa",
                    cursor: "pointer",
                    fontWeight: i === currentIndex ? 700 : 400,
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <hr className="divider" />
            <div style={{ display: "flex", gap: 16 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "#a1a1aa" }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: "rgba(34,197,94,0.3)", display: "inline-block" }} />
                Answered ({answeredCount})
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", color: "#a1a1aa" }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: "#27272a", display: "inline-block" }} />
                Unanswered ({questions.length - answeredCount})
              </span>
            </div>
          </div>
        </div>
      ) : null}

      {showSubmitConfirm ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
          }}
        >
          <div className="card" style={{ width: "min(400px,90vw)" }}>
            <h2>Submit Exam?</h2>
            <p className="muted" style={{ marginBottom: 20 }}>
              You have answered {answeredCount} of {questions.length} questions.
              {questions.length - answeredCount > 0
                ? ` ${questions.length - answeredCount} questions are unanswered.`
                : ""}
              {" "}
              This action cannot be undone.
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-ghost btn-full" onClick={() => setShowSubmitConfirm(false)}>
                Cancel
              </button>
              <button
                className="btn btn-danger btn-full"
                onClick={() => {
                  setShowSubmitConfirm(false)
                  void handleSubmitExam()
                }}
              >
                Yes, Submit
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
