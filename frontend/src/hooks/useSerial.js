import { useEffect, useRef, useState } from 'react'

// 프로토콜은 두 스케치 공통 — ASCII 한 줄, 줄 끝 \r\n.
//   cash_sorter(지폐, 9600)  : RESET COMPLETE / INPUT=CARD / INPUT=<n>WON / INPUT=UNKNOWN / INPUT=RETRY
//   money_sorter(동전,115200): RESET COMPLETE / INPUT=CARD / INPUT=<n>WON / TOTAL:<n> / 구분선
const WON_LINE = /^INPUT=(\d+)WON$/

// 지폐 보드 9600, 동전 보드 115200. 어느 USB 포트에 어느 보드가 붙을지는 고정이 아니다 —
// getPorts()는 권한 부여 순서를 돌려줄 뿐이므로 순서로 배정하면 틀린다.
// 순서는 첫 추측으로만 쓰고, 깨진 바이트가 계속 오면 다음 후보로 스스로 전환한다.
const BAUD_RATES = [9600, 115200]

// 아두이노는 포트를 열 때 DTR로 리셋된다. 그 순간의 선로 노이즈를 보드레이트 불일치로
// 오판하면 멀쩡한 설정을 버리게 되므로 판정에서 뺀다. 다만 너무 길게 잡으면 안 된다 —
// 부팅이 끝나면 보드가 RESET COMPLETE를 보내는데, 보드레이트가 틀렸다면 그게 깨져서
// 들어오는 게 가장 확실한 불일치 증거다. DTR 펄스만 건너뛸 만큼만 준다.
const RESET_SETTLE_MS = 800

// 보드레이트가 틀리면 프레이밍이 깨져 비출력 바이트가 섞여 들어온다.
// 프로토콜이 순수 ASCII라 U+FFFD(디코딩 실패)는 곧 잘못된 바이트라는 뜻이다.
// 실제로는 "��" 같은 두세 글자짜리 청크로 들어오므로 비율이 아니라 개수로 센다.
function looksLikeGarbage(s) {
  if (!s) return false
  let bad = 0
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i)
    if (c === 0xFFFD) { bad += 2; continue }        // 디코딩 실패 — 확실한 증거
    if (c === 9 || c === 10 || c === 13) continue   // 탭/개행
    if (c >= 32 && c < 127) continue                // 일반 출력 문자
    bad++
  }
  return bad >= 2
}

// 반환: 'garbage' = 보드레이트 불일치로 판단, 'ended' = 그 외 종료
async function readPortLines(port, onLine, activeRef, label) {
  const decoder = new TextDecoder()
  let buffer = ''
  let rawLogged = 0
  let badRuns = 0
  let confirmed = false
  const openedAt = performance.now()
  while (activeRef.current) {
    let reader = null
    try {
      reader = port.readable.getReader()
      while (activeRef.current) {
        const { value, done } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        // 보드레이트가 틀리면 개행이 안 나와 onLine이 영영 안 불린다.
        // 원시 청크를 찍어 "데이터 없음"과 "데이터는 오는데 깨짐"을 구분한다.
        if (rawLogged < 10) {
          rawLogged++
          console.log(`[Serial:${label}] raw`, JSON.stringify(chunk.slice(0, 80)))
        }
        // 리셋 직후 노이즈는 제외하고, 노이즈 한 번에 바꾸지 않도록 연속 2회를 본다.
        const settled = performance.now() - openedAt >= RESET_SETTLE_MS
        if (looksLikeGarbage(chunk)) {
          if (settled && ++badRuns >= 2) {
            console.warn(`[Serial:${label}] 깨진 바이트 연속 수신 — 보드레이트 불일치로 판단`)
            return 'garbage'
          }
        } else {
          badRuns = 0
        }
        buffer += chunk
        let nl
        while ((nl = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, nl).replace(/\r$/, '').trim()
          buffer = buffer.slice(nl + 1)
          if (!line) continue
          if (!confirmed) {
            confirmed = true
            console.info(`[Serial] ${label} 확정 — 정상 라인 수신`)
          }
          onLine(line)
        }
      }
    } catch (err) {
      if (!activeRef.current) break
      console.warn(`[Serial:${label}] 읽기 오류, 2초 후 재시도:`, err?.message ?? err)
    } finally {
      try { reader?.releaseLock() } catch {}
    }
    if (activeRef.current) await new Promise(r => setTimeout(r, 2000))
  }
  return 'ended'
}

function dispatchLine(line, onCard, onCash) {
  console.log('[Serial] received:', JSON.stringify(line))

  if (line === 'INPUT=CARD') { onCard?.(); return }

  // 금액은 정규식으로 받는다 — 두 보드의 모든 권종(10~50000)을 한 줄로 처리한다.
  const won = WON_LINE.exec(line)
  if (won) { onCash?.(Number(won[1])); return }

  if (line === 'INPUT=UNKNOWN')  { console.warn('[Serial] 지폐 인식 실패 — 재투입 필요'); return }
  if (line === 'INPUT=RETRY')    { console.warn('[Serial] 지폐 판별 경계 — 재투입 필요'); return }
  if (line === 'RESET COMPLETE') { console.info('[Serial] 장치 초기화 완료'); return }

  // TOTAL:은 동전 보드가 자체 누적한 금액이다. 프론트는 INPUT=*WON을 직접 합산하므로
  // 같이 반영하면 이중 계산이 된다. 구분선과 함께 무시한다.
  if (line.startsWith('TOTAL:') || /^-+$/.test(line)) return

  console.warn('[Serial] 처리하지 않는 라인:', JSON.stringify(line))
}

/**
 * Arduino 시리얼 입력 훅.
 * - 최초 1회: requestPermission()을 사용자 제스처(버튼 클릭 등)로 호출해 포트 권한 부여
 * - 이후 자동: getPorts()로 기허가 포트에 재연결
 *
 * @param {() => void}          opts.onCard  INPUT=CARD 수신 시 호출
 * @param {(n: number) => void} opts.onCash  INPUT=*WON 수신 시 금액과 함께 호출
 * @param {boolean}             opts.enabled
 * @returns {{ requestPermission: () => Promise<void>, connected: boolean, portCount: number }}
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
  const [portCount, setPortCount] = useState(0)
  const syncCount = useRef(null)
  syncCount.current = setPortCount

  const markOpen = (port) => {
    openPorts.current.add(port)
    syncCount.current(openPorts.current.size)
  }
  const markClosed = (port) => {
    openPorts.current.delete(port)
    syncCount.current(openPorts.current.size)
  }
  const connected = portCount > 0

  const connectPort = async (port, preferredBaud) => {
    // StrictMode 이중 마운트나 requestPermission 재호출로 같은 포트를 동시에 열면
    // 두 번째 open()이 InvalidStateError로 실패하고, 그 finally가 실제로 열려 있는
    // 포트를 목록에서 지워 연결 상태가 OFF로 잘못 표시된다.
    if (handlingRef.current.has(port)) return
    handlingRef.current.add(port)

    const info = port.getInfo?.() ?? {}
    const id = `${info.usbVendorId?.toString(16) ?? '?'}:${info.usbProductId?.toString(16) ?? '?'}`
    // 확정된 값 > 호출자 추측 > 나머지 후보 순으로 시도
    const first = portBauds.current.get(port) ?? preferredBaud
    const order = first ? [first, ...BAUD_RATES.filter(b => b !== first)] : [...BAUD_RATES]

    try {
      for (const baudRate of order) {
        if (!activeRef.current) return
        const label = `${id}@${baudRate}`
        try {
          if (!port.readable) await port.open({ baudRate })
        } catch (err) {
          console.warn(`[useSerial] 포트 열기 실패 ${label} — ${err?.name}: ${err?.message}`)
          return
        }
        console.log(`[Serial] 포트 열림 ${label}`)
        portBauds.current.set(port, baudRate)
        markOpen(port)

        const verdict = await readPortLines(
          port,
          (line) => dispatchLine(line, () => onCardRef.current?.(), (amt) => onCashRef.current?.(amt)),
          activeRef,
          label,
        )
        markClosed(port)
        if (verdict !== 'garbage') return

        try { await port.close() } catch {}
        console.warn(`[Serial] ${id}: 다른 보드레이트로 재시도`)
      }
      console.warn(`[Serial] ${id}: 후보 보드레이트를 모두 시도했지만 정상 수신 없음`)
    } finally {
      handlingRef.current.delete(port)
      markClosed(port)
    }
  }

  useEffect(() => {
    if (!enabled || !navigator?.serial) return
    activeRef.current = true

    navigator.serial.getPorts().then(ports => {
      ports.forEach((port, i) => connectPort(port, BAUD_RATES[i]))
    })

    const handleConnect = (e) => connectPort(e.target, portBauds.current.get(e.target))
    navigator.serial.addEventListener('connect', handleConnect)

    return () => {
      activeRef.current = false
      navigator.serial.removeEventListener('connect', handleConnect)
    }
  }, [enabled]) // eslint-disable-line react-hooks/exhaustive-deps

  // requestPort()는 사용자 제스처를 소비한다. 한 번의 클릭에서 두 번 호출하면
  // 두 번째가 SecurityError("Must be handling a user gesture")로 반드시 실패해
  // 장치가 하나만 등록된다. 그래서 클릭당 한 포트씩만 추가한다.
  const requestPermission = async () => {
    if (!navigator?.serial) {
      alert('이 브라우저는 Web Serial API를 지원하지 않습니다.')
      return
    }
    try {
      const port = await navigator.serial.requestPort()
      connectPort(port)
    } catch (err) {
      if (err.name !== 'NotFoundError') console.warn('[useSerial] 포트 선택 취소 또는 오류:', err)
    }
  }

  return { requestPermission, connected, portCount }
}
