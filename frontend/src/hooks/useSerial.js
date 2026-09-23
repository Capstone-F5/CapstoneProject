import { useEffect, useRef, useState } from 'react'

const CASH_MAP = {
  '1000WON':  1000,
  '5000WON':  5000,
  '10000WON': 10000,
  '50000WON': 50000,
  '10WON':    10,
  '50WON':    50,
  '100WON':   100,
  '500WON':   500,
}

// getPorts() 순서: [지폐(9600), 동전(115200)] 고정 배치 기준
const BAUD_RATES = [9600, 115200]

async function readPortLines(port, onLine, activeRef) {
  const decoder = new TextDecoder()
  let buffer = ''
  while (activeRef.current) {
    let reader = null
    try {
      reader = port.readable.getReader()
      while (activeRef.current) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let nl
        while ((nl = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, nl).replace(/\r$/, '').trim()
          buffer = buffer.slice(nl + 1)
          if (line) onLine(line)
        }
      }
    } catch (err) {
      if (!activeRef.current) break
      console.warn('[useSerial] 읽기 오류, 2초 후 재시도:', err)
    } finally {
      try { reader?.releaseLock() } catch {}
    }
    if (activeRef.current) await new Promise(r => setTimeout(r, 2000))
  }
}

function dispatchLine(line, onCard, onCash) {
  if (line === 'INPUT=CARD') {
    onCard?.()
    return
  }
  if (line.startsWith('INPUT=')) {
    const key = line.slice(6)
    const amount = CASH_MAP[key]
    if (amount != null) onCash?.(amount)
  }
  // RESET COMPLETE, TOTAL:*, --- 등은 무시
}

/**
 * Arduino 시리얼 입력 훅.
 * - 최초 1회: requestPermission()을 사용자 제스처(버튼 클릭 등)로 호출해 포트 권한 부여
 * - 이후 자동: getPorts()로 기허가 포트에 재연결
 *
 * @param {() => void}          opts.onCard  INPUT=CARD 수신 시 호출
 * @param {(n: number) => void} opts.onCash  INPUT=*WON 수신 시 금액과 함께 호출
 * @param {boolean}             opts.enabled
 * @returns {{ requestPermission: () => Promise<void>, connected: boolean }}
 */
export function useSerial({ onCard, onCash, enabled = true } = {}) {
  const onCardRef = useRef(onCard)
  const onCashRef = useRef(onCash)
  useEffect(() => { onCardRef.current = onCard }, [onCard])
  useEffect(() => { onCashRef.current = onCash }, [onCash])

  const activeRef    = useRef(false)
  const openPorts    = useRef(new Set())
  const setConnected = useRef(null)
  const [connected, _setConnected] = useState(false)
  setConnected.current = _setConnected

  const markOpen = (port) => {
    openPorts.current.add(port)
    setConnected.current(true)
  }
  const markClosed = (port) => {
    openPorts.current.delete(port)
    if (openPorts.current.size === 0) setConnected.current(false)
  }

  const connectPort = async (port, baudRate) => {
    try {
      if (!port.readable) await port.open({ baudRate })
      markOpen(port)
      await readPortLines(
        port,
        (line) => dispatchLine(line, () => onCardRef.current?.(), (amt) => onCashRef.current?.(amt)),
        activeRef,
      )
    } catch (err) {
      console.warn(`[useSerial] 포트 열기 실패 (${baudRate}bps):`, err)
    } finally {
      markClosed(port)
    }
  }

  useEffect(() => {
    if (!enabled || !navigator?.serial) return
    activeRef.current = true

    navigator.serial.getPorts().then(ports => {
      ports.forEach((port, i) => {
        const baud = BAUD_RATES[i] ?? BAUD_RATES[BAUD_RATES.length - 1]
        connectPort(port, baud)
      })
    })

    const handleConnect = (e) => {
      connectPort(e.target, 9600)
    }
    navigator.serial.addEventListener('connect', handleConnect)

    return () => {
      activeRef.current = false
      navigator.serial.removeEventListener('connect', handleConnect)
    }
  }, [enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  const requestPermission = async () => {
    if (!navigator?.serial) {
      alert('이 브라우저는 Web Serial API를 지원하지 않습니다.')
      return
    }
    try {
      const port1 = await navigator.serial.requestPort()
      connectPort(port1, 9600)
      const port2 = await navigator.serial.requestPort()
      connectPort(port2, 115200)
    } catch (err) {
      if (err.name !== 'NotFoundError') console.warn('[useSerial] 포트 선택 취소 또는 오류:', err)
    }
  }

  return { requestPermission, connected }
}
