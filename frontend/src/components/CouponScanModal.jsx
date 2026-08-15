import { useEffect, useRef, useState } from 'react'
import { BrowserMultiFormatReader } from '@zxing/browser'
import { validateCoupon } from '../services/orderService'

// QR/바코드 스캔 + 수동 입력 겸용 쿠폰 입력 → 검증 → 확인 모달
// onDetect(code, validationInfo): 사용하기 버튼 클릭 시 호출
export default function CouponScanModal({ onDetect, onClose, total, phone = null }) {
  const videoRef  = useRef(null)
  const readerRef = useRef(null)

  const [manualCode,   setManualCode]   = useState('')
  const [cameraError,  setCameraError]  = useState('')
  const [scanning,     setScanning]     = useState(true)
  const [checking,     setChecking]     = useState(false)
  const [confirmed,    setConfirmed]    = useState(null)  // { code, info } — 확인 단계
  const [checkError,   setCheckError]   = useState('')

  const stopCamera = () => {
    try { readerRef.current?.reset?.() } catch { /* ignore */ }
  }

  useEffect(() => {
    let stopped = false
    const reader = new BrowserMultiFormatReader()
    readerRef.current = reader

    reader.decodeFromVideoDevice(undefined, videoRef.current, (result) => {
      if (stopped || confirmed) return
      if (result) {
        stopped = true
        handleVerify(result.getText())
      }
    }).catch(err => {
      if (stopped) return
      console.error('[CouponScanModal] 카메라 시작 실패:', err)
      setCameraError('카메라를 사용할 수 없습니다. 아래에 쿠폰 코드를 직접 입력해 주세요.')
      setScanning(false)
    })

    return () => {
      stopped = true
      stopCamera()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleVerify = async (code) => {
    const trimmed = code.trim().toUpperCase()
    if (!trimmed) return
    setCheckError('')
    setChecking(true)
    stopCamera()
    try {
      const info = await validateCoupon(trimmed, total, phone)
      if (!info.valid) {
        setCheckError(info.message || '유효하지 않은 쿠폰입니다')
        setChecking(false)
        return
      }
      setConfirmed({ code: trimmed, info })
    } catch (e) {
      setCheckError(e.message || '쿠폰 확인에 실패했습니다')
    } finally {
      setChecking(false)
    }
  }

  const handleManualSubmit = () => handleVerify(manualCode)

  const handleApply = () => {
    if (!confirmed) return
    onDetect(confirmed.code, confirmed.info)
  }

  const handleRetry = () => {
    setConfirmed(null)
    setCheckError('')
    setManualCode('')
    setScanning(true)
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
          <span style={{ fontSize: 20, fontWeight: 900 }}>
            {confirmed ? '쿠폰 확인' : '쿠폰 QR·바코드 스캔'}
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#999',
          }}>✕</button>
        </div>

        {/* ── 확인 단계 ── */}
        {confirmed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{
              background: '#fff8f0', border: '1.5px solid #f0e0c8',
              borderRadius: 12, padding: '18px 20px',
              display: 'flex', flexDirection: 'column', gap: 10,
            }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#744032' }}>
                쿠폰 코드: <span style={{ fontFamily: 'monospace' }}>{confirmed.code}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15 }}>
                <span style={{ color: '#666' }}>할인 금액</span>
                <span style={{ fontWeight: 700, color: '#2e7d32' }}>
                  −{confirmed.info.discountAmount.toLocaleString('ko-KR')}원
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15 }}>
                <span style={{ color: '#666' }}>최종 결제 금액</span>
                <span style={{ fontWeight: 900, fontSize: 18, color: '#744032' }}>
                  {confirmed.info.finalAmount.toLocaleString('ko-KR')}원
                  {confirmed.info.finalAmount === 0 && (
                    <span style={{ fontSize: 13, color: '#2e7d32', marginLeft: 6 }}>(무료)</span>
                  )}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={handleRetry}
                style={{
                  flex: 1, padding: '16px', border: '1.5px solid #e0e0e0', borderRadius: 12,
                  background: '#f5f5f5', color: '#555', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                }}
              >
                다시 입력
              </button>
              <button
                onClick={handleApply}
                style={{
                  flex: 1, padding: '16px', border: 'none', borderRadius: 12,
                  background: '#744032', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                }}
              >
                사용하기
              </button>
            </div>
          </div>
        )}

        {/* ── 입력/스캔 단계 ── */}
        {!confirmed && (
          <>
            {/* 카메라 뷰 */}
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
                {checking && (
                  <div style={{
                    position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: 16, fontWeight: 700,
                  }}>
                    쿠폰 확인 중…
                  </div>
                )}
              </div>
            )}

            {cameraError && (
              <p style={{ fontSize: 14, color: '#e44', fontWeight: 600, margin: 0 }}>{cameraError}</p>
            )}

            {/* 수동 입력 */}
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={manualCode}
                onChange={e => setManualCode(e.target.value.toUpperCase())}
                onKeyDown={e => { if (e.key === 'Enter') handleManualSubmit() }}
                placeholder="쿠폰 코드 직접 입력"
                disabled={checking}
                style={{
                  flex: 1, boxSizing: 'border-box', border: '1.5px solid #e0e0e0',
                  borderRadius: 10, padding: '12px 14px', fontSize: 15,
                }}
              />
              <button
                onClick={handleManualSubmit}
                disabled={!manualCode.trim() || checking}
                style={{
                  border: 'none', borderRadius: 10, padding: '0 20px',
                  background: (manualCode.trim() && !checking) ? '#744032' : '#e0e0e0',
                  color: (manualCode.trim() && !checking) ? '#fff' : '#999',
                  fontSize: 14, fontWeight: 700,
                  cursor: (manualCode.trim() && !checking) ? 'pointer' : 'default',
                  whiteSpace: 'nowrap',
                }}
              >
                {checking ? '확인 중…' : '입력'}
              </button>
            </div>

            {checkError && (
              <p style={{ fontSize: 13, color: '#e44', fontWeight: 600, margin: 0 }}>
                {checkError}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
