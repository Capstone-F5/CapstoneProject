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

import { writeFileSync, mkdirSync, existsSync } from 'fs'
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
  // 잘 못 알아들었을 때의 고정 응답(backend/ai_modules/llm/guards.py의 NOISE_REPLY["ko"]와 같은 문장이어야 한다)
  'not_heard.mp3':          '잘 못 들었어요. 다시 한번 말씀해 주세요.',
  // 접근 감지(휠체어) 안내 — App.jsx handleApproachModeAction과 같은 문장. 대상을 지칭하지 않고 기능만 알린다.
  'approach_wheelchair.mp3': '손동작으로도 메뉴를 선택하실 수 있습니다.',
}

// 주문번호 낭독용 조각 — 번호를 말할 때마다 API로 합성하지 않고 이 조각을 이어 붙인다(src/utils/numberSpeech.js).
// 1~999번을 "주문번호는" + [백] + [십] + [일의 자리] + "번입니다"로 조합하므로 숫자 9개와 십·백, 앞뒤 문구 14개면 된다.
// 파일 이름은 numberSpeech.js의 CLIP_FILES와 짝을 맞춰야 한다.
const NUMBER_PHRASES = {
  'prefix.mp3': '주문번호는',
  'n1.mp3': '일', 'n2.mp3': '이', 'n3.mp3': '삼', 'n4.mp3': '사', 'n5.mp3': '오',
  'n6.mp3': '육', 'n7.mp3': '칠', 'n8.mp3': '팔', 'n9.mp3': '구',
  'ten.mp3': '십', 'hundred.mp3': '백',
  'suffix.mp3': '번입니다',
}
const NUMBER_DIR = join(__dirname, '../public/audio/numbers')

async function generate(phrases, dir) {
  mkdirSync(dir, { recursive: true })
  for (const [filename, text] of Object.entries(phrases)) {
    const outPath = join(dir, filename)
    // 이미 있는 파일은 다시 합성하지 않는다(비용 절약, 목소리 일관성). 전부 다시 만들려면 --force
    if (!process.argv.includes('--force') && existsSync(outPath)) {
      console.log(`- ${filename} (이미 있음, 건너뜀)`)
      continue
    }
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
}

await generate(PHRASES, OUTPUT_DIR)
await generate(NUMBER_PHRASES, NUMBER_DIR)   // 주문번호 낭독 조각

console.log(`
완료. 파일 위치: ${OUTPUT_DIR}, ${NUMBER_DIR}`)
