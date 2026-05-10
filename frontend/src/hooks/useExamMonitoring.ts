import { useEffect, useRef } from "react"
import client from "../api/client"

interface MonitoringOptions {
  examId: string
  active: boolean
}

export function useExamMonitoring({ examId, active }: MonitoringOptions) {
  const examIdRef = useRef(examId)
  examIdRef.current = examId

  useEffect(() => {
    if (!active || !examId) return

    const handleVisibilityChange = () => {
      const eventType = document.hidden ? "hidden" : "visible"
      client.post("/api/tab/event", {
        exam_id: examIdRef.current,
        event_type: eventType,
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    const handleBlur = () => {
      client.post("/api/tab/event", {
        exam_id: examIdRef.current,
        event_type: "blur",
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    const handleFocus = () => {
      client.post("/api/tab/event", {
        exam_id: examIdRef.current,
        event_type: "focus",
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    const handleCopy = () => {
      client.post("/api/clipboard/event", {
        exam_id: examIdRef.current,
        event_type: "copy",
        content_length: window.getSelection()?.toString().length || 0,
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    const handlePaste = (event: ClipboardEvent) => {
      const text = event.clipboardData?.getData("text") || ""
      client.post("/api/clipboard/event", {
        exam_id: examIdRef.current,
        event_type: "paste",
        content_length: text.length,
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    const handleCut = () => {
      client.post("/api/clipboard/event", {
        exam_id: examIdRef.current,
        event_type: "cut",
        content_length: window.getSelection()?.toString().length || 0,
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }

    document.addEventListener("visibilitychange", handleVisibilityChange)
    window.addEventListener("blur", handleBlur)
    window.addEventListener("focus", handleFocus)
    document.addEventListener("copy", handleCopy)
    document.addEventListener("paste", handlePaste)
    document.addEventListener("cut", handleCut)

    const heartbeat = window.setInterval(() => {
      client.post("/api/activity/heartbeat", {
        exam_id: examIdRef.current,
        timestamp: new Date().toISOString(),
      }).catch(() => {})
    }, 30000)

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange)
      window.removeEventListener("blur", handleBlur)
      window.removeEventListener("focus", handleFocus)
      document.removeEventListener("copy", handleCopy)
      document.removeEventListener("paste", handlePaste)
      document.removeEventListener("cut", handleCut)
      window.clearInterval(heartbeat)
    }
  }, [active, examId])
}
