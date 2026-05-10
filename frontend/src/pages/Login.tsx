import { useState, type FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import axios from "axios"
import { useAuth } from "../hooks/useAuth"

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage
    }
  }

  return "Invalid username or password"
}

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
      <div className="auth-box">
        <h1>Sign in</h1>
        <p className="muted">Secure Online Examination System</p>

        {successMessage ? <div className="alert alert-success">{successMessage}</div> : null}
        {error ? <div className="alert alert-error">{error}</div> : null}

        <form onSubmit={handleSubmit} className="card">
          <label className="field">
            <span className="label">Username</span>
            <input
              type="text"
              className="input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoComplete="username"
              placeholder="Enter your username"
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
              placeholder="Enter your password"
            />
          </label>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? <span className="spinner" aria-label="Loading" /> : "Sign in"}
          </button>
        </form>

        <p className="auth-footer">
          New here? <a href="/register">Create an account</a>
        </p>
      </div>
    </div>
  )
}
