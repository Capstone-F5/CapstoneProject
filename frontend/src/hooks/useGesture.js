import { useEffect, useRef } from 'react'

const WS_URL = import.meta.env.VITE_GESTURE_WS ?? 'ws://localhost:8765'

/**
 * Python 제스처 모듈과 WebSocket으로 연결합니다.
 * onGesture({ gesture, cursor, progress, ok_progress }) 콜백으로 이벤트를 전달합니다.
 *
 * gesture 값: 'none' | 'swipe_up' | 'swipe_down' | 'swipe_left' | 'swipe_right'
 *             | 'point' | 'dwell' | 'ok'
 * cursor: [normX, normY] (0~1) 또는 null
 */
export function useGesture(onGesture) {
  const cbRef = useRef(onGesture)
  useEffect(() => { cbRef.current = onGesture })

  useEffect(() => {
    let ws
    let retryTimer

    function connect() {
      ws = new WebSocket(WS_URL)

      ws.onopen = () => console.log('[Gesture] WS 연결됨')

      ws.onmessage = (e) => {
        try {
          cbRef.current(JSON.parse(e.data))
        } catch (err) {
          console.warn('[Gesture] 메시지 파싱 오류', err)
        }
      }

      ws.onclose = () => {
        console.log('[Gesture] WS 끊김, 1.5초 후 재연결...')
        retryTimer = setTimeout(connect, 1500)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      clearTimeout(retryTimer)
      ws?.close()
    }
  }, [])
}
