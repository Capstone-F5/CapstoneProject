import { createContext, useContext } from 'react'

// 기본값 true — Provider로 안 감싸진 곳에서 실수로 쓰여도 배지가 사라지지 않도록 안전하게 처리
const GestureUIContext = createContext(true)

export function GestureUIProvider({ enabled, children }) {
  return (
    <GestureUIContext.Provider value={enabled}>
      {children}
    </GestureUIContext.Provider>
  )
}

// HandBadge 등에서 "지금 제스처 켜져 있는지"만 간단히 읽어오는 훅
export function useGestureUIEnabled() {
  return useContext(GestureUIContext)
}
