import { useEffect, useState } from 'react'
import { getSpeedLimits, getTtsSpeed, resetTtsSpeed, stepTtsSpeed, subscribeTtsSpeed } from '../utils/ttsSpeed'

// 음성 배속 조절: [ − ]  1.2배속  [ + ]  — 화면 하단 컨트롤 바(검은 배경)에 "음성인식 ON"일 때만 나타난다(App.jsx).
// - 범위(최소~최대)와 기본 배속은 관리자 설정(키오스크 설정 → 음성 안내 속도). 한계에 닿으면 해당 버튼이 비활성화된다.
// - 가운데 숫자를 누르면 기본 배속으로 돌아간다.
// - 재생 중에도 바로 적용된다(ChatPanel이 같은 구독으로 재생 중인 오디오의 속도를 바꾼다).

const BTN = {
  width: 44, height: 44, borderRadius: 22, border: 'none', padding: 0, lineHeight: 1,
  fontSize: 24, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
  flexShrink: 0, touchAction: 'manipulation',
}

export function formatSpeed(v) {
  return `${Number(v).toFixed(1)}배속`
}

export default function SpeedControl({ variant = 'panel' }) {
  const [speed, setSpeed] = useState(getTtsSpeed)
  const [limits, setLimits] = useState(getSpeedLimits)

  useEffect(() => subscribeTtsSpeed((s, l) => { setSpeed(s); setLimits(l) }), [])

  // 손님이 화면을 만지는 중이므로 유휴 타이머를 리셋한다(ChatPanel의 빠른 응답 경로와 같은 신호)
  const touched = () => window.dispatchEvent(new Event('gesture-activity'))
  const atMin = speed <= limits.min
  const atMax = speed >= limits.max
  const isDefault = Math.abs(speed - limits.def) < 0.001

  const bar = variant === 'bar'
  const btn = (disabled) => bar
    ? {   // 하단 바(검은 배경): 바의 다른 버튼처럼 흰 글자, 한계에서는 흐리게
        ...BTN, width: 40, height: 40, borderRadius: 20, fontSize: 24,
        background: 'rgba(255,255,255,0.16)', color: disabled ? 'rgba(255,255,255,0.3)' : '#fff',
        cursor: disabled ? 'default' : 'pointer',
      }
    : {
        ...BTN,
        background: disabled ? '#d9d9d9' : '#744032',
        color: disabled ? '#999' : '#fff',
        cursor: disabled ? 'default' : 'pointer',
      }

  return (
    <div
      role="group"
      aria-label="음성 배속 조절"
      style={{ display: 'flex', alignItems: 'center', gap: 6, userSelect: 'none' }}
    >
      <button
        type="button"
        aria-label="음성 느리게"
        disabled={atMin}
        onClick={() => { touched(); stepTtsSpeed(-1) }}
        style={btn(atMin)}
      >−</button>
      <button
        type="button"
        aria-label={`현재 ${formatSpeed(speed)}. 누르면 기본 속도로 돌아갑니다`}
        onClick={() => { touched(); resetTtsSpeed() }}
        style={bar ? {
          // 바의 ControlText와 같은 모양: 한글(위, 크게) + 영문(아래, 작게). 기본에서 바뀌면 노란색
          minWidth: 78, background: 'none', border: 'none', padding: '4px 0', cursor: 'pointer', touchAction: 'manipulation',
          color: isDefault ? '#fff' : '#F5B800', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, lineHeight: 1.3,
        } : {
          minWidth: 76, height: 44, padding: '0 6px', borderRadius: 10, border: '1.5px solid #744032',
          background: isDefault ? '#fff' : '#F5B800', color: '#744032', fontSize: 15, fontWeight: 800,
          cursor: 'pointer', touchAction: 'manipulation',
        }}
      >{bar ? (<>
        <span style={{ fontSize: 15, fontWeight: 700 }}>{formatSpeed(speed)}</span>
        <span style={{ fontSize: 11, fontWeight: 400, opacity: 0.75 }}>Voice speed</span>
      </>) : formatSpeed(speed)}</button>
      <button
        type="button"
        aria-label="음성 빠르게"
        disabled={atMax}
        onClick={() => { touched(); stepTtsSpeed(+1) }}
        style={btn(atMax)}
      >+</button>
    </div>
  )
}
