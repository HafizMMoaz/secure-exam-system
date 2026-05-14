import axios from "axios"

const STATE_LABELS: Record<string, string> = {
  NOT_STARTED: "still being prepared by the teacher",
  DEVICE_VERIFIED: "still being set up",
  TEACHER_APPROVED: "ready",
  ACTIVATION_VALID: "ready to begin",
  IN_PROGRESS: "currently in progress",
  SUBMITTED: "already submitted",
  ANALYZING: "being graded",
  COMPLETED: "finished",
}

function describeState(state: string) {
  return STATE_LABELS[state] || state.replace(/_/g, " ").toLowerCase()
}

function humanize(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return "Something went wrong. Please try again."

  // "Exam is in state 'X', expected 'Y'" - most common state-machine error.
  const stateMatch = trimmed.match(/Exam is in state '([A-Z_]+)', expected '([^']+)'/)
  if (stateMatch) {
    const [, current, expected] = stateMatch
    // Pick a context-appropriate message based on what action was attempted.
    if (expected.startsWith("TEACHER_APPROVED")) {
      return `This exam isn't open for enrollment yet — it's ${describeState(current)}.`
    }
    if (expected.startsWith("ACTIVATION_VALID")) {
      return `You can't start this exam yet — it's ${describeState(current)}.`
    }
    if (expected.startsWith("IN_PROGRESS")) {
      return `This exam isn't in progress right now — it's ${describeState(current)}.`
    }
    if (expected.startsWith("SUBMITTED")) {
      return `Risk scoring isn't available yet — this exam is ${describeState(current)}.`
    }
    return `This action isn't available right now — the exam is ${describeState(current)}.`
  }

  // Bare ExamStateException fallback (no current/expected captured).
  if (/^Exam already approved/i.test(trimmed)) {
    return "This exam has already been approved."
  }
  if (/^Exam already submitted/i.test(trimmed)) {
    return "This exam has already been submitted."
  }

  // Common literal messages we can soften without changing meaning.
  const map: Array<[RegExp, string]> = [
    [/^Cannot approve exam with no questions.*/i, "Add at least one question before approving the exam."],
    [/^Exam has not started yet$/i, "This exam hasn't opened yet. Please come back at the start time."],
    [/^Exam (period has ended|has ended)$/i, "This exam has already closed."],
    [/^Exam time has expired$/i, "The exam window has expired."],
    [/^Exam (must be in TEACHER_APPROVED state)/i, "Activation codes can only be generated after the exam is approved."],
    [/^Exam is full$/i, "This exam is full and can't accept more students."],
    [/^Exam not started$/i, "You haven't started this exam yet."],
    [/^Exam not found$/i, "We couldn't find that exam. Please check the ID."],
    [/^User not found$/i, "We couldn't find an account with those details."],
    [/^Invalid (credentials|password)$/i, "That username or password didn't match."],
    [/^Invalid activation code$/i, "That activation code doesn't look right. Please re-check with your teacher."],
    [/^Activation code has expired$/i, "That activation code has expired. Ask your teacher for a new one."],
    [/^Only teachers can /i, "You don't have permission to do that."],
    [/^You are not allowed /i, "You don't have permission to do that."],
    [/^Field '([^']+)' is required$/i, "Please fill in every field before continuing."],
    [/required$/i, "Please fill in every field before continuing."],
    [/^(Database|Mongo) /i, "The server hit a snag. Please try again in a moment."],
    [/Network Error$/i, "We can't reach the server. Check your connection and try again."],
  ]

  for (const [pattern, message] of map) {
    if (pattern.test(trimmed)) {
      // For "Field 'X' is required" we want a per-field hint, but most callers
      // pass several fields at once - keep it generic and clear.
      return message
    }
  }

  // As a last resort, return the original message but stripped of leaked
  // internals like quoted state names, module prefixes, or hash fragments.
  return trimmed
    .replace(/'[A-Z_]{4,}'/g, "")
    .replace(/Module_\d+_\w+/g, "")
    .replace(/\s{2,}/g, " ")
    .trim()
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message
    if (typeof responseMessage === "string" && responseMessage.length > 0) {
      return humanize(responseMessage)
    }
    if (error.message) {
      return humanize(error.message)
    }
  }
  if (error instanceof Error && error.message) {
    return humanize(error.message)
  }
  return "Something went wrong. Please try again."
}
