import test from 'node:test'
import assert from 'node:assert/strict'
import { clampSpeed, normalizeLimits, resolveSpeed, stepSpeed, SPEED_DEFAULTS } from '../src/utils/ttsSpeed.js'

const L = { min: 0.7, max: 1.5, def: 1.0 }

test('normalizeLimits: 기본값, 범위 보정, 잘못된 값', () => {
  assert.deepEqual(normalizeLimits(null), { min: 0.7, max: 1.5, def: 1.0 })
  assert.deepEqual(normalizeLimits({ default_speed: 1.2, min_speed: 0.6, max_speed: 1.8 }), { min: 0.6, max: 1.8, def: 1.2 })
  // 범위 밖은 백엔드와 같게 자른다
  assert.deepEqual(normalizeLimits({ default_speed: 9, min_speed: 0.1, max_speed: 9 }), { min: 0.5, max: 2.0, def: 2.0 })
  assert.deepEqual(normalizeLimits({ default_speed: 0.01, min_speed: 5, max_speed: 0.2 }), { min: 1.0, max: 1.0, def: 1.0 })
  // 기본은 항상 [최소, 최대] 안
  assert.equal(normalizeLimits({ default_speed: 1.8, min_speed: 0.9, max_speed: 1.3 }).def, 1.3)
  assert.equal(normalizeLimits({ default_speed: 0.6, min_speed: 0.9, max_speed: 1.3 }).def, 0.9)
  for (const bad of ['fast', null, undefined, NaN, Infinity, [], {}, true]) {
    assert.deepEqual(normalizeLimits({ default_speed: bad, min_speed: bad, max_speed: bad }), { min: SPEED_DEFAULTS.min_speed, max: SPEED_DEFAULTS.max_speed, def: SPEED_DEFAULTS.default_speed }, String(bad))
  }
  assert.equal(normalizeLimits({ default_speed: '1.234' }).def, 1.23)
})

test('resolveSpeed: 고른 적 없으면 기본, 고른 값은 범위 안으로', () => {
  assert.equal(resolveSpeed(null, L), 1.0)
  assert.equal(resolveSpeed(undefined, L), 1.0)
  assert.equal(resolveSpeed('abc', L), 1.0)
  assert.equal(resolveSpeed('1.3', L), 1.3)
  assert.equal(resolveSpeed(0.2, L), 0.7)      // 설정이 바뀌어 범위를 벗어난 값은 즉시 보정
  assert.equal(resolveSpeed(3, L), 1.5)
  assert.equal(resolveSpeed(0, L), 0.7)        // 0은 "고르지 않음"이 아니라 너무 느린 값이다
})

test('stepSpeed: 0.1 단위, 부동소수점 오차 없음, 한계에서 멈춤', () => {
  assert.equal(stepSpeed(1.0, +1, L), 1.1)
  assert.equal(stepSpeed(1.1, +1, L), 1.2)    // 1.1 + 0.1 = 1.2000000000000002 가 아니다
  assert.equal(stepSpeed(0.8, -1, L), 0.7)
  assert.equal(stepSpeed(0.7, -1, L), 0.7)
  assert.equal(stepSpeed(1.5, +1, L), 1.5)
  // 눈금 밖 한계(1.35)에도 닿는다
  const odd = { min: 0.75, max: 1.35, def: 1.0 }
  assert.equal(stepSpeed(1.3, +1, odd), 1.35)
  assert.equal(stepSpeed(1.35, +1, odd), 1.35)
  assert.equal(stepSpeed(0.8, -1, odd), 0.75)
  // 한 칸씩 끝까지 가면 정확히 끝값
  let v = L.min
  for (let i = 0; i < 20; i++) v = stepSpeed(v, +1, L)
  assert.equal(v, 1.5)
})

test('clampSpeed', () => {
  assert.equal(clampSpeed(5, 0.5, 2), 2)
  assert.equal(clampSpeed(0, 0.5, 2), 0.5)
  assert.equal(clampSpeed(1, 0.5, 2), 1)
})
