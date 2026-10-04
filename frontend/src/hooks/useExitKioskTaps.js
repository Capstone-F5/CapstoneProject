import { useEffect } from 'react'

// 화면 좌상단 영역을 짧은 시간 안에 TAP_COUNT번 터치하면 키오스크 전체화면을 해제한다.
// 모든 화면에서 동작하도록 window 캡처 단계에서 감지하고, 아래 UI의 클릭은 막지 않는다.
const TAP_COUNT = 10
const TAP_WINDOW_MS = 5000
const CORNER_SIZE = 100

// Chromium --kiosk 전체화면은 JS(document.exitFullscreen)로 해제되지 않는다.
// Pi에서 도는 로컬 도우미(deploy/raspberry-pi/exit_kiosk_helper.py)가 Chromium을 창 모드로 다시 띄운다.
const HELPER_URL = 'http://127.0.0.1:8765/exit-fullscreen'

function exitFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
  // 응답은 필요 없고 도우미가 요청을 받기만 하면 되므로 no-cors. 도우미가 없으면 조용히 무시된다.
  fetch(HELPER_URL, { method: 'POST', mode: 'no-cors' }).catch(() => {})
}

export function useExitKioskTaps(enabled = true) {
  useEffect(() => {
    if (!enabled) return
    let taps = []
    const onPointerDown = (e) => {
      if (e.clientX > CORNER_SIZE || e.clientY > CORNER_SIZE) return
      const now = Date.now()
      taps = taps.filter(t => now - t < TAP_WINDOW_MS)
      taps.push(now)
      if (taps.length >= TAP_COUNT) {
        taps = []
        exitFullscreen()
      }
    }
    window.addEventListener('pointerdown', onPointerDown, true)
    return () => window.removeEventListener('pointerdown', onPointerDown, true)
  }, [enabled])
}
