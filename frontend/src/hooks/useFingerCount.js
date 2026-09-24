import { useEffect, useRef, useState } from 'react'

const WS_PATH = '/ws/finger'
const SEND_INTERVAL_MS = 200
const HOLD_MS = 1000
// 두 손 합산은 한 손보다 불안정 — 한 프레임씩 검출이 빠져도 total이 달라진다.
// 3으로 올려 600ms(3프레임)까지 후보를 붙잡는다.
const MISS_TOLERANCE = 3
const COOLDOWN_MS = 1500
const JPEG_QUALITY = 0.7
const REPLY_TIMEOUT_MS = 5000
// 최근 N 프레임 다수결 — 단일 프레임 노이즈에 hold가 리셋되는 것을 방지.
// 두 손 합산처럼 프레임 간 값이 튀는 경우 효과적.
const VOTE_WINDOW = 5

/**
 * 수화 숫자(0~9) 인식 훅. 카메라는 useGesture가 연 것을 그대로 쓴다.
 *
 * @param {{current: HTMLVideoElement|null}} opts.videoRef
 * @param {boolean}  opts.enabled
 * @param {(digit: number) => void} opts.onConfirm  1초 유지되어 확정된 숫자
 * @returns {{pending: {digit,progress}|null, connected: boolean}}
 */
export function useFingerCount({ videoRef, enabled = false, onConfirm } = {}) {
  const [pending, setPending] = useState(null)
  const [connected, setConnected] = useState(false)

  const onConfirmRef = useRef(onConfirm)
  useEffect(() => { onConfirmRef.current = onConfirm }, [onConfirm])

  const wsRef     = useRef(null)
  const canvasRef = useRef(null)
  const timerRef  = useRef(null)
  const watchdog  = useRef(null)
  const activeRef = useRef(false)
  const holdRef   = useRef({ digit: null, since: 0, lastFire: -Infinity, miss: 0 })
  // 최근 VOTE_WINDOW 프레임의 digit 값 — 다수결로 안정된 후보 선출
  const voteRef   = useRef([])

  // 최근 N개에서 가장 많이 나온 값 (동점이면 최근 것, null은 제외)
  function majority(arr) {
    const counts = new Map()
    for (let i = arr.length - 1; i >= 0; i--) {
      const v = arr[i]
      if (v == null) continue
      counts.set(v, (counts.get(v) ?? 0) + 1)
    }
    let best = null, bestN = 0
    for (const [v, n] of counts) {
      if (n > bestN) { best = v; bestN = n }
    }
    return best
  }

  useEffect(() => {
    if (!enabled) return
    activeRef.current = true
    canvasRef.current = document.createElement('canvas')
    voteRef.current   = []

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${proto}://${window.location.host}${WS_PATH}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    const scheduleNext = () => {
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(sendFrame, SEND_INTERVAL_MS)
    }

    const sendFrame = () => {
      if (!activeRef.current) return
      const video  = videoRef?.current
      const canvas = canvasRef.current
      if (ws.readyState !== WebSocket.OPEN) return

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
          clearTimeout(watchdog.current)
          watchdog.current = setTimeout(() => {
            console.warn(`[FingerCount] 워치독: ${REPLY_TIMEOUT_MS}ms 응답 없음 — 재전송`)
            sendFrame()
          }, REPLY_TIMEOUT_MS)
        })
      }, 'image/jpeg', JPEG_QUALITY)
    }

    const handleResult = (data) => {
      const now   = performance.now()
      const hold  = holdRef.current
      const hands = data.hands ?? []
      const rawDigit = hands.length ? data.total : null

      // ── 다수결 투표 ──────────────────────────────────────────────────────
      const vote = voteRef.current
      vote.push(rawDigit)
      if (vote.length > VOTE_WINDOW) vote.shift()
      const digit = majority(vote)

      // ── 수신 로그 ────────────────────────────────────────────────────────
      const handsSummary = hands.map(h => `${h.digit}(${(h.conf * 100).toFixed(0)}%)`).join('+')
      console.log(
        `[FingerCount] 수신: raw=${rawDigit ?? '-'} voted=${digit ?? '-'}` +
        (handsSummary ? ` [${handsSummary}]` : ' [손 없음]') +
        ` vote=${JSON.stringify(vote)}`
      )

      // ── 쿨다운 ───────────────────────────────────────────────────────────
      const cooldownLeft = COOLDOWN_MS - (now - hold.lastFire)
      if (cooldownLeft > 0) {
        console.log(`[FingerCount] 쿨다운 중 — ${cooldownLeft.toFixed(0)}ms 남음`)
        return
      }

      // ── Hold 상태 관리 ───────────────────────────────────────────────────
      if (digit !== hold.digit) {
        if (hold.digit != null && ++hold.miss <= MISS_TOLERANCE) {
          console.log(`[FingerCount] miss ${hold.miss}/${MISS_TOLERANCE} — 후보 ${hold.digit} 유지`)
          setPending({ digit: hold.digit, progress: Math.min(1, (now - hold.since) / HOLD_MS) })
          return
        }
        const prev = hold.digit
        if (digit == null) {
          hold.digit = null
          hold.miss  = 0
          setPending(null)
          if (prev != null) console.log(`[FingerCount] 후보 해제: ${prev} → 없음`)
          return
        }
        console.log(`[FingerCount] 후보 변경: ${prev ?? '없음'} → ${digit}`)
        hold.digit = digit
        hold.since = now
      }
      hold.miss = 0

      const held = now - hold.since
      if (held >= HOLD_MS) {
        console.log(`[FingerCount] 확정: ${digit} (${held.toFixed(0)}ms 유지)`)
        hold.lastFire = now
        hold.digit    = null
        voteRef.current = []
        setPending(null)
        onConfirmRef.current?.(digit)
      } else {
        const pct = (held / HOLD_MS * 100).toFixed(0)
        console.log(`[FingerCount] 진행: ${digit} ${pct}%`)
        setPending({ digit, progress: held / HOLD_MS })
      }
    }

    ws.onopen = () => {
      console.log(`[FingerCount] 연결됨: ${wsUrl}`)
      setConnected(true)
      sendFrame()
    }
    ws.onclose = (e) => {
      console.log(`[FingerCount] 끊김 code=${e.code} reason=${e.reason || '-'}`)
      setConnected(false)
    }
    ws.onerror = (e) => {
      console.warn('[FingerCount] WebSocket 오류', e)
    }

    ws.onmessage = (e) => {
      clearTimeout(watchdog.current)
      let data
      try { data = JSON.parse(e.data) } catch { scheduleNext(); return }
      if (data.error) {
        console.warn('[FingerCount] 서버 오류:', data.error)
      } else {
        handleResult(data)
      }
      scheduleNext()
    }

    return () => {
      activeRef.current = false
      clearTimeout(timerRef.current)
      clearTimeout(watchdog.current)
      wsRef.current = null
      holdRef.current = { digit: null, since: 0, lastFire: -Infinity, miss: 0 }
      voteRef.current = []
      setPending(null)
      setConnected(false)
      ws.close()
    }
  }, [enabled, videoRef])

  return { pending, connected }
}
