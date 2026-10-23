import test from 'node:test'
import assert from 'node:assert/strict'
import { gestureTargetFps, confirmGesture, acceptsPalm, cursorHideDelay, pinchReleased } from '../src/utils/gestureScheduling.js'

const state = () => ({ candidate: null, count: 0, since: 0, lastSampleAt: -Infinity, lastFire: -Infinity })

test('slow inference has a bounded cursor grace period', () => {
  assert.equal(cursorHideDelay(60), 350)
  assert.equal(cursorHideDelay(250), 600)
  assert.equal(cursorHideDelay(1000), 800)
})

test('a brief release cannot rearm clicks; sustained separation can', () => {
  const release = { since: null, lastAt: -Infinity }
  assert.equal(pinchReleased(release, 0.6, 0), false)
  assert.equal(pinchReleased(release, 0.3, 70), false)
  assert.equal(pinchReleased(release, 0.6, 140), false)
  assert.equal(pinchReleased(release, 0.6, 280), true)
  assert.equal(pinchReleased(release, 0.6, 700), false)
  assert.equal(pinchReleased(release, NaN, 800), false)
})

test('idle scanning preserves low configured FPS and resumes immediately on detection', () => {
  assert.equal(gestureTargetFps(15, 999, 0), 15)
  assert.equal(gestureTargetFps(15, 1000, 0), 5)
  assert.equal(gestureTargetFps(3, 1000, 0), 3)
  assert.equal(gestureTargetFps(15, 1001, 1000), 15)
})

test('brief pinch is rejected; sustained pinch works at both 15 and 5 FPS', () => {
  const fast = state()
  assert.equal(confirmGesture(fast, 'ok', 0), null)
  assert.equal(confirmGesture(fast, 'ok', 67), null)
  assert.equal(confirmGesture(fast, 'ok', 134), 'ok')
  const slow = state()
  assert.equal(confirmGesture(slow, 'ok', 0), null)
  assert.equal(confirmGesture(slow, 'ok', 200), 'ok')
})

test('lost or interrupted pinch does not combine stale evidence; cooldown prevents double click', () => {
  const s = state()
  confirmGesture(s, 'ok', 0)
  assert.equal(confirmGesture(s, 'ok', 400), null)
  confirmGesture(s, null, 450)
  assert.equal(confirmGesture(s, 'ok', 500), null)
  assert.equal(confirmGesture(s, 'ok', 650), 'ok')
  assert.equal(confirmGesture(s, 'ok', 800), null)
  assert.equal(confirmGesture(s, 'ok', 950), null)
})

test('distant hand must enter above threshold but can remain slightly below it', () => {
  assert.equal(acceptsPalm(0.049, 0.05, false), false)
  assert.equal(acceptsPalm(0.05, 0.05, false), true)
  assert.equal(acceptsPalm(0.045, 0.05, true), true)
  assert.equal(acceptsPalm(0.04, 0.05, true), false)
  assert.equal(acceptsPalm(NaN, 0.05, true), false)
})
