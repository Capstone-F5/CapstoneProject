import { useState, useEffect, useRef, useCallback } from 'react'
import { useGesture } from '../hooks/useGesture'

const GESTURES = ['none', 'ok', 'finger_1', 'finger_2', 'finger_3', 'finger_4', 'finger_5']
const TARGET   = 150

const HINTS = {
  none:     '핀치 직전(손가락 거의 붙음) / 주먹 / 자연스러운 손 모양',
  ok:       '엄지-검지 끝 확실히 닿기 — 정면/측면/위아래, 왼손/오른손 모두',
  finger_1: '검지만 펴기 (엄지 접기)',
  finger_2: '검지+중지 (V자), 나머지 접기',
  finger_3: '검지+중지+약지 펴기',
  finger_4: '엄지 제외 4개 펴기',
  finger_5: '5개 모두 펴기',
}

// MediaPipe Hands 관절 연결 목록
const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [0,17],[13,17],[17,18],[18,19],[19,20],
]

// 손가락 끝 인덱스 (빨간 점으로 강조)
const FINGERTIPS = new Set([4, 8, 12, 16, 20])

function drawHand(ctx, lm, w, h) {
  // lm: flat [x0,y0,z0, x1,y1,z1, ...] — 화면 미러 맞춰 x 반전
  const px = (i) => (1 - lm[i * 3])     * w
  const py = (i) =>      lm[i * 3 + 1]  * h

  // 연결선
  ctx.strokeStyle = 'rgba(0, 210, 255, 0.85)'
  ctx.lineWidth   = 2
  for (const [a, b] of CONNECTIONS) {
    ctx.beginPath()
    ctx.moveTo(px(a), py(a))
    ctx.lineTo(px(b), py(b))
    ctx.stroke()
  }

  // 관절 점
  for (let i = 0; i < 21; i++) {
    ctx.beginPath()
    ctx.arc(px(i), py(i), FINGERTIPS.has(i) ? 5 : 3, 0, Math.PI * 2)
    ctx.fillStyle = FINGERTIPS.has(i)
      ? 'rgba(255, 80, 80, 0.95)'
      : (i === 0 ? 'rgba(255, 220, 0, 0.95)' : 'rgba(80, 255, 180, 0.9)')
    ctx.fill()
  }
}

export default function CollectTool() {
  const [gestureIdx, setGestureIdx] = useState(0)
  const [counts,     setCounts]     = useState({})
  const [flash,      setFlash]      = useState(false)
  const [message,    setMessage]    = useState('SPACE=저장  N=다음  P=이전  Z=실수취소')
  const [saving,     setSaving]     = useState(false)
  const [handSeen,   setHandSeen]   = useState(false)

  const latestLmRef  = useRef(null)    // 저장용 최신 랜드마크
  const allLmsRef    = useRef([])      // 드로잉용 전체 손 페이로드
  const canvasRef    = useRef(null)
  const videoRef     = useRef(null)    // useGesture가 채워줌
  const rafRef       = useRef(null)

  const gesture = GESTURES[gestureIdx]

  // ── 샘플 수 조회 ─────────────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/collect/status')
      if (res.ok) setCounts(await res.json())
    } catch {}
  }, [])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  // ── 랜드마크 수신 ────────────────────────────────────────────────────────
  const handleLandmarks = useCallback((payload) => {
    allLmsRef.current = payload
    const hand = payload.find(h => h.label === 'Left') || payload[0] || null
    latestLmRef.current = hand?.lm ?? null
    setHandSeen(hand !== null)
  }, [])

  useGesture({ onLandmarks: handleLandmarks, videoRef, enabled: true })

  // ── 캔버스 드로잉 RAF 루프 ────────────────────────────────────────────────
  useEffect(() => {
    const draw = () => {
      rafRef.current = requestAnimationFrame(draw)
      const canvas = canvasRef.current
      const video  = videoRef.current
      if (!canvas || !video || video.readyState < 2) return

      const vw = video.videoWidth  || 640
      const vh = video.videoHeight || 480
      if (canvas.width !== vw || canvas.height !== vh) {
        canvas.width  = vw
        canvas.height = vh
      }

      const ctx = canvas.getContext('2d')
      // 좌우 반전 (미러 뷰)
      ctx.save()
      ctx.translate(vw, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(video, 0, 0, vw, vh)
      ctx.restore()

      // 관절 오버레이
      for (const hand of allLmsRef.current) {
        drawHand(ctx, hand.lm, vw, vh)
      }
    }
    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [])

  // ── 저장 ─────────────────────────────────────────────────────────────────
  const saveOne = useCallback(async () => {
    if (saving) return
    if (!latestLmRef.current) { setMessage('⚠ 손이 감지되지 않음'); return }
    setSaving(true)
    try {
      const res = await fetch('/api/collect/static', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ gesture, lm: latestLmRef.current }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setMessage(`✓ 저장됨: ${gesture} #${data.saved}`)
      setFlash(true)
      setTimeout(() => setFlash(false), 150)
      fetchStatus()
    } catch (e) {
      setMessage(`✗ 저장 실패: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }, [gesture, saving, fetchStatus])

  // ── 실행 취소 ─────────────────────────────────────────────────────────────
  const undoOne = useCallback(async () => {
    try {
      const res = await fetch(`/api/collect/static/undo/${gesture}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setMessage(`↩ 삭제됨: ${gesture} (남은: ${data.remaining}개)`)
      fetchStatus()
    } catch (e) {
      setMessage(`✗ 실패: ${e.message}`)
    }
  }, [gesture, fetchStatus])

  // ── 키보드 ────────────────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if      (e.code === 'Space') { e.preventDefault(); saveOne() }
      else if (e.code === 'KeyN')  { setGestureIdx(i => (i + 1) % GESTURES.length); setMessage('') }
      else if (e.code === 'KeyP')  { setGestureIdx(i => (i - 1 + GESTURES.length) % GESTURES.length); setMessage('') }
      else if (e.code === 'KeyZ')  { undoOne() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [saveOne, undoOne])

  const cnt    = counts[gesture] ?? 0
  const pct    = Math.min(cnt / TARGET * 100, 100)
  const isDone = cnt >= TARGET

  return (
    <div style={{
      display: 'flex', height: '100dvh', background: '#111',
      color: '#eee', fontFamily: 'monospace', fontSize: 14,
      userSelect: 'none',
    }}>

      {/* ── 왼쪽: 클래스 목록 ──────────────────────────────────────────── */}
      <div style={{
        width: 240, flexShrink: 0,
        borderRight: '1px solid #2a2a2a',
        display: 'flex', flexDirection: 'column',
        overflowY: 'auto', background: '#161616',
      }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #2a2a2a', color: '#555', fontSize: 11 }}>
          클래스 목록 (클릭 / N·P)
        </div>
        {GESTURES.map((g, i) => {
          const c    = counts[g] ?? 0
          const done = c >= TARGET
          const sel  = i === gestureIdx
          return (
            <div key={g} onClick={() => { setGestureIdx(i); setMessage('') }}
              style={{
                padding: '9px 14px', cursor: 'pointer',
                background: sel ? '#1c2c3c' : 'transparent',
                borderLeft: `3px solid ${sel ? '#4af' : 'transparent'}`,
                display: 'flex', flexDirection: 'column', gap: 4,
              }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: sel ? '#4af' : done ? '#4d4' : '#bbb', fontWeight: sel ? 700 : 400 }}>
                  {g}
                </span>
                <span style={{ color: done ? '#4d4' : '#666', fontSize: 11 }}>{c}/{TARGET}</span>
              </div>
              <div style={{ height: 3, background: '#2a2a2a', borderRadius: 2 }}>
                <div style={{
                  height: '100%', borderRadius: 2,
                  background: done ? '#4d4' : sel ? '#4af' : '#444',
                  width: `${Math.min(c / TARGET * 100, 100)}%`,
                  transition: 'width 0.2s',
                }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* ── 오른쪽: 메인 패널 ───────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {/* 헤더 */}
        <div style={{
          padding: '14px 20px',
          background: flash ? '#1a3a1a' : '#181818',
          borderBottom: '1px solid #2a2a2a',
          transition: 'background 0.1s',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <span style={{ fontSize: 22, fontWeight: 700, color: isDone ? '#4d4' : '#4af' }}>
              {gesture}
            </span>
            {isDone && <span style={{ fontSize: 13, color: '#4d4' }}>✓ 완료</span>}
            <span style={{ marginLeft: 'auto', color: isDone ? '#4d4' : '#aaa', fontSize: 13 }}>
              {cnt} / {TARGET}
            </span>
          </div>
          <div style={{ color: '#666', fontSize: 12, marginTop: 3 }}>{HINTS[gesture]}</div>
          <div style={{ height: 5, background: '#2a2a2a', borderRadius: 3, marginTop: 8 }}>
            <div style={{
              height: '100%', borderRadius: 3,
              background: isDone ? '#4d4' : '#4af',
              width: `${pct}%`, transition: 'width 0.2s',
            }} />
          </div>
        </div>

        {/* 카메라 + 관절 캔버스 */}
        <div style={{
          flex: 1, minHeight: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#0d0d0d', position: 'relative',
        }}>
          <canvas ref={canvasRef} style={{
            maxWidth: '100%', maxHeight: '100%',
            objectFit: 'contain',
            border: `2px solid ${handSeen ? '#4af' : '#2a2a2a'}`,
            borderRadius: 8,
            transition: 'border-color 0.2s',
          }} />

          {/* 손 감지 상태 배지 */}
          <div style={{
            position: 'absolute', top: 12, right: 12,
            padding: '4px 10px', borderRadius: 12, fontSize: 12,
            background: handSeen ? 'rgba(0,150,255,0.25)' : 'rgba(80,80,80,0.4)',
            border: `1px solid ${handSeen ? '#4af' : '#444'}`,
            color: handSeen ? '#4af' : '#666',
          }}>
            {handSeen ? '✋ 손 감지됨' : '손 없음'}
          </div>
        </div>

        {/* 하단: 메시지 + 버튼 */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid #2a2a2a', background: '#141414', flexShrink: 0 }}>
          <div style={{ color: '#fa4', minHeight: 18, marginBottom: 10, fontSize: 13 }}>{message}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { label: 'SPACE  저장', action: saveOne,  active: handSeen },
              { label: 'N  다음',     action: () => { setGestureIdx(i => (i + 1) % GESTURES.length); setMessage('') }, active: true },
              { label: 'P  이전',     action: () => { setGestureIdx(i => (i - 1 + GESTURES.length) % GESTURES.length); setMessage('') }, active: true },
              { label: 'Z  취소',     action: undoOne,   active: true, danger: true },
            ].map(({ label, action, active, danger }) => (
              <button key={label} onClick={action} style={{
                padding: '7px 16px', borderRadius: 6,
                background: '#1e1e1e',
                border: `1px solid ${!active ? '#333' : danger ? '#854' : '#4af'}`,
                color: !active ? '#444' : danger ? '#c86' : '#4af',
                cursor: active ? 'pointer' : 'default',
                fontFamily: 'monospace', fontSize: 13,
              }}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
