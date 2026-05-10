import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"
import client from "../../api/client"
import { useAuth } from "../../hooks/useAuth"
import { getDeviceSignals, useDeviceFingerprint } from "../../hooks/useDeviceFingerprint"
import { useExamMonitoring } from "../../hooks/useExamMonitoring"
import type { ApiResponse, ExamStep, Question } from "../../types"

interface NextQuestionPayload {
  question: Question | null
  exam_complete: boolean
}

interface ExamStatePayload {
  state: string
}

interface TimerStartPayload {
  remaining_seconds: number
}

type NextQuestionResponse = ApiResponse<NextQuestionPayload>
type ExamStateResponse = ApiResponse<ExamStatePayload>
type TimerStartResponse = ApiResponse<TimerStartPayload>

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage
    }
  }

  return "Unknown error"
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
          <span className="">{user?.username || "Unknown"}</span>
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
  const [activationCode, setActivationCode] = useState("")
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [selectedAnswer, setSelectedAnswer] = useState("")
  const [questionStartTime, setQuestionStartTime] = useState<number>(0)
  const [examStartTime, setExamStartTime] = useState<number>(0)
  const [submissionTimes, setSubmissionTimes] = useState<number[]>([])
  const [editCount, setEditCount] = useState(0)
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [examComplete, setExamComplete] = useState(false)
  const [examState, setExamState] = useState("")

  const autoSubmitRef = useRef(false)
  const questionLoadRef = useRef(false)

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

  const handleSubmitExam = useCallback(async () => {
    if (autoSubmitRef.current) return
    autoSubmitRef.current = true
    setLoading(true)

    try {
      await client.post("/api/timer/submit", { exam_id: examId })
    } catch (submitError) {
      const message = getErrorMessage(submitError)
      if (!message.toLowerCase().includes("already submitted")) {
        setError(message)
        autoSubmitRef.current = false
        setLoading(false)
        return
      }
    }

    try {
      await client.post("/api/behavioral/analyze", undefined, {
        params: { exam_id: examId },
      })
    } catch {
      // Best effort: the exam is still marked submitted even if analysis fails here.
    }

    setExamComplete(true)
    setStep("SUBMITTED")
    setCurrentQuestion(null)
    setSelectedAnswer("")
    setLoading(false)
  }, [examId])

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

        setExamState(response.data.data.state)
        if (response.data.data.state === "TEACHER_APPROVED") {
          setStep("ACTIVATION")
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
        setExamStartTime(Date.now())
        setStep("IN_PROGRESS")
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
    if (step !== "IN_PROGRESS" || !examId) return

    let cancelled = false

    const loadFirstQuestion = async () => {
      if (questionLoadRef.current) return
      questionLoadRef.current = true
      setLoading(true)
      setError("")

      try {
        const response = await client.get<NextQuestionResponse>("/api/questions/next", {
          params: { exam_id: examId },
        })

        if (cancelled) return

        if (response.data.data.exam_complete || !response.data.data.question) {
          await handleSubmitExam()
          return
        }

        setCurrentQuestion(response.data.data.question)
        setSelectedAnswer("")
        setEditCount(0)
        setQuestionStartTime(Date.now())
      } catch (questionError) {
        if (!cancelled) {
          setError(getErrorMessage(questionError))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
          questionLoadRef.current = false
        }
      }
    }

    void loadFirstQuestion()

    return () => {
      cancelled = true
      questionLoadRef.current = false
    }
  }, [examId, handleSubmitExam, step])

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
    if (step !== "IN_PROGRESS" || remainingSeconds > 0 || autoSubmitRef.current) return

    void handleSubmitExam()
  }, [handleSubmitExam, remainingSeconds, step])

  const handleExamSelectionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError("")

    try {
      const response = await client.get<ExamStateResponse>(`/api/auth/exam/state/${examIdInput.trim()}`)
      setExamState(response.data.data.state)
      setExamId(examIdInput.trim())
      setStep("EXAM_WAITING")
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

  const handleSelectAnswer = (option: string) => {
    setSelectedAnswer((current) => {
      if (current !== option) {
        setEditCount((previous) => previous + 1)
      }
      return option
    })
  }

  const handleSubmitAnswer = async () => {
    if (!currentQuestion || !selectedAnswer || loading) return

    setLoading(true)
    setError("")

    const answerTimeSeconds = (Date.now() - questionStartTime) / 1000
    const submissionTimeSeconds = (Date.now() - examStartTime) / 1000

    try {
      await client.post("/api/behavioral/event", {
        exam_id: examId,
        question_id: currentQuestion.question_id,
        answer_time_seconds: answerTimeSeconds,
        submission_time_seconds: submissionTimeSeconds,
        edit_count: editCount,
        answer: selectedAnswer,
      })

      await client.post("/api/activity/event", {
        exam_id: examId,
        event_type: "answer_selected",
        details: { question_id: currentQuestion.question_id },
        timestamp: new Date().toISOString(),
      })

      setSubmissionTimes((previous) => [...previous, submissionTimeSeconds])
      setEditCount(0)

      const response = await client.get<NextQuestionResponse>("/api/questions/next", {
        params: { exam_id: examId },
      })

      if (response.data.data.exam_complete || !response.data.data.question) {
        await handleSubmitExam()
        return
      }

      setCurrentQuestion(response.data.data.question)
      setSelectedAnswer("")
      setQuestionStartTime(Date.now())
    } catch (answerError) {
      setError(getErrorMessage(answerError))
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
    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(560px, 100%)" }}>
            <h1>Join your exam</h1>
            <p className="muted">Enter the exam identifier provided by your teacher to continue.</p>

            {error ? <div className="alert alert-error">{error}</div> : null}

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
          </div>
        </div>
      </StudentChrome>
    )
  }

  if (step === "EXAM_WAITING") {
    return (
      <StudentChrome user={user} onLogout={handleLogout}>
        <div className="auth-shell">
          <div className="auth-box" style={{ width: "min(620px, 100%)" }}>
            <div className="card">
              <span className="label">Waiting Room</span>
              <h2 style={{ marginTop: 16 }}>Waiting for teacher approval...</h2>
              <p style={{ marginBottom: 14 }}>
                Exam ID: <strong>{examId}</strong>
              </p>
              <p>
                Current state: <strong>{examState || "Checking..."}</strong>
              </p>
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
              <h1 style={{ marginTop: 16 }}>
                {examComplete ? "Exam Submitted Successfully" : "Submitting Exam..."}
              </h1>
              <p style={{ marginBottom: 24 }}>
                Your responses have been recorded and are under review.
              </p>
              <button type="button" className="btn btn-ghost" onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      </StudentChrome>
    )
  }

  return (
    <div>
      <header className="navbar">
        <div className="navbar-brand">SecureExam</div>
        <div className="navbar-right">
          <span className="badge badge-zinc">{user?.username || "Unknown"}</span>
          <span className="badge badge-zinc">{user?.role || "student"}</span>
          <button type="button" className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="page">
        <section className="card" style={{ display: "grid", gap: 20 }}>
          <div>
            <span className="label">Student Workspace</span>
            <h1>Secure Exam Session</h1>
          </div>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <span className="badge badge-zinc">Username: {user?.username || "Unknown"}</span>
            <span className="badge badge-zinc">Role: {user?.role || "student"}</span>
          </div>

          <div className="timer-bar">
            <span>Exam Timer</span>
            <span className={`timer-value ${remainingSeconds < 60 ? "red" : remainingSeconds < 300 ? "orange" : "green"}`}>
              {formatTime(remainingSeconds)}
            </span>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            <p>Answer questions one by one and submit before time runs out.</p>
            {currentQuestion ? <strong>Question {submissionTimes.length + 1} of ?</strong> : null}
          </div>

          {error ? <div className="alert alert-error">{error}</div> : null}

          {loading && !currentQuestion ? (
            <div className="card" style={{ minHeight: 220, display: "grid", placeItems: "center" }}>
              <span className="spinner" aria-label="Loading" />
            </div>
          ) : null}

          {currentQuestion ? (
            <div style={{ display: "grid", gap: 18 }}>
              <div>
                <div className="label">Question</div>
                <h2 style={{ marginTop: 14 }}>{currentQuestion.text}</h2>
              </div>

              <div style={{ display: "grid", gap: 12 }}>
                {currentQuestion.options.map((option) => {
                  const isSelected = selectedAnswer === option
                  return (
                    <button
                      key={option}
                      type="button"
                      onClick={() => handleSelectAnswer(option)}
                      className={`option-btn ${isSelected ? "selected" : ""}`}
                    >
                      {option}
                    </button>
                  )
                })}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                <span className="progress-text">Questions answered: {submissionTimes.length}</span>
                <button type="button" className="btn btn-primary" onClick={() => void handleSubmitAnswer()} disabled={loading || !selectedAnswer}>
                  {loading ? <span className="spinner" aria-label="Loading" /> : "Submit Answer"}
                </button>
              </div>
            </div>
          ) : (
            <div className="card" style={{ minHeight: 220, display: "grid", placeItems: "center" }}>
              <span className="spinner" aria-label="Loading" />
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
