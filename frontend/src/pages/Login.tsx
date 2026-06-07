import { useState, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { ShieldCheck } from "lucide-react"
import { useAuth } from "../hooks/useAuth"
import { getErrorMessage } from "../api/errors"

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const successMessage = (location.state as { message?: string } | null)?.message ?? ""

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError("")
    setLoading(true)
    try {
      const user = await login(username.trim(), password)
      navigate(user.role === "student" ? "/exam" : "/dashboard", { replace: true })
    } catch (loginError: unknown) {
      setError(getErrorMessage(loginError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-form">
        <div className="auth-logo">
          <span className="auth-logo-mark">
            <ShieldCheck size={14} />
          </span>
          Secure Exam
        </div>

        <h1>Sign in</h1>
        <p className="auth-sub">Enter your credentials to continue.</p>

        {successMessage ? <div className="alert alert-success">{successMessage}</div> : null}
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
              autoComplete="current-password"
            />
          </label>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? <span className="spinner" aria-label="Loading" /> : "Sign in"}
          </button>
        </form>

        <div className="auth-meta-row">
          <span>Don&apos;t have an account?</span>
          <Link to="/register">Create one</Link>
        </div>
      </div>
    </div>
  )
}
