/**
 * 초경량 배경 변화(모션) 감지기 (Motion Gate / Frame Differencing)
 *
 * 매장 내 형광등/LED 조명 점멸(50/60Hz 플리커)이나 카메라 자동 노출(AE) 흔들림으로 인한
 * 가짜 모션(오탐)을 제거하기 위해 다음 기법을 적용합니다:
 * 1. 32x24 초소형 다운샘플링 (768 픽셀) -> GPU Bilinear 축소로 고주파 센서 노이즈 자동 제거 (연산 0.2ms 미만)
 * 2. 전역 밝기 편차(Global Luma Drift Δμ) 상쇄 -> 조명 점멸/노출 변화로 전체가 일괄 변한 값 무효화
 * 3. 색채(Chroma) 및 조명 보정 명도(Compensated Luma) 복합 차분
 * 4. 킵얼라이브(Keep-Alive) 하트비트 -> 완전 정지 고객 유실 방지 및 세션 유지
 */

const DEFAULT_W = 32
const DEFAULT_H = 24

export class MotionDetector {
  constructor(options = {}) {
    this.width = options.width || DEFAULT_W
    this.height = options.height || DEFAULT_H
    this.pixelThreshold = options.pixelThreshold || 20 // 0~255 기준 개별 픽셀 유효 변화량
    this.motionThreshold = options.motionThreshold ?? 0.025 // 활성 픽셀 비율 (기본 2.5%)
    this.keepaliveMs = options.keepaliveMs || 4000 // 정적 대기 시 하트비트 전송 주기 (기본 4초)
    this.enabled = options.enabled ?? true

    this.canvas = document.createElement('canvas')
    this.canvas.width = this.width
    this.canvas.height = this.height
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true })

    this.prevPixels = null
    this.lastSentTime = 0
    this.lastActiveRatio = 0
  }

  /**
   * 카메라 비디오 엘리먼트로부터 프레임을 추출하여 모션 여부 및 전송 결정을 반환.
   *
   * @param {HTMLVideoElement} video
   * @param {object} overrides - 런타임 동적 설정
   * @returns {{
   *   shouldSend: boolean,
   *   hasMotion: boolean,
   *   isHeartbeat: boolean,
   *   activeRatio: number,
   *   motionLevel: number,
   * }}
   */
  evaluate(video, overrides = {}) {
    const isEnabled = overrides.enabled ?? this.enabled
    const motionThresh = overrides.motionThreshold ?? this.motionThreshold
    const keepalive = overrides.keepaliveMs ?? this.keepaliveMs
    const pixelThresh = overrides.pixelThreshold ?? this.pixelThreshold
    const isModeOn = Boolean(overrides.modeOn)
    const now = performance.now()

    // 1. 모션 게이트가 비활성화되었거나 이미 안내가 활성화된 상태라면 무조건 전송
    if (!isEnabled || isModeOn) {
      this.lastSentTime = now
      return {
        shouldSend: true,
        hasMotion: true,
        isHeartbeat: false,
        activeRatio: this.lastActiveRatio || motionThresh,
        motionLevel: 1.0,
      }
    }

    if (!video || video.readyState < 2) {
      return {
        shouldSend: false,
        hasMotion: false,
        isHeartbeat: false,
        activeRatio: 0,
        motionLevel: 0,
      }
    }

    // 2. 32x24 다운스케일 렌더링
    this.ctx.drawImage(video, 0, 0, this.width, this.height)
    let frame
    try {
      frame = this.ctx.getImageData(0, 0, this.width, this.height).data
    } catch {
      return {
        shouldSend: true,
        hasMotion: true,
        isHeartbeat: false,
        activeRatio: motionThresh,
        motionLevel: 1.0,
      }
    }

    const totalPixels = this.width * this.height

    // 3. 첫 프레임 초기화
    if (!this.prevPixels || this.prevPixels.length !== frame.length) {
      this.prevPixels = new Uint8ClampedArray(frame)
      this.lastSentTime = now
      return {
        shouldSend: true,
        hasMotion: true,
        isHeartbeat: false,
        activeRatio: motionThresh,
        motionLevel: 0.5,
      }
    }

    const curr = frame
    const prev = this.prevPixels

    // 4. 1차 패스: 전역 평균 휘도(Global Mean Luma) 계산 -> 조명 플리커/AE 편차 산출
    let currLumaSum = 0
    let prevLumaSum = 0
    for (let i = 0; i < curr.length; i += 4) {
      currLumaSum += (curr[i] * 77 + curr[i + 1] * 150 + curr[i + 2] * 29) >> 8
      prevLumaSum += (prev[i] * 77 + prev[i + 1] * 150 + prev[i + 2] * 29) >> 8
    }
    const globalOffset = (currLumaSum - prevLumaSum) / totalPixels

    // 5. 2차 패스: 조명 보정 픽셀 차분 및 모션 픽셀 집계
    let activePixels = 0
    let totalDelta = 0

    for (let i = 0; i < curr.length; i += 4) {
      const r1 = prev[i]
      const g1 = prev[i + 1]
      const b1 = prev[i + 2]

      const r2 = curr[i]
      const g2 = curr[i + 1]
      const b2 = curr[i + 2]

      const y1 = (r1 * 77 + g1 * 150 + b1 * 29) >> 8
      const y2 = (r2 * 77 + g2 * 150 + b2 * 29) >> 8

      // 전체 조명 편차를 제거한 순수 국소 휘도 변화량
      const compYDiff = Math.abs((y2 - y1) - globalOffset)

      // 순수 색채(Chroma) 변화량: (R-Y), (B-Y) 색차 벡터 거리 근사
      const cr1 = r1 - y1
      const cb1 = b1 - y1
      const cr2 = r2 - y2
      const cb2 = b2 - y2
      const chromaDiff = (Math.abs(cr2 - cr1) + Math.abs(cb2 - cb1)) * 0.5

      // 최종 복합 차분 지수 (국소 휘도 45% + 색채 55%)
      const pixelDiff = compYDiff * 0.45 + chromaDiff * 0.55
      totalDelta += pixelDiff

      if (pixelDiff >= pixelThresh) {
        activePixels++
      }
    }

    // 다음 비교를 위해 현재 프레임 복사
    this.prevPixels.set(curr)

    const activeRatio = activePixels / totalPixels
    this.lastActiveRatio = Number(activeRatio.toFixed(4))
    const hasMotion = activeRatio >= motionThresh

    // 6. 킵얼라이브(Keep-Alive) 하트비트 판정
    const elapsedSinceLastSend = now - this.lastSentTime
    const isHeartbeat = !hasMotion && elapsedSinceLastSend >= keepalive

    const shouldSend = hasMotion || isHeartbeat

    if (shouldSend) {
      this.lastSentTime = now
    }

    // 모션 게이지 시각화용 레벨 (0.0 ~ 1.0)
    const motionLevel = Math.min(1.0, activeRatio / (motionThresh * 2.5))

    return {
      shouldSend,
      hasMotion,
      isHeartbeat,
      activeRatio: this.lastActiveRatio,
      motionLevel: Number(motionLevel.toFixed(3)),
    }
  }

  reset() {
    this.prevPixels = null
    this.lastSentTime = 0
    this.lastActiveRatio = 0
  }
}
