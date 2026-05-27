import { useState, type FormEvent, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { ShieldCheck } from "lucide-react"
import client from "../api/client"
import { getErrorMessage } from "../api/errors"

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<"student" | "teacher">("student")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError("")
    setLoading(true)
    try {
      await client.post("/api/auth/register", {
        username: username.trim(),
        password,
        role,
      })
      navigate("/login", {
        replace: true,
        state: { message: "Account created. Sign in to continue." },
      })
    } catch (registerError: unknown) {
      setError(getErrorMessage(registerError))
    } finally {
      setLoading(false)
    }
  }

  const pwdChecks = useMemo(() => {
    const len = password.length >= 8
    const upper = /[A-Z]/.test(password)
    const lower = /[a-z]/.test(password)
    const digit = /[0-9]/.test(password)
    const special = /[^A-Za-z0-9]/.test(password)
    return { len, upper, lower, digit, special, all: len && upper && lower && digit && special }
  }, [password])

  return (
    <div className="auth-shell">
      <div className="auth-form">
        <div className="auth-logo">
          <span className="auth-logo-mark">
            <ShieldCheck size={14} />
          </span>
          Secure Exam
        </div>

        <h1>Create account</h1>
        <p className="auth-sub">Sign up to get started.</p>

        {error ? <div className="alert alert-error">{error}</div> : null}

        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="label">Username</span>
            <input
              type="text"
              className="input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </label>

          <label className="field">
            <span className="label">Password</span>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="new-password"
            />

            <ul style={{ marginTop: 8, marginBottom: 0, listStyle: "none" }}>
              <li style={{ color: pwdChecks.len ? "#16a34a" : "#6b7280" }}>
                {pwdChecks.len ? "✅" : "⚪"} At least 8 characters
              </li>
              <li style={{ color: pwdChecks.upper ? "#16a34a" : "#6b7280" }}>
                {pwdChecks.upper ? "✅" : "⚪"} Contains an uppercase letter
              </li>
              <li style={{ color: pwdChecks.lower ? "#16a34a" : "#6b7280" }}>
                {pwdChecks.lower ? "✅" : "⚪"} Contains a lowercase letter
              </li>
              <li style={{ color: pwdChecks.digit ? "#16a34a" : "#6b7280" }}>
                {pwdChecks.digit ? "✅" : "⚪"} Contains a number
              </li>
              <li style={{ color: pwdChecks.special ? "#16a34a" : "#6b7280" }}>
                {pwdChecks.special ? "✅" : "⚪"} Contains a special character
              </li>
            </ul>
          </label>

          <div className="field">
            <span className="label">I am a</span>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
              <button
                type="button"
                className={`btn ${role === "student" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setRole("student")}
              >
                Student
              </button>
              <button
                type="button"
                className={`btn ${role === "teacher" ? "btn-primary" : "btn-ghost"}`}
                onClick={() => setRole("teacher")}
              >
                Teacher
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading || !pwdChecks.all}>
            {loading ? <span className="spinner" aria-label="Loading" /> : "Create account"}
          </button>
        </form>

        <div className="auth-meta-row">
          <span>Already have an account?</span>
          <a href="/login">Sign in</a>
        </div>
      </div>
    </div>
  )
}
