// [테스트용] 주문번호 낭독 테스트 패널 — 미리 녹음한 조각을 이어 붙인 낭독(numberSpeech.js)을 소리로 확인한다. "API 읽기"는 비교용.
// 쓰지 못하게 하려면 App.jsx의 `import NumberSpeechTest`와 `<NumberSpeechTest />` 두 줄을 주석 처리하면 된다(다른 곳에 영향 없음).
import { useState } from 'react'
import { speakOrderNumber, koreanNumber, numberClips } from '../utils/numberSpeech'
import { playTTS } from '../utils/tts'

const box = { padding: '6px 10px', border: '1px solid #744032', borderRadius: 6, background: '#fff', color: '#744032', fontSize: 13, cursor: 'pointer' }

export default function NumberSpeechTest() {
  const [text, setText] = useState('12')
  const [busy, setBusy] = useState(false)
  const n = Number(text)
  const valid = Number.isInteger(n) && n >= 1 && n <= 999

  const run = async (fn) => {
    if (busy || !valid) return
    setBusy(true)
    try { await fn() } finally { setBusy(false) }
  }

  return (
    <div style={{
      position: 'fixed', left: 8, bottom: 8, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 6,
      padding: 8, background: 'rgba(255,255,255,0.95)', border: '2px dashed #744032', borderRadius: 8, fontFamily: 'sans-serif',
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#744032' }}>주문번호 낭독 테스트</div>
      <div style={{ display: 'flex', gap: 6 }}>
        <input
          type="number" min={1} max={999} value={text}
          onChange={e => setText(e.target.value)}
          style={{ width: 70, padding: '6px 8px', fontSize: 14, border: '1px solid #ccc', borderRadius: 6 }}
        />
        <button style={box} disabled={!valid || busy} onClick={() => run(() => speakOrderNumber(n))}>조각 읽기</button>
        <button style={box} disabled={!valid || busy} onClick={() => run(() => playTTS(`주문번호는 ${koreanNumber(n)} 번입니다`, { cache: false }))}>API 읽기</button>
        <button style={box} onClick={() => setText(String(1 + Math.floor(Math.random() * 999)))}>랜덤</button>
      </div>
      <div style={{ fontSize: 11, color: '#777' }}>{valid ? numberClips(n).join(' + ') : '1~999 사이의 번호를 입력하세요'}</div>
    </div>
  )
}
