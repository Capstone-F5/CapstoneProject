import { useState, useEffect, useRef, useCallback } from 'react'
import '../admin.css'
import {
  DEFAULT_KIOSK_SETTINGS,
  fetchKioskSettings,
  saveKioskSettings,
  resetKioskSettings,
  fetchKioskDiagnosticLogs,
  applyKioskSettingsToRuntime,
} from '../../services/settingsService.js'
import { AudioEnergyGate, installMicAgcGuard } from '../../utils/audioGate.js'
import { _palmSize } from '../../hooks/useGesture.js'

const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17],
]

const MIC_PRESETS = {
  quiet: {
    label: '조용한 실내 (민감)',
    desc: '주변 소음이 거의 없는 환경입니다. 작은 목소리나 단답도 민감하게 포착합니다.',
    values: {
      preset: 'quiet',
      auto_gain_control: false,
      min_speech_rms: 0.012,
      snr_margin: 1.6,
      min_active_ms: 90,
      vad_positive_threshold: 0.72,
      vad_negative_threshold: 0.38,
      vad_redemption_frames: 10,
      no_speech_threshold: 0.70,
      logprob_threshold: -1.15,
      short_word_logprob_threshold: -1.45,
      compression_threshold: 2.4,
    },
  },
  standard: {
    label: '일반 매장 · 웹캠 표준 (권장)',
    desc: '무지향성 웹캠 마이크 기준 권장 설정입니다. 1.5m 밖 주변 대화와 잔잔한 매장 음악을 걸러냅니다.',
    values: {
      preset: 'standard',
      auto_gain_control: false,
      min_speech_rms: 0.018,
      snr_margin: 2.0,
      min_active_ms: 120,
      vad_positive_threshold: 0.80,
      vad_negative_threshold: 0.45,
      vad_redemption_frames: 8,
      no_speech_threshold: 0.65,
      logprob_threshold: -1.0,
      short_word_logprob_threshold: -1.35,
      compression_threshold: 2.4,
    },
  },
  noisy: {
    label: '시끄러운 매장 · BGM 강함 (엄격)',
    desc: '매장 배경음악이 크거나 주변 테이블 대화가 시끄러운 환경에서 오인식을 강하게 차단합니다.',
    values: {
      preset: 'noisy',
      auto_gain_control: false,
      min_speech_rms: 0.025,
      snr_margin: 2.5,
      min_active_ms: 150,
      vad_positive_threshold: 0.85,
      vad_negative_threshold: 0.52,
      vad_redemption_frames: 7,
      no_speech_threshold: 0.58,
      logprob_threshold: -0.85,
      short_word_logprob_threshold: -1.25,
      compression_threshold: 2.2,
    },
  },
  strict: {
    label: '초근접 발화 전용 (초엄격)',
    desc: '키오스크 정면 30~40cm 이내에서 또렷하게 말하는 음성만 허용합니다.',
    values: {
      preset: 'strict',
      auto_gain_control: false,
      min_speech_rms: 0.032,
      snr_margin: 3.0,
      min_active_ms: 150,
      vad_positive_threshold: 0.88,
      vad_negative_threshold: 0.58,
      vad_redemption_frames: 6,
      no_speech_threshold: 0.52,
      logprob_threshold: -0.75,
      short_word_logprob_threshold: -1.15,
      compression_threshold: 2.1,
    },
  },
}

const APPROACH_PRESETS = {
  near: {
    label: '근거리 전용 (약 1.0m)',
    desc: '키오스크 바로 앞에 멈춰 선 손님만 감지합니다. 통행량이 많은 매장에 적합합니다.',
    values: {
      preset: 'near',
      enabled: true,
      confidence_threshold: 0.58,
      min_box_h: 0.22,
      frame_interval_ms: 500,
      confirm_window: 5,
      confirm_hits: 4,
      rearm_absent_frames: 8,
      announcement_interval_sec: 10.0,
      max_announcements: 3,
    },
  },
  standard: {
    label: '표준 거리 (약 1.5m, 권장)',
    desc: '화면 높이의 15% 이상 크기로 잡히는 흰 지팡이·휠체어를 4프레임 중 3프레임 연속 확인 시 안내합니다.',
    values: {
      preset: 'standard',
      enabled: true,
      confidence_threshold: 0.50,
      min_box_h: 0.15,
      frame_interval_ms: 500,
      confirm_window: 4,
      confirm_hits: 3,
      rearm_absent_frames: 6,
      announcement_interval_sec: 10.0,
      max_announcements: 3,
    },
  },
  far: {
    label: '원거리 감지 (약 2.5m)',
    desc: '멀리서 접근하는 휠체어·흰 지팡이도 빠르게 포착해 선제적으로 음성·제스처 안내를 시작합니다.',
    values: {
      preset: 'far',
      enabled: true,
      confidence_threshold: 0.40,
      min_box_h: 0.10,
      frame_interval_ms: 400,
      confirm_window: 3,
      confirm_hits: 2,
      rearm_absent_frames: 6,
      announcement_interval_sec: 10.0,
      max_announcements: 3,
    },
  },
}

const GESTURE_PRESETS = {
  standard: {
    label: '표준 권장 (약 0.8~1.2m)',
    desc: '일반적인 키오스크 사용 거리에서 안정적으로 커서 이동과 핀치 확인/스와이프를 인식합니다.',
    values: {
      preset: 'standard',
      enabled: true,
      min_palm_size: 0.08,
      detection_confidence: 0.65,
      tracking_confidence: 0.50,
      target_fps: 15,
      cam_width: 640,
      cam_height: 480,
    },
  },
  far_reach: {
    label: '원거리 손 인식 강화 (약 1.5m+)',
    desc: '손이 멀리 있어 작게 잡힐 때도 인식이 끊기지 않도록 크기 임계값과 감지 기준을 완화합니다.',
    values: {
      preset: 'far_reach',
      enabled: true,
      min_palm_size: 0.05,
      detection_confidence: 0.50,
      tracking_confidence: 0.45,
      target_fps: 15,
      cam_width: 640,
      cam_height: 480,
    },
  },
  rpi_eco: {
    label: '라즈베리 파이 4B 경량화 (저발열·절전)',
    desc: '해상도와 프레임률을 낮춰 라즈베리 파이 4B의 온디바이스 CPU 발열과 스로틀링을 예방합니다.',
    values: {
      preset: 'rpi_eco',
      enabled: true,
      min_palm_size: 0.07,
      detection_confidence: 0.55,
      tracking_confidence: 0.45,
      target_fps: 10,
      cam_width: 480,
      cam_height: 360,
    },
  },
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <div
      role="switch"
      aria-checked={checked}
      className={`toggle${checked ? ' checked' : ''}`}
      onClick={e => { e.stopPropagation(); if (!disabled) onChange(!checked) }}
      style={{ cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.5 : 1, flexShrink: 0 }}
    >
      <div className="toggle-track" />
      <div className="toggle-thumb" />
    </div>
  )
}

function SliderRow({ label, hint, value, min, max, step, unit = '', onChange, isLast = false }) {
  return (
    <div style={{ padding: '14px 0', borderBottom: isLast ? 'none' : '1px solid #f0f0f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontWeight: 500, fontSize: 14, color: '#222' }}>{label}</span>
        <span style={{ fontWeight: 600, fontSize: 14, color: '#744032' }}>
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: '100%', accentColor: '#744032', cursor: 'pointer' }}
      />
      {hint && <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>{hint}</div>}
    </div>
  )
}

function ToggleRow({ label, hint, checked, onChange, isLast = false }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '14px 0',
      borderBottom: isLast ? 'none' : '1px solid #f0f0f0',
      gap: 16,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 500, fontSize: 14, color: '#222' }}>{label}</div>
        {hint && <div style={{ fontSize: 12, color: '#888', marginTop: 3 }}>{hint}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  )
}

function drawGestureFrame(video, canvas, results, minPalmSize) {
  if (!canvas || !video) return { detected: false, label: '미감지', palmSize: 0, action: '대기', isFar: false }
  const ctx = canvas.getContext('2d')
  const cw = canvas.width
  const ch = canvas.height

  // 1. 비디오 프레임 그리기 (거울 모드로 좌우 반전)
  ctx.save()
  ctx.translate(cw, 0)
  ctx.scale(-1, 1)
  ctx.drawImage(video, 0, 0, cw, ch)
  ctx.restore()

  const lms = results?.multiHandLandmarks || []
  const handed = results?.multiHandedness || []
  if (!lms.length) {
    return { detected: false, label: '미감지', palmSize: 0, action: '대기', isFar: false }
  }

  const lm = lms[0]
  const rawLabel = handed[0]?.label || 'Right'
  const label = rawLabel === 'Left' ? '오른손' : '왼손'
  const camAR = cw / ch
  const pSize = _palmSize(lm, camAR)
  const isFar = pSize < minPalmSize

  // 2. 스켈레톤 관절 연결선
  ctx.save()
  ctx.lineWidth = 2.5
  ctx.strokeStyle = isFar ? 'rgba(231, 76, 60, 0.9)' : 'rgba(245, 184, 0, 0.95)'
  for (const [s, e] of HAND_CONNECTIONS) {
    const p1 = lm[s]
    const p2 = lm[e]
    ctx.beginPath()
    ctx.moveTo((1 - p1.x) * cw, p1.y * ch)
    ctx.lineTo((1 - p2.x) * cw, p2.y * ch)
    ctx.stroke()
  }

  // 3. 관절 점 그리기
  for (let i = 0; i < 21; i++) {
    const pt = lm[i]
    const x = (1 - pt.x) * cw
    const y = pt.y * ch
    ctx.beginPath()
    ctx.arc(x, y, i === 8 ? 5.5 : (i === 4 ? 5 : 3.5), 0, Math.PI * 2)
    ctx.fillStyle = i === 8 ? '#744032' : (i === 4 ? '#e67e22' : '#ffffff')
    ctx.strokeStyle = '#222222'
    ctx.lineWidth = 1.2
    ctx.fill()
    ctx.stroke()
  }
  ctx.restore()

  // 4. 간단한 제스처 판정
  const dThumbIndex = Math.hypot((lm[4].x - lm[8].x) * camAR, lm[4].y - lm[8].y)
  const isPinch = dThumbIndex < 0.08
  const dTip = Math.hypot((lm[8].x - lm[0].x) * camAR, lm[8].y - lm[0].y)
  const dPip = Math.hypot((lm[6].x - lm[0].x) * camAR, lm[6].y - lm[0].y)
  const isPointing = dTip > dPip * 1.15

  let action = '손 감지됨'
  if (isPinch) {
    action = '선택 OK (핀치)'
  } else if (isPointing) {
    action = '포인팅 (커서 이동)'
  }

  return {
    detected: true,
    label,
    palmSize: Number(pSize.toFixed(3)),
    action,
    isFar,
  }
}

export default function KioskSettingsPage({ isKioskOverlay = false, onClose }) {
  const [settings, setSettings] = useState(DEFAULT_KIOSK_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [toast, setToast] = useState(null)
  const [logs, setLogs] = useState({ approach: [], voice: [] })
  const [logsLoading, setLogsLoading] = useState(false)

  // 실시간 웹캠 마이크 감도 테스터 상태
  const [micTesting, setMicTesting] = useState(false)
  const [liveRms, setLiveRms] = useState(0)
  const [liveNoiseFloor, setLiveNoiseFloor] = useState(0.004)
  const [gateHistory, setGateHistory] = useState([])
  const micStreamRef = useRef(null)
  const audioCtxRef = useRef(null)
  const speechBufRef = useRef([])
  const speakingFramesRef = useRef(0)
  const silenceFramesRef = useRef(0)
  const gateInstanceRef = useRef(new AudioEnergyGate())
  const latestMicCfgRef = useRef(settings.mic)
  latestMicCfgRef.current = settings.mic

  // 실시간 카메라 확인 상태 (접근 감지 vs 온디바이스 제스처)
  const [camMode, setCamMode] = useState('approach') // 'approach' | 'gesture'
  const [camTesting, setCamTesting] = useState(false)
  const [camStatus, setCamStatus] = useState(null)
  const [camWsNote, setCamWsNote] = useState('')
  const camVideoRef = useRef(null)
  const camStreamRef = useRef(null)
  const camCanvasRef = useRef(null)
  const camWsRef = useRef(null)
  const camTimerRef = useRef(null)

  // 실시간 제스처 모니터 상태
  const [gestureLive, setGestureLive] = useState({
    detected: false,
    label: '미감지',
    palmSize: 0,
    action: '대기',
    fps: 0,
    isFar: false,
  })
  const gestureHandsRef = useRef(null)
  const gestureCanvasRef = useRef(null)
  const gestureRafRef = useRef(null)
  const gesturePerfRef = useRef({ frames: 0, fpsTimer: performance.now(), fps: 0 })
  const gestureInflightRef = useRef(false)

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchKioskSettings()
      if (data?.settings) {
        setSettings(data.settings)
        setDirty(false)
      }
    } catch (e) {
      showToast(e.message || '설정을 불러오지 못했습니다', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  const loadLogs = useCallback(async () => {
    setLogsLoading(true)
    try {
      const data = await fetchKioskDiagnosticLogs(20)
      setLogs({
        approach: data?.approach || [],
        voice: data?.voice || [],
      })
    } catch {
      // ignore
    } finally {
      setLogsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
    loadLogs()
  }, [loadAll, loadLogs])

  // 키오스크 디버깅 모드 토글 시 즉시 서버에 저장하여 별도 기기(키오스크) 하단 바에 바로 반영
  const handleToggleDebugMode = async (enabled) => {
    const next = {
      ...settings,
      debug_mode: Boolean(enabled),
    }
    setSettings(next)
    applyKioskSettingsToRuntime(next, true)
    try {
      const res = await saveKioskSettings(next)
      if (res?.settings) setSettings(res.settings)
      showToast(enabled ? '키오스크 디버깅 모드가 켜졌습니다.' : '키오스크 디버깅 모드가 꺼졌습니다.')
    } catch (e) {
      showToast(e.message || '디버깅 모드 저장 실패', 'error')
    }
  }

  const updateMic = (patch) => {
    setSettings(prev => {
      const next = {
        ...prev,
        mic: {
          ...prev.mic,
          preset: patch.preset ?? 'custom',
          ...patch,
        },
      }
      applyKioskSettingsToRuntime(next, true)
      return next
    })
    setDirty(true)
  }

  const updateApproach = (patch) => {
    setSettings(prev => {
      const next = {
        ...prev,
        approach: {
          ...prev.approach,
          preset: patch.preset ?? 'custom',
          ...patch,
        },
      }
      applyKioskSettingsToRuntime(next, true)
      return next
    })
    setDirty(true)
  }

  const updateGesture = (patch) => {
    setSettings(prev => {
      const next = {
        ...prev,
        gesture: {
          ...prev.gesture,
          preset: patch.preset ?? 'custom',
          ...patch,
        },
      }
      applyKioskSettingsToRuntime(next, true)
      return next
    })
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await saveKioskSettings(settings)
      if (res?.settings) setSettings(res.settings)
      setDirty(false)
      showToast('설정이 저장되었습니다.')
    } catch (e) {
      showToast(e.message || '저장 실패', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!window.confirm('마이크 감도 및 접근 감지 설정을 기본값으로 초기화하시겠습니까?')) return
    setSaving(true)
    try {
      const res = await resetKioskSettings()
      if (res?.settings) setSettings(res.settings)
      setDirty(false)
      showToast('기본값으로 복원되었습니다.')
    } catch (e) {
      showToast(e.message || '초기화 실패', 'error')
    } finally {
      setSaving(false)
    }
  }

  const stopMicTest = useCallback(() => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop())
      micStreamRef.current = null
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {})
      audioCtxRef.current = null
    }
    speechBufRef.current = []
    speakingFramesRef.current = 0
    silenceFramesRef.current = 0
    setMicTesting(false)
    setLiveRms(0)
  }, [])

  const startMicTest = async () => {
    if (micTesting) {
      stopMicTest()
      return
    }
    try {
      installMicAgcGuard()
      const allowAgc = Boolean(settings.mic.auto_gain_control)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: allowAgc,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      micStreamRef.current = stream
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      const ctx = new AudioCtx({ sampleRate: 16000 })
      audioCtxRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const processor = ctx.createScriptProcessor(512, 1, 1)

      gateInstanceRef.current = new AudioEnergyGate({
        minSpeechRms: settings.mic.min_speech_rms,
        snrMargin: settings.mic.snr_margin,
        minActiveMs: settings.mic.min_active_ms,
      })

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0)
        let sumSq = 0
        for (let i = 0; i < input.length; i++) sumSq += input[i] * input[i]
        const rms = Math.sqrt(sumSq / input.length)
        setLiveRms(rms)

        const mcfg = latestMicCfgRef.current
        gateInstanceRef.current.configure({
          minSpeechRms: mcfg.min_speech_rms,
          snrMargin: mcfg.snr_margin,
          minActiveMs: mcfg.min_active_ms,
        })

        const triggerLevel = Math.max(0.008, mcfg.min_speech_rms * 0.55)
        if (rms >= triggerLevel) {
          speakingFramesRef.current += 1
          silenceFramesRef.current = 0
          speechBufRef.current.push(new Float32Array(input))
        } else if (speakingFramesRef.current > 0) {
          silenceFramesRef.current += 1
          speechBufRef.current.push(new Float32Array(input))
          if (silenceFramesRef.current >= 11) {
            const chunks = speechBufRef.current
            const totalLen = chunks.reduce((acc, c) => acc + c.length, 0)
            const merged = new Float32Array(totalLen)
            let offset = 0
            for (const c of chunks) {
              merged.set(c, offset)
              offset += c.length
            }
            const res = gateInstanceRef.current.evaluate(merged)
            setLiveNoiseFloor(gateInstanceRef.current.noiseFloor)
            setGateHistory(prev => [
              {
                id: Date.now(),
                time: new Date().toLocaleTimeString('ko-KR', { hour12: false }),
                ...res,
              },
              ...prev.slice(0, 4),
            ])
            speechBufRef.current = []
            speakingFramesRef.current = 0
            silenceFramesRef.current = 0
          }
        } else {
          speechBufRef.current.push(new Float32Array(input))
          if (speechBufRef.current.length > 8) speechBufRef.current.shift()
        }
      }

      source.connect(processor)
      processor.connect(ctx.destination)
      setMicTesting(true)
    } catch (e) {
      showToast(`마이크 연결 실패: ${e.message}`, 'error')
    }
  }

  const stopApproachWs = useCallback(() => {
    if (camTimerRef.current) {
      clearInterval(camTimerRef.current)
      camTimerRef.current = null
    }
    if (camWsRef.current) {
      camWsRef.current.onclose = null
      camWsRef.current.onerror = null
      camWsRef.current.onmessage = null
      camWsRef.current.close()
      camWsRef.current = null
    }
    setCamStatus(null)
    setCamWsNote('')
  }, [])

  const startApproachWs = useCallback((video) => {
    stopApproachWs()
    if (!video) return
    try {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/approach`)
      ws.binaryType = 'arraybuffer'
      camWsRef.current = ws

      const canvas = document.createElement('canvas')
      canvas.width = 320
      canvas.height = 240
      camCanvasRef.current = canvas

      ws.onopen = () => {
        const interval = Math.max(200, Number(settings.approach?.frame_interval_ms) || 500)
        camTimerRef.current = setInterval(() => {
          if (!video || video.readyState < 2 || ws.readyState !== WebSocket.OPEN) return
          const ctx = canvas.getContext('2d')
          ctx.drawImage(video, 0, 0, 320, 240)
          canvas.toBlob(blob => {
            if (!blob) return
            blob.arrayBuffer().then(buf => {
              if (ws.readyState === WebSocket.OPEN) ws.send(buf)
            })
          }, 'image/jpeg', 0.6)
        }, interval)
      }

      ws.onmessage = (e) => {
        if (typeof e.data !== 'string') return
        try {
          const data = JSON.parse(e.data)
          if (data.error) {
            setCamWsNote(data.error)
          } else {
            setCamStatus(data)
          }
        } catch {}
      }

      ws.onclose = () => {
        if (camTimerRef.current) {
          clearInterval(camTimerRef.current)
          camTimerRef.current = null
        }
      }
    } catch (e) {
      console.warn('[KioskSettingsPage] 접근 감지 WebSocket 연결 실패:', e)
    }
  }, [settings.approach?.frame_interval_ms, stopApproachWs])

  const stopGestureLoop = useCallback(() => {
    if (gestureRafRef.current) {
      cancelAnimationFrame(gestureRafRef.current)
      gestureRafRef.current = null
    }
    if (gestureHandsRef.current) {
      try { gestureHandsRef.current.close() } catch {}
      gestureHandsRef.current = null
    }
    gestureInflightRef.current = false
    setGestureLive({
      detected: false,
      label: '미감지',
      palmSize: 0,
      action: '대기',
      fps: 0,
      isFar: false,
    })
  }, [])

  const startGestureLoop = useCallback(async (video) => {
    stopGestureLoop()
    if (!video) return
    try {
      const { Hands } = await import('@mediapipe/hands')
      const hands = new Hands({ locateFile: (f) => `/mediapipe-hands/${f}` })
      hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 0,
        minDetectionConfidence: Number(settings.gesture?.detection_confidence) || 0.65,
        minTrackingConfidence: Number(settings.gesture?.tracking_confidence) || 0.50,
      })
      gestureHandsRef.current = hands

      hands.onResults((results) => {
        const canvas = gestureCanvasRef.current
        if (!canvas || !video) return
        const minPalm = Number(settings.gesture?.min_palm_size) || 0.08
        const metrics = drawGestureFrame(video, canvas, results, minPalm)

        const now = performance.now()
        const p = gesturePerfRef.current
        p.frames++
        if (now - p.fpsTimer >= 1000) {
          p.fps = +(p.frames * 1000 / (now - p.fpsTimer)).toFixed(1)
          p.frames = 0
          p.fpsTimer = now
        }

        setGestureLive({
          ...metrics,
          fps: p.fps || Number(settings.gesture?.target_fps) || 15,
        })
      })

      await hands.initialize()

      const targetFps = Math.max(8, Number(settings.gesture?.target_fps) || 15)
      let lastSend = 0

      const loop = () => {
        if (!camStreamRef.current) return
        const now = performance.now()
        if (!gestureInflightRef.current && video.readyState >= 2 && now - lastSend >= 1000 / targetFps) {
          gestureInflightRef.current = true
          lastSend = now
          hands.send({ image: video }).catch(() => {}).finally(() => {
            gestureInflightRef.current = false
          })
        }
        gestureRafRef.current = requestAnimationFrame(loop)
      }
      gestureRafRef.current = requestAnimationFrame(loop)
    } catch (e) {
      console.warn('[KioskSettingsPage] 제스처 모델 구동 실패:', e)
    }
  }, [settings.gesture?.detection_confidence, settings.gesture?.tracking_confidence, settings.gesture?.min_palm_size, settings.gesture?.target_fps, stopGestureLoop])

  const stopCamTest = useCallback(() => {
    stopApproachWs()
    stopGestureLoop()
    if (camStreamRef.current) {
      camStreamRef.current.getTracks().forEach(t => t.stop())
      camStreamRef.current = null
    }
    if (camVideoRef.current) {
      camVideoRef.current.srcObject = null
    }
    setCamTesting(false)
  }, [stopApproachWs, stopGestureLoop])

  // camTesting 이 켜졌을 때 video 엘리먼트에 스트림을 안정적으로 연결
  useEffect(() => {
    if (camTesting && camVideoRef.current && camStreamRef.current) {
      if (camVideoRef.current.srcObject !== camStreamRef.current) {
        camVideoRef.current.srcObject = camStreamRef.current
      }
      camVideoRef.current.play().catch(() => {})
    }
  }, [camTesting])

  const startCamTest = async () => {
    if (camTesting) {
      stopCamTest()
      return
    }
    try {
      let stream
      const reqW = Number(settings.gesture?.cam_width) || 640
      const reqH = Number(settings.gesture?.cam_height) || 480
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: reqW }, height: { ideal: reqH }, facingMode: 'user' },
        })
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({ video: true })
      }
      camStreamRef.current = stream
      setCamWsNote('')
      setCamTesting(true)

      const video = camVideoRef.current
      if (video) {
        video.srcObject = stream
        await video.play().catch(() => {})
        if (camMode === 'approach') {
          startApproachWs(video)
        } else {
          startGestureLoop(video)
        }
      }
    } catch (e) {
      showToast(`카메라 연결 실패: ${e.message}`, 'error')
      stopCamTest()
    }
  }

  const switchCamMode = (newMode) => {
    if (newMode === camMode) return
    setCamMode(newMode)
    if (camTesting && camVideoRef.current) {
      if (newMode === 'approach') {
        stopGestureLoop()
        startApproachWs(camVideoRef.current)
      } else {
        stopApproachWs()
        startGestureLoop(camVideoRef.current)
      }
    }
  }

  useEffect(() => {
    return () => {
      stopMicTest()
      stopCamTest()
    }
  }, [stopMicTest, stopCamTest])

  if (loading) {
    return <div className="loading-text">설정을 불러오는 중…</div>
  }

  const { mic, approach, gesture = DEFAULT_KIOSK_SETTINGS.gesture } = settings
  const rmsBarPct = Math.min(100, Math.round((liveRms / 0.08) * 100))
  const thresholdMarkerPct = Math.min(100, Math.round((mic.min_speech_rms / 0.08) * 100))
  const palmSizeBarPct = Math.min(100, Math.round(((gestureLive.palmSize || 0) / 0.16) * 100))
  const minPalmMarkerPct = Math.min(100, Math.round(((gesture.min_palm_size || 0.08) / 0.16) * 100))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 상단 상태, 디버깅 모드 토글 및 저장 버튼 */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, paddingBottom: 14, borderBottom: '1px solid #f0f0f0' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 15, fontWeight: 600, color: '#222' }}>
                {isKioskOverlay ? '키오스크 디버깅 설정' : '마이크 감도 및 접근 감지 설정'}
              </span>
              <span className={`badge ${dirty ? 'badge-cooking' : 'badge-active'}`}>
                {dirty ? '변경사항 있음' : '저장됨'}
              </span>
            </div>
            <div style={{ fontSize: 13, color: '#888', marginTop: 4 }}>
              웹캠 마이크의 배경 소음·음악·주변 대화 필터 임계값과 흰 지팡이·휠체어 접근 감지 기준을 조정합니다.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn-outline" onClick={handleReset} disabled={saving}>
              기본값 복원
            </button>
            <button type="button" className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? '저장 중…' : '설정 저장'}
            </button>
            {isKioskOverlay && onClose && (
              <button type="button" className="btn-outline" onClick={onClose}>
                닫기
              </button>
            )}
          </div>
        </div>

        <ToggleRow
          label="키오스크 디버깅 모드"
          hint="켜면(ON) 키오스크 기기 하단 컨트롤 바에 디버깅 버튼이 표시되어, 키오스크 화면에서 직접 마이크·카메라 감도를 측정하고 설정을 조절할 수 있습니다."
          checked={Boolean(settings.debug_mode)}
          onChange={handleToggleDebugMode}
          isLast
        />
      </div>

      {toast && (
        <div
          className="card"
          style={{
            padding: '12px 20px',
            background: toast.type === 'error' ? '#fde8e8' : '#e6f4ea',
            color: toast.type === 'error' ? '#c0392b' : '#2e7d32',
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          {toast.msg}
        </div>
      )}

      {/* 2단 구성: 마이크 감도 / 접근 감지 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '20px', alignItems: 'start' }}>
        {/* 1. 웹캠 마이크 및 STT 감도 */}
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>웹캠 마이크 및 음성 인식 감도</div>
          <div style={{ fontSize: 13, color: '#888', marginBottom: 16 }}>
            주변 대화나 매장 음악이 주문으로 오인식되지 않도록 음량·신호비·STT 신뢰도 기준을 설정합니다.
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#555', marginBottom: 8 }}>환경 프리셋</div>
            <div className="filter-chips">
              {Object.entries(MIC_PRESETS).map(([key, p]) => (
                <button
                  key={key}
                  type="button"
                  className={`chip${mic.preset === key ? ' active' : ''}`}
                  onClick={() => updateMic(p.values)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            {MIC_PRESETS[mic.preset] && (
              <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                {MIC_PRESETS[mic.preset].desc}
              </div>
            )}
          </div>

          {/* 실시간 마이크 입력 레벨 확인 */}
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: '14px 16px', marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#222' }}>마이크 입력 레벨 확인</div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                  평소 주문 목소리와 주변 소음을 비교해 최소 통과 기준선(minSpeechRms)을 조정하세요.
                </div>
              </div>
              <button
                type="button"
                className={micTesting ? 'btn-danger btn-sm' : 'btn-outline btn-sm'}
                onClick={startMicTest}
              >
                {micTesting ? '측정 중지' : '마이크 측정'}
              </button>
            </div>

            <div style={{ position: 'relative', height: 10, background: '#e5e5e5', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${rmsBarPct}%`,
                  height: '100%',
                  background: liveRms >= mic.min_speech_rms ? '#744032' : '#F5B800',
                  transition: 'width 60ms linear',
                }}
              />
              <div
                title={`최소 발화 기준선 (${mic.min_speech_rms})`}
                style={{
                  position: 'absolute',
                  left: `${thresholdMarkerPct}%`,
                  top: 0,
                  bottom: 0,
                  width: 2,
                  background: '#c0392b',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#666', marginTop: 6 }}>
              <span>현재 음량(RMS): {liveRms.toFixed(4)}</span>
              <span style={{ color: '#744032', fontWeight: 600 }}>기준선: {mic.min_speech_rms}</span>
              <span>배경 소음 바닥: {liveNoiseFloor.toFixed(4)}</span>
            </div>

            {gateHistory.length > 0 && (
              <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #e5e5e5', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {gateHistory.map(item => (
                  <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <span className={`badge ${item.pass ? 'badge-active' : 'badge-cancelled'}`}>
                      {item.pass ? '통과 (STT 전송)' : `차단 (${item.reason})`}
                    </span>
                    <span style={{ color: '#666' }}>
                      RMS {item.metrics?.activeRms} · SNR {item.metrics?.snrRatio}배 · {item.metrics?.activeMs}ms
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <ToggleRow
            label="웹캠 마이크 자동 증폭 (AGC)"
            hint="끄면(OFF) 조용할 때 웹캠이 멀리 있는 주변 대화나 음악을 증폭해 끌어당기는 현상을 막습니다. OFF 권장."
            checked={Boolean(mic.auto_gain_control)}
            onChange={v => updateMic({ auto_gain_control: v })}
          />

          <SliderRow
            label="근접 발화 최소 음량 (minSpeechRms)"
            hint="이 값보다 작은 원거리 대화나 웅얼거림은 STT 서버로 보내지 않습니다. (권장: 0.016 ~ 0.025)"
            value={mic.min_speech_rms}
            min={0.005}
            max={0.050}
            step={0.001}
            onChange={v => updateMic({ min_speech_rms: v })}
          />

          <SliderRow
            label="배경 소음 대비 최소 신호비 (snrMargin)"
            hint="평소 매장 소음 바닥보다 최소 몇 배 이상 커야 발화로 인정할지 설정합니다. (권장: 2.0배)"
            value={mic.snr_margin}
            min={1.2}
            max={4.0}
            step={0.1}
            unit="배"
            onChange={v => updateMic({ snr_margin: v })}
          />

          <SliderRow
            label="최소 발화 지속시간 (minActiveMs)"
            hint="순간 음량은 크지만 지속 시간이 짧은 박수·기침·식기 소음을 걸러냅니다. (권장: 120ms)"
            value={mic.min_active_ms}
            min={60}
            max={300}
            step={15}
            unit="ms"
            onChange={v => updateMic({ min_active_ms: v })}
          />

          <SliderRow
            label="음성 감지(VAD) 시작 임계값"
            hint="높일수록 사람 목소리가 분명할 때만 녹음을 시작합니다."
            value={mic.vad_positive_threshold}
            min={0.55}
            max={0.95}
            step={0.01}
            onChange={v => updateMic({ vad_positive_threshold: v })}
          />

          <SliderRow
            label="음성 감지(VAD) 말 끝 대기 프레임"
            hint="말이 끝난 뒤 기다리는 프레임 수입니다. 줄이면 말 끝에 주변 소음이 섞여 들어오는 것을 줄입니다."
            value={mic.vad_redemption_frames}
            min={4}
            max={18}
            step={1}
            unit="프레임"
            onChange={v => updateMic({ vad_redemption_frames: v })}
          />

          <SliderRow
            label="Whisper 무음 확률 차단 (no_speech_threshold)"
            hint="무음·잡음 확률이 이 값 이상이면 전사 결과를 폐기합니다. (낮출수록 엄격, 기본 0.65)"
            value={mic.no_speech_threshold}
            min={0.35}
            max={0.90}
            step={0.05}
            onChange={v => updateMic({ no_speech_threshold: v })}
          />

          <SliderRow
            label="Whisper 전사 신뢰도 하한 (logprob_threshold)"
            hint="배경 소음이 억지로 글자로 변환된 저신뢰 전사 구간을 차단합니다. (-0.7에 가까울수록 엄격, 기본 -1.0)"
            value={mic.logprob_threshold}
            min={-1.8}
            max={-0.5}
            step={0.05}
            onChange={v => updateMic({ logprob_threshold: v })}
          />

          <ToggleRow
            label="도메인 문맥 필터 (비주문 대화·노래 가사 무시)"
            hint="메뉴·주문·결제와 무관한 일상 대화나 노래 가사가 인식되었을 때 조용히 무시합니다."
            checked={Boolean(mic.domain_guard_enabled)}
            onChange={v => updateMic({ domain_guard_enabled: v })}
          />

          <ToggleRow
            label="안내 음성 중 끼어들기 (Barge-in)"
            hint="키오스크 음성 안내 도중 손님이 말하면 안내를 멈추고 바로 듣습니다."
            checked={Boolean(mic.barge_in_enabled)}
            onChange={v => updateMic({ barge_in_enabled: v })}
            isLast
          />
        </div>

        {/* 2. 접근 감지 설정 */}
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>접근 감지 설정 (흰 지팡이 · 휠체어)</div>
          <div style={{ fontSize: 13, color: '#888', marginBottom: 16 }}>
            대기 화면에서 흰 지팡이 및 휠체어 접근을 인식하는 거리, 최소 신뢰도, 연속 확정 기준을 설정합니다.
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#555', marginBottom: 8 }}>거리 프리셋</div>
            <div className="filter-chips">
              {Object.entries(APPROACH_PRESETS).map(([key, p]) => (
                <button
                  key={key}
                  type="button"
                  className={`chip${approach.preset === key ? ' active' : ''}`}
                  onClick={() => updateApproach(p.values)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            {APPROACH_PRESETS[approach.preset] && (
              <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                {APPROACH_PRESETS[approach.preset].desc}
              </div>
            )}
          </div>

          {/* 실시간 카메라 확인 (접근 감지 vs 제스처 감지 탭) */}
          <div style={{ background: '#f5f5f5', borderRadius: 8, padding: '14px 16px', marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 10 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#222' }}>카메라 감지 실시간 확인</div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                  서버 PC의 접근 감지와 라즈베리 파이 온디바이스 제스처 인식을 각각 실시간 테스트합니다.
                </div>
              </div>
              <button
                type="button"
                className={camTesting ? 'btn-danger btn-sm' : 'btn-outline btn-sm'}
                onClick={startCamTest}
              >
                {camTesting ? '카메라 중지' : '카메라 확인'}
              </button>
            </div>

            {/* 모드 전환 탭 */}
            <div className="filter-chips" style={{ marginBottom: 12 }}>
              <button
                type="button"
                className={`chip${camMode === 'approach' ? ' active' : ''}`}
                onClick={() => switchCamMode('approach')}
              >
                접근 감지 테스트 (서버 PC)
              </button>
              <button
                type="button"
                className={`chip${camMode === 'gesture' ? ' active' : ''}`}
                onClick={() => switchCamMode('gesture')}
              >
                제스처 감지 테스트 (라즈베리 파이 온디바이스)
              </button>
            </div>

            <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative', width: 200, height: 150, background: '#e8e8e8', borderRadius: 6, overflow: 'hidden', flexShrink: 0 }}>
                <video
                  ref={camVideoRef}
                  playsInline
                  muted
                  autoPlay
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    display: camTesting && camMode === 'approach' ? 'block' : 'none',
                  }}
                />
                <canvas
                  ref={gestureCanvasRef}
                  width={320}
                  height={240}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    display: camTesting && camMode === 'gesture' ? 'block' : 'none',
                  }}
                />
                {!camTesting && (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 12, color: '#888' }}>
                    카메라 대기 중
                  </div>
                )}
              </div>

              <div style={{ flex: 1, minWidth: 220, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {camMode === 'approach' ? (
                  <>
                    <div style={{ background: '#fff', borderRadius: 6, padding: '8px 12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>흰 지팡이 (음성 안내)</span>
                        <span className={`badge ${camStatus?.confirmed?.white_cane ? 'badge-active' : 'badge-inactive'}`}>
                          {camStatus?.confirmed?.white_cane ? '감지 확정' : '대기'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        신뢰도 {((camStatus?.white_cane_confidence ?? 0) * 100).toFixed(1)}% (기준 {Math.round(approach.confidence_threshold * 100)}%)
                        {' · '}
                        높이 {((camStatus?.white_cane_box_h ?? 0) * 100).toFixed(1)}% (기준 {Math.round(approach.min_box_h * 100)}%)
                      </div>
                    </div>

                    <div style={{ background: '#fff', borderRadius: 6, padding: '8px 12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>휠체어 (제스처 안내)</span>
                        <span className={`badge ${camStatus?.confirmed?.wheelchair ? 'badge-active' : 'badge-inactive'}`}>
                          {camStatus?.confirmed?.wheelchair ? '감지 확정' : '대기'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        신뢰도 {((camStatus?.wheelchair_confidence ?? 0) * 100).toFixed(1)}% (기준 {Math.round(approach.confidence_threshold * 100)}%)
                        {' · '}
                        높이 {((camStatus?.wheelchair_box_h ?? 0) * 100).toFixed(1)}% (기준 {Math.round(approach.min_box_h * 100)}%)
                      </div>
                    </div>

                    {camWsNote && (
                      <div style={{ fontSize: 12, color: '#888' }}>
                        {camWsNote}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div style={{ background: '#fff', borderRadius: 6, padding: '8px 12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>온디바이스 손 인식 및 동작</span>
                        <span className={`badge ${gestureLive.detected ? (gestureLive.isFar ? 'badge-cooking' : 'badge-active') : 'badge-inactive'}`}>
                          {gestureLive.detected ? (gestureLive.isFar ? '원거리 손' : '정상 감지') : '미감지'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        {gestureLive.label} · 동작: {gestureLive.action} · {gestureLive.fps} FPS
                      </div>
                    </div>

                    <div style={{ background: '#fff', borderRadius: 6, padding: '8px 12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>손 크기(거리): {gestureLive.palmSize.toFixed(3)}</span>
                        <span style={{ fontSize: 12, color: '#744032', fontWeight: 600 }}>
                          기준선 {gesture.min_palm_size.toFixed(3)}
                        </span>
                      </div>
                      <div style={{ position: 'relative', height: 8, background: '#e5e5e5', borderRadius: 4, overflow: 'hidden', marginBottom: 4 }}>
                        <div
                          style={{
                            width: `${palmSizeBarPct}%`,
                            height: '100%',
                            background: gestureLive.isFar ? '#e74c3c' : '#744032',
                            transition: 'width 60ms linear',
                          }}
                        />
                        <div
                          title={`원거리 최소 기준선 (${gesture.min_palm_size})`}
                          style={{
                            position: 'absolute',
                            left: `${minPalmMarkerPct}%`,
                            top: 0,
                            bottom: 0,
                            width: 2,
                            background: '#c0392b',
                          }}
                        />
                      </div>
                      <div style={{ fontSize: 11, color: '#888' }}>
                        {gestureLive.detected
                          ? (gestureLive.isFar
                            ? '손이 멀어 기준선 미달입니다. 아래 슬라이더에서 기준을 낮춰보세요.'
                            : '정상 인식 거리입니다. 커서 이동 및 선택이 원활합니다.')
                          : '손을 카메라에 비추어 크기(거리)를 확인하세요.'}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          <ToggleRow
            label="대기 화면 접근 감지 사용"
            hint="시작 화면에서 웹캠으로 흰 지팡이·휠체어 접근을 상시 감지합니다."
            checked={Boolean(approach.enabled)}
            onChange={v => updateApproach({ enabled: v })}
          />

          <SliderRow
            label="객체 인식 최소 신뢰도"
            hint="모델의 추론 점수가 이 값 이상일 때만 유효 감지로 인정합니다. (기본 0.50)"
            value={approach.confidence_threshold}
            min={0.25}
            max={0.85}
            step={0.05}
            onChange={v => updateApproach({ confidence_threshold: v })}
          />

          <SliderRow
            label="최소 객체 높이 비율 (인식 거리)"
            hint="화면 세로 대비 객체 높이가 이 비율 이상일 때만 근접한 손님으로 인정합니다. 높일수록 가까이 와야 반응합니다."
            value={approach.min_box_h}
            min={0.05}
            max={0.45}
            step={0.01}
            onChange={v => updateApproach({ min_box_h: v })}
          />

          <SliderRow
            label="카메라 프레임 전송 주기"
            hint="서버로 카메라 프레임을 보내는 간격입니다. (500ms = 초당 2프레임)"
            value={approach.frame_interval_ms}
            min={250}
            max={1000}
            step={50}
            unit="ms"
            onChange={v => updateApproach({ frame_interval_ms: v })}
          />

          <SliderRow
            label="확정 판정 프레임 윈도우"
            hint="최근 몇 프레임을 모아 진입 여부를 판정할지 설정합니다."
            value={approach.confirm_window}
            min={2}
            max={8}
            step={1}
            unit="프레임"
            onChange={v => updateApproach({
              confirm_window: v,
              confirm_hits: Math.min(approach.confirm_hits, v),
            })}
          />

          <SliderRow
            label="확정 최소 감지 횟수"
            hint={`최근 ${approach.confirm_window}프레임 중 몇 번 이상 감지되어야 안내를 시작할지 설정합니다.`}
            value={approach.confirm_hits}
            min={1}
            max={approach.confirm_window}
            step={1}
            unit="회"
            onChange={v => updateApproach({ confirm_hits: v })}
          />

          <SliderRow
            label="안내 종료 후 재감지 대기 프레임"
            hint="안내가 끝난 뒤 대상이 연속으로 몇 프레임 동안 사라져야 다음 손님 감지를 다시 준비할지 설정합니다."
            value={approach.rearm_absent_frames}
            min={2}
            max={16}
            step={1}
            unit="프레임"
            onChange={v => updateApproach({ rearm_absent_frames: v })}
          />

          <SliderRow
            label="안내 음성 반복 간격"
            hint="반응이 없을 때 안내 음성을 다시 재생하는 간격입니다."
            value={approach.announcement_interval_sec}
            min={5}
            max={25}
            step={1}
            unit="초"
            onChange={v => updateApproach({ announcement_interval_sec: v })}
          />

          <SliderRow
            label="최대 안내 반복 횟수"
            hint="안내 음성을 최대 몇 번까지 반복할지 설정합니다."
            value={approach.max_announcements}
            min={1}
            max={5}
            step={1}
            unit="회"
            onChange={v => updateApproach({ max_announcements: v })}
            isLast
          />
        </div>

        {/* 3. 제스처 감도 및 라즈베리 파이 4B 최적화 설정 */}
        <div className="card">
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>제스처 감도 및 라즈베리 파이 4B 최적화 (온디바이스)</div>
          <div style={{ fontSize: 13, color: '#888', marginBottom: 16 }}>
            라즈베리 파이 4B의 온디바이스 손 인식 감도, 원거리 인식 손 크기 임계값 및 CPU 부하를 설정합니다.
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#555', marginBottom: 8 }}>제스처 & 하드웨어 프리셋</div>
            <div className="filter-chips">
              {Object.entries(GESTURE_PRESETS).map(([key, p]) => (
                <button
                  key={key}
                  type="button"
                  className={`chip${gesture.preset === key ? ' active' : ''}`}
                  onClick={() => updateGesture(p.values)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            {GESTURE_PRESETS[gesture.preset] && (
              <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                {GESTURE_PRESETS[gesture.preset].desc}
              </div>
            )}
          </div>

          <ToggleRow
            label="온디바이스 제스처 인식 사용"
            hint="키오스크 주문 및 메뉴 화면에서 손동작을 인식해 비접촉 제어합니다."
            checked={Boolean(gesture.enabled)}
            onChange={v => updateGesture({ enabled: v })}
          />

          <SliderRow
            label="원거리 손 인식 최소 크기 (min_palm_size)"
            hint="손목과 중지 관절 사이의 거리 비율입니다. 손이 멀어 인식이 잘 안 될 때는 0.05~0.06으로 낮추어 보십시오. (기본 0.08)"
            value={gesture.min_palm_size}
            min={0.03}
            max={0.15}
            step={0.005}
            onChange={v => updateGesture({ min_palm_size: v })}
          />

          <SliderRow
            label="손 검출 최소 신뢰도 (detection_confidence)"
            hint="MediaPipe가 손으로 감지할 최소 확률입니다. 낮출수록 어두운 곳이나 원거리에서 잘 잡히지만 배경 오인식에 주의해야 합니다. (기본 0.65)"
            value={gesture.detection_confidence}
            min={0.35}
            max={0.85}
            step={0.05}
            onChange={v => updateGesture({ detection_confidence: v })}
          />

          <SliderRow
            label="손 랜드마크 추적 신뢰도 (tracking_confidence)"
            hint="연속 프레임에서 손가락 관절 21개를 추적하는 신뢰도입니다. (기본 0.50)"
            value={gesture.tracking_confidence}
            min={0.30}
            max={0.80}
            step={0.05}
            onChange={v => updateGesture({ tracking_confidence: v })}
          />

          <SliderRow
            label="라즈베리 파이 4B 목표 프레임률 (target_fps)"
            hint="초당 온디바이스 손 추론 횟수입니다. 라즈베리 파이 4B에서는 10~15 FPS 설정을 권장하며 발열과 전력 소모를 줄입니다."
            value={gesture.target_fps}
            min={8}
            max={24}
            step={1}
            unit=" FPS"
            onChange={v => updateGesture({ target_fps: v })}
          />

          <div style={{ padding: '14px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 500, fontSize: 14, color: '#222' }}>카메라 입력 해상도</span>
              <span style={{ fontWeight: 600, fontSize: 14, color: '#744032' }}>
                {gesture.cam_width} × {gesture.cam_height}
              </span>
            </div>
            <div className="filter-chips">
              {[
                { w: 640, h: 480, label: '640 × 480 (표준)' },
                { w: 480, h: 360, label: '480 × 360 (RPi 권장 절전)' },
                { w: 320, h: 240, label: '320 × 240 (초경량)' },
              ].map(opt => (
                <button
                  key={`${opt.w}x${opt.h}`}
                  type="button"
                  className={`chip${gesture.cam_width === opt.w && gesture.cam_height === opt.h ? ' active' : ''}`}
                  onClick={() => updateGesture({ cam_width: opt.w, cam_height: opt.h })}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>
              해상도를 480 × 360으로 낮추면 라즈베리 파이 4B의 온디바이스 CPU 부하가 크게 감소하여 장시간 운용 시 안정성이 높아집니다.
            </div>
          </div>

          <div style={{ background: '#f8f9fa', borderRadius: 6, padding: '12px 14px', marginTop: 14, fontSize: 12, color: '#555', lineHeight: 1.6 }}>
            <div style={{ fontWeight: 600, color: '#333', marginBottom: 4 }}>라즈베리 파이 4B 최적화 및 원거리 인식 안내</div>
            <div>• 라즈베리 파이 4B는 CPU 연산 자원이 한정되어 있으므로 목표 FPS 10~15, 해상도 480 × 360 설정 시 발열로 인한 스로틀링(속도 저하) 없이 쾌적하게 구동됩니다.</div>
            <div>• 손이 멀어 인식이 잘 안 될 때는 상단 카메라 테스트 창에서 Palm Size를 확인한 후, '원거리 손 인식 최소 크기'를 0.05~0.06으로 낮추면 원거리 손도 매끄럽게 포착됩니다.</div>
          </div>
        </div>
      </div>

      {/* 4. 최근 감지 및 차단 로그 */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>최근 감지 및 소음 차단 기록</div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
              음성 인식 타이밍·소음 차단 내역(voice_timing.log)과 접근 감지 내역(approach.log)을 확인합니다.
            </div>
          </div>
          <button
            type="button"
            className="btn-outline btn-sm"
            onClick={loadLogs}
            disabled={logsLoading}
          >
            {logsLoading ? '불러오는 중…' : '새로고침'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginBottom: 8 }}>음성 인식 및 소음 차단 로그</div>
            <div style={{
              background: '#f5f5f5',
              color: '#333',
              padding: '12px 14px',
              borderRadius: 8,
              fontSize: 12,
              height: 180,
              overflowY: 'auto',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {logs.voice.length ? logs.voice.slice().reverse().join('\n') : '기록된 음성 로그가 없습니다.'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginBottom: 8 }}>접근 감지 추론 로그</div>
            <div style={{
              background: '#f5f5f5',
              color: '#333',
              padding: '12px 14px',
              borderRadius: 8,
              fontSize: 12,
              height: 180,
              overflowY: 'auto',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {logs.approach.length ? logs.approach.slice().reverse().join('\n') : '기록된 접근 감지 로그가 없습니다.'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
