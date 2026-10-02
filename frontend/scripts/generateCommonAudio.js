/**
 * 자주 사용되는 TTS 문구를 미리 생성해 public/audio/common/ 에 저장한다.
 * 백엔드가 실행 중인 상태에서 한 번만 돌리면 된다.
 *
 * 사용법:
 *   node scripts/generateCommonAudio.js
 *
 * 환경변수:
 *   TTS_API  — TTS 엔드포인트 (기본값: http://localhost:8000/ai_modules/tts)
 */

import { writeFileSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUTPUT_DIR = join(__dirname, '../public/audio/common')
const TTS_API = process.env.TTS_API ?? 'http://localhost:8000/ai_modules/tts'

const PHRASES = {
  'cart_added.mp3':        '장바구니에 담았습니다.',
  'order_complete.mp3':    '주문이 완료되었습니다.',
  'payment_complete.mp3':  '결제가 완료되었습니다.',
  'yes_understood.mp3':    '네, 알겠습니다.',
  'sorry_not_understood.mp3': '죄송합니다, 잘 이해하지 못했습니다.',
  'anything_else.mp3':     '다른 도움이 필요하신가요?',
  'select_menu.mp3':       '메뉴를 선택해 주세요.',
  'say_quantity.mp3':      '수량을 말씀해 주세요.',
  // 터치 플로우 내레이션 — ttsCache.js의 COMMON_PHRASES와 짝을 맞춰야 한다.
  // 여기에 빠지면 파일이 생성되지 않아 해당 문구만 무음이 된다.
  'select_order_type.mp3':  '식사하실 장소를 선택해 주세요.',
  'select_menu_order.mp3':  '주문하실 메뉴를 선택해 주세요.',
  'confirm_order_type.mp3': '식사 장소를 확인해 주세요.',
  'ask_points.mp3':         '포인트를 적립하시겠습니까?',
  'select_payment.mp3':     '결제 수단을 선택해 주세요.',
}

mkdirSync(OUTPUT_DIR, { recursive: true })

for (const [filename, text] of Object.entries(PHRASES)) {
  const outPath = join(OUTPUT_DIR, filename)
  try {
    const res = await fetch(TTS_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, format: 'mp3', language: 'ko' }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const buf = Buffer.from(await res.arrayBuffer())
    writeFileSync(outPath, buf)
    console.log(`✓ ${filename} (${buf.length} bytes)`)
  } catch (e) {
    console.error(`✗ ${filename}: ${e.message}`)
  }
}

console.log(`\n완료. 파일 위치: ${OUTPUT_DIR}`)
