import { useState, useEffect, useRef, useCallback } from 'react'

// idleMs        : 마지막 상호작용 후 경고창이 뜨기까지의 시간 (ms)
// warningSeconds: 경고 카운트다운 시간 (초) — 0이 되면 onExpire 호출
export function useIdleTimer({ idleMs, warningSeconds, onExpire }) {
  const [secondsLeft, setSecondsLeft] = useState(null) // null = 대기중, number = 카운트다운
  const mainRef    = useRef(null)
  const countRef   = useRef(null)
  const expireRef  = useRef(onExpire)
  expireRef.current = onExpire

  const clear = () => {
    clearTimeout(mainRef.current)
    clearInterval(countRef.current)
  }

  const reset = useCallback(() => {
    clear()
    setSecondsLeft(null)
    mainRef.current = setTimeout(() => {
      let s = warningSeconds
      setSecondsLeft(s)
      countRef.current = setInterval(() => {
        s -= 1
        if (s <= 0) {
          clearInterval(countRef.current)
          expireRef.current?.()
        } else {
          setSecondsLeft(s)
        }
      }, 1000)
    }, idleMs)
  }, [idleMs, warningSeconds])

  useEffect(() => {
    const EVENTS = ['pointerdown', 'keydown', 'wheel', 'touchstart']
    EVENTS.forEach(e => window.addEventListener(e, reset, { passive: true }))
    reset()
    return () => {
      EVENTS.forEach(e => window.removeEventListener(e, reset))
      clear()
    }
  }, [reset])

  return secondsLeft // null → 정상 대기, 숫자 → 카운트다운 중
}
