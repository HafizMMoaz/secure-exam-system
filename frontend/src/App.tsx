import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import { ProtectedRoute } from "./components/ProtectedRoute"
import Login from "./pages/Login"
import Register from "./pages/Register"
import ExamPage from "./pages/student/ExamPage.tsx"
import Dashboard from "./pages/teacher/Dashboard"
import "./App.css"

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="shell">
          <div className="container">
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route
                path="/exam"
                element={
                  <ProtectedRoute role="student">
                    <ExamPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute role="teacher">
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}
