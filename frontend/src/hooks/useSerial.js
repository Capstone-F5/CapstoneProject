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

async function readPortLines(port, onLine, activeRef, label) {
  const decoder = new TextDecoder()
  let buffer = ''
  let rawLogged = 0
  while (activeRef.current) {
    let reader = null
    try {
      reader = port.readable.getReader()
      while (activeRef.current) {
        const { value, done } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        // 보드레이트가 틀리면 깨진 바이트만 들어오고 개행이 없어 onLine이 영영 안 불린다.
        // 원시 청크를 앞부분만 찍어 "데이터 없음"과 "데이터는 오는데 깨짐"을 구분한다.
        if (rawLogged < 10) {
          rawLogged++
          console.log(`[Serial:${label}] raw`, JSON.stringify(chunk.slice(0, 80)))
        }
        buffer += chunk
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
  console.log('[Serial] received:', JSON.stringify(line))
  if (line === 'INPUT=CARD') {
    onCard?.()
    return
  }
  if (line.startsWith('INPUT=')) {
    const key = line.slice(6)
    const amount = CASH_MAP[key]
    if (amount != null) {
      onCash?.(amount)
    } else {
      console.warn('[Serial] 알 수 없는 INPUT 키:', key, '— CASH_MAP:', Object.keys(CASH_MAP).join(', '))
    }
  }
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
  const portBauds    = useRef(new Map())
  const handlingRef  = useRef(new Set())
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
    // StrictMode 이중 마운트나 requestPermission 재호출로 같은 포트를 동시에 열면
    // 두 번째 open()이 InvalidStateError로 실패하고, 그 finally가 실제로 열려 있는
    // 포트를 목록에서 지워 연결 상태가 OFF로 잘못 표시된다.
    if (handlingRef.current.has(port)) return
    handlingRef.current.add(port)
    portBauds.current.set(port, baudRate)
    // getPorts() 순서로 보드레이트를 배정하므로, 어느 장치가 어느 속도로 열렸는지
    // USB vid/pid를 남겨야 매핑이 뒤바뀐 경우를 판별할 수 있다.
    const info = port.getInfo?.() ?? {}
    const label = `${info.usbVendorId?.toString(16) ?? '?'}:${info.usbProductId?.toString(16) ?? '?'}@${baudRate}`
    try {
      if (!port.readable) await port.open({ baudRate })
      console.log(`[Serial] 포트 열림 ${label}`)
      markOpen(port)
      await readPortLines(
        port,
        (line) => dispatchLine(line, () => onCardRef.current?.(), (amt) => onCashRef.current?.(amt)),
        activeRef,
        label,
      )
    } catch (err) {
      console.warn(`[useSerial] 포트 열기 실패 ${label} — ${err?.name}: ${err?.message}`)
    } finally {
      handlingRef.current.delete(port)
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
      const baud = portBauds.current.get(e.target) ?? 9600
      connectPort(e.target, baud)
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
