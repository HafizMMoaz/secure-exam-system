import { useState, type ReactNode } from "react"
import type { ApiResponse, User } from "../types"
import client from "../api/client"
import { AuthContext } from "./AuthContextValue"

function readStoredUser(): User | null {
  const savedUser = localStorage.getItem("user")
  if (!savedUser) return null

  try {
    return JSON.parse(savedUser) as User
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredUser())
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"))
  const [loading] = useState(false)

  const login = async (username: string, password: string): Promise<User> => {
    const response = await client.post<ApiResponse<{ token: string; role: User["role"]; username: string }>>(
      "/api/auth/login",
      { username, password },
    )
    const { token: authToken, role, username: uname } = response.data.data
    const userData: User = { username: uname, role }

    localStorage.setItem("token", authToken)
    localStorage.setItem("user", JSON.stringify(userData))
    setToken(authToken)
    setUser(userData)

    void client.post("/api/session/create").catch(() => {})

    return userData
  }

  const logout = () => {
    void client.post("/api/session/invalidate").catch(() => {})
    localStorage.removeItem("token")
    localStorage.removeItem("user")
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}
