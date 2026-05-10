export interface User {
  username: string
  role: "student" | "teacher"
}

export type ExamStep =
  | "DEVICE_REGISTRATION"
  | "EXAM_SELECTION"
  | "EXAM_WAITING"
  | "ACTIVATION"
  | "RANDOMIZATION"
  | "IN_PROGRESS"
  | "SUBMITTED"

export interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<User>
  logout: () => void
}

export interface ApiResponse<T = Record<string, unknown>> {
  status: "success" | "error"
  data: T
  message: string
}

export interface ErrorResponse {
  status: "error"
  error_code: number
  message: string
  timestamp: string
}

export interface Question {
  question_id: string
  text: string
  options: string[]
  marks: number
  order_index: number
}

export interface Exam {
  exam_id: string
  title: string
  description: string
  duration_minutes: number
  state: string
  created_at: string
}

export interface QuestionWithAnswer {
  question_id: string
  text: string
  options: string[]
  correct_answer: string
  marks: number
  order_index: number
}

export interface StudentUser {
  user_id: string
  username: string
  role: string
  is_active: boolean
  joined_at?: string
}

export interface RiskScore {
  student_id: string
  username: string
  score: number
  risk_level: "LOW" | "MEDIUM" | "HIGH"
  metrics: Record<string, number>
  computed_at: string
}

export interface LogEntry {
  log_id: string
  module: string
  level: string
  user_id: string
  exam_id: string
  action: string
  details: Record<string, unknown>
  timestamp: string
  integrity_hash: string
  received_at: string
}
