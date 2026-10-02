import test from 'node:test'
import assert from 'node:assert/strict'
import { findMenuOption, normalizeSetOptions } from '../src/services/menuOptions.js'

test('set choices and prices come from available menu options', () => {
  const normalized = normalizeSetOptions([
    { id: 'upgrade', option_group: 'SET_UPGRADE', additional_price: '2500', is_available: true },
    { id: 'side', option_group: 'SET_SIDE', name_ko: '고구마튀김', name_en: 'Sweet potato fries', additional_price: '700', is_available: true },
    { id: 'drink', option_group: 'SET_DRINK', name_ko: '레몬에이드', name_en: 'Lemonade', additional_price: 300, is_available: true },
    { id: 'hidden', option_group: 'SET_SIDE', name_ko: '품절 사이드', additional_price: 0, is_available: false },
  ])

  assert.deepEqual(normalized, {
    setSides: [{ name: '고구마튀김', nameEn: 'Sweet potato fries', extra: 700 }],
    setDrinks: [{ name: '레몬에이드', nameEn: 'Lemonade', extra: 300 }],
    setSurcharge: 2500,
  })
})

test('option lookup accepts localized names and ignores unavailable options', () => {
  const menu = { options: [
    { id: 'exclude', option_group: 'EXCLUDE', name_ko: '양파 제외', name_en: 'No onions', is_available: true },
    { id: 'hidden', option_group: 'SET_SIDE', name_ko: '품절', is_available: false },
  ] }

  assert.equal(findMenuOption(menu, 'EXCLUDE', 'No onions').id, 'exclude')
  assert.equal(findMenuOption(menu, 'SET_SIDE', '품절'), undefined)
})
