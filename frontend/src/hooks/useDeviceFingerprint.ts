import { useMemo } from "react"

export function getDeviceSignals() {
  return {
    user_agent: navigator.userAgent,
    screen_resolution: `${screen.width}x${screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    platform: navigator.platform,
  }
}

export function useDeviceFingerprint(): string {
  return useMemo(() => {
    const signals = getDeviceSignals()
    return btoa(JSON.stringify(signals)).slice(0, 32)
  }, [])
}
