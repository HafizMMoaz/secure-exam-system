import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import client from "../api/client"

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return responseMessage
    }
  }

  return "Registration failed"
}

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<"student" | "teacher">("student")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError("")
    setSuccess("")
    setLoading(true)

    try {
      await client.post("/api/auth/register", {
        username: username.trim(),
        password,
        role,
      })

      setSuccess("Registration successful. Please log in.")
      navigate("/login", { replace: true, state: { message: "Registration successful. Please log in." } })
    } catch (registerError: unknown) {
      setError(getErrorMessage(registerError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-box">
        <h1>Create account</h1>
        <p className="muted">Secure Online Examination System</p>

        {success ? <div className="alert alert-success">{success}</div> : null}
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
              placeholder="Choose a username"
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
              placeholder="Create a password"
            />
          </label>

          <label className="field">
            <span className="label">Role</span>
            <select className="select" value={role} onChange={(event) => setRole(event.target.value as "student" | "teacher")}>
              <option value="student">student</option>
              <option value="teacher">teacher</option>
            </select>
          </label>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
            {loading ? <span className="spinner" aria-label="Loading" /> : "Register"}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <a href="/login">Back to login</a>
        </p>
      </div>
    </div>
  )
}
