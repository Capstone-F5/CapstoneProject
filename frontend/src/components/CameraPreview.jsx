import { useEffect, useRef, useState } from 'react'

// 간편결제 대기 화면 등에서 쓰는 단순 라이브 카메라 미리보기(디코딩 없음).
// QR/바코드 인식이 필요하면 CouponScanModal처럼 @zxing/browser 를 쓰고,
// 여기는 "카메라가 켜져 있다"는 시각 피드백만 필요한 곳에서 재사용한다.
export default function CameraPreview({ style }) {
  const videoRef = useRef(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stream
    let stopped = false
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      .then(s => {
        if (stopped) { s.getTracks().forEach(t => t.stop()); return }
        stream = s
        if (videoRef.current) videoRef.current.srcObject = s
      })
      .catch(err => {
        console.error('[CameraPreview] 카메라 시작 실패:', err)
        setError('카메라를 사용할 수 없습니다')
      })

    return () => {
      stopped = true
      stream?.getTracks().forEach(t => t.stop())
    }
  }, [])

  if (error) {
    return (
      <div style={{ ...style, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#e44', fontSize: 13 }}>
        {error}
      </div>
    )
  }

  return <video ref={videoRef} muted playsInline autoPlay style={style} />
}
