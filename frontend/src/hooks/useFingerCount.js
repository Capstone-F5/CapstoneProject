import { useEffect, useRef, useState } from 'react'

const WS_PATH = '/ws/finger'
// 응답을 받은 뒤 이만큼 쉬고 다음 프레임을 보낸다. 서버 왕복이 ~55ms라 더 빨리 보낼 수도
// 있지만, Pi가 매 프레임 JPEG 인코딩을 하므로 필요 이상으로 올리지 않는다.
const SEND_INTERVAL_MS = 200
const HOLD_MS = 1000      // 같은 숫자를 이만큼 유지해야 확정
// 5fps라 검출이 한두 프레임 비거나 튀는 건 흔하다. 그때마다 유지 시간을 초기화하면
// 진행률이 계속 리셋되어 영영 확정되지 않는다. 연속 이 횟수까지는 후보를 붙잡는다.
const MISS_TOLERANCE = 2
const COOLDOWN_MS = 1500  // 확정 후 연속 발화 방지
const JPEG_QUALITY = 0.7
// 응답이 끊겨도 루프가 멈추지 않도록 — 서버가 느리거나 프레임을 흘렸을 때 복구용
const REPLY_TIMEOUT_MS = 5000

/**
 * 수화 숫자(0~9) 인식 훅. 카메라는 useGesture가 연 것을 그대로 쓴다 —
 * Pi는 물리 카메라가 1대라 getUserMedia를 또 부르면 NotReadableError가 난다.
 *
 * @param {{current: HTMLVideoElement|null}} opts.videoRef  useGesture가 채워주는 video
 * @param {boolean}  opts.enabled
 * @param {(digit: number) => void} opts.onConfirm  1초 유지되어 확정된 숫자
 * @returns {{pending: {digit,progress}|null, connected: boolean}}
 */
export function useFingerCount({ videoRef, enabled = false, onConfirm } = {}) {
  const [pending, setPending] = useState(null)
  const [connected, setConnected] = useState(false)

  const onConfirmRef = useRef(onConfirm)
  useEffect(() => { onConfirmRef.current = onConfirm }, [onConfirm])

  const wsRef      = useRef(null)
  const canvasRef  = useRef(null)
  const timerRef   = useRef(null)
  const watchdog   = useRef(null)
  const activeRef  = useRef(false)
  // digit: 현재 후보, since: 후보가 처음 잡힌 시각, lastFire: 마지막 확정 시각,
  // miss: 후보와 다른 값이 연속으로 나온 횟수
  const holdRef    = useRef({ digit: null, since: 0, lastFire: -Infinity, miss: 0 })
  const lastLogRef = useRef(undefined)

  useEffect(() => {
    if (!enabled) return
    activeRef.current = true
    canvasRef.current = document.createElement('canvas')

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}${WS_PATH}`)
    wsRef.current = ws

    const scheduleNext = () => {
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(sendFrame, SEND_INTERVAL_MS)
    }

    const sendFrame = () => {
      if (!activeRef.current) return
      const video = videoRef?.current
      const canvas = canvasRef.current
      if (ws.readyState !== WebSocket.OPEN) return

      // useGesture가 카메라를 아직 안 열었을 수 있다 — 준비될 때까지 가볍게 재시도
      if (!video || video.readyState < 2 || !video.videoWidth) {
        scheduleNext()
        return
      }

      canvas.width  = video.videoWidth
      canvas.height = video.videoHeight
      canvas.getContext('2d').drawImage(video, 0, 0)
      canvas.toBlob(blob => {
        if (!blob || !activeRef.current || ws.readyState !== WebSocket.OPEN) return
        blob.arrayBuffer().then(buf => {
          if (!activeRef.current || ws.readyState !== WebSocket.OPEN) return
          ws.send(buf)
          // 응답이 안 오면 루프가 영영 멈추므로 워치독으로 되살린다
          clearTimeout(watchdog.current)
          watchdog.current = setTimeout(() => {
            console.warn('[FingerCount] 응답 지연 — 프레임 재전송')
            sendFrame()
          }, REPLY_TIMEOUT_MS)
        })
      }, 'image/jpeg', JPEG_QUALITY)
    }

    const handleResult = (data) => {
      const now = performance.now()
      const hold = holdRef.current
      const hands = data.hands ?? []
      // 손이 하나면 그 숫자, 둘이면 합산 — 서버가 total로 계산해 보내준다
      const digit = hands.length ? data.total : null

      // 어떤 값이 오는지 확인용 — 값이 바뀔 때만 찍어 로그가 넘치지 않게 한다
      if (digit !== lastLogRef.current) {
        lastLogRef.current = digit
        console.log('[FingerCount]', digit, hands)
      }

      if (now - hold.lastFire < COOLDOWN_MS) return

      if (digit !== hold.digit) {
        // 검출이 잠깐 비거나 튄 것은 넘긴다 — 진행률도 유지한다
        if (hold.digit != null && ++hold.miss <= MISS_TOLERANCE) {
          setPending({ digit: hold.digit, progress: Math.min(1, (now - hold.since) / HOLD_MS) })
          return
        }
        if (digit == null) {
          hold.digit = null
          hold.miss  = 0
          setPending(null)
          return
        }
        hold.digit = digit
        hold.since = now
      }
      hold.miss = 0

      const held = now - hold.since
      if (held >= HOLD_MS) {
        hold.lastFire = now
        hold.digit = null
        setPending(null)
        onConfirmRef.current?.(digit)
      } else {
        setPending({ digit, progress: held / HOLD_MS })
      }
    }

    ws.onopen = () => { setConnected(true); sendFrame() }
    ws.onclose = () => setConnected(false)

    ws.onmessage = (e) => {
      clearTimeout(watchdog.current)
      let data
      try { data = JSON.parse(e.data) } catch { scheduleNext(); return }
      if (data.error) console.warn('[FingerCount] 서버 오류:', data.error)
      else handleResult(data)
      scheduleNext()
    }

    ws.onerror = () => console.warn('[FingerCount] WebSocket 오류')

    return () => {
      activeRef.current = false
      clearTimeout(timerRef.current)
      clearTimeout(watchdog.current)
      wsRef.current = null
      holdRef.current = { digit: null, since: 0, lastFire: -Infinity, miss: 0 }
      setPending(null)
      setConnected(false)
      ws.close()
    }
  }, [enabled, videoRef])

  return { pending, connected }
}
