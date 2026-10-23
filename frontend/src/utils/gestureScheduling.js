// 잠깐의 추적 실패에는 활성 FPS를 유지한다. 대기 중에도 손을 계속 탐색한다.
export function gestureTargetFps(targetFps, now, lastHandAt) {
  const fps = Number.isFinite(targetFps) && targetFps > 0 ? targetFps : 15
  return now - lastHandAt >= 1000 ? Math.min(fps, 5) : fps
}

// 낮은 FPS에서도 확인 시간을 일정하게 유지하고 끊긴 추적 결과는 합치지 않는다.
export function confirmGesture(state, gesture, now) {
  const cooldown = gesture === 'ok' ? 600 : 800
  if (gesture !== state.candidate || now - state.lastSampleAt > 350) {
    state.candidate = gesture
    state.since = now
    state.count = 0
  }
  state.lastSampleAt = now
  state.count++
  if (!gesture || now - state.lastFire < cooldown) return null
  if (state.count < 2 || now - state.since < 120) return null
  state.lastFire = now
  state.candidate = null
  return gesture
}

export function acceptsPalm(size, minimum, tracking) {
  return Number.isFinite(size) && size >= minimum * (tracking ? 0.85 : 1)
}

// 느린 추론 사이에 커서 숨김 타이머가 먼저 끝나지 않게 한다.
export function cursorHideDelay(inferenceMs) {
  return Math.min(800, Math.max(350, inferenceMs * 2 + 100))
}

// 한 프레임의 핀치 흔들림으로 다음 클릭이 재활성화되지 않게 한다.
export function pinchReleased(state, ratio, now) {
  if (!Number.isFinite(ratio) || ratio < 0.55 || now - state.lastAt > 350) {
    state.since = null
  }
  state.lastAt = now
  if (!Number.isFinite(ratio) || ratio < 0.55) return false
  state.since ??= now
  return now - state.since >= 120
}
