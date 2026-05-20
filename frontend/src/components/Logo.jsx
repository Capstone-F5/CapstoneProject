import { useEffect, useRef, useState } from 'react'

/**
 * logo.png의 흰 배경을 canvas로 제거해 투명 PNG로 렌더링.
 * 어두운 헤더 위에도 노란 로고가 제대로 표시된다.
 */
export default function Logo({ height = 36 }) {
  const [dataUrl, setDataUrl] = useState(null)

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width  = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)

      const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height)

      // 흰색 계열 픽셀 → 투명 처리 (엣지 안티앨리어싱 고려)
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i], g = data[i + 1], b = data[i + 2]
        const dist = Math.sqrt((255 - r) ** 2 + (255 - g) ** 2 + (255 - b) ** 2)
        if (dist < 40) {
          data[i + 3] = 0
        } else if (dist < 80) {
          data[i + 3] = Math.round(255 * (dist - 40) / 40)
        }
      }

      const id = ctx.createImageData(canvas.width, canvas.height)
      id.data.set(data)
      ctx.putImageData(id, 0, 0)
      setDataUrl(canvas.toDataURL('image/png'))
    }
    img.onerror = () => setDataUrl(null)
    img.src = '/logo.png'
  }, [])

  if (!dataUrl) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1 }}>
      <span style={{ color: '#F5B800', fontSize: height * 0.35, fontWeight: 900, letterSpacing: 1 }}>F≡</span>
      <span style={{ color: '#F5B800', fontSize: height * 0.42, fontWeight: 900, letterSpacing: 3 }}>BURGER</span>
    </div>
  )

  return <img src={dataUrl} alt="F BURGER" style={{ height, objectFit: 'contain' }} />
}
