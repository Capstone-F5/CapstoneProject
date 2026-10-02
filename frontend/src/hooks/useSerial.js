import { useEffect, useRef, useState } from 'react'

// 프로토콜은 두 스케치 공통 — ASCII 한 줄, 줄 끝 \r\n.
//   cash_sorter(지폐, 9600)  : RESET COMPLETE / INPUT=CARD / INPUT=<n>WON / INPUT=UNKNOWN / INPUT=RETRY
//   money_sorter(동전,115200): RESET COMPLETE / INPUT=CARD / INPUT=<n>WON / TOTAL:<n> / 구분선
const WON_LINE = /^INPUT=(\d+)WON$/

// 지폐 보드 9600, 동전 보드 115200. 어느 USB 포트에 어느 보드가 붙을지는 고정이 아니다 —
// getPorts()는 권한 부여 순서를 돌려줄 뿐이므로 순서로 배정하면 틀린다.
// 순서는 첫 추측으로만 쓰고, 깨진 바이트가 계속 오면 다음 후보로 스스로 전환한다.
const BAUD_RATES = [9600, 115200]

// 보레이트를 처음 추측할 때 쓰는 기본값 — 현재 구성: Arduino Uno(0x2341)=지폐 9600, CH340(0x1a86)=동전 115200.
// getPorts() 순서는 재부팅·재연결 때마다 바뀔 수 있어 순서로 추측하면 두 보드의 보레이트가 뒤바뀐다.
// (틀린 보레이트로 열면 프레이밍 오류로 Chromium이 "The device has been lost."를 내며 읽기가 끊긴다.)
// 보드가 바뀌어도 한 번 정상 수신한 값은 localStorage에 기억해 다음부터 우선한다.
const DEFAULT_BAUD_BY_VID = { 0x2341: 9600, 0x1a86: 115200 }
const baudKey = (id) => `serialBaud:${id}`
const loadBaud = (id) => {
  const n = Number(localStorage.getItem(baudKey(id)))
  return BAUD_RATES.includes(n) ? n : null
}

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
async function readPortLines(port, onLine, activeRef, label, onConfirmed) {
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
            onConfirmed?.()
          }
          onLine(line)
        }
      }
    } catch (err) {
      if (!activeRef.current) break
      // 치명적 오류(보드 리셋·USB 순간 끊김·전원 흔들림 등)가 나면 port.readable이 null이 되어
      // 같은 포트에서는 reader를 다시 만들 수 없다("Cannot read properties of null (reading 'getReader')").
      // 2초마다 재시도해 봐야 같은 오류만 반복되므로, 호출자에게 알려 포트를 닫았다 다시 열게 한다.
      if (!port.readable) {
        console.warn(`[Serial:${label}] 포트를 읽을 수 없는 상태 — 포트를 다시 엽니다 (${err?.name}: ${err?.message})`)
        return 'unreadable'
      }
      console.warn(`[Serial:${label}] 읽기 오류, 2초 후 재시도:`, err?.message ?? err)
    } finally {
      try { reader?.releaseLock() } catch {}
    }
    if (activeRef.current) await new Promise(r => setTimeout(r, 2000))
  }
  return 'ended'
}

// 포트를 읽을 수 없게 됐을 때 닫았다 다시 여는 최대 횟수와 대기 시간(점점 늘어남, 상한 8초)
const MAX_REOPEN = 20
const reopenDelay = (attempt) => Math.min(1000 * 2 ** attempt, 8000)

function dispatchLine(line, onCard, onCash, onSignal) {
  console.log('[Serial] received:', JSON.stringify(line))

  if (line === 'INPUT=CARD') { onCard?.(); return }

  // 금액은 정규식으로 받는다 — 두 보드의 모든 권종(10~50000)을 한 줄로 처리한다.
  const won = WON_LINE.exec(line)
  if (won) { onCash?.(Number(won[1])); return }

  if (line === 'INPUT=UNKNOWN')  { console.warn('[Serial] 지폐 인식 실패 — 재투입 필요'); onSignal?.(line); return }
  if (line === 'INPUT=RETRY')    { console.warn('[Serial] 지폐 판별 경계 — 재투입 필요'); onSignal?.(line); return }
  if (line === 'RESET COMPLETE') { console.info('[Serial] 장치 초기화 완료'); return }

  // TOTAL:은 동전 보드가 자체 누적한 금액이다. 프론트는 INPUT=*WON을 직접 합산하므로
  // 같이 반영하면 이중 계산이 된다. 구분선과 함께 무시한다.
  // (금액 합산에는 쓰지 않지만, 카드 팝업이 열려 있을 때의 '신호 있음' 알림으로는 쓴다)
  if (/^total\s*[:=]/i.test(line)) { onSignal?.(line); return }   // 대소문자·공백 차이가 있어도 인식
  if (/^-+$/.test(line)) return

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
export function useSerial({ onCard, onCash, onSignal, enabled = true } = {}) {
  const onCardRef = useRef(onCard)
  const onCashRef = useRef(onCash)
  const onSignalRef = useRef(onSignal)   // TOTAL·INPUT=UNKNOWN/RETRY 같은 '금액이 아닌 신호'
  useEffect(() => { onCardRef.current = onCard }, [onCard])
  useEffect(() => { onCashRef.current = onCash }, [onCash])
  useEffect(() => { onSignalRef.current = onSignal }, [onSignal])

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

  const connectPort = async (port, preferredBaud, reopenAttempt = 0) => {
    // StrictMode 이중 마운트나 requestPermission 재호출로 같은 포트를 동시에 열면
    // 두 번째 open()이 InvalidStateError로 실패하고, 그 finally가 실제로 열려 있는
    // 포트를 목록에서 지워 연결 상태가 OFF로 잘못 표시된다.
    if (handlingRef.current.has(port)) return
    handlingRef.current.add(port)

    const info = port.getInfo?.() ?? {}
    const id = `${info.usbVendorId?.toString(16) ?? '?'}:${info.usbProductId?.toString(16) ?? '?'}`
    // 이번 실행에서 확정된 값 > 이전에 기억한 값 > 장치(VID) 기본값 > 호출자 추측 순으로 시도
    const first = portBauds.current.get(port) ?? loadBaud(id) ??
      DEFAULT_BAUD_BY_VID[info.usbVendorId] ?? preferredBaud
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
        const sessionStartedAt = Date.now()
        let confirmedOnce = false

        let verdict = await readPortLines(
          port,
          (line) => dispatchLine(line, () => onCardRef.current?.(), (amt) => onCashRef.current?.(amt), (l) => onSignalRef.current?.(l)),
          activeRef,
          label,
          () => { confirmedOnce = true; localStorage.setItem(baudKey(id), String(baudRate)) },
        )
        markClosed(port)

        // 정상 라인을 한 번도 받기 전, 열린 지 몇 초 안에 장치가 "사라졌다"면 장치 문제가 아니라
        // 보레이트 불일치로 인한 프레이밍 오류일 가능성이 높다 → 같은 속도로 다시 열지 말고 다른 속도를 시도한다.
        if (verdict === 'unreadable' && !confirmedOnce && Date.now() - sessionStartedAt < 8000) {
          console.warn(`[Serial] ${label}: 정상 수신 전에 연결이 끊김 — 보레이트 불일치로 보고 다른 속도를 시도합니다`)
          verdict = 'garbage'
        }

        if (verdict === 'unreadable') {
          // 포트를 닫고 잠시 뒤 같은 보드레이트로 다시 연다. 재연결 중 가드가 막지 않도록 먼저 풀고,
          // await로 기다려 이 호출의 finally가 새 연결의 열림 표시를 지우지 않게 한다.
          try { await port.close() } catch {}
          if (!activeRef.current || reopenAttempt >= MAX_REOPEN) {
            console.warn(`[Serial] ${id}: 다시 열기를 포기했습니다 (시도 ${reopenAttempt}회)`)
            return
          }
          await new Promise(r => setTimeout(r, reopenDelay(reopenAttempt)))
          if (!activeRef.current) return
          handlingRef.current.delete(port)
          // 30초 넘게 정상 동작했다면 일시적인 끊김으로 보고 재시도 횟수를 처음부터 센다
          const nextAttempt = Date.now() - sessionStartedAt > 30000 ? 0 : reopenAttempt + 1
          return await connectPort(port, baudRate, nextAttempt)
        }

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
