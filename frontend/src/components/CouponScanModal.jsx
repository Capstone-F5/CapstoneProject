import { useEffect, useRef, useState } from 'react'
import { BrowserMultiFormatReader } from '@zxing/browser'

// QR/바코드 스캔 + 수동 입력 겸용 쿠폰 코드 입력 모달.
// 카메라 권한이 없거나 인식이 안 되는 경우를 대비해 수동 입력을 항상 함께 제공한다.
export default function CouponScanModal({ onDetect, onClose }) {
  const videoRef = useRef(null)
  const readerRef = useRef(null)
  const [manualCode, setManualCode] = useState('')
  const [cameraError, setCameraError] = useState('')
  const [scanning, setScanning] = useState(true)

  useEffect(() => {
    let stopped = false
    const reader = new BrowserMultiFormatReader()
    readerRef.current = reader

    reader.decodeFromVideoDevice(undefined, videoRef.current, (result, err) => {
      if (stopped) return
      if (result) {
        stopped = true
        onDetect(result.getText())
      }
      // NotFoundException은 매 프레임마다 정상적으로 발생(아직 인식 못 함) — 무시.
    }).catch(err => {
      if (stopped) return
      console.error('[CouponScanModal] 카메라 시작 실패:', err)
      setCameraError('카메라를 사용할 수 없습니다. 아래에 쿠폰 코드를 직접 입력해 주세요.')
      setScanning(false)
    })

    return () => {
      stopped = true
      try { readerRef.current?.reset?.() } catch { /* ignore */ }
    }
  }, [onDetect])

  const handleManualSubmit = () => {
    const code = manualCode.trim()
    if (!code) return
    onDetect(code)
  }

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 130,
      background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '0 clamp(16px,5vw,24px)',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: '94%', maxWidth: 480,
        background: '#fff', borderRadius: 18,
        padding: 'clamp(22px,5vw,28px)',
        boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 20, fontWeight: 900 }}>쿠폰 QR·바코드 스캔</span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#999',
          }}>✕</button>
        </div>

        {scanning && !cameraError && (
          <div style={{
            position: 'relative', width: '100%', aspectRatio: '4 / 3',
            background: '#000', borderRadius: 12, overflow: 'hidden',
          }}>
            <video ref={videoRef} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted playsInline />
            <div style={{
              position: 'absolute', inset: '15% 20%', border: '3px solid #F5B800',
              borderRadius: 10, pointerEvents: 'none',
            }} />
          </div>
        )}

        {cameraError && (
          <p style={{ fontSize: 14, color: '#e44', fontWeight: 600, margin: 0 }}>{cameraError}</p>
        )}

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={manualCode}
            onChange={e => setManualCode(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleManualSubmit() }}
            placeholder="쿠폰 코드 직접 입력"
            style={{
              flex: 1, boxSizing: 'border-box', border: '1.5px solid #e0e0e0',
              borderRadius: 10, padding: '12px 14px', fontSize: 15,
            }}
          />
          <button
            onClick={handleManualSubmit}
            disabled={!manualCode.trim()}
            style={{
              border: 'none', borderRadius: 10, padding: '0 20px',
              background: manualCode.trim() ? '#744032' : '#e0e0e0',
              color: manualCode.trim() ? '#fff' : '#999',
              fontSize: 14, fontWeight: 700,
              cursor: manualCode.trim() ? 'pointer' : 'default',
            }}
          >입력</button>
        </div>
      </div>
    </div>
  )
}
